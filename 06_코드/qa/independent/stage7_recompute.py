# -*- coding: utf-8 -*-
"""7단계 독립 재산출 — 2026-07-30 의결 규칙 적용

의결 내용 (2026-07-30, 파일럿 범위 한정)
  ① 환율 적용시점   평가일 당일 ECOS 환율. 지수와 미국 BM 에 동일 적용.
                    ECOS 계열코드·공표 이용시각의 공식성은 별도 확인 전까지 PROVISIONAL.
  ② 산출일          COMMON_OPEN_DAYS_PILOT — 한·미 공통 개장일.
                    합집합 달력·휴장시장 가격이월의 production 적용은 후속 적용시험으로 분리.
  ③ 연결 방식       CHAIN_REBASE_PILOT — 연결계수 체인.
                    production 승격은 effective_date 규칙·정기변경 전후 연결산식·
                    실제 회차 시험·독립 QA 완료 후 별도 승인.
  ④ 기업행사        파일럿 사건 판정 — 010120 액면가 기준 5:1, 경계일 신주권상장일 2026-04-13.
                    일반 규칙 승격은 추가 표본 검토 후.

의결이 실증한 것과 실증하지 않은 것 — 섞으면 안 된다
  ③은 이번 파일럿에 정기변경 적용일이 없어 두 방식이 같은 값을 냈다. 이것은
  연결계수의 정확성을 실증한 것이 아니라 **차이가 발동되지 않았다**는 뜻이다.
  따라서 산출물에 CHAIN_REBASE_PILOT 로 기록하되 검증 상태는 NOT_EXERCISED 다.

독립성
  가중치는 engine 산출물이 아니라 내 6단계 독립 재산출분을 쓴다.
  engine 모듈은 import 하지 않는다. 계산 커널은 stage7_sensitivity 와 공유해
  같은 수식이 두 벌 존재하는 것을 막는다.

허용오차
  RTOL = 1e-12 (상대오차). 부동소수점 한계 수준이라 '완전일치'는 정의상 불가능하므로
  판정 기준을 수치로 고정한다. 근거는 우선결정 ⑪ 보완 2.

실행
  python stage7_recompute.py
"""
import hashlib
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import paths as P                    # noqa: E402
import stage7_sensitivity as K       # noqa: E402  계산 커널 공유

OUT = os.path.join(HERE, "out_stage7")
RTOL = 1e-12

# 의결 규칙명 → 커널 선택지 매핑. 좌변이 결정로그에 남는 이름이다.
DECIDED = {
    "fx_application":  ("FX_SAME_DAY_ECOS_PROVISIONAL", "fx",   "SAME_DAY"),
    "calc_days":       ("COMMON_OPEN_DAYS_PILOT",        "days", "COMMON_OPEN_ONLY"),
    "index_linking":   ("CHAIN_REBASE_PILOT",            "link", "SEGMENT_RELINK"),
    "corporate_action": ("PAR_VALUE_5TO1_LISTING_BOUNDARY_PILOT",
                        "ca", "SPLIT_5_ON_LISTING"),
    "bm_fx_treatment": ("BM_US_SAME_DAY_KRW_CONVERT",    "bmfx", "CONVERT"),
}

# 의결 범위 — 무엇이 확정이고 무엇이 파일럿 한정인지 산출물에 남긴다.
SCOPE = {
    "fx_application":   {"status": "APPROVED_PILOT", "series_officiality": "PROVISIONAL",
                         "note": "ECOS 계열코드·공표 이용시각 별도 확인 전"},
    "calc_days":        {"status": "APPROVED_PILOT", "production": "DEFERRED_TRIAL",
                         "note": "합집합 달력·가격이월은 후속 적용시험으로 분리"},
    "index_linking":    {"status": "APPROVED_PILOT", "verification": "NOT_EXERCISED",
                         "note": "정기변경 적용일이 없어 차이가 발동되지 않았음. 정확성 실증 아님"},
    "corporate_action": {"status": "APPROVED_PILOT_EVENT", "generalization": "PENDING_SAMPLES",
                         "note": "010120 개별 사건 판정. 일반 규칙 승격은 추가 표본 후"},
    "bm_fx_treatment":  {"status": "APPROVED_PILOT",
                         "note": "지수·BM 에 동일 평가일 환율 적용 (B-2 통합)"},
}


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


def cfg_of(ca_option):
    c = {k: v for _, (_, k, v) in DECIDED.items()}
    c["ca"] = ca_option
    return c


def main():
    P.force_utf8_stdout()
    os.makedirs(OUT, exist_ok=True)

    st, fx, cal, bk, bu, w, pub = K.load()
    start, end = pub.market_date.min(), pub.market_date.max()

    print("=" * 66)
    print("7단계 독립 재산출 — 2026-07-30 의결 규칙")
    print("=" * 66)
    for key, (name, ax, opt) in DECIDED.items():
        print(f"  {key:17s} {name}")
    print(f"\n  구간 {start.date()} ~ {end.date()}")
    print(f"  가중 내 6단계 독립분 {len(w)}종목 · {w.weighting_rule_version.iloc[0]}")
    print(f"  가중합 {w.final_target_weight.sum():.12f}\n")

    # ── 1. 구현 검증: 기업행사 미조정 상태로 공표 산출물을 재현하는가 ──
    # 보정본을 믿으려면 보정하지 않은 상태를 먼저 그대로 재현할 수 있어야 한다.
    # 이 대조가 통과해야 아래 보정 결과가 의미를 갖는다.
    asrun = K.run(st, fx, cal, bk, bu, w, start, end, cfg_of("NONE"), pub=pub)
    err = asrun["repro_max_rel_err"]
    ok = err < RTOL
    print("[1] 구현 검증 — 기업행사 미조정분을 공표 산출물과 대조")
    print(f"    최대 상대오차 {err:.3e}  허용오차 {RTOL:.0e}  ->  "
          f"{'일치' if ok else '불일치'}")
    if not ok:
        print("    구현이 공표분을 재현하지 못했다. 보정 결과를 인용하지 말 것.")
        return 1
    print(f"    as-run  지수 {asrun['index_last']:.4f} · BM 대비 {asrun['excess_pp']:+.4f}%p\n")

    # ── 2. 의결 규칙 적용 (기업행사 보정 포함) ────────────────
    fin = K.run(st, fx, cal, bk, bu, w, start, end, cfg_of("SPLIT_5_ON_LISTING"), pub=pub)
    print("[2] 의결 규칙 적용 — 010120 액면가 5:1 · 경계일 2026-04-13")
    print(f"    지수 {fin['index_last']:.4f} ({fin['index_ret_pct']:+.4f}%)")
    print(f"    BM   {fin['bm_last']:.4f} ({fin['bm_ret_pct']:+.4f}%)")
    print(f"    BM 대비 {fin['excess_pp']:+.4f}%p")
    print(f"    보정 효과 {fin['excess_pp'] - asrun['excess_pp']:+.4f}%p\n")

    print("[3] 경로 지표 — 경계일 선택이 레벨로는 안 보이므로 함께 기록한다")
    alt = K.run(st, fx, cal, bk, bu, w, start, end, cfg_of("SPLIT_5_ON_EFFECTIVE"))
    print(f"    {'':22s} {'연변동성':>10s} {'최대낙폭':>10s} {'최저일간':>10s}")
    for lab, r in [("의결 경계일 04-13", fin), ("(참고) 04-10", alt)]:
        print(f"    {lab:22s} {r['ann_vol_pct']:9.4f}% {r['max_drawdown_pct']:9.4f}% "
              f"{r['min_daily_ret_pct']:9.4f}%")
    print(f"    추적오차 {fin['tracking_err_pct']:.4f}%\n")

    # ── 3. 입력 지문·버전 기록 ────────────────────────────────
    inputs = {}
    for f in ["fx.csv", "calendar.csv", "bm_kr.csv", "bm_us.csv"]:
        p = os.path.join(K.INPUT, f)
        if os.path.exists(p):
            inputs[f] = sha16(p)
    for lbl, p in [("daily_market_state.csv",
                    os.path.join(K.PUBLISHED, "daily_market_state.csv")),
                   (f"weights_{K.ROUND}.csv (독립)",
                    os.path.join(K.MINE, f"weights_{K.ROUND}.csv"))]:
        if os.path.exists(p):
            inputs[lbl] = sha16(p)

    meta = {
        "artifact": "qa_stage7_independent_recompute",
        "rule_decision_date": "2026-07-30",
        "scope": "SEED18_LIMITED_PILOT",
        "rules": {k: {"name": n, **SCOPE[k]} for k, (n, _, _) in DECIDED.items()},
        "tolerance_rtol": RTOL,
        "implementation_check": {
            "target": "output_f1/index_vs_benchmark.csv",
            "corporate_action": "NONE",
            "max_rel_err": err,
            "verdict": "MATCH" if ok else "MISMATCH",
        },
        "result_asrun": asrun,
        "result_decided": fin,
        "split_effect_pp": fin["excess_pp"] - asrun["excess_pp"],
        "weights_source": "qa/independent/out (engine 산출물 아님)",
        "engine_import": False,
        "inputs_sha256_16": inputs,
        "performance_status": "PERFORMANCE_NOT_FROZEN",
        "not_frozen_reason": [
            "엔진 정식 재산출 미완 — 본 산출은 QA 독립분이다",
            "BM 원계열 확인 미완 (bm_kr.csv 가 야후 예비계열, 안건 13)",
            "ECOS 계열코드 PROVISIONAL",
            "기업행사 원장 미구축 — KR9 나머지 8종목 미확인",
            "ADTV90 분모의 거래정지일 처리 미의결 — 아래 adtv90_denominator 참조",
        ],
        # 결측일수에 무엇을 넣었는지를 산출물에 남긴다. 이것을 적지 않으면 다음 검산자가
        # 같은 '90 − 결측일수' 문구를 서로 다르게 구현하고도 그 사실을 모른다.
        "adtv90_denominator": {
            "window": "상장 중인 최근 90 개장일 (시장 휴장일은 창 구성에서 애초에 제외)",
            "counted_in_denominator": ["TRADED", "ZERO_VOLUME", "TRADING_HALT"],
            "excluded_from_denominator": ["DATA_MISSING"],
            "excluded_from_window": ["NOT_LISTED", "MARKET_CLOSED"],
            "halt_treatment_used": "ZERO — 정지일 거래대금 0 으로 반영하고 분모에 포함",
            "halt_treatment_alternative": "분모에서도 제외 (adtv90_exclude_halt 로 병기)",
            "halt_treatment_status": "NOT_DECIDED",
            "observed_in_pilot": {
                "DATA_MISSING": 0,
                "TRADING_HALT": "010120 2026-06-30 회차 3일 (04-08~04-10)",
            },
            "effect_if_switched": {
                "010120_adtv90": "241.83B -> 250.17B (+3.4%)",
                "kr_p10_threshold": "127.63B -> 127.63B (변화 없음)",
                "inclusion": "변화 없음 — 018260 제외 1건 유지",
                "why": "h=(9-1)*0.1=0.8 <1 이라 P10 이 최소 2개 값만 사용하고 "
                       "010120 은 거기에 들지 않는다. 우연이며 일반 보장이 아니다",
            },
        },
        "citation_rule": "as-run 과 병기한다. 보정본 단독 인용 금지.",
    }
    mp = os.path.join(OUT, "stage7_recompute_meta.json")
    with open(mp, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    rows = [{"run": "as_run_no_corporate_action", **asrun},
            {"run": "decided_2026_07_30", **fin}]
    cp = os.path.join(OUT, "stage7_recompute.csv")
    pd.DataFrame(rows).to_csv(cp, index=False, encoding="utf-8-sig")

    print("[4] 산출")
    print(f"    {os.path.relpath(mp, P.ROOT)}")
    print(f"    {os.path.relpath(cp, P.ROOT)}")
    print(f"    입력 지문 {len(inputs)}개 기록\n")

    print("[5] 남은 것 — 이 산출로 닫히지 않는 것")
    for x in meta["not_frozen_reason"]:
        print(f"    · {x}")
    print(f"\n  performance_status = {meta['performance_status']}")
    print("  인용 형식 — as-run 과 병기한다:")
    print(f"    as-run {asrun['excess_pp']:+.2f}%p / 의결규칙 적용 "
          f"{fin['excess_pp']:+.2f}%p (QA 독립분, 엔진 재산출 전)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
