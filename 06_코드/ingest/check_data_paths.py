# -*- coding: utf-8 -*-
"""데이터 경로 실체 확인 스크립트 — 팀 로컬 환경에서 실행 (클라우드 세션은 외부 시세망 차단).
사용: pip install pykrx yfinance 후 python check_data_paths.py
각 경로의 성공/실패와 표본 값을 출력. 전부 성공해야 파일럿 수집 착수."""
import sys
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try: _s.reconfigure(encoding="utf-8")   # Windows cp949 콘솔에서 —·→ 등 출력 깨짐 방지
    except Exception: pass

def check(name, fn):
    try:
        msg = fn()
        print(f"[OK]   {name}: {msg}")
        return True
    except Exception as e:
        print(f"[FAIL] {name}: {type(e).__name__} {str(e)[:160]}")
        return False

def krx_stock():
    from pykrx import stock
    df = stock.get_market_ohlcv("20260622", "20260630", "005930")
    assert len(df) > 0 and "거래대금" in df.columns, f"행 {len(df)}, 컬럼 {list(df.columns)}"
    return f"삼성전자 {len(df)}행, 거래대금 컬럼 확인 (KRX 제공값 — 제59조 복원안의 공식 경로)"

def krx_index():
    from pykrx import stock
    kospi200 = stock.get_index_ohlcv("20260622", "20260630", "1028")   # KOSPI 200
    krx300 = stock.get_index_ohlcv("20260622", "20260630", "1035")     # KRX 300 (예비 — BM 재확인 대비)
    assert len(kospi200) > 0 and len(krx300) > 0
    return f"KOSPI200 {len(kospi200)}행 / KRX300 {len(krx300)}행"

def yahoo_us():
    import yfinance as yf
    df = yf.download("LMT", start="2026-06-22", end="2026-07-01", auto_adjust=False, progress=False)
    assert len(df) > 0, "0행"
    return f"LMT {len(df)}행 (auto_adjust=False, 비조정 Close·Volume)"

def yahoo_rua():
    import yfinance as yf
    df = yf.download("^RUA", start="2026-06-22", end="2026-07-01", auto_adjust=False, progress=False)
    assert len(df) > 0, "0행 — 실패 시 ^RUI(Russell 1000) 대체 검토·기록"
    return f"Russell 3000(^RUA) {len(df)}행"

def ecos():
    import os, urllib.request, json
    key = os.environ.get("ECOS_API_KEY")
    if not key:
        raise RuntimeError("ECOS_API_KEY 환경변수 없음 — API 키 발급 필요 또는 수동 CSV 경로로 전환")
    url = f"https://ecos.bok.or.kr/api/StatisticSearch/{key}/json/kr/1/5/731Y001/D/20260622/20260630/0000001"
    with urllib.request.urlopen(url, timeout=20) as r:
        data = json.loads(r.read())
    rows = data.get("StatisticSearch", {}).get("row", [])
    assert rows, f"응답에 row 없음: {str(data)[:150]}"
    return f"원/달러 {len(rows)}행 (계열 731Y001 — 계열코드는 데이터사전 확정 대기)"

if __name__ == "__main__":
    results = [check("KRX 개별종목 OHLCV+거래대금 (pykrx)", krx_stock),
               check("KRX 지수 KOSPI200·KRX300 (pykrx)", krx_index),
               check("미국 개별종목 (yfinance)", yahoo_us),
               check("Russell 3000 ^RUA (yfinance)", yahoo_rua),
               check("ECOS 원/달러 환율 API", ecos)]
    print(f"\n{sum(results)}/{len(results)} 경로 통과" + ("" if all(results) else " — 실패 경로는 계획서 4장 대비책으로 전환"))
    sys.exit(0 if all(results) else 1)
