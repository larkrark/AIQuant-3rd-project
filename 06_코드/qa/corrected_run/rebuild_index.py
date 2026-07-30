# -*- coding: utf-8 -*-
"""
7단계(지수 산출) 재현 + 010120 액면분할 보정 재산출 — QA 참고본

목적
  1) 공표 산출물(output_f1)의 지수·BM을 규칙 명세만으로 재현해 명세 완결성을 확인한다.
  2) 재현이 성립한 그 명세 위에서 010120 액면분할만 보정해, 보정 효과를 분리 측정한다.

명세 출처 (2026-07-27 엔진 담당 공유, run_meta.json 기록)
  index_linking_method = SEGMENT_RELINK   연결계수 체인(제수 조정 아님)
  fx_application       = SAME_DAY_ECOS    평가일 당일 ECOS 매매기준율
  calc_days            = COMMON_OPEN_ONLY 한·미 공통 개장일 한정

주의
  - 이 스크립트의 산출물은 QA 참고본이며 공표 산출물이 아니다.
  - 보정본 수치는 D-7 산출물 게이트를 통과하지 않았으므로 단독 인용을 금지한다.
  - 보정 사유는 '입력 오류 정정'이며 '성과 개선'이 아니다(R3).

실행
  python rebuild_index.py                 # as-run 재현 + 5:1 보정
  python rebuild_index.py --ratio 4       # 다른 분할비율 가정 시
"""
import argparse
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
QA = os.path.abspath(os.path.join(HERE, ".."))
CODE = os.path.abspath(os.path.join(QA, ".."))

sys.path.insert(0, QA)
from paths import force_utf8_stdout, require  # noqa: E402

PILOT = os.path.join(CODE, "data", "pilot_run")
INPUT = os.path.join(PILOT, "input_krxbm")
PUBLISHED = os.path.join(PILOT, "output_f1")
OUT = os.path.join(HERE, "out")

BASE_LEVEL = 1000.0

# 보정 대상 기업행사 — 공시 대조 완료분만 등재한다 (EVIDENCE.md 참조)
CORPORATE_ACTIONS = [
    {
        "security_id": "010120",
        "market": "KR",
        "action": "STOCK_SPLIT",
        "ratio": 5.0,               # 액면가 5,000원 -> 1,000원
        "effective_date": "2026-04-13",   # 변경상장·거래재개일
        "halt_dates": ["2026-04-08", "2026-04-09", "2026-04-10"],
    }
]


def load_inputs():
    require(os.path.join(PUBLISHED, "daily_market_state.csv"), "공표 상태 원장")
    state = pd.read_csv(
        os.path.join(PUBLISHED, "daily_market_state.csv"), dtype={"security_id": str}
    )
    state["market_date"] = pd.to_datetime(state["market_date"])

    fx = pd.read_csv(os.path.join(INPUT, "fx.csv"))
    fx["market_date"] = pd.to_datetime(fx["market_date"])
    fx = fx.set_index("market_date")["fx_rate"]

    cal = pd.read_csv(os.path.join(INPUT, "calendar.csv"))
    cal["market_date"] = pd.to_datetime(cal["market_date"])

    bm_kr = pd.read_csv(os.path.join(INPUT, "bm_kr.csv"))
    bm_kr["market_date"] = pd.to_datetime(bm_kr["market_date"])
    bm_kr = bm_kr.set_index("market_date")["close"]

    bm_us = pd.read_csv(os.path.join(INPUT, "bm_us.csv"))
    bm_us["market_date"] = pd.to_datetime(bm_us["market_date"])
    bm_us = bm_us.set_index("market_date")["close"]

    weights = pd.read_csv(
        os.path.join(PUBLISHED, "weights_2026-03-31.csv"), dtype={"security_id": str}
    )

    published = pd.read_csv(os.path.join(PUBLISHED, "index_vs_benchmark.csv"))
    published["market_date"] = pd.to_datetime(published["market_date"])

    return state, fx, cal, bm_kr, bm_us, weights, published


def common_open_days(cal, start, end):
    """COMMON_OPEN_ONLY — 한·미 양 시장이 모두 개장한 날만 산출일로 삼는다."""
    open_kr = set(cal[(cal.market == "KR") & (cal.is_market_open == 1)]["market_date"])
    open_us = set(cal[(cal.market == "US") & (cal.is_market_open == 1)]["market_date"])
    days = sorted(open_kr & open_us)
    return [d for d in days if start <= d <= end]


def price_matrix(state, weights, days, fx, split_ratio=None):
    """평가가격 행렬(원화). split_ratio가 주어지면 해당 기업행사를 보정한다."""
    ids = weights["security_id"].tolist()
    sub = state[state.security_id.isin(ids)]
    px = sub.pivot(index="market_date", columns="security_id", values="raw_close")
    px = px.reindex(days).ffill()

    if split_ratio is not None:
        for ca in CORPORATE_ACTIONS:
            sid = ca["security_id"]
            if sid not in px.columns:
                continue
            eff = pd.Timestamp(ca["effective_date"])
            ratio = split_ratio if split_ratio else ca["ratio"]
            # 분할 전용 조정: 효력일 '이전' 가격을 분할비율로 나눈다 (데이터사전 4.1)
            px.loc[px.index < eff, sid] = px.loc[px.index < eff, sid] / float(ratio)

    mkt = weights.set_index("security_id")["market"]
    fx_d = fx.reindex(days).ffill()
    missing_fx = int(fx_d.isna().sum())
    for sid in px.columns:
        if mkt.get(sid) == "US":
            px[sid] = px[sid] * fx_d.values
    return px, missing_fx


def segment_relink(px, weights, days):
    """SEGMENT_RELINK — 리밸런싱 구간 내에서는 구간 시작가 대비 가중평균 수익률.

    파일럿 지수구간(2026-04-01~06-30)에는 유효 리밸런싱이 없어 단일 구간이며,
    연결계수는 1.0으로 고정된다. 다구간 검증은 리밸런싱 발생 후에만 가능하다.
    """
    w = weights.set_index("security_id")["final_target_weight"]
    base = px.loc[days[0]]
    rel = px.divide(base, axis=1)
    level = (rel * w.reindex(px.columns).values).sum(axis=1) * BASE_LEVEL
    return level


def synthetic_bm(bm_kr, bm_us, fx, days):
    """합성 BM = KOSPI200 PR 50% + Russell3000 PR 50% (D-08).

    미국 구성분은 평가일 당일 환율로 원화 환산한다. 커스텀 지수가 원화·무헤지이므로
    BM도 같은 통화 기준이어야 비교가 성립한다. 환산 없이 지수레벨 비율만 쓰면
    공표 BM과 2.4e-02 어긋난다(검증 완료).
    """
    kr = bm_kr.reindex(days).ffill()
    us = bm_us.reindex(days).ffill()
    f = fx.reindex(days).ffill()
    us_krw = us * f
    return (0.5 * kr / kr.iloc[0] + 0.5 * us_krw / us_krw.iloc[0]) * BASE_LEVEL


def main():
    force_utf8_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("--ratio", type=float, default=None,
                    help="분할비율 가정 (기본: CORPORATE_ACTIONS 등재값 5.0)")
    args = ap.parse_args()

    state, fx, cal, bm_kr, bm_us, weights, published = load_inputs()
    start, end = published["market_date"].min(), published["market_date"].max()
    days = common_open_days(cal, start, end)

    print(f"[구간] {start.date()} ~ {end.date()}  공통 개장일 {len(days)}일 "
          f"(공표 산출일 {len(published)}일)")

    # --- 1. as-run 재현 ---
    px_asrun, missing_fx = price_matrix(state, weights, days, fx, split_ratio=None)
    idx_asrun = segment_relink(px_asrun, weights, days)
    bm = synthetic_bm(bm_kr, bm_us, fx, days)
    print(f"[환율] 공통 개장일 {len(days)}일 중 결측 {missing_fx}일")

    pub = published.set_index("market_date")
    err_idx = (idx_asrun - pub["index_level"]).abs() / pub["index_level"]
    err_bm = (bm - pub["benchmark_level"]).abs() / pub["benchmark_level"]
    print(f"[재현] 지수 최대 상대오차 {err_idx.max():.3e} / BM {err_bm.max():.3e}")
    reproduced = bool(err_idx.max() < 1e-9 and err_bm.max() < 1e-9)
    print(f"[재현] 명세 완결성 {'성립' if reproduced else '불성립 — 보정 결과 인용 금지'}")

    # --- 2. 분할 보정 재산출 ---
    ratio = args.ratio if args.ratio else CORPORATE_ACTIONS[0]["ratio"]
    px_corr, _ = price_matrix(state, weights, days, fx, split_ratio=ratio)
    idx_corr = segment_relink(px_corr, weights, days)

    def summarize(level):
        ret = level.iloc[-1] / BASE_LEVEL - 1.0
        gap = ret - (bm.iloc[-1] / BASE_LEVEL - 1.0)
        return level.iloc[-1], ret, gap

    l_a, r_a, g_a = summarize(idx_asrun)
    l_c, r_c, g_c = summarize(idx_corr)
    bm_ret = bm.iloc[-1] / BASE_LEVEL - 1.0

    print()
    print(f"{'구분':<22}{'종가레벨':>12}{'누적수익률':>12}{'BM대비':>12}")
    print("-" * 58)
    print(f"{'as-run (분할 미반영)':<22}{l_a:>12.4f}{r_a:>11.2%}{g_a:>12.2%}")
    print(f"{f'{ratio:g}:1 분할 보정':<22}{l_c:>12.4f}{r_c:>11.2%}{g_c:>12.2%}")
    print(f"{'합성 BM':<22}{bm.iloc[-1]:>12.4f}{bm_ret:>11.2%}{'—':>12}")
    print("-" * 58)
    print(f"{'보정 효과':<22}{l_c - l_a:>12.4f}{r_c - r_a:>11.2%}{g_c - g_a:>12.2%}")

    # --- 3. 불변식 체크포인트 ---
    # 과보정 탐지: 보정 후 분할일 종목수익률은 0이 아니라 실제 시장반응이어야 한다.
    # 0이 나오면 분할비율을 이중 적용한 것이므로 즉시 실패시킨다.
    sid = CORPORATE_ACTIONS[0]["security_id"]
    eff = pd.Timestamp(CORPORATE_ACTIONS[0]["effective_date"])
    col = px_corr[sid]
    prev = col[col.index < eff].iloc[-1]
    split_day_ret = col.loc[eff] / prev - 1.0
    print(f"\n[체크] 보정 후 {sid} 분할일 수익률 {split_day_ret:+.4%} "
          f"(0%면 과보정)")
    assert abs(split_day_ret) > 1e-6, "과보정 — 분할일 수익률이 0이다"

    # 축 분리: 누적 %p 차와 상대 수익률 차는 다른 축이다. 발표자료에서 섞으면 안 된다.
    w_sid = weights.set_index("security_id")["final_target_weight"].get(sid)
    sec_ret_a = px_asrun[sid].iloc[-1] / px_asrun[sid].iloc[0] - 1.0
    sec_ret_c = px_corr[sid].iloc[-1] / px_corr[sid].iloc[0] - 1.0
    implied_pp = (sec_ret_c - sec_ret_a) * w_sid
    print(f"[체크] 종목 전구간 수익률 차 {(sec_ret_c - sec_ret_a):+.4%} "
          f"x 비중 {w_sid:.6f} = {implied_pp:+.4%}p")
    print(f"       지수 누적 수익률 차 {(r_c - r_a):+.4%}p  "
          f"잔차 {abs(implied_pp - (r_c - r_a)):.2e}")
    assert abs(implied_pp - (r_c - r_a)) < 1e-12, "누적 %p 축 분해 불일치"
    print(f"[체크] 상대 수익률 차 {(l_c / l_a - 1):+.4%} "
          f"— 누적 %p({r_c - r_a:+.4%}p)와 다른 축. 혼용 금지")

    os.makedirs(OUT, exist_ok=True)
    out = pd.DataFrame({
        "market_date": [d.date() for d in days],
        "index_level_asrun": idx_asrun.values,
        "index_level_corrected": idx_corr.values,
        "benchmark_level": bm.values,
        "published_index_level": pub["index_level"].reindex(days).values,
        "reproduction_rel_error": err_idx.reindex(days).values,
    })
    out.to_csv(os.path.join(OUT, "index_corrected_vs_asrun.csv"),
               index=False, encoding="utf-8-sig")

    meta = {
        "status": "QA_REFERENCE_ONLY",
        "gate": "D-7 산출물 게이트 미통과 — 단독 인용 금지",
        "correction_reason": "INPUT_ERROR_FIX",
        "rule_version_base": "v0.9-pilot",
        "source_run": "output_f1",
        "spec": {
            "index_linking_method": "SEGMENT_RELINK",
            "fx_application": "SAME_DAY_ECOS",
            "calc_days": "COMMON_OPEN_ONLY",
        },
        "reproduction": {
            "index_max_rel_error": float(err_idx.max()),
            "benchmark_max_rel_error": float(err_bm.max()),
            "fx_missing_days": missing_fx,
            "common_open_days": len(days),
            "passed": reproduced,
        },
        "corporate_actions_applied": [dict(ca, ratio=ratio) for ca in CORPORATE_ACTIONS],
        "result": {
            "asrun": {"level": float(l_a), "return": float(r_a), "vs_bm": float(g_a)},
            "corrected": {"level": float(l_c), "return": float(r_c), "vs_bm": float(g_c)},
            "benchmark": {"level": float(bm.iloc[-1]), "return": float(bm_ret)},
            "correction_effect_pp": float(g_c - g_a),
        },
    }
    with open(os.path.join(OUT, "corrected_run_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\n[산출] {os.path.join(OUT, 'index_corrected_vs_asrun.csv')}")
    print(f"[산출] {os.path.join(OUT, 'corrected_run_meta.json')}")


if __name__ == "__main__":
    main()
