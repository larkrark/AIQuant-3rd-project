# -*- coding: utf-8 -*-
"""데이터 로더 — 실데이터 수집·정제 → engine 입력 스키마 CSV 생성.

★ 위치: 백테스팅(독립 재산출). 팀 collect_pilot_inputs.py 와 '의도적으로 중복'.
   목적: 팀과 독립적으로, 그러나 동일 룰북·동일 유니버스(seed_basket)로 수집하여
        engine 산출이 팀 결과와 일치하는지 교차검증. 통합·폐기 금지.

기준 인용(임의값 사용 금지):
  - 유니버스     : seed_basket.csv (유니버스 정본, 팀 확정분)
  - 종가         : raw_close = 비조정 종가 (데이터사전 4.1 · auto_adjust=False)
  - 거래대금     : 공식값 우선, 미확보 시 재구성값 — 여기선 공식(KRX 로그인) 미보유이므로
                  exchange_trading_value 를 채우지 않음 → engine 이 RECONSTRUCTED 처리 (데이터사전 4.1)
  - 상장일       : 실제 listing_date 수집 → 시즈닝 판정 근거 (데이터사전 3 · D-06 유효관측일수)
  - 환율         : fx_series_provider = ECOS, KRW_PER_USD (데이터사전 15.3) — 임의 프록시(야후) 금지
  - BM           : KOSPI200 PR(공식 우선) + Russell3000 PR(^RUA) (데이터사전 15 · D-08)

수집 창(START~END): 3/31 회차 관측창(90개장일) 여유 포함 ~ 6/30 회차 이후. 팀과 무관하게 독립 설정.
비밀키(.env, 커밋 금지): ECOS_API_KEY(환율), KRX_ID·KRX_PW(선택 — KRX 공식 지수·거래대금).
"""
import os
import sys
import json
import time
import warnings
import pandas as pd

warnings.filterwarnings("ignore")

START, END = "2025-10-01", "2026-07-20"
ECOS_FX_SERIES = ("731Y001", "0000001")   # 원/달러 일별 — 계열코드 데이터사전 확정 대기(잠정)
HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.abspath(os.path.join(HERE, "..", "engine"))
DEFAULT_BASKET = os.path.join(ENGINE, "seed_basket.csv")


def _load_env() -> None:
    """engine/.env 를 읽어 환경변수로 주입 (로컬 편의 · BOM 제거). dotenv 없어도 동작."""
    p = os.path.join(ENGINE, ".env")
    if not os.path.exists(p):
        return
    for line in open(p, encoding="utf-8-sig"):
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.strip().split("=", 1)
            os.environ.setdefault(k.strip().lstrip("﻿"), v.strip().strip('"').strip("'"))


def _retry(fn, tries=4, base=2.0):
    """yfinance 429(레이트리밋) 대비 지수 백오프 재시도."""
    for i in range(tries):
        try:
            r = fn()
            if r is not None and len(r) > 0:
                return r
        except Exception:
            pass
        time.sleep(base * (i + 1))
    return None


def _epoch_to_date(ftd):
    """야후 firstTradeDate epoch → 날짜. 초/밀리초 단위 모호성은 '그럴듯한 연도(1900~2100)'로 판별.
    (단순 임계값은 1970년대 ms값을 초로 오해 → 5112년 등 오류. 팀 draft 폐기 원인과 동일 이슈.)"""
    if not ftd:
        return ""
    for unit in ("s", "ms"):
        try:
            ts = pd.Timestamp(ftd, unit=unit)
            if pd.Timestamp("1900-01-01") <= ts <= pd.Timestamp("2100-01-01"):
                return ts.strftime("%Y-%m-%d")
        except Exception:
            pass
    return ""


# --- 미국: 가격(비조정) + 실제 상장일 ---
def _us_prices(sid, start, end):
    import yfinance as yf
    t = yf.Ticker(sid)
    h = _retry(lambda: t.history(start=start, end=end, auto_adjust=False))   # 비조정 Close·Volume
    if h is None or h.empty:
        return None, None
    h = h.reset_index()
    px = pd.DataFrame({
        "security_id": sid, "market": "US",
        "market_date": pd.to_datetime(h["Date"]).dt.strftime("%Y-%m-%d"),
        "raw_close": h["Close"].round(4), "volume": h["Volume"].fillna(0).astype("int64"),
    })
    # 상장일: 야후 firstTradeDate(epoch) → 그럴듯한 연도로 변환. 관측창 이전이면 시즈닝 충분.
    info = t.info or {}
    ftd = info.get("firstTradeDateEpochUtc") or info.get("firstTradeDateMilliseconds")
    listing = _epoch_to_date(ftd)
    rec = {"security_id": sid, "listing_date": listing,
           "validation_status": "PASS" if listing and listing < start else "REVIEW_REQUIRED",
           "status_source": "YAHOO_REFERENCE"}
    return px, rec


# --- 한국: 가격(비조정) + 상장일 프록시 ---
def _kr_prices(sid, start, end):
    from pykrx import stock
    s, e = start.replace("-", ""), end.replace("-", "")
    df = _retry(lambda: stock.get_market_ohlcv(s, e, sid))
    if df is None or df.empty:
        return None, None
    df = df.reset_index().rename(columns={"날짜": "market_date", "종가": "raw_close", "거래량": "volume"})
    df["market_date"] = pd.to_datetime(df["market_date"]).dt.strftime("%Y-%m-%d")
    px = pd.DataFrame({"security_id": sid, "market": "KR", "market_date": df["market_date"],
                       "raw_close": df["raw_close"].round(2), "volume": df["volume"].astype("int64")})
    # 상장일: pykrx 직접 API 부재 → 관측된 최초 거래일을 프록시로 사용(검토 필요 플래그).
    #         관측창 이전이면 시즈닝 판정에 충분(실상장일은 근형 인계본으로 교체 예정).
    listing = px["market_date"].min()
    rec = {"security_id": sid, "listing_date": listing,
           "validation_status": "REVIEW_REQUIRED", "status_source": "PYKRX_FIRST_OBS_PROXY"}
    return px, rec


# --- 환율: ECOS 공식 (데이터사전 15.3) ---
def _ecos_fx(start, end):
    """한국은행 ECOS 원/달러 일별. 반환 (df[market_date,fx_rate], 출처메모). 키 없으면 (None, 사유)."""
    import urllib.request
    key = os.environ.get("ECOS_API_KEY")
    if not key:
        return None, "ECOS_API_KEY 없음 → 환율 HOLD (야후 프록시 대체 금지: 룰북 15.3 ECOS 지정)"
    stat, item = ECOS_FX_SERIES
    url = (f"https://ecos.bok.or.kr/api/StatisticSearch/{key}/json/kr/1/1000/{stat}/D/"
           f"{start.replace('-','')}/{end.replace('-','')}/{item}")
    try:
        rows = json.loads(urllib.request.urlopen(url, timeout=30).read()) \
            .get("StatisticSearch", {}).get("row", [])
    except Exception as ex:
        return None, f"ECOS 호출 실패: {type(ex).__name__}"
    fx = pd.DataFrame({"market_date": [f"{r['TIME'][:4]}-{r['TIME'][4:6]}-{r['TIME'][6:]}" for r in rows],
                       "fx_rate": [float(r["DATA_VALUE"]) for r in rows]})
    return fx, f"ECOS {stat}/{item} (KRW_PER_USD, 계열 잠정)"


# --- BM: KOSPI200(공식 우선) + Russell3000 ---
def _bm_kospi200(start, end):
    """KRX 공식(pykrx, 로그인 시) 우선 → 실패 시 야후 ^KS200 예비. 반환 (df, 출처메모)."""
    from pykrx import stock
    try:
        df = stock.get_index_ohlcv(start.replace("-", ""), end.replace("-", ""), "1028")  # KOSPI200
        if len(df):
            out = pd.DataFrame({"market_date": [d.strftime("%Y-%m-%d") for d in df.index],
                                "close": df["종가"].round(2).values})
            return out, "KRX 공식(pykrx 1028)"
    except Exception:
        pass
    import yfinance as yf
    ks = _retry(lambda: yf.Ticker("^KS200").history(start=start, end=end, auto_adjust=False))
    if ks is None or ks.empty:
        return None, "KOSPI200 전 경로 실패"
    ks = ks.reset_index()
    out = pd.DataFrame({"market_date": pd.to_datetime(ks["Date"]).dt.strftime("%Y-%m-%d"),
                        "close": ks["Close"].round(2)})
    return out, "야후 ^KS200 예비(KRX 로그인 미보유 → 공식값으로 교체 예정)"


def _bm_russell3000(start, end):
    import yfinance as yf
    h = _retry(lambda: yf.Ticker("^RUA").history(start=start, end=end, auto_adjust=False))
    if h is None or h.empty:
        return None, "^RUA 실패(^RUI 대체 검토 필요)"
    h = h.reset_index()
    return pd.DataFrame({"market_date": pd.to_datetime(h["Date"]).dt.strftime("%Y-%m-%d"),
                         "close": h["Close"].round(4)}), "야후 ^RUA (Russell3000)"


def build_inputs(out_dir: str, basket_path: str = DEFAULT_BASKET,
                 start: str = START, end: str = END) -> dict:
    """seed_basket 유니버스로 실데이터 수집 → engine 입력 CSV 8종 + 출처메모(sources.json) 기록.
    반환: 출처·행수 요약 dict."""
    _load_env()
    os.makedirs(out_dir, exist_ok=True)
    basket = pd.read_csv(basket_path, dtype={"security_id": str})
    print(f"[data_loader] 독립 수집 {start}~{end} · 유니버스 {len(basket)}종목 ({basket_path})")

    prices, listings, prov = [], [], {}
    for r in basket.itertuples():
        px, rec = (_kr_prices(r.security_id, start, end) if r.market == "KR"
                   else _us_prices(r.security_id, start, end))
        if px is None:
            print(f"  - {r.security_id} ({r.market}) 수집 실패 → 스킵(HOLD)")
            prov[r.security_id] = "COLLECTION_HOLD"
            continue
        prices.append(px)
        listings.append(rec)
        print(f"  + {r.security_id:6} {r.market} {r.primary_theme:13} rows={len(px)} 상장 {rec['listing_date']}({rec['validation_status']})")
    if not prices:
        raise RuntimeError("수집 가격 0 — 유니버스(KR 인계 대기)·네트워크 확인")
    prices = pd.concat(prices, ignore_index=True)
    # 거래대금(exchange_trading_value) 미포함 → engine 이 RECONSTRUCTED 처리 (공식값 KRX 로그인 필요, 재구성 위장 금지)

    kr_dates = set(prices[prices["market"] == "KR"]["market_date"])
    us_dates = set(prices[prices["market"] == "US"]["market_date"])

    fx, fx_src = _ecos_fx(start, end)
    bm_kr, bmkr_src = _bm_kospi200(start, end)
    bm_us, bmus_src = _bm_russell3000(start, end)
    if bm_kr is not None:
        kr_dates |= set(bm_kr["market_date"])   # BM 개장일도 KR 달력에 반영

    # calendar: 시장별 관측된 거래일 = 개장(is_market_open=1) — 거래소 공식 달력 검증은 QA 단계
    all_days = sorted(kr_dates | us_dates)
    cal = [{"market": m, "market_date": d, "is_market_open": int(d in (kr_dates if m == "KR" else us_dates))}
           for d in all_days for m in ("KR", "US")]
    n_common = sum(1 for d in all_days if d in kr_dates and d in us_dates)

    W = lambda name, df: df.to_csv(os.path.join(out_dir, name), index=False)
    W("prices.csv", prices)
    W("calendar.csv", pd.DataFrame(cal))
    W("listings.csv", pd.DataFrame(listings)[["security_id", "listing_date"]])   # engine 계약(실상장일)
    W("halts.csv", pd.DataFrame(columns=["security_id", "market_date", "full_day_halt"]))  # KR 정지 근형 인계 대기
    basket.to_csv(os.path.join(out_dir, "seed_basket.csv"), index=False)         # 유니버스 정본 복사
    if fx is not None:
        W("fx.csv", fx)
    if bm_kr is not None:
        W("bm_kr.csv", bm_kr)
    if bm_us is not None:
        W("bm_us.csv", bm_us)

    # 출처메모: 독립 QA·재현성 검증 기준 (팀 INPUT_MANIFEST 와 대조용)
    sources = {
        "rule_version": "v0.9-pilot", "window": [start, end],
        "trading_value": "RECONSTRUCTED (공식 KRX 로그인 미보유 — 재구성 위장 금지)",
        "fx": fx_src, "bm_kr": bmkr_src, "bm_us": bmus_src,
        "listings": "US=YAHOO_REFERENCE, KR=PYKRX_FIRST_OBS_PROXY (실상장일 근형 인계본 교체 예정)",
        "common_open_days": n_common,
        "note": "야후·프록시·재구성은 파일럿 한정·인용 금지(D-13 ①). 독립 재산출 — 팀 결과와 대조.",
    }
    with open(os.path.join(out_dir, "sources.json"), "w", encoding="utf-8") as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)
    print(f"[data_loader] 완료 → {out_dir}  (공통 개장일 {n_common}일 · fx: {fx_src})")
    return sources


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ENGINE, "real_data")
    build_inputs(out)
