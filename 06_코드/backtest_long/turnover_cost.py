# -*- coding: utf-8 -*-
"""회전율·거래비용·수용력 — 이 지수를 실제로 따라갈 수 있는가.

지수는 비중만 정한다. 실제 매매는 이 지수를 추종하는 펀드가 하고, 그 비용은
지수에 들어가 있지 않다. 그래서 지수 수익률은 언제나 실현 수익률보다 높다.
얼마나 높은지를 재는 것이 이 분석이다.

세 가지를 본다
  1 회전율    리밸런싱마다 포트폴리오의 몇 %를 갈아치우는가
              비중은 리밸런싱 사이에 표류한다. 오른 종목은 저절로 커지고
              내린 종목은 작아진다. 다음 리밸런싱에 목표비중으로 되돌리는데,
              그 되돌리는 양이 회전율이다.
  2 거래비용   회전율 × 비용률을 매 리밸런싱마다 차감한 순지수
  3 수용력     펀드 규모별로 하루 거래대금(ADTV90)의 몇 %를 사야 하는가
              통상 20% 를 넘으면 시장충격으로 체결가가 밀린다

비용 가정 (변경 가능 — 실측이 아니라 가정임을 명시한다)
  한국  매도 0.20% (증권거래세 0.18 + 수수료 0.02) · 매수 0.02%
  미국  매도 0.05% · 매수 0.05% (수수료 + 스프레드 근사)

성과 인용 제한 — 본 분석도 Seed18 선택편향 위에 있다. 비용 차감 후 수치 역시
수익성 근거가 아니다. 읽을 것은 "규칙이 요구하는 거래량의 크기" 다.
"""
import argparse
import glob
import json
import os
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.path.join(HERE, ".."))
OUT = os.path.join(HERE, "out")
INPUT_LONG = os.path.join(CODE, "data", "input_long")

COST = {"KR": {"sell": 0.0020, "buy": 0.0002},
        "US": {"sell": 0.0005, "buy": 0.0005}}
FUND_SIZES = [100e8, 1000e8, 10000e8]      # 100억 · 1,000억 · 1조


def krw_prices():
    px = pd.read_csv(os.path.join(INPUT_LONG, "prices.csv"), dtype={"security_id": str})
    fx = pd.read_csv(os.path.join(INPUT_LONG, "fx.csv"))
    df = px.merge(fx, on="market_date", how="left")
    val = df["adj_close"].fillna(df["raw_close"]) if "adj_close" in df else df["raw_close"]
    df["close_krw"] = np.where(df["market"] == "KR", val, val * df["fx_rate"])
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kr-sell", type=float, default=COST["KR"]["sell"])
    ap.add_argument("--us-sell", type=float, default=COST["US"]["sell"])
    a = ap.parse_args()
    COST["KR"]["sell"], COST["US"]["sell"] = a.kr_sell, a.us_sell

    idx = pd.read_csv(os.path.join(OUT, "index_vs_benchmark.csv"))
    dates = idx.market_date.tolist()
    px = krw_prices()
    wide = px.pivot_table(index="market_date", columns="security_id",
                          values="close_krw").reindex(dates).ffill()
    mkt = px.drop_duplicates("security_id").set_index("security_id")["market"]

    wfiles = sorted(glob.glob(os.path.join(OUT, "weights_*.csv")))
    rounds, wsets, effs = [], [], []
    for f in wfiles:
        s = os.path.basename(f)[8:18]
        nxt = [d for d in dates if d > s]
        if not nxt:
            continue
        w = pd.read_csv(f, dtype={"security_id": str})
        rounds.append(s)
        wsets.append(w.set_index("security_id")["final_target_weight"])
        effs.append(nxt[0])

    print("=" * 70)
    print("회전율 · 거래비용 · 수용력")
    print("=" * 70)
    print(f"  리밸런싱 {len(effs)}회 · 구간 {dates[0]} ~ {dates[-1]}\n")

    # ── 1. 회전율 ────────────────────────────────────────────
    recs = []
    for i in range(1, len(effs)):
        prev_w, new_w = wsets[i - 1], wsets[i]
        p0 = wide.loc[effs[i - 1]]
        p1 = wide.loc[effs[i]]                 # 리밸런싱 직전 가치 = 새 효력일 가격
        shares = prev_w / p0.reindex(prev_w.index)
        val = (shares * p1.reindex(prev_w.index)).dropna()
        drift = val / val.sum()                # 표류한 실제 비중
        allid = drift.index.union(new_w.index)
        d0 = drift.reindex(allid).fillna(0.0)
        d1 = new_w.reindex(allid).fillna(0.0)
        delta = d1 - d0
        to = float(np.abs(delta).sum() / 2)    # 단방향 회전율
        cost = 0.0
        for sid, dv in delta.items():
            m = mkt.get(sid, "US")
            cost += (abs(dv) * COST[m]["buy"]) if dv > 0 else (abs(dv) * COST[m]["sell"])
        recs.append({"effective_date": effs[i], "turnover": to, "cost": cost,
                     "max_weight": float(d1.max())})
    t = pd.DataFrame(recs)
    yrs = (pd.Timestamp(dates[-1]) - pd.Timestamp(dates[0])).days / 365.25
    ann_to = t.turnover.sum() / yrs
    print("[1] 회전율 — 리밸런싱마다 갈아치우는 비율 (단방향)")
    print(f"    평균 {t.turnover.mean()*100:5.2f}%  중앙 {t.turnover.median()*100:5.2f}%"
          f"  최대 {t.turnover.max()*100:5.2f}%  ({t.loc[t.turnover.idxmax(),'effective_date']})")
    print(f"    연간 회전율 {ann_to*100:.1f}%   "
          f"→ 보유종목을 연 {ann_to:.2f}회 갈아치우는 셈")

    # ── 2. 거래비용 차감 ─────────────────────────────────────
    ann_cost = t.cost.sum() / yrs
    gross = idx.index_level.iloc[-1] / idx.index_level.iloc[0]
    gross_cagr = gross ** (1 / yrs) - 1
    net_mult = gross * np.prod([1 - c for c in t.cost])
    net_cagr = net_mult ** (1 / yrs) - 1
    print(f"\n[2] 거래비용 — 가정: KR 매도 {COST['KR']['sell']*100:.2f}%·매수 "
          f"{COST['KR']['buy']*100:.2f}% / US 각 {COST['US']['sell']*100:.2f}%")
    print(f"    회당 평균 {t.cost.mean()*1e4:5.1f}bp   연간 {ann_cost*1e4:5.1f}bp")
    print(f"    총비용 누적 {(1-np.prod([1-c for c in t.cost]))*100:.2f}%")
    print(f"    CAGR   비용전 {gross_cagr*100:6.2f}%  →  비용후 {net_cagr*100:6.2f}%"
          f"   ({(net_cagr-gross_cagr)*1e4:+.0f}bp)")

    # ── 3. 수용력 ────────────────────────────────────────────
    led = pd.read_csv(os.path.join(OUT, "adtv90_ledger.csv"), dtype={"security_id": str})
    last = led[led.selection_date == rounds[-1]]
    last = last[last.adtv90_status == "CALCULATED"].set_index("security_id")
    fxl = pd.read_csv(os.path.join(INPUT_LONG, "fx.csv")).iloc[-1]["fx_rate"]
    adtv_krw = last.apply(
        lambda r: r.official_adtv90 * (1 if r.market == "KR" else fxl), axis=1)
    w_last = wsets[-1]
    to_med = t.turnover.median()
    print(f"\n[3] 수용력 — 최근 회차 기준, 회전율 중앙값 {to_med*100:.1f}% 적용")
    print(f"    {'펀드규모':>10}  {'최대 종목 1일 거래액':>18}  {'ADTV90 대비':>12}  판정")
    cap = []
    for fs in FUND_SIZES:
        worst, worst_sid = 0.0, None
        for sid, w in w_last.items():
            if sid not in adtv_krw.index:
                continue
            trade = fs * w * to_med
            ratio = trade / adtv_krw[sid]
            if ratio > worst:
                worst, worst_sid = ratio, sid
        v = "여유" if worst < 0.05 else ("주의" if worst < 0.20 else "★시장충격 우려★")
        print(f"    {fs/1e8:>8,.0f}억  {fs*w_last.max()*to_med/1e8:>16,.0f}억"
              f"  {worst*100:>10.1f}%  {v}  ({worst_sid})")
        cap.append({"fund_krw": fs, "worst_ratio": worst, "worst_security": worst_sid,
                    "verdict": v})

    res = {"artifact": "turnover_cost_capacity",
           "rebalances": len(t), "years": yrs,
           "turnover": {"mean": t.turnover.mean(), "median": t.turnover.median(),
                        "max": t.turnover.max(), "annual": ann_to},
           "cost_assumption": COST,
           "cost": {"per_rebalance_bp": t.cost.mean() * 1e4, "annual_bp": ann_cost * 1e4,
                    "cumulative_pct": (1 - np.prod([1 - c for c in t.cost])) * 100},
           "cagr": {"gross_pct": gross_cagr * 100, "net_pct": net_cagr * 100,
                    "drag_bp": (net_cagr - gross_cagr) * 1e4},
           "capacity": cap,
           "note": "비용률은 가정이며 실측이 아니다. 지수 자체에는 거래비용이 포함되지 않는다.",
           "citation_rule": "Seed18 선택편향 위의 분석 — 수익성 근거 아님."}
    with open(os.path.join(OUT, "turnover_cost.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2, default=float)
    t.to_csv(os.path.join(OUT, "turnover_by_rebalance.csv"), index=False)
    print(f"\n  {os.path.join(OUT, 'turnover_cost.json')}")


if __name__ == "__main__":
    main()
