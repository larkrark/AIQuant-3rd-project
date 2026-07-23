# -*- coding: utf-8 -*-
"""데이터 로더 — 실데이터 수집·정제 → engine 입력 스키마 CSV 생성.

★ 이 파일만 실데이터에 의존한다. 나머지(engine·metrics·report)는 스키마만 같으면 무변경 재사용.
   원칙: 가짜 CSV(make_sample) ─교체─▶ 진짜 CSV(여기), 컬럼·형식 동일.

출처:
  - KR 가격/거래량 : pykrx (거래대금은 KRX 제공값이 로그인 필요 → 여기선 close×volume 재구성, source=RECONSTRUCTED)
  - US 가격        : yfinance
  - BM KR          : ^KS200  (yfinance; pykrx 지수 API는 로그인 필요)
  - BM US          : ^RUA    (Russell3000, yfinance)
  - 환율           : KRW=X   (USD/KRW, yfinance; 공식은 ECOS → TBD)

⚠️ DEMO_UNIVERSE 는 데모용 실종목이다. 최종 유니버스 확정은 규칙팀(김근형)의 몫(config·결정로그).
   여기 종목 구성은 "실데이터 배관이 흐르는지" 증명용이며 성과 인용 대상이 아니다.
"""
import os
import sys
import time
import warnings
import pandas as pd

warnings.filterwarnings("ignore")

# security_id, market, primary_theme  (테마는 config.THEMES 와 일치해야 함)
DEMO_UNIVERSE = [
    ("005930", "KR", "AI_ROBOTICS"),  ("000660", "KR", "AI_ROBOTICS"),   # 삼성전자·SK하이닉스
    ("034020", "KR", "ENERGY_POWER"), ("010120", "KR", "ENERGY_POWER"),  # 두산에너빌리티·LS ELECTRIC
    ("012450", "KR", "SPACE_DEFENSE"),("079550", "KR", "SPACE_DEFENSE"),  # 한화에어로·LIG넥스원
    ("NVDA",   "US", "AI_ROBOTICS"),  ("AMD",    "US", "AI_ROBOTICS"),
    ("GEV",    "US", "ENERGY_POWER"), ("VST",    "US", "ENERGY_POWER"),   # GE Vernova·Vistra
    ("LMT",    "US", "SPACE_DEFENSE"),("RTX",    "US", "SPACE_DEFENSE"),
]
DEFAULT_LISTING = "2020-01-02"   # 데모: 시즈닝 통과용. 실상장일 연동은 TBD.


def _retry(fn, tries=4, base=2.0):
    """yfinance 429 대비 지수 백오프 재시도."""
    for i in range(tries):
        try:
            r = fn()
            if r is not None and len(r) > 0:
                return r
        except Exception as e:
            last = e
        time.sleep(base * (i + 1))
    return None


def _fetch_kr_prices(sid, start, end):
    from pykrx import stock
    s, e = start.replace("-", ""), end.replace("-", "")
    df = _retry(lambda: stock.get_market_ohlcv(s, e, sid))
    if df is None or df.empty:
        return None
    df = df.reset_index().rename(columns={"날짜": "market_date", "종가": "raw_close", "거래량": "volume"})
    df["market_date"] = pd.to_datetime(df["market_date"]).dt.strftime("%Y-%m-%d")
    df = df[df["volume"] >= 0].copy()
    df["security_id"], df["market"] = sid, "KR"
    df["exchange_trading_value"] = (df["raw_close"] * df["volume"]).round(0)   # 재구성(제공값 TBD)
    return df[["security_id", "market", "market_date", "raw_close", "volume", "exchange_trading_value"]]


def _fetch_us_prices(sid, start, end):
    import yfinance as yf
    h = _retry(lambda: yf.Ticker(sid).history(start=start, end=end, auto_adjust=False))
    if h is None or h.empty:
        return None
    h = h.reset_index()
    h["market_date"] = pd.to_datetime(h["Date"]).dt.strftime("%Y-%m-%d")
    out = pd.DataFrame({"security_id": sid, "market": "US", "market_date": h["market_date"],
                        "raw_close": h["Close"].round(4), "volume": h["Volume"].fillna(0).astype("int64")})
    return out


def _fetch_yf_close(ticker, start, end):
    import yfinance as yf
    h = _retry(lambda: yf.Ticker(ticker).history(start=start, end=end, auto_adjust=False))
    if h is None or h.empty:
        return None
    h = h.reset_index()
    return pd.DataFrame({"market_date": pd.to_datetime(h["Date"]).dt.strftime("%Y-%m-%d"),
                         "close": h["Close"].round(4)})


def build_inputs(out_dir: str, start: str = "2025-10-01", end: str = "2026-07-20") -> None:
    """실데이터 수집 → engine 입력 CSV 8종을 out_dir 에 기록."""
    os.makedirs(out_dir, exist_ok=True)
    print(f"[data_loader] 실데이터 수집 {start}~{end}  (종목 {len(DEMO_UNIVERSE)}개)")

    prices, listings, basket = [], [], []
    for sid, mkt, theme in DEMO_UNIVERSE:
        p = _fetch_kr_prices(sid, start, end) if mkt == "KR" else _fetch_us_prices(sid, start, end)
        if p is None or p.empty:
            print(f"  - {sid} ({mkt}) 수집 실패 → 스킵")
            continue
        prices.append(p)
        listings.append({"security_id": sid, "listing_date": DEFAULT_LISTING})
        basket.append({"security_id": sid, "entity_id": "E" + sid, "market": mkt,
                       "primary_theme": theme, "gate_status": "CANDIDATE"})
        print(f"  + {sid:7} {mkt} {theme:13} rows={len(p)}")

    if not prices:
        raise RuntimeError("수집된 가격이 없음 — 네트워크/레이트리밋 확인")
    prices = pd.concat(prices, ignore_index=True)

    # 달력: 시장별 실제 거래일 = is_market_open 1
    kr_dates = set(prices[prices["market"] == "KR"]["market_date"])
    us_dates = set(prices[prices["market"] == "US"]["market_date"])
    all_dates = sorted(kr_dates | us_dates)
    cal = [{"market": m, "market_date": d, "is_market_open": int(d in (kr_dates if m == "KR" else us_dates))}
           for d in all_dates for m in ("KR", "US")]

    fx = _fetch_yf_close("KRW=X", start, end)
    if fx is None:
        raise RuntimeError("환율(KRW=X) 수집 실패")
    fx = fx.rename(columns={"close": "fx_rate"})

    bm_kr = _fetch_yf_close("^KS200", start, end)
    bm_us = _fetch_yf_close("^RUA", start, end)
    if bm_kr is None or bm_us is None:
        raise RuntimeError("BM 지수 수집 실패 (^KS200 / ^RUA)")

    W = lambda name, df: df.to_csv(os.path.join(out_dir, name), index=False)
    W("prices.csv", prices)
    W("calendar.csv", pd.DataFrame(cal))
    W("listings.csv", pd.DataFrame(listings))
    W("halts.csv", pd.DataFrame(columns=["security_id", "market_date", "full_day_halt"]))
    W("seed_basket.csv", pd.DataFrame(basket))
    W("fx.csv", fx)
    W("bm_kr.csv", bm_kr)
    W("bm_us.csv", bm_us)
    print(f"[data_loader] 완료 → {out_dir}  (거래일 KR {len(kr_dates)} / US {len(us_dates)})")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "real_data"
    build_inputs(out)
