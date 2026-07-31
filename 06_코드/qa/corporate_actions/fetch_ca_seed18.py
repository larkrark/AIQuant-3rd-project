# -*- coding: utf-8 -*-
"""
Seed18 기업행사 공시 일괄 조회 — 원장 구축용 1단계

배경
  QA 소견 F-3: 현재 파이프라인은 가격 수집·공시 수집 어느 쪽에서도
  기업행사(액면분할·병합·증자·감자·합병·상호변경)를 가져오지 않는다.
  담당표(260722) 원자료 수집 항목 16~18행에 해당 칸 자체가 없다.

  010120 액면분할 1건 반영으로 파일럿 지수가 6.66%p 이동했다.
  나머지 8종목에 같은 사건이 있는지는 미조회 상태다.

독립성 등급 (2026-07-31 강등 선언)
  PRIOR_INDEPENDENT -> POST_DISCLOSURE_MECHANICAL
  사유: 발표 일정상 담당자 대기 불가, QA가 수집 대행.
  경계 유지: 이 스크립트는 조회만 한다. 비율·효력일 판정은 사람이 원문을 보고
            reviewed_* 칸에 후보로 적으며, approved_* 는 팀 승인 후에만 채운다
            (데이터사전 v0.8 §4).

corp_code 출처
  crosscheck_kr9/out/kr9_corp_code_crosscheck.csv — 3자 대조 9/9 MATCH 완료본.
  재조회하지 않는다(이미 검증된 값을 다시 뽑으면 대조 기록이 무의미해진다).

실행
  python fetch_ca_seed18.py                    # 2025-10-01 ~ 2026-06-30
  python fetch_ca_seed18.py --all              # 키워드 필터 없이 전량
  python fetch_ca_seed18.py --bgn 20260101 --end 20260430
"""
import argparse
import csv
import os
import sys

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
QA = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, QA)
from paths import env_path, force_utf8_stdout  # noqa: E402

API = "https://opendart.fss.or.kr/api"
VIEWER = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo="

CORP_REF = os.path.join(QA, "crosscheck_kr9", "out", "kr9_corp_code_crosscheck.csv")
OUT = os.path.join(HERE, "out")

# 조회 기간 — ADTV90 창 시작까지 소급한다.
#   2026-03-31 회차의 90 개장일 창은 2025-11월경까지 거슬러 간다.
#   지수 구간(2026-04-01~06-30)만 보면 창 안에서 일어난 사건을 놓친다.
BGN, END = "20251001", "20260630"

# 넓게 잡고 사람이 거른다. 좁히면 보고서명 표기 차이로 누락된다.
#   예) "주요사항보고서(주식분할결정)" / "[기재정정]주요사항보고서(주식분할결정)"
KEYWORDS = [
    "분할", "병합", "액면",          # 액면분할·주식병합·물적/인적분할·분할합병
    "증자", "감자",                  # 무상증자·유상증자(권리락)·감자
    "합병",
    "상호", "회사명", "사명",        # 상호변경 (079550 사례)
    "주식배당",
]


def load_key() -> str:
    p = env_path()
    if not p:
        raise SystemExit("[중단] .env를 찾지 못했다. ingest/.env 또는 engine/.env 필요.")
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if line.startswith("DART_API_KEY="):
            key = line.split("=", 1)[1].strip()
            if key:
                return key
    raise SystemExit("[중단] DART_API_KEY 없음. .env는 커밋 금지(저장소 공개).")


def load_targets() -> list:
    """대조 완료본에서 (종목코드, 회사명, corp_code)를 읽는다."""
    if not os.path.exists(CORP_REF):
        raise SystemExit(f"[중단] corp_code 대조본 없음: {CORP_REF}")
    out = []
    with open(CORP_REF, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row.get("corp_code_verdict") != "MATCH":
                print(f"[경고] corp_code 미대조 종목 건너뜀: {row.get('security_id')}")
                continue
            out.append((row["security_id"], row["dart_corp_name"],
                        row["corp_code_qa_lookup"]))
    return out


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
    ap.add_argument("--bgn", default=BGN)
    ap.add_argument("--end", default=END)
    ap.add_argument("--all", action="store_true", help="키워드 필터 없이 전량 저장")
    args = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    key = load_key()
    targets = load_targets()

    print(f"[대상] KR {len(targets)}종목   [기간] {args.bgn} ~ {args.end}")
    print(f"[키워드] {' '.join(KEYWORDS)}\n")

    all_rows, hits = [], []
    for sec, name, corp in targets:
        rows = list_filings(key, corp, args.bgn, args.end)
        for x in rows:
            x["security_id"] = sec
            x["qa_corp_code"] = corp
        all_rows.extend(rows)
        hit = [x for x in rows
               if any(k in x.get("report_nm", "") for k in KEYWORDS)]
        hits.extend(hit)
        mark = f"  <-- {len(hit)}건" if hit else ""
        print(f"  {sec} {name:<20} 전체 {len(rows):>3}건{mark}")

    cols = ["security_id", "qa_corp_code", "corp_name", "rcept_dt", "rcept_no",
            "report_nm", "flr_nm", "rm"]

    def dump(path, rows):
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for x in sorted(rows, key=lambda r: (r["security_id"], r["rcept_dt"])):
                w.writerow(x)

    dump(os.path.join(OUT, "dart_filings_raw.csv"), all_rows)
    dump(os.path.join(OUT, "dart_ca_hits.csv"), hits)

    print(f"\n[결과] 전체 {len(all_rows)}건 중 키워드 일치 {len(hits)}건")
    print(f"       out/dart_filings_raw.csv   전량 (누락 확인용)")
    print(f"       out/dart_ca_hits.csv       필터 결과")

    if not hits:
        print("\n[판정] 기업행사 후보 0건. 010120 외 추가 사건 없음으로 잠정 확인.")
        print("       단 키워드 누락 가능성은 dart_filings_raw.csv 로 직접 확인할 것.")
        return

    print("\n--- 원문 판독 대상 (효력일 / 상장·재개일 분리 확인) ---\n")
    for x in sorted(hits, key=lambda r: (r["security_id"], r["rcept_dt"])):
        print(f"  {x['security_id']}  {x['rcept_dt']}  {x['report_nm']}")
        print(f"      {VIEWER}{x['rcept_no']}")
    print("\n  [기재정정] 표기가 있으면 원본이 아니라 정정본을 근거로 삼는다.")
    print("  효력일과 신주권상장·거래재개일은 반드시 별도 칸에 적는다")
    print("  (010120 사례: 04-10 vs 04-13 이 연변동성 42.40% <-> 71.77% 를 갈랐다).")


if __name__ == "__main__":
    main()
