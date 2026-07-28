# -*- coding: utf-8 -*-
"""
DART 공시 원문 식별자 수집 — 기업행사 근거 확보용

배경
  010120 액면분할의 비율(5:1)은 액면가 변경으로 확정됐으나, 근거가 언론 보도다.
  회의안 §5 근거자료에 올리려면 공시 원문 접수번호(rcept_no)가 필요하다.

접근 시도 결과 (2026-07-28)
  OpenDART API   엔드포인트 정상. {"status":"010","message":"등록되지 않은 인증키입니다."}
                 -> 인증키만 있으면 즉시 수집 가능
  DART 웹 검색    JS/POST 구동. 정적 요청으로는 빈 껍데기만 반환
  KIND 뷰어       acptno를 알면 메타데이터는 서버 렌더링됨. 목록 열거는 불가

따라서 인증키가 유일한 차단 요소다.

사전 준비 (1회, 약 1분)
  1) https://opendart.fss.or.kr 에서 무료 인증키 발급
  2) 06_코드/ingest/.env (없으면 engine/.env)에 추가
       DART_API_KEY=발급받은키
     .env는 .gitignore로 차단돼 있다. 저장소가 공개이므로 절대 커밋하지 않는다.

실행
  python fetch_dart.py                          # 010120, 2026-01-01~04-30
  python fetch_dart.py --corp-name 엘에스일렉트릭
  python fetch_dart.py --bgn 20260101 --end 20260430 --keyword 분할

이 스크립트는 조회만 한다. 산출물을 갱신하거나 규칙을 바꾸지 않는다.
"""
import argparse
import io
import os
import sys
import zipfile
import xml.etree.ElementTree as ET

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
QA = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, QA)
from paths import env_path, force_utf8_stdout  # noqa: E402

API = "https://opendart.fss.or.kr/api"
VIEWER = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo="
DEFAULT_STOCK = "010120"


def load_key() -> str:
    p = env_path()
    if not p:
        raise SystemExit("[중단] .env를 찾지 못했다. ingest/.env 또는 engine/.env 필요.")
    key = ""
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("DART_API_KEY="):
                key = line.split("=", 1)[1].strip()
    if not key:
        raise SystemExit(
            f"[중단] {p} 에 DART_API_KEY가 없다.\n"
            "       https://opendart.fss.or.kr 에서 무료 발급 후 한 줄 추가하면 된다.\n"
            "       발급키는 채팅·커밋에 노출하지 않는다."
        )
    return key


def resolve_corp_code(key: str, stock_code: str, corp_name: str) -> tuple:
    """고유번호 전체목록(corpCode.xml)에서 종목코드로 corp_code를 찾는다.

    제3자 사이트에 적힌 corp_code를 그대로 쓰지 않는다. 근거자료로 쓸 값이므로
    원출처인 OpenDART 목록에서 확인한다.
    """
    r = requests.get(f"{API}/corpCode.xml", params={"crtfc_key": key}, timeout=60)
    r.raise_for_status()
    if r.content[:2] != b"PK":  # zip이 아니면 에러 JSON
        raise SystemExit(f"[중단] corpCode 응답이 zip이 아니다: {r.text[:200]}")
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        xml = z.read(z.namelist()[0])
    root = ET.fromstring(xml)
    for item in root.iter("list"):
        sc = (item.findtext("stock_code") or "").strip()
        nm = (item.findtext("corp_name") or "").strip()
        if stock_code and sc == stock_code:
            return item.findtext("corp_code").strip(), nm
        if corp_name and nm == corp_name:
            return item.findtext("corp_code").strip(), nm
    raise SystemExit(f"[중단] corp_code 미발견 (stock={stock_code} name={corp_name})")


def list_filings(key: str, corp_code: str, bgn: str, end: str) -> list:
    out, page = [], 1
    while True:
        r = requests.get(f"{API}/list.json", timeout=30, params={
            "crtfc_key": key, "corp_code": corp_code,
            "bgn_de": bgn, "end_de": end,
            "page_no": page, "page_count": 100,
        })
        r.raise_for_status()
        j = r.json()
        if j.get("status") == "013":      # 조회 결과 없음
            break
        if j.get("status") != "000":
            raise SystemExit(f"[중단] status={j.get('status')} {j.get('message')}")
        out.extend(j.get("list", []))
        if page >= int(j.get("total_page", 1)):
            break
        page += 1
    return out


def main():
    force_utf8_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("--stock-code", default=DEFAULT_STOCK)
    ap.add_argument("--corp-name", default="")
    ap.add_argument("--corp-code", default="", help="알고 있으면 조회 생략")
    ap.add_argument("--bgn", default="20260101")
    ap.add_argument("--end", default="20260430")
    ap.add_argument("--keyword", default="분할", help="보고서명 필터 (빈 값이면 전체)")
    args = ap.parse_args()

    key = load_key()
    if args.corp_code:
        corp_code, corp_name = args.corp_code, "(미확인)"
    else:
        corp_code, corp_name = resolve_corp_code(key, args.stock_code, args.corp_name)
    print(f"[대상] {corp_name}  stock={args.stock_code}  corp_code={corp_code}")
    print(f"[기간] {args.bgn} ~ {args.end}\n")

    rows = list_filings(key, corp_code, args.bgn, args.end)
    hits = [x for x in rows
            if not args.keyword or args.keyword in x.get("report_nm", "")]

    if not hits:
        print(f"[결과] 전체 {len(rows)}건 중 '{args.keyword}' 포함 0건.")
        print("       키워드를 비우고(--keyword '') 전체 목록을 확인해 볼 것.")
        return

    print(f"[결과] 전체 {len(rows)}건 중 {len(hits)}건 일치\n")
    for x in hits:
        print(f"  접수일자 {x['rcept_dt']}   접수번호 {x['rcept_no']}")
        print(f"  보고서명 {x['report_nm']}")
        print(f"  제출인   {x.get('flr_nm', '')}")
        print(f"  원문     {VIEWER}{x['rcept_no']}")
        print()

    print("EVIDENCE.md §5-2 대체 문안 (수집 성공 시):")
    top = hits[0]
    print(f"  공시 원문 확보 — DART 접수번호 {top['rcept_no']} "
          f"({top['rcept_dt']}, {top['report_nm']})")
    print(f"  {VIEWER}{top['rcept_no']}")


if __name__ == "__main__":
    main()
