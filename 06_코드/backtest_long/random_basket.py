# -*- coding: utf-8 -*-
"""랜덤 바스켓 대조 (플라시보 검정) — 우리 성과가 규칙 덕인가, 종목 덕인가.

묻는 것
  같은 기간·같은 구조로 **아무 종목이나** 15개 뽑아 굴리면 어떤 결과가 나오는가.
  그 분포에서 우리 지수가 어디에 있는가.

    상위 1~5% 밖   -> 종목 선택이 결정적이었다는 뜻이다.
                     Seed18 은 2026년 시점 선택이므로 이는 편향의 크기를 보여줄 뿐,
                     규칙의 우수성을 뜻하지 않는다.
    중앙값 근처     -> 성과는 그 시기 그 시장이 좋았던 것이다.

설계
  모집단   현재 KOSPI200 · S&P500 (13년 이상 가격이 있는 종목만)
  1회 시행 KR 8 + US 7 무작위 추출 (우리 지수 최종 구성과 같은 지역 배분)
           분기말마다 동일가중으로 리셋 — 우리 리밸런싱 주기·연결 방식과 동일
  비교     기준 1,000 에서 출발한 종료 지수

공정성에 관하여
  모집단이 '현재' 지수 구성종목이라 생존편향이 있다. 그러나 우리 지수도 같은 편향을
  가지므로(Seed18 = 2026년 선택) **양쪽이 같은 조건**이며 비교는 성립한다.
  이 검정이 답하는 것은 "같은 편향된 풀에서, 우리 선택이 무작위보다 나은가" 다.

성과 인용 제한 — 본 검정 결과는 수익성 근거가 아니다. 편향 크기의 측정이다.
"""
import argparse
import json
import os
import sys
import urllib.request

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(CODE, "qa"))
OUT = os.path.join(HERE, "out")
POOL = os.path.join(CODE, "data", "input_long", "pool_prices.csv")
SP500 = ("https://raw.githubusercontent.com/datasets/s-and-p-500-companies/"
         "main/data/constituents.csv")


def load_env():
    from paths import env_path
    p = env_path()
    if p:
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def build_pool(n_kr, n_us, start, end, seed=7):
    """모집단 가격 수집 — yfinance 일괄. 한국은 .KS 접미사."""
    import yfinance as yf
    load_env()
    from pykrx import stock
    rng = np.random.default_rng(seed)

    kr_all = stock.get_index_portfolio_deposit_file("1028")
    kr = [f"{t}.KS" for t in rng.choice(kr_all, min(n_kr, len(kr_all)), replace=False)]
    sp = pd.read_csv(SP500)
    us_all = [s for s in sp["Symbol"].tolist() if "." not in s]
    us = list(rng.choice(us_all, min(n_us, len(us_all)), replace=False))
    print(f"[모집단] KR {len(kr)} · US {len(us)} 종목 다운로드")

    frames = []
    for tag, tickers in (("KR", kr), ("US", us)):
        df = yf.download(tickers, start=start, end=end, auto_adjust=True,
                         progress=False, threads=True)["Close"]
        df = df.dropna(axis=1, thresh=int(len(df) * 0.9))     # 13년 이상 있는 종목만
        df.index = pd.to_datetime(df.index).tz_localize(None)
        long = df.reset_index().melt(id_vars=df.index.name or "Date",
                                     var_name="security_id", value_name="close")
        long.columns = ["market_date", "security_id", "close"]
        long["market"] = tag
        frames.append(long.dropna())
        print(f"  {tag}: 유효 {df.shape[1]}종목 · {len(df)}일")
    pool = pd.concat(frames, ignore_index=True)
    pool["market_date"] = pool["market_date"].dt.strftime("%Y-%m-%d")
    os.makedirs(os.path.dirname(POOL), exist_ok=True)
    pool.to_csv(POOL, index=False)
    return pool


def simulate(pool, dates, eff_dates, n_kr, n_us, trials, seed=11):
    """무작위 바스켓 → 분기 동일가중 리셋 → 체인 연결. 종료 지수만 반환."""
    rng = np.random.default_rng(seed)
    wide = pool.pivot_table(index="market_date", columns="security_id", values="close")
    wide = wide.reindex(dates).ffill().dropna(axis=1)
    mkt = pool.drop_duplicates("security_id").set_index("security_id")["market"]
    kr_ids = [c for c in wide.columns if mkt.get(c) == "KR"]
    us_ids = [c for c in wide.columns if mkt.get(c) == "US"]
    print(f"[시뮬] 사용 가능 KR {len(kr_ids)} · US {len(us_ids)} · {trials}회 시행")
    if len(kr_ids) < n_kr or len(us_ids) < n_us:
        raise SystemExit("[중단] 모집단이 부족하다")

    segs = []
    for i, ed in enumerate(eff_dates):
        end = eff_dates[i + 1] if i + 1 < len(eff_dates) else None
        seg = [d for d in dates if d >= ed and (d <= end if end else True)]
        if len(seg) > 1:
            segs.append(seg)

    finals = []
    for _ in range(trials):
        pick = list(rng.choice(kr_ids, n_kr, replace=False)) + \
               list(rng.choice(us_ids, n_us, replace=False))
        w = 1.0 / len(pick)
        level = 1000.0
        for seg in segs:
            p = wide.loc[seg, pick]
            pv = (p / p.iloc[0] * w).sum(axis=1)     # 구간 시작 대비 가중평균
            level *= pv.iloc[-1] / pv.iloc[0]
        finals.append(level)
    return np.array(finals)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=1000)
    ap.add_argument("--pool-kr", type=int, default=150)
    ap.add_argument("--pool-us", type=int, default=150)
    ap.add_argument("--reuse-pool", action="store_true")
    a = ap.parse_args()

    idx = pd.read_csv(os.path.join(OUT, "index_vs_benchmark.csv"))
    dates = idx.market_date.tolist()
    ours = float(idx.index_level.iloc[-1])
    bm = float(idx.benchmark_level.iloc[-1])
    import glob
    eff = []
    for f in sorted(glob.glob(os.path.join(OUT, "weights_*.csv"))):
        s = os.path.basename(f)[8:18]
        nxt = [d for d in dates if d > s]
        if nxt:
            eff.append(nxt[0])
    eff = sorted(set(eff))

    print("=" * 70)
    print("랜덤 바스켓 대조 (플라시보 검정)")
    print("=" * 70)
    print(f"  구간 {dates[0]} ~ {dates[-1]} · 리밸런싱 {len(eff)}회")
    print(f"  우리 지수 {ours:,.0f} · BM {bm:,.0f}\n")

    if a.reuse_pool and os.path.exists(POOL):
        pool = pd.read_csv(POOL, dtype={"security_id": str})
        print(f"[모집단] 기존 파일 재사용 — {pool.security_id.nunique()}종목")
    else:
        pool = build_pool(a.pool_kr, a.pool_us, dates[0], dates[-1])

    finals = simulate(pool, dates, eff, 8, 7, a.trials)
    pct = (finals < ours).mean() * 100
    pct_bm = (finals < bm).mean() * 100

    print(f"\n[결과] 무작위 {a.trials}회 종료 지수 분포")
    for q in (5, 25, 50, 75, 95, 99):
        print(f"    {q:>3}%  {np.percentile(finals, q):>12,.0f}")
    print(f"    평균  {finals.mean():>12,.0f}   최대 {finals.max():>12,.0f}")
    print(f"\n  우리 지수 {ours:,.0f}  →  상위 {100-pct:.1f}% (백분위 {pct:.1f})")
    print(f"  합성 BM  {bm:,.0f}  →  상위 {100-pct_bm:.1f}% (백분위 {pct_bm:.1f})")

    if pct >= 95:
        verdict = ("우리 지수가 무작위 분포의 상위 5% 안에 있다. "
                   "종목 선택이 결정적이었다는 뜻이며, Seed18 이 2026년 시점 선택이므로 "
                   "이는 규칙의 우수성이 아니라 선택편향의 크기를 보여준다.")
    elif pct <= 60:
        verdict = ("우리 지수가 무작위 분포의 중앙 부근이다. "
                   "성과는 규칙이나 종목 선택보다 시장 국면에 기인한다.")
    else:
        verdict = "우리 지수가 무작위 분포의 상위권이나 극단은 아니다."
    print(f"\n  판정: {verdict}")

    res = {"artifact": "random_basket_placebo", "trials": a.trials,
           "window": [dates[0], dates[-1]], "rebalance_events": len(eff),
           "basket": {"kr": 8, "us": 7, "weighting": "EQUAL", "reset": "QUARTERLY"},
           "ours": ours, "benchmark": bm,
           "percentile_ours": pct, "percentile_bm": pct_bm,
           "random_dist": {f"p{q}": float(np.percentile(finals, q))
                           for q in (1, 5, 25, 50, 75, 95, 99)},
           "random_mean": float(finals.mean()), "random_max": float(finals.max()),
           "verdict": verdict,
           "fairness_note": ("모집단이 현재 지수 구성종목이라 생존편향이 있으나, "
                             "우리 지수도 같은 편향을 가지므로 비교는 성립한다."),
           "citation_rule": "수익성 근거 아님 — 편향 크기의 측정이다."}
    with open(os.path.join(OUT, "random_basket.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    np.save(os.path.join(OUT, "random_basket_finals.npy"), finals)
    print(f"\n  {os.path.join(OUT, 'random_basket.json')}")


if __name__ == "__main__":
    main()
