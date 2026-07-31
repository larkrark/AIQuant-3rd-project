# -*- coding: utf-8 -*-
"""
연결 기전 시험 — 리밸런싱 경계에서 CHAIN_REBASE 와 DIVISOR_ADJUST 가 갈리는가

왜 필요한가
  파일럿 지수구간(2026-04-01~06-30)에는 리밸런싱 적용 이벤트가 0회다.
  선정은 2회 수행됐고 결과도 실제로 달라졌지만(3/31 KTOS -> 6/30 ATI),
  6/30 선정의 효력발생일이 구간 밖이라 지수에 반영될 날이 없었다.

  그래서 stage7_recompute meta 는 index_linking 을
  `CHAIN_REBASE_PILOT` + `verification: NOT_EXERCISED` 로 기록해 두었다.
  이름은 정했으나 발동한 적이 없다는 뜻이다.

  구간을 뒤로 늘려 실제 적용을 보려 했으나 bm_us.csv 가 2026-06-30 에서 끝나
  06-30 이후 공통 개장일이 0일이다. 데이터로는 확장할 수 없다.

무엇을 시험하는가
  가격·환율·BM 은 전부 실데이터다. 가정하는 것은 **교체 시점 하나**뿐이다.
  파일럿 구간 안의 여러 날짜를 리밸런싱 적용일로 놓고, 두 연결 방식이
  경계에서 지수를 끊는지 / 서로 갈리는지를 본다.

  이것은 기전(mechanism) 시험이다. 성과 주장이 아니다.
  산출되는 지수 수준은 어디에도 인용하지 않는다.

  MECHANISM_TEST_ONLY · 성과 인용 금지 · 가상 교체일

두 연결 방식
  CHAIN_REBASE     L(t) = L(T) × Σ w2_i × P_i(t)/P_i(T)          t ≥ T
  DIVISOR_ADJUST   주식수를 경계에서 재산출하고 제수를 맞춰 잇는다

qa/ 는 engine/ 을 import 하지 않는다.
"""
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

OUT = os.path.join(HERE, "out_stage7")
RTOL = 1e-12
BASE = K.BASE_LEVEL

# 의결 규칙 그대로. 연결 방식만 두 갈래로 나눈다.
CFG = dict(fx="SAME_DAY", days="COMMON_OPEN_ONLY", ca="SPLIT_5_ON_LISTING",
           bmfx="CONVERT")

# 가상 교체일 후보 — 구간 초·중·말을 고루 본다. 경계가 분할일과 겹치는 경우도 넣는다.
BOUNDARIES = ["2026-04-13", "2026-05-04", "2026-05-15", "2026-06-01", "2026-06-15"]


def px_for(st, w, days, fxs):
    """w 에 든 종목의 원화 환산 가격. prices_krw 는 w 로 종목을 고르므로 그대로 쓴다."""
    return K.prices_krw(st, w, days, fxs, CFG["ca"])


def two_segment(px1, px2, w1, w2, days, t_idx, link):
    """t_idx 에서 w1 -> w2 로 교체한 2구간 지수.

    t_idx 는 새 가중이 처음 적용되는 날의 위치다. 그 날 지수는 구간1 의 값을
    그대로 이어받아야 한다 — 가중을 바꿨다는 이유만으로 지수가 튀면 안 된다.
    """
    ww1 = w1.set_index("security_id")["final_target_weight"].reindex(px1.columns)
    ww2 = w2.set_index("security_id")["final_target_weight"].reindex(px2.columns)

    if link == "CHAIN_REBASE":
        seg1 = (px1.divide(px1.iloc[0], axis=1) * ww1.values).sum(axis=1) * BASE
        lt = seg1.iloc[t_idx]                      # 경계일 레벨 — 여기서 이어붙인다
        pt = px2.iloc[t_idx]
        seg2 = (px2.divide(pt, axis=1) * ww2.values).sum(axis=1) * lt
    elif link == "DIVISOR_ADJUST":
        sh1 = ww1.values / px1.iloc[0].values      # 기준일 비중을 주식수로 환산
        m1 = (px1 * sh1).sum(axis=1)
        seg1 = m1 / m1.iloc[0] * BASE
        lt = seg1.iloc[t_idx]
        sh2 = ww2.values / px2.iloc[t_idx].values  # 경계에서 주식수 재산출
        m2 = (px2 * sh2).sum(axis=1)
        seg2 = m2 / m2.iloc[t_idx] * lt            # 제수를 경계에 맞춘다
    else:
        raise ValueError(link)

    out = seg1.copy()
    out.iloc[t_idx:] = seg2.iloc[t_idx:]
    return out, float(seg1.iloc[t_idx]), float(seg2.iloc[t_idx])


def main():
    P.force_utf8_stdout()
    os.makedirs(OUT, exist_ok=True)
    print("=" * 70)
    print("연결 기전 시험 — MECHANISM_TEST_ONLY · 성과 인용 금지")
    print("=" * 70)

    st, fx, cal, bk, bu, w1, pub = K.load()
    w2 = pd.read_csv(os.path.join(K.MINE, "weights_2026-06-30.csv"),
                     dtype={"security_id": str})
    start, end = pub.market_date.min(), pub.market_date.max()
    days = K.calc_days(cal, start, end, CFG["days"])
    fxs = K.fx_series(fx, days, CFG["fx"])

    s1 = set(w1.security_id)
    s2 = set(w2.security_id)
    print(f"  3/31 가중 {len(w1)}종목 · 6/30 가중 {len(w2)}종목")
    print(f"  교체 내용  편입 {sorted(s2 - s1)}  ->  제외 {sorted(s1 - s2)}")
    print(f"  구간 {days[0].date()} ~ {days[-1].date()} · {len(days)}일\n")

    px1 = px_for(st, w1, days, fxs)
    px2 = px_for(st, w2, days, fxs)

    # 교체가 없을 때(현행 파일럿) — 비교 기준
    flat = (px1.divide(px1.iloc[0], axis=1)
            * w1.set_index("security_id")["final_target_weight"]
            .reindex(px1.columns).values).sum(axis=1) * BASE
    print(f"[0] 교체 없음 (현행 파일럿) 최종 {flat.iloc[-1]:.6f}\n")

    rows, worst_jump, worst_gap = [], 0.0, 0.0
    print("[1] 가상 교체일별 — 경계 연속성과 두 방식 일치 여부")
    print(f"    {'교체일':<12}{'경계前':>12}{'경계後':>12}{'단절':>11}"
          f"{'두방식차':>11}{'최종지수':>13}")
    for b in BOUNDARIES:
        t = pd.Timestamp(b)
        if t not in days:
            print(f"    {b:<12} 공통 개장일 아님 — 건너뜀")
            continue
        ti = days.index(t)

        chain, a1, a2 = two_segment(px1, px2, w1, w2, days, ti, "CHAIN_REBASE")
        divis, b1, b2 = two_segment(px1, px2, w1, w2, days, ti, "DIVISOR_ADJUST")

        jump = abs(a2 - a1) / abs(a1)                    # 경계에서 튀는가
        gap = float((np.abs(chain - divis) / np.abs(chain)).max())  # 두 방식이 갈리는가
        worst_jump = max(worst_jump, jump)
        worst_gap = max(worst_gap, gap)
        print(f"    {b:<12}{a1:12.4f}{a2:12.4f}{jump:11.2e}{gap:11.2e}"
              f"{chain.iloc[-1]:13.4f}")
        rows.append({"boundary": b, "level_before": a1, "level_after": a2,
                     "continuity_rel_err": jump, "method_gap_rel": gap,
                     "final_chain": float(chain.iloc[-1]),
                     "final_divisor": float(divis.iloc[-1]),
                     "vs_no_rebalance_pp":
                         (float(chain.iloc[-1]) - float(flat.iloc[-1])) / BASE * 100})

    ok_cont = worst_jump < RTOL
    ok_same = worst_gap < RTOL
    print(f"\n[2] 판정")
    print(f"    경계 연속성   최대 {worst_jump:.3e}  ->  "
          f"{'연속 — 가중 교체가 지수를 튀게 하지 않는다' if ok_cont else '★단절★'}")
    print(f"    두 방식 일치  최대 {worst_gap:.3e}  ->  "
          f"{'동일' if ok_same else '★갈림★'}")

    print(f"\n[3] 리밸런싱이 지수를 실제로 움직이는가 (교체 없음 대비)")
    for r in rows:
        print(f"    {r['boundary']}  {r['vs_no_rebalance_pp']:+.4f}%p")

    meta = {
        "artifact": "qa_relink_mechanism_test",
        "status": "MECHANISM_TEST_ONLY",
        "citation": "성과 인용 금지 — 교체일은 가정이며 실제 적용 이벤트가 아니다",
        "why": ("파일럿 구간에 리밸런싱 적용 0회. 구간 확장은 bm_us.csv 가 "
                "2026-06-30 에서 끝나 06-30 이후 공통 개장일이 0일이므로 불가"),
        "real_inputs": ["prices(daily_market_state)", "fx", "calendar", "bm_kr", "bm_us"],
        "assumed": ["리밸런싱 적용일"],
        "swap": {"added": sorted(s2 - s1), "removed": sorted(s1 - s2)},
        "tolerance_rtol": RTOL,
        "continuity_max_rel_err": worst_jump,
        "method_gap_max_rel": worst_gap,
        "verdict_continuity": "CONTINUOUS" if ok_cont else "DISCONTINUOUS",
        "verdict_methods": "EQUIVALENT" if ok_same else "DIVERGENT",
        "no_rebalance_final": float(flat.iloc[-1]),
        "cases": rows,
        "limitation": ("본 시험은 목표비중 재설정형 리밸런싱에서 두 연결 방식이 "
                       "수학적으로 같아짐을 보인다. 주식수 변동(증자·분할)이 "
                       "리밸런싱과 겹치는 경우는 다루지 않았다"),
    }
    p = os.path.join(OUT, "relink_mechanism_test.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"\n  {p}")
    return 0 if (ok_cont and ok_same) else 1


if __name__ == "__main__":
    sys.exit(main())
