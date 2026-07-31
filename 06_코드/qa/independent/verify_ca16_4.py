# -*- coding: utf-8 -*-
"""
16-4 corrected-run 독립 검증 — 엔진 보정본 vs QA 독립 재산출

대상   data/pilot_run/output_ca16_4   (엔진, run_id=16-4_corporate_action_fix)
기준   output_f1                      (보정 전 공표분)

검증 설계
  엔진은 daily_market_state 에 adj_close 열을 만들어 보정한다.
  QA 는 그 열을 쓰지 않는다. output_f1 의 raw_close 에서 출발해
  SPLIT_5_ON_LISTING 규칙을 직접 적용하고 지수를 다시 만든다.
  즉 같은 결론에 서로 다른 경로로 도달하는지를 본다.

  가중은 QA 6단계 독립 재산출분(independent/out/weights_*.csv)을 쓴다.
  엔진 산출 가중을 가져다 쓰면 검증이 아니라 복사가 된다.

검사
  1  기저 재현   보정 없이 output_f1 을 재현하는가 (이게 깨지면 나머지 무의미)
  2  보정 대조   QA 독립 보정 ↔ 엔진 output_ca16_4  (RTOL 1e-12)
  3  불변 주장   구성·가중·임계값·BM·상태코드가 정말 안 바뀌었는가
  4  보정 적용   adj_close 가 010120 에만, 경계일 이전에만 걸렸는가
  5  경로 지표   경계일 선택이 레벨에는 안 드러나므로 별도 기록

qa/ 는 engine/ 을 import 하지 않는다.
"""
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import paths as P  # noqa: E402
sys.path.insert(0, HERE)
import stage7_sensitivity as K  # noqa: E402

RTOL = 1e-12
CA_DIR = os.path.join(P.PILOT, "output_ca16_4")
F1_DIR = os.path.join(P.PILOT, "output_f1")
OUT = os.path.join(HERE, "out_stage7")

CA_SID = "010120"
BOUNDARY = "2026-04-13"
RATIO = 5.0

# 엔진이 "F-1과 동일"을 주장한 산출물. 파일 단위로 확인한다.
INVARIANT_FILES = [
    "adtv90_ledger.csv", "cell_shortage.csv",
    "constituents_2026-03-31.csv", "constituents_2026-06-30.csv",
    "thresholds_2026-03-31.json", "thresholds_2026-06-30.json",
    "weights_2026-03-31.csv", "weights_2026-06-30.csv",
]

result = {"checks": {}}


def sha16(p):
    return hashlib.sha256(
        open(p, "rb").read().replace(b"\r\n", b"\n")).hexdigest()[:16]


def head(n, t):
    print(f"\n[{n}] {t}")


def main():
    P.force_utf8_stdout()
    os.makedirs(OUT, exist_ok=True)
    print("=" * 68)
    print("16-4 corrected-run 독립 검증")
    print("=" * 68)

    st, fx, cal, bk, bu, w, pub_f1 = K.load()
    pub_ca = pd.read_csv(os.path.join(CA_DIR, "index_vs_benchmark.csv"),
                         parse_dates=["market_date"])
    start, end = pub_f1.market_date.min(), pub_f1.market_date.max()
    print(f"  구간 {start.date()} ~ {end.date()} · {len(pub_ca)}일")
    print(f"  QA 독립 가중 {len(w)}종목 · 합계 {w.final_target_weight.sum():.12f}")

    # ── 1. 기저 재현 ────────────────────────────────────────────
    head(1, "기저 재현 — 보정 없이 output_f1 을 만드는가")
    base = K.run(st, fx, cal, bk, bu, w, start, end,
                 dict(fx="SAME_DAY", days="COMMON_OPEN_ONLY",
                      link="SEGMENT_RELINK", ca="NONE", bmfx="CONVERT"),
                 pub=pub_f1)
    e = base["repro_max_rel_err"]
    ok1 = e < RTOL
    print(f"    최대 상대오차 {e:.3e}  (허용 {RTOL:.0e})  ->  {'일치' if ok1 else '불일치'}")
    result["checks"]["base_reproduction"] = {"max_rel_err": e, "pass": bool(ok1)}
    if not ok1:
        print("    기저가 깨졌다. 이후 결과를 인용하지 말 것.")
        return 1

    # ── 2. 보정 대조 ────────────────────────────────────────────
    head(2, "보정 대조 — QA 독립 보정 ↔ 엔진 output_ca16_4")
    mine = K.run(st, fx, cal, bk, bu, w, start, end,
                 dict(fx="SAME_DAY", days="COMMON_OPEN_ONLY",
                      link="SEGMENT_RELINK", ca="SPLIT_5_ON_LISTING",
                      bmfx="CONVERT"),
                 pub=pub_ca)
    e2 = mine["repro_max_rel_err"]
    ok2 = e2 < RTOL
    eng_last = float(pub_ca.index_level.iloc[-1])
    print(f"    QA   독립 재산출 지수 {mine['index_last']:.12f}")
    print(f"    엔진 output_ca16_4   {eng_last:.12f}")
    print(f"    최대 상대오차 {e2:.3e}  (허용 {RTOL:.0e})  ->  {'일치' if ok2 else '★불일치★'}")
    print(f"    BM 대비 {mine['excess_pp']:+.4f}%p · 보정 효과 "
          f"{mine['excess_pp'] - base['excess_pp']:+.4f}%p")
    result["checks"]["corrected_match"] = {
        "qa_index_last": mine["index_last"], "engine_index_last": eng_last,
        "max_rel_err": e2, "pass": bool(ok2),
        "excess_pp": mine["excess_pp"],
        "split_effect_pp": mine["excess_pp"] - base["excess_pp"],
    }

    # ── 3. 불변 주장 ────────────────────────────────────────────
    head(3, "불변 주장 — 구성·가중·임계값·BM·상태코드")
    inv = {}
    for f in INVARIANT_FILES:
        pa, pb = os.path.join(F1_DIR, f), os.path.join(CA_DIR, f)
        same = os.path.exists(pa) and os.path.exists(pb) and sha16(pa) == sha16(pb)
        inv[f] = bool(same)
        if not same:
            print(f"    ★ {f} 해시 상이")
    print(f"    파일 해시 동일 {sum(inv.values())}/{len(inv)}")

    a = pd.read_csv(os.path.join(F1_DIR, "index_vs_benchmark.csv"))
    b = pd.read_csv(os.path.join(CA_DIR, "index_vs_benchmark.csv"))
    bm_rel = float((np.abs(a.benchmark_level.values - b.benchmark_level.values)
                    / np.abs(a.benchmark_level.values)).max())
    print(f"    BM 열 최대 상대차 {bm_rel:.3e}  ->  "
          f"{'동일' if bm_rel < RTOL else '★차이★'}")

    sa = pd.read_csv(os.path.join(F1_DIR, "daily_market_state.csv"),
                     dtype={"security_id": str})
    sb = pd.read_csv(os.path.join(CA_DIR, "daily_market_state.csv"),
                     dtype={"security_id": str})
    common = [c for c in sa.columns if c in sb.columns]
    added = [c for c in sb.columns if c not in sa.columns]
    key = ["security_id", "market_date"]
    m = sa[common].merge(sb[common], on=key, suffixes=("_a", "_b"))
    diff = {c: int((m[c + "_a"].astype(str) != m[c + "_b"].astype(str)).sum())
            for c in common if c not in key}
    bad = {k: v for k, v in diff.items() if v}
    print(f"    상태코드 공통 {len(common)}열 · 불일치 {sum(diff.values())}행 "
          f"· 추가 열 {added}")
    if bad:
        print(f"    ★ 변경된 열: {bad}")
    ok3 = all(inv.values()) and bm_rel < RTOL and not bad
    result["checks"]["invariants"] = {
        "files_identical": inv, "bm_max_rel": bm_rel,
        "state_common_cols": len(common), "state_diff_rows": sum(diff.values()),
        "state_added_cols": added, "pass": bool(ok3),
    }

    # ── 4. 보정 적용 범위 ───────────────────────────────────────
    head(4, "보정 적용 — 010120 에만, 경계일 이전에만")
    d = sb.copy()
    d["market_date"] = d.market_date.astype(str)
    oth = d[d.security_id != CA_SID]
    e_oth = float(np.abs(oth.adj_close - oth.raw_close).max())
    k = d[d.security_id == CA_SID]
    pre, post = k[k.market_date < BOUNDARY], k[k.market_date >= BOUNDARY]
    e_pre = float(np.abs(pre.adj_close - pre.raw_close / RATIO).max())
    e_post = float(np.abs(post.adj_close - post.raw_close).max())
    print(f"    타 종목 |adj−raw|          {e_oth:.3e}  ({len(oth)}행)")
    print(f"    010120 경계前 |adj−raw/5| {e_pre:.3e}  ({len(pre)}행)")
    print(f"    010120 경계後 |adj−raw|   {e_post:.3e}  ({len(post)}행)")
    ok4 = max(e_oth, e_pre, e_post) < 1e-9
    result["checks"]["adjustment_scope"] = {
        "others_max": e_oth, "pre_max": e_pre, "post_max": e_post,
        "pre_rows": len(pre), "post_rows": len(post), "pass": bool(ok4),
    }

    # ── 5. 경로 지표 ────────────────────────────────────────────
    head(5, "경로 지표 — 경계일 선택은 레벨에 안 드러난다")
    alt = K.run(st, fx, cal, bk, bu, w, start, end,
                dict(fx="SAME_DAY", days="COMMON_OPEN_ONLY", link="SEGMENT_RELINK",
                     ca="SPLIT_5_ON_EFFECTIVE", bmfx="CONVERT"))
    print(f"    {'':24s}{'최종지수':>14s}{'연변동성':>11s}{'최대낙폭':>11s}")
    for lab, r in [("의결 경계일 04-13", mine), ("(참고) 효력일 04-10", alt)]:
        print(f"    {lab:24s}{r['index_last']:14.4f}{r['ann_vol_pct']:10.4f}%"
              f"{r['max_drawdown_pct']:10.4f}%")
    print(f"    추적오차 {mine['tracking_err_pct']:.4f}%")
    result["checks"]["path_metrics"] = {
        "decided_04_13": {kk: mine[kk] for kk in
                          ("index_last", "ann_vol_pct", "max_drawdown_pct",
                           "tracking_err_pct")},
        "alt_04_10": {kk: alt[kk] for kk in
                      ("index_last", "ann_vol_pct", "max_drawdown_pct")},
        "note": "최종 레벨이 같아도 변동성이 갈린다. 경계일은 위험지표를 바꾼다.",
    }

    # ── 판정 ────────────────────────────────────────────────────
    passed = ok1 and ok2 and ok3 and ok4
    result.update({
        "artifact": "qa_verify_ca16_4",
        "target": "output_ca16_4", "baseline": "output_f1",
        "engine_import": False,
        "weights_source": "qa/independent/out (엔진 산출물 아님)",
        "tolerance_rtol": RTOL,
        "verdict": "PASS" if passed else "FAIL",
        "citation_rule": "as-run 과 병기한다. 보정본 단독 인용 금지.",
        "performance_status": "PERFORMANCE_NOT_FROZEN",
        "not_frozen_reason": [
            "BM 원계열 출처 미확정 — 값은 KRX 1028 과 동일하나 수집 경로 증빙 대기",
            "기업행사 원장 미수신 — 010120 외 사건 유무 미확정",
            "ADTV90 분모의 거래정지일 처리 미의결",
            "리밸런싱 적용 이벤트 0회 — 연결 방식 정확성 NOT_EXERCISED",
        ],
    })
    print("\n" + "=" * 68)
    print(f"판정  {result['verdict']}")
    print("=" * 68)

    p = os.path.join(OUT, "verify_ca16_4.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  {p}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
