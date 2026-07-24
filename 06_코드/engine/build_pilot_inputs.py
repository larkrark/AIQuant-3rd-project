# -*- coding: utf-8 -*-
"""KR9 + US9 입력을 run_pilot.py 입력계약(18종목)으로 병합. 드라이런 준비용."""
import os, pandas as pd
ID = {"security_id": str}
IN = "input_data"; KR = os.path.join(IN, "kr9_handoff")
OUT = "pilot_run/input"; os.makedirs(OUT, exist_ok=True)
rd = lambda p: pd.read_csv(p, dtype=ID, encoding="utf-8-sig")

# 1) seed_basket (5 core cols)
core = ["security_id","entity_id","market","primary_theme","gate_status"]
us_s = rd("seed_basket.csv")[core]
kr_s = rd(os.path.join(KR,"seed_basket.csv"))[core]
seed = pd.concat([kr_s, us_s], ignore_index=True)
seed.to_csv(os.path.join(OUT,"seed_basket.csv"), index=False)

# 2) prices (KR has exchange_trading_value, US none -> NaN)
us_p = rd(os.path.join(IN,"prices_us.csv"))
kr_p = rd(os.path.join(KR,"prices.csv"))
prices = pd.concat([kr_p, us_p], ignore_index=True)
prices.to_csv(os.path.join(OUT,"prices.csv"), index=False)

# 3) listings (security_id, listing_date, delisting_date)
us_l = rd(os.path.join(IN,"listings_us_fixed.csv"))[["security_id","listing_date"]].copy()
us_l["delisting_date"] = ""
kr_l = rd(os.path.join(KR,"listings.csv"))[["security_id","listing_date","delisting_date"]]
listings = pd.concat([kr_l, us_l], ignore_index=True)
listings.to_csv(os.path.join(OUT,"listings.csv"), index=False)

# 4) halts (KR only)
rd(os.path.join(KR,"halts.csv")).to_csv(os.path.join(OUT,"halts.csv"), index=False)

# 5) passthrough
for f in ["calendar.csv","fx.csv","bm_kr.csv","bm_us.csv"]:
    rd(os.path.join(IN,f)).to_csv(os.path.join(OUT,f), index=False)

print("seed", seed.shape, "| prices", prices.shape, "| listings", listings.shape)
print("종목수 seed", seed.security_id.nunique(), "| markets", dict(seed.market.value_counts()))
print("prices markets", dict(prices.market.value_counts().head()))
print("US exchange_trading_value NaN?", prices[prices.market=="US"]["exchange_trading_value"].isna().all() if "exchange_trading_value" in prices else "col없음")
