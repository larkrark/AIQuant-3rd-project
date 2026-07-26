# -*- coding: utf-8 -*-
"""합성 표본 데이터 생성 — 파이프라인 관통 시험 전용 (실데이터 아님).
12종목 = 6셀 × 2 (단, KR_SPACE_DEFENSE는 1종목 → 정상, US_ENERGY_POWER는 0종목 → 재배분 발동 시험).
시즈닝 미달 1종목, 종일정지 이력 1종목, 결측 1일 1종목 포함."""
import numpy as np, pandas as pd
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try: _s.reconfigure(encoding="utf-8")   # Windows cp949 콘솔에서 —·→ 등 출력 깨짐 방지
    except Exception: pass

rng = np.random.default_rng(20260723)
dates = pd.bdate_range("2025-10-01", "2026-07-10").strftime("%Y-%m-%d")
kr_holidays = {"2026-02-16", "2026-02-17", "2026-03-02", "2026-05-05"}
us_holidays = {"2025-11-27", "2025-12-25", "2026-01-01", "2026-01-19", "2026-02-16", "2026-05-25", "2026-07-03"}

cal = []
for d in dates:
    cal.append({"market": "KR", "market_date": d, "is_market_open": int(d not in kr_holidays)})
    cal.append({"market": "US", "market_date": d, "is_market_open": int(d not in us_holidays)})
calendar = pd.DataFrame(cal)

SECS = [  # security_id, market, theme, listing, base_price, adtv_scale
    ("KR001", "KR", "AI_ROBOTICS", "2020-01-02", 50000, 1.0), ("KR002", "KR", "AI_ROBOTICS", "2020-01-02", 120000, 3.0),
    ("KR003", "KR", "ENERGY_POWER", "2020-01-02", 80000, 2.0), ("KR004", "KR", "ENERGY_POWER", "2020-01-02", 30000, 0.5),
    ("KR005", "KR", "SPACE_DEFENSE", "2020-01-02", 200000, 4.0),
    ("KR006", "KR", "SPACE_DEFENSE", "2026-05-15", 45000, 1.0),   # 시즈닝 미달 시험
    ("US001", "US", "AI_ROBOTICS", "2020-01-02", 150, 5.0), ("US002", "US", "AI_ROBOTICS", "2020-01-02", 300, 8.0),
    ("US003", "US", "SPACE_DEFENSE", "2020-01-02", 450, 6.0), ("US004", "US", "SPACE_DEFENSE", "2020-01-02", 80, 2.0),
    ("US005", "US", "SPACE_DEFENSE", "2020-01-02", 60, 1.5),
    # US_ENERGY_POWER 0종목 → KR로 재배분 발동
]

prices, listings, halts = [], [], []
for sid, mkt, theme, listing, p0, sc in SECS:
    listings.append({"security_id": sid, "listing_date": listing})
    open_days = calendar[(calendar["market"] == mkt) & (calendar["is_market_open"] == 1)]["market_date"]
    open_days = [d for d in open_days if d >= max(listing, "2025-10-01")]
    p = p0
    for i, d in enumerate(open_days):
        p = max(p * (1 + rng.normal(0.0003, 0.018)), 1)
        vol = max(int(rng.lognormal(11, 0.6) * sc), 0)
        if sid == "KR004" and rng.random() < 0.05:
            vol = 0                                            # 무거래일
        row = {"security_id": sid, "market": mkt, "market_date": d,
               "raw_close": round(p, 2), "volume": vol}
        if mkt == "KR":
            row["exchange_trading_value"] = round(p * vol * (1 + rng.normal(0, 0.01)), 0)  # KRX 제공값(체결분포 오차 모사)
        if sid == "KR003" and d in ("2026-04-06", "2026-04-07"):
            halts.append({"security_id": sid, "market_date": d, "full_day_halt": 1})       # 종일정지 2일
            row["volume"] = 0
        if sid == "US004" and d == "2026-03-10":
            continue                                            # 결측 1일 (DATA_MISSING)
        prices.append(row)

basket = pd.DataFrame([{"security_id": s[0], "entity_id": "E" + s[0], "market": s[1],
                        "primary_theme": s[2], "gate_status": "CANDIDATE"} for s in SECS])

fx_days = sorted(set(calendar["market_date"]))
fx_rate, fx = 1350.0, []
for d in fx_days:
    fx_rate = max(fx_rate * (1 + rng.normal(0, 0.004)), 900)
    fx.append({"market_date": d, "fx_rate": round(fx_rate, 2)})

def make_bm(p0, drift, vol_, mkt):
    rows, p = [], p0
    for d in calendar[(calendar["market"] == mkt) & (calendar["is_market_open"] == 1)]["market_date"]:
        p = max(p * (1 + rng.normal(drift, vol_)), 1)
        rows.append({"market_date": d, "close": round(p, 2)})
    return pd.DataFrame(rows)

import os
os.makedirs("sample_data", exist_ok=True)
pd.DataFrame(prices).to_csv("sample_data/prices.csv", index=False)
calendar.to_csv("sample_data/calendar.csv", index=False)
pd.DataFrame(listings).to_csv("sample_data/listings.csv", index=False)
pd.DataFrame(halts).to_csv("sample_data/halts.csv", index=False)
basket.to_csv("sample_data/seed_basket.csv", index=False)
pd.DataFrame(fx).to_csv("sample_data/fx.csv", index=False)
make_bm(360, 0.0002, 0.01, "KR").to_csv("sample_data/bm_kr.csv", index=False)
make_bm(3200, 0.0004, 0.011, "US").to_csv("sample_data/bm_us.csv", index=False)
print("sample_data 생성 완료")
