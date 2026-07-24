# -*- coding: utf-8 -*-
"""파일럿 입력 수집 스크립트 — 보성 담당분 (로컬 실행 전용, 클라우드는 시세망 차단).
수집: 미국 9종목 시계열 + 미국 상장일 확인 + calendar.csv + KOSPI200 PR·KRX300(예비)·^RUA + ECOS 환율.
한국 9종목 시계열·상태·PIT는 김근형 담당 (별도 인계).
사용: pip install pykrx yfinance 후
     python collect_pilot_inputs.py sample_data/seed_basket.csv input_data
출력 스키마 = 데이터사전 v0.2 / run_pilot.py 입력계약. rule_version = v0.9-pilot
"""
import sys, os, json
import pandas as pd
try:  # .env의 ECOS_API_KEY 자동 로드 (로컬 편의)
    from dotenv import load_dotenv; load_dotenv()
except ImportError:
    _p = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(_p):
        for _l in open(_p, encoding="utf-8-sig"):   # utf-8-sig: 메모장 BOM 제거
            if "=" in _l and not _l.strip().startswith("#"):
                k, v = _l.strip().split("=", 1)
                os.environ.setdefault(k.strip().lstrip("\ufeff"), v.strip().strip('"').strip("'"))

START, END = "2025-10-01", "2026-07-01"    # 3/31 회차 관측창(90개장일) 여유 포함 ~ 6/30 회차 이후
ECOS_FX_STAT = ("731Y001", "0000001")      # 원/달러 — 계열코드는 데이터사전 확정 대기(잠정)


def collect_us_prices(tickers: list, out: str):
    import yfinance as yf
    rows, listing_rows = [], []
    for tk in tickers:
        t = yf.Ticker(tk)
        df = t.history(start=START, end=END, auto_adjust=False)   # 비조정 Close·Volume (가이드라인)
        if df.empty:
            print(f"[WARN] {tk}: 0행 — 수집 실패, HOLD 기록 필요")
            continue
        for d, r in df.iterrows():
            rows.append({"security_id": tk, "market": "US", "market_date": d.strftime("%Y-%m-%d"),
                         "raw_close": round(float(r["Close"]), 4), "volume": float(r["Volume"]),
                         "adj_close": round(float(r["Adj Close"]), 4) if "Adj Close" in df.columns else None})
            # adj_close = 수정주가 — 지수 평가·수익률 전용 (D-07). raw_close는 거래대금 재구성 전용
        # 상장일 확인 — 야후 firstTradeDate는 참고값. 2025-10 이전 상장이면 파일럿에 충분, 이후면 원출처 확인 필요
        ftd = t.info.get("firstTradeDateEpochUtc") or t.info.get("firstTradeDateMilliseconds")
        if ftd:
            # 판별: 1e11 초과면 ms (초 단위로는 서기 5000년대라 불가능). 예: TER 99153000000ms=1973-02-21
            ftd = pd.Timestamp(ftd, unit="ms" if ftd > 1e11 else "s").strftime("%Y-%m-%d")
        listing_rows.append({"security_id": tk, "listing_date": ftd or "",
                             "validation_status": "PASS" if ftd and ftd < START else "REVIEW_REQUIRED",
                             "unresolved_reason": "" if ftd and ftd < START else "상장일 원출처(EDGAR·거래소) 확인 필요",
                             "status_source": "YAHOO_REFERENCE", "rule_version": "v0.9-pilot"})
    pd.DataFrame(rows).to_csv(os.path.join(out, "prices_us.csv"), index=False)
    pd.DataFrame(listing_rows).to_csv(os.path.join(out, "listings_us_draft.csv"), index=False)
    print(f"prices_us.csv {len(rows)}행 / listings_us_draft.csv {len(listing_rows)}종목 (근형님 listings.csv와 병합용 DRAFT)")


def collect_indices_and_calendar(out: str):
    import yfinance as yf
    from pykrx import stock
    def _try_pykrx(code):
        try:
            df = stock.get_index_ohlcv(START.replace("-", ""), END.replace("-", ""), code)
            return df if len(df) else None
        except Exception as e:   # pykrx는 로그인 미설정 시 KeyError 등 예외를 던짐
            print(f"[INFO] pykrx 지수 {code} 실패: {type(e).__name__}")
            return None
    k200 = _try_pykrx("1028")     # KOSPI 200
    krx300 = _try_pykrx("1035")   # KRX 300 (예비 — BM 재확인 대비)
    if k200 is None:   # yfinance ^KS200 예비 경로
        ks = yf.Ticker("^KS200").history(start=START, end=END, auto_adjust=False)
        if not ks.empty:
            k200 = pd.DataFrame({"종가": ks["Close"].round(2).values}, index=ks.index)
            print("[INFO] KOSPI200: pykrx 실패 → yfinance ^KS200 예비 경로 사용 (출처 기록 필요)")
        else:
            print("[FAIL] KOSPI200 전 경로 실패 — KRX 정보데이터시스템 수동 CSV 후 convert_krx_csv() 사용")
            k200 = pd.DataFrame({"종가": []})
    if krx300 is None:
        print("[WARN] KRX300 예비 시계열 미확보 — BM 재확인 표결 시 수동 CSV로 보완 (파일럿 필수 아님)")
        krx300 = pd.DataFrame({"종가": []})
    rua = yf.Ticker("^RUA").history(start=START, end=END, auto_adjust=False)             # Russell 3000
    if rua.empty:
        print("[WARN] ^RUA 0행 — ^RUI(Russell 1000) 대체 검토·기록 필요")
    bm_kr = pd.DataFrame({"market_date": [d.strftime("%Y-%m-%d") for d in k200.index], "close": k200["종가"].values})
    bm_us = pd.DataFrame({"market_date": [d.strftime("%Y-%m-%d") for d in rua.index], "close": rua["Close"].round(4).values})
    if len(bm_kr):
        bm_kr.to_csv(os.path.join(out, "bm_kr.csv"), index=False)
    bm_us.to_csv(os.path.join(out, "bm_us.csv"), index=False)
    if not len(bm_kr):
        print("[WARN] bm_kr 미생성 — calendar.csv의 KR 개장일이 비므로, bm_kr 확보 후 rebuild_calendar() 필수")
    if len(krx300):
        pd.DataFrame({"market_date": [d.strftime("%Y-%m-%d") for d in krx300.index],
                      "close": krx300["종가"].values}).to_csv(os.path.join(out, "bm_kr_krx300_reserve.csv"), index=False)

    # calendar.csv — 개장일 판정: 지수 시계열에 행이 있는 날 = 해당 시장 개장일 (거래소 공식 달력 검증은 QA에서)
    all_days = pd.bdate_range(START, END).strftime("%Y-%m-%d")
    kr_open, us_open = set(bm_kr["market_date"]), set(bm_us["market_date"])
    cal = [{"market": m, "market_date": d, "is_market_open": int(d in s)}
           for d in all_days for m, s in (("KR", kr_open), ("US", us_open))]
    pd.DataFrame(cal).to_csv(os.path.join(out, "calendar.csv"), index=False)
    n_common = sum(1 for d in all_days if d in kr_open and d in us_open)
    print(f"bm_kr {len(bm_kr)}행 / bm_us {len(bm_us)}행 / krx300 예비 {len(krx300)}행 / calendar 공통 개장일 {n_common}일")


def collect_fx(out: str):
    import os as _os, urllib.request
    key = _os.environ.get("ECOS_API_KEY")
    if not key:
        print("[WARN] ECOS_API_KEY 없음 — ECOS 웹에서 원/달러 일별 CSV 수동 다운로드 후 fx.csv(market_date,fx_rate)로 저장")
        return
    stat, item = ECOS_FX_STAT
    url = (f"https://ecos.bok.or.kr/api/StatisticSearch/{key}/json/kr/1/500/{stat}/D/"
           f"{START.replace('-','')}/{END.replace('-','')}/{item}")
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.loads(r.read())
    rows = data.get("StatisticSearch", {}).get("row", [])
    fx = pd.DataFrame({"market_date": [f"{x['TIME'][:4]}-{x['TIME'][4:6]}-{x['TIME'][6:]}" for x in rows],
                       "fx_rate": [float(x["DATA_VALUE"]) for x in rows]})
    fx.to_csv(os.path.join(out, "fx.csv"), index=False)
    print(f"fx.csv {len(fx)}행 (계열 {stat}/{item} — 잠정, 데이터사전 확정 대기)")


def convert_krx_csv(krx_csv_path: str, out_path: str):
    """KRX 정보데이터시스템 수동 다운로드 CSV(일자/종가, 한글 헤더·천단위 콤마) → bm 스키마 변환"""
    df = pd.read_csv(krx_csv_path, encoding="cp949")
    date_col = [c for c in df.columns if "일자" in c][0]
    close_col = [c for c in df.columns if "종가" in c][0]
    out = pd.DataFrame({
        "market_date": pd.to_datetime(df[date_col].astype(str).str.replace("/", "-")).dt.strftime("%Y-%m-%d"),
        "close": df[close_col].astype(str).str.replace(",", "").astype(float)})
    out = out.sort_values("market_date")
    out = out[(out["market_date"] >= START) & (out["market_date"] < END)]
    out.to_csv(out_path, index=False)
    print(f"{out_path} {len(out)}행 변환 완료")


def rebuild_calendar(out: str):
    """bm_kr.csv 보완 후 달력만 재생성 (재다운로드 없이)"""
    bm_kr = pd.read_csv(os.path.join(out, "bm_kr.csv"))
    bm_us = pd.read_csv(os.path.join(out, "bm_us.csv"))
    all_days = pd.bdate_range(START, END).strftime("%Y-%m-%d")
    kr_open, us_open = set(bm_kr["market_date"]), set(bm_us["market_date"])
    cal = [{"market": m, "market_date": d, "is_market_open": int(d in s)}
           for d in all_days for m, s in (("KR", kr_open), ("US", us_open))]
    pd.DataFrame(cal).to_csv(os.path.join(out, "calendar.csv"), index=False)
    n = sum(1 for d in all_days if d in kr_open and d in us_open)
    print(f"calendar.csv 재생성 — 공통 개장일 {n}일")
    # 사용: python -c "import collect_pilot_inputs as c; c.convert_krx_csv('다운로드.csv','input_data/bm_kr.csv'); c.rebuild_calendar('input_data')"


if __name__ == "__main__":
    basket_path = sys.argv[1] if len(sys.argv) > 1 else "seed_basket.csv"
    out = sys.argv[2] if len(sys.argv) > 2 else "input_data"
    os.makedirs(out, exist_ok=True)
    basket = pd.read_csv(basket_path, dtype={"security_id": str})
    us_tickers = basket[basket["market"] == "US"]["security_id"].tolist()
    print(f"미국 대상 {len(us_tickers)}종목: {us_tickers}")
    collect_us_prices(us_tickers, out)
    collect_indices_and_calendar(out)
    collect_fx(out)
    print("완료 — 산출 CSV를 repo 또는 세션에 공유하면 드라이런 시작 가능")
