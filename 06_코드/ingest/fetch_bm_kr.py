# -*- coding: utf-8 -*-
"""KOSPI 200 PR 원계열 수집 — BM 한국 원계열 교체용 (2026-07-31, 권보성)

기존 입력을 덮어쓰지 않는다. 새 파일로만 쓴다.
    ../data/input_data/bm_kr_krx1028.csv

사용
  py fetch_bm_kr.py            pykrx (.env 의 KRX_ID / KRX_PW 자동 로드)
  py fetch_bm_kr.py --krx      KRX 데이터시스템 직접 호출 (계정 불필요)
  py fetch_bm_kr.py "경로.csv" 수동 다운로드 CSV 변환
"""
import sys, os, hashlib
for s in (sys.stdout, sys.stderr):
    try: s.reconfigure(encoding="utf-8")
    except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))

# --- .env 로드 (collect_pilot_inputs.py 와 동일 방식) --------------------------
_p = os.path.join(HERE, ".env")
if os.path.exists(_p):
    for _l in open(_p, encoding="utf-8-sig"):
        if "=" in _l and not _l.strip().startswith("#"):
            k, v = _l.strip().split("=", 1)
            os.environ.setdefault(k.strip().lstrip("﻿"), v.strip().strip('"').strip("'"))
print("[env] KRX_ID", "설정됨" if os.environ.get("KRX_ID") else "없음",
      "/ KRX_PW", "설정됨" if os.environ.get("KRX_PW") else "없음")

import pandas as pd

START, END = "2025-10-01", "2026-07-01"
CODE = "1028"
OUT = os.path.join(HERE, "..", "data", "input_data", "bm_kr_krx1028.csv")


def from_manual_csv(path):
    df = None
    for enc in ("cp949", "utf-8-sig", "utf-8", "euc-kr"):
        try:
            df = pd.read_csv(path, encoding=enc); break
        except Exception:
            continue
    if df is None:
        print(f"[FAIL] CSV 읽기 실패: {path}"); sys.exit(1)
    print(f"[INFO] 열: {list(df.columns)}")
    dc = [c for c in df.columns if "일자" in c or "날짜" in c]
    cc = [c for c in df.columns if "종가" in c or "체결가" in c]
    if not dc or not cc:
        print("[FAIL] '일자'/'종가' 열 없음 — 위 열 목록을 알려주면 매핑한다"); sys.exit(1)
    d = df[dc[0]].astype(str).str.replace("/", "-").str.replace(".", "-", regex=False).str.strip()
    v = df[cc[0]].astype(str).str.replace(",", "").str.strip()
    return pd.DataFrame({"market_date": pd.to_datetime(d, errors="coerce").dt.strftime("%Y-%m-%d"),
                         "close": pd.to_numeric(v, errors="coerce")}).dropna()


def from_krx_direct():
    """개별지수 시세추이 MDCSTAT00301. 세션 쿠키 선취득 후 POST."""
    import requests, json
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "ko-KR,ko;q=0.9",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://data.krx.co.kr",
        "Referer": "https://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201020101",
    })
    try:
        s.get("https://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201020101",
              timeout=20)
    except Exception as e:
        print(f"[WARN] 쿠키 선취득 실패: {type(e).__name__}")

    payload = {
        "bld": "dbms/MDC/STAT/standard/MDCSTAT00301",
        "locale": "ko_KR",
        "tboxindIdx_finder_equidx0_0": "코스피 200",
        "indIdx": "1",
        "indIdx2": "028",
        "codeNmindIdx_finder_equidx0_0": "코스피 200",
        "param1indIdx_finder_equidx0_0": "",
        "strtDd": START.replace("-", ""),
        "endDd": END.replace("-", ""),
        "share": "2",
        "money": "3",
        "csvxls_isNo": "false",
    }
    r = s.post("https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd",
               data=payload, timeout=30)
    print(f"[INFO] HTTP {r.status_code}  len={len(r.content)}")
    if r.status_code != 200:
        print("[FAIL] 응답 앞부분:"); print(r.text[:300]); sys.exit(1)
    try:
        data = r.json()
    except Exception:
        print("[FAIL] JSON 아님. 응답 앞부분:"); print(r.text[:300]); sys.exit(1)
    rows = data.get("output") or data.get("OutBlock_1") or []
    if not rows:
        print(f"[FAIL] 0행. 응답 키: {list(data.keys())}"); print(str(data)[:300]); sys.exit(1)
    print(f"[INFO] 첫 행 키: {list(rows[0].keys())}")
    dk = "TRD_DD" if "TRD_DD" in rows[0] else [k for k in rows[0] if "DD" in k][0]
    ck = "CLSPRC_IDX" if "CLSPRC_IDX" in rows[0] else [k for k in rows[0] if "CLSPRC" in k][0]
    return pd.DataFrame({"market_date": [str(r_[dk]).replace("/", "-") for r_ in rows],
                         "close": [float(str(r_[ck]).replace(",", "")) for r_ in rows]})


def from_pykrx():
    try:
        from pykrx import stock
    except ImportError:
        print("[FAIL] pykrx 미설치 —  py -m pip install pykrx"); sys.exit(1)
    try:
        df = stock.get_index_ohlcv(START.replace("-", ""), END.replace("-", ""), CODE)
    except Exception as e:
        print(f"[FAIL] pykrx 호출 실패: {type(e).__name__}: {e}")
        print("       →  py fetch_bm_kr.py --krx   로 재시도")
        sys.exit(1)
    if df is None or not len(df):
        print("[FAIL] 0행 반환"); sys.exit(1)

    # --- 출처 판별용 원 DataFrame 보존 (QA 요청 2026-07-31) --------------------
    # get_index_ohlcv 는 시가·고가·저가·종가·거래량·거래대금 6열을 반환한다.
    # 야후 ^KS200 에는 KRX 거래대금이 없으므로 이 열이 경로를 판별한다.
    full = df.copy()
    full.insert(0, "market_date", [d.strftime("%Y-%m-%d") for d in df.index])
    full_path = os.path.join(HERE, "..", "data", "input_data", "bm_kr_krx1028_full.csv")
    full.to_csv(full_path, index=False, encoding="utf-8-sig")
    print(f"[SRC] 원 DataFrame 열: {list(df.columns)}")
    for _c in df.columns:
        if "거래대금" in _c or "거래량" in _c:
            _v = pd.to_numeric(df[_c], errors="coerce")
            print(f"[SRC] {_c}: 비영 {int((_v > 0).sum())}/{len(_v)}행  "
                  f"최소 {_v.min():,.0f}  최대 {_v.max():,.0f}")
    _h = hashlib.sha256(open(full_path, "rb").read()).hexdigest()
    print(f"[SRC] bm_kr_krx1028_full.csv  {len(full)}행  sha256 {_h}")

    col = "종가" if "종가" in df.columns else df.columns[3]
    return pd.DataFrame({"market_date": [d.strftime("%Y-%m-%d") for d in df.index],
                         "close": df[col].values})


arg = sys.argv[1] if len(sys.argv) > 1 else None
if arg == "--krx":
    out = from_krx_direct()
elif arg:
    out = from_manual_csv(arg)
else:
    out = from_pykrx()

out = out[(out["market_date"] >= START) & (out["market_date"] <= END)]
out = out.drop_duplicates("market_date").sort_values("market_date")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
out.to_csv(OUT, index=False, encoding="utf-8")

h = hashlib.sha256(open(OUT, "rb").read()).hexdigest()
print(f"[OK] bm_kr_krx1028.csv  {len(out)}행  {out['market_date'].iloc[0]} ~ {out['market_date'].iloc[-1]}")
print(f"     종가 {out['close'].iloc[0]} -> {out['close'].iloc[-1]}")
print(f"     sha256 {h}")
print("     ※ bm_kr.csv 는 그대로. 대조 후 교체한다.")
