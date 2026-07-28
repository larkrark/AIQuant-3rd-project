# -*- coding: utf-8 -*-
"""
P10 유동성 스크리닝 구조 진단 — 룰북 제78조 경계구간 판정용

확인 대상
  1) [P5, P10] 경계구간에 실제 관측치가 들어가는가 (제78조 경계사례 판정)
  2) P10 미만 종목수가 표본크기 n에 의해 구조적으로 결정되는가

선형보간 분위수(numpy 기본, 데이터사전 U-2)에서 백분위 p의 위치는
  h(p) = (n - 1) * p / 100
h(P10) < 1 이면 P10은 항상 최솟값과 2번째 값 사이에 떨어진다.
따라서 P10 미만 종목은 언제나 정확히 1개이며, 이는 유동성 수준과 무관하다.
h(P10) >= 1 이 되려면 n >= 11 이어야 한다.

실행: python p10_diagnostic.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
QA = os.path.abspath(os.path.join(HERE, ".."))
CODE = os.path.abspath(os.path.join(QA, ".."))
sys.path.insert(0, QA)
from paths import force_utf8_stdout  # noqa: E402

PUBLISHED = os.path.join(CODE, "data", "pilot_run", "output_f1")
CYCLES = ["2026-03-31", "2026-06-30"]


def main():
    force_utf8_stdout()
    led = pd.read_csv(os.path.join(PUBLISHED, "adtv90_ledger.csv"),
                      dtype={"security_id": str})
    rows = []

    for cyc in CYCLES:
        th = json.load(open(os.path.join(PUBLISHED, f"thresholds_{cyc}.json"),
                            encoding="utf-8"))
        for mk in ["KR", "US"]:
            g = led[(led.market == mk) & (led.selection_date == cyc)]
            # 모집단: official_adtv90 산출된 종목만. SEASONING_INCOMPLETE는 NaN이라 제외된다.
            s = g.dropna(subset=["official_adtv90"]).sort_values("official_adtv90")
            v = s["official_adtv90"].values
            n = len(v)
            excluded_pop = len(g) - n

            h5, h10 = (n - 1) * 0.05, (n - 1) * 0.10
            in_band = [k for k in range(n) if h5 <= k <= h10]
            p10_engine = th["provisional_P10"][mk]
            p10_calc = float(np.percentile(v, 10))
            below = int((v < p10_engine).sum())

            rows.append({
                "cycle": cyc, "market": mk, "n": n,
                "seasoning_excluded": excluded_pop,
                "h_P5": h5, "h_P10": h10,
                "boundary_band_count": len(in_band),
                "P10_engine": p10_engine,
                "P10_recalc": p10_calc,
                "P10_match": abs(p10_engine - p10_calc) < 1e-6,
                "min_value": float(v[0]),
                "second_value": float(v[1]),
                "min_security": s.iloc[0]["security_id"],
                "below_P10_count": below,
                "min_gap_to_P10_pct": float(v[0] / p10_engine - 1) * 100,
            })

    df = pd.DataFrame(rows)
    for _, r in df.iterrows():
        print(f"===== {r['cycle']} {r['market']} =====")
        print(f"  모집단 n={r['n']} (시즈닝 미충족 제외 {r['seasoning_excluded']}건)")
        print(f"  보간위치 h(P5)={r['h_P5']:.2f}  h(P10)={r['h_P10']:.2f}"
              f"  -> 경계구간 [P5,P10] 내 관측치 {r['boundary_band_count']}건")
        print(f"  P10 엔진={r['P10_engine']:,.2f}  재산출={r['P10_recalc']:,.2f}"
              f"  일치={r['P10_match']}")
        print(f"  최솟값 {r['min_security']}={r['min_value']:,.2f}"
              f"  (P10 대비 {r['min_gap_to_P10_pct']:+.2f}%)")
        print(f"  2번째={r['second_value']:,.2f}")
        print(f"  P10 미만 종목수 = {r['below_P10_count']}")
        print()

    print("[결론 1] 경계구간 [P5, P10]에 들어가는 관측치는 전 회차·전 시장에서 0건이다.")
    print("         제78조 경계사례 판정은 표본 부족이 아니라 분위수 정의상 공집합이므로")
    print("         NOT_APPLICABLE로 기록해야 한다.")
    print()
    need = 11
    print(f"[결론 2] h(P10) = (n-1)*0.10 < 1 이면 P10은 항상 x1과 x2 사이에 놓인다.")
    print(f"         따라서 n <= {need - 1} 에서는 P10 미만 종목이 항상 정확히 1개다.")
    print(f"         현재 n은 KR 9 / US 8 이므로 P10 스크리닝은 유동성 임계가 아니라")
    print(f"         '최저 유동성 1종목 기계적 탈락' 장치로 동작한다.")
    print(f"         2종목 이상 탈락이 가능하려면 n >= {need} 이 필요하다.")
    print()
    print("[결론 3] 절대 유동성이 아니라 상대 순위가 탈락을 결정한다는 실증:")
    us = led[(led.market == 'US')].dropna(subset=['official_adtv90'])
    for sid in ["KTOS", "ATI"]:
        r = us[us.security_id == sid]
        vals = {row['selection_date']: row['official_adtv90'] for _, row in r.iterrows()}
        print(f"         {sid}: " + "  ".join(
            f"{k} {v/1e6:,.2f}M" for k, v in sorted(vals.items())))
    print("         KTOS 6/30(315.15M)은 ATI 3/31(234.03M)보다 34% 크지만 탈락했다.")

    out = os.path.join(HERE, "out", "p10_diagnostic.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"\n[산출] {out}")


if __name__ == "__main__":
    main()
