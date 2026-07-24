# -*- coding: utf-8 -*-
"""파일럿 파이프라인 실행 — 입력 CSV 폴더를 받아 산출물 폴더에 결과 저장.
사용: python run_pilot.py <input_dir> <output_dir>
입력 파일 (데이터사전 v0.2 필드명):
  seed_basket.csv  security_id,entity_id,market,primary_theme,gate_status
  prices.csv       security_id,market,market_date,raw_close,volume[,exchange_trading_value]
  calendar.csv     market,market_date,is_market_open
  listings.csv     security_id,listing_date[,delisting_date]
  halts.csv        security_id,market_date,full_day_halt   (없으면 생략 가능)
  fx.csv           market_date,fx_rate                     (ECOS 원/달러)
  bm_kr.csv        market_date,close                       (KOSPI200 PR)
  bm_us.csv        market_date,close                       (Russell3000 PR, USD)
"""
import sys, os, json
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try: _s.reconfigure(encoding="utf-8")   # Windows cp949 콘솔에서 —·→ 등 출력 깨짐 방지
    except Exception: pass
import pandas as pd
import config as C
import market_state, indicators, composition, index_calc


def run(input_dir: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    rd = lambda n, **kw: pd.read_csv(os.path.join(input_dir, n), dtype={"security_id": str}, **kw)
    basket = rd("seed_basket.csv")
    prices = rd("prices.csv")
    calendar = rd("calendar.csv")
    listings = rd("listings.csv")
    halts_path = os.path.join(input_dir, "halts.csv")
    halts = pd.read_csv(halts_path, dtype={"security_id": str}) if os.path.exists(halts_path) else None
    fx = rd("fx.csv")
    bm_kr, bm_us = rd("bm_kr.csv"), rd("bm_us.csv")

    states = market_state.assign_daily_states(prices, calendar, listings, halts)
    states.to_csv(os.path.join(output_dir, "daily_market_state.csv"), index=False)

    weight_sets, ledgers, cell_notes = {}, [], []
    kr_open = set(calendar[(calendar["market"] == "KR") & (calendar["is_market_open"] == 1)]["market_date"])
    us_open = set(calendar[(calendar["market"] == "US") & (calendar["is_market_open"] == 1)]["market_date"])
    common_open = sorted(kr_open & us_open)

    for sel_date in C.SELECTION_DATES:
        led = indicators.compute_indicators(states, observation_end_date=sel_date)
        led["review_cycle_id"] = f"RC-{sel_date}"
        ledgers.append(led)
        th = indicators.provisional_thresholds(led)
        selected = composition.select_constituents(basket, led, th)
        weights, notes = composition.assign_weights(selected)
        notes["review_cycle_id"] = f"RC-{sel_date}"
        cell_notes.append(notes)
        eff = next((d for d in common_open if d > sel_date), None)   # 효력발생: 선정 후 첫 공통 거래일 (잠정)
        if eff:
            weight_sets[eff] = weights
        selected.to_csv(os.path.join(output_dir, f"constituents_{sel_date}.csv"), index=False)
        weights.to_csv(os.path.join(output_dir, f"weights_{sel_date}.csv"), index=False)
        with open(os.path.join(output_dir, f"thresholds_{sel_date}.json"), "w") as f:
            json.dump({"provisional_P10": th, "rule_version": C.RULE_VERSION}, f, ensure_ascii=False, indent=2)

    pd.concat(ledgers).to_csv(os.path.join(output_dir, "adtv90_ledger.csv"), index=False)
    pd.concat(cell_notes).to_csv(os.path.join(output_dir, "cell_shortage.csv"), index=False)

    idx = index_calc.compute_portfolio_index(weight_sets, prices, fx, common_open)
    bm = index_calc.compute_benchmark(bm_kr, bm_us, fx, sorted(weight_sets.keys()), common_open)
    out = idx.merge(bm, on="market_date", how="inner")
    out["alpha"] = out["index_level"] - out["benchmark_level"]
    out["rule_version"] = C.RULE_VERSION
    out.to_csv(os.path.join(output_dir, "index_vs_benchmark.csv"), index=False)
    print(f"[{C.RULE_VERSION}] 산출 완료 → {output_dir}")
    print(out.tail(3).to_string(index=False))
    return out


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "sample_data",
        sys.argv[2] if len(sys.argv) > 2 else "output")
