# -*- coding: utf-8 -*-
"""KR9 corp_code 독립 교차검토 — Stage 14-3 인계본 대조

대상
  review/kim-geun-hyung-stage14-3-frozen 브랜치의
  handoff/kr9_dart_rceptno_validator_git_ready_20260728/data/
  KR9_COMPANY_CORPCODE_REFERENCE_FILLED.csv  (9종목 corp_code)

왜 이 대조가 성립하는가
  인계본은 corp_code를 englishdart 회사팝업(englishdart.fss.or.kr/dsbc001)에서 확인했다.
  이 스크립트는 OpenDART 고유번호 전체목록(corpCode.xml)에서 확인한다.
  같은 기관의 서로 다른 배포경로이므로, 두 값이 일치하면 전사(轉寫) 오류가 배제된다.
  일치하더라도 "이 회사가 테마에 적격한가"는 확인하지 않는다 — §미확인 참조.

독립성 등급 — 두 종류를 구분해서 기록한다
  PRIOR_INDEPENDENT           인계본을 보기 전에 이미 확정한 값
                              010120: qa 커밋 095e59f 2026-07-28 13:53:45 +0900
                              인계본:  커밋 e825f4c 2026-07-28 16:49:01 +0900
                              -> 2시간 55분 앞선다. git 타임스탬프로 검증 가능한 블라인드.
  POST_DISCLOSURE_MECHANICAL  인계본을 본 뒤에 조회한 값
                              나머지 8종목. 조회가 결정적(종목코드->고유번호 단순 대응)이고
                              조회 코드도 07-28에 이미 작성돼 있었으므로 확증편향 여지는
                              작지만, 블라인드는 아니다. 등급을 낮춰 기록한다.

실행
  python verify_corp_code.py
  종료코드 0 = 전건 일치 / 1 = 불일치 있음

이 스크립트는 조회·대조만 한다. 인계본을 수정하지 않고, 산출물로 승격하지 않는다.
"""
import csv
import io
import os
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import paths as P  # noqa: E402

API = "https://opendart.fss.or.kr/api"

# 인계본을 커밋 SHA로 고정한다. 브랜치명으로 읽으면 상대가 force-push 했을 때
# 대조 대상이 조용히 바뀌어, 무엇과 비교한 기록인지 알 수 없게 된다.
PIN = "ed6a23f"
REF = ("handoff/kr9_dart_rceptno_validator_git_ready_20260728/"
       "data/KR9_COMPANY_CORPCODE_REFERENCE_FILLED.csv")

# 인계본을 보기 전에 확정한 값 — 대조 상대가 아니라 나의 사전기록이다.
PRIOR = {"010120": ("00105855", "095e59f", "2026-07-28 13:53:45 +0900")}

OUT = os.path.join(HERE, "out")


def git_show(path: str) -> str:
    r = subprocess.run(["git", "show", f"{PIN}:{path}"],
                       cwd=P.ROOT, capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"[중단] git show 실패 — {PIN} 를 fetch 했는가?\n{r.stderr.decode(errors='replace')}")
    return r.stdout.decode("utf-8-sig")


def load_key() -> str:
    p = P.env_path()
    if not p:
        raise SystemExit("[중단] .env 없음 (ingest/.env 또는 engine/.env)")
    for line in open(p, encoding="utf-8"):
        if line.strip().startswith("DART_API_KEY="):
            return line.strip().split("=", 1)[1].strip()
    raise SystemExit(f"[중단] {p} 에 DART_API_KEY 없음")


def corp_code_table(key: str) -> dict:
    """corpCode.xml 전체를 한 번만 받아 {종목코드: (고유번호, 회사명)} 로 만든다.

    종목당 한 번씩 받으면 같은 대용량 zip을 9번 내려받는다. 원출처 확인이라는
    성질은 같으므로 한 번 받아 나눠 쓴다.
    """
    r = requests.get(f"{API}/corpCode.xml", params={"crtfc_key": key}, timeout=120)
    r.raise_for_status()
    if r.content[:2] != b"PK":
        raise SystemExit(f"[중단] corpCode 응답이 zip이 아니다: {r.text[:200]}")
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        root = ET.fromstring(z.read(z.namelist()[0]))
    out = {}
    for it in root.iter("list"):
        sc = (it.findtext("stock_code") or "").strip()
        if sc:                                    # 비상장은 종목코드가 빈칸
            out[sc] = ((it.findtext("corp_code") or "").strip(),
                       (it.findtext("corp_name") or "").strip())
    return out


def company_info(key: str, corp_code: str) -> dict:
    """company.json — 현재 법인명·종목명·영문명.

    corp_code 가 맞아도 회사 이름이 바뀌었을 수 있다. 이름이 바뀐 것은 오류가 아니지만,
    프로젝트 문서가 옛 이름으로 적혀 있으면 이름 기준으로 붙인 자료가 어긋난다.
    영문명을 함께 받는 이유: 한글 음역차이(삼성SDS/삼성에스디에스)와 실제 개명을
    사람이 구분할 수 있는 근거가 영문명이다.
    """
    j = requests.get(f"{API}/company.json", timeout=30,
                     params={"crtfc_key": key, "corp_code": corp_code}).json()
    if j.get("status") != "000":
        return {}
    return {"corp_name": j.get("corp_name", ""), "stock_name": j.get("stock_name", ""),
            "corp_name_eng": j.get("corp_name_eng", "")}


def main() -> int:
    P.force_utf8_stdout()
    os.makedirs(OUT, exist_ok=True)

    ref = list(csv.DictReader(io.StringIO(git_show(REF))))
    print(f"[대조 대상] {PIN}:{os.path.basename(REF)}  {len(ref)}행\n")

    # ── 검사 1. 유니버스 정합 — DART 없이 가능하다 ────────────────
    # 인계본의 9종목이 유니버스 정본과 같은 집합인지 먼저 본다. 집합이 다르면
    # corp_code가 맞아도 "무엇의 유니버스인지"가 어긋난 것이므로 값 비교가 무의미하다.
    seed = list(csv.DictReader(open(P.UNIVERSE, encoding="utf-8-sig")))
    seed_kr = {r["security_id"] for r in seed if r["market"] == "KR"}
    ref_ids = {r["security_id"] for r in ref}
    print(f"1) 유니버스 정합 — {os.path.relpath(P.UNIVERSE, P.ROOT)} KR 집합 대조")
    if seed_kr == ref_ids:
        print(f"   [일치] {len(ref_ids)}종목 집합 동일\n")
    else:
        print(f"   [불일치] 인계본에만 {sorted(ref_ids - seed_kr)} / "
              f"정본에만 {sorted(seed_kr - ref_ids)}\n")

    # ── 검사 2. corp_code 원출처 대조 ─────────────────────────────
    print("2) corp_code — corpCode.xml(원출처) 대조")
    key = load_key()
    tbl = corp_code_table(key)
    print(f"   corpCode.xml 상장사 {len(tbl):,}건 수신\n")

    rows, mismatch = [], 0
    for r in sorted(ref, key=lambda x: x["security_id"]):
        sid = r["security_id"]
        theirs = r["corp_code"].strip()
        mine, dart_name = tbl.get(sid, ("", ""))

        ok = bool(mine) and mine == theirs
        if not ok:
            mismatch += 1
        # 회사명은 참고로만 비교한다. 프로젝트 표기(LG CNS)와 DART 법인명이
        # 다를 수 있고, 이는 오류가 아니라 표기 차이다.
        name_same = r["project_company_name"].strip() == dart_name

        if sid in PRIOR:
            grade, note = "PRIOR_INDEPENDENT", f"{PRIOR[sid][1]} {PRIOR[sid][2]}"
            # 사전기록과도 어긋나면 내 기록 쪽을 의심해야 한다.
            if mine and mine != PRIOR[sid][0]:
                note += f" / 사전기록 {PRIOR[sid][0]} 와 불일치"
                mismatch += 1
        else:
            grade, note = "POST_DISCLOSURE_MECHANICAL", ""

        info = company_info(key, mine) if mine else {}
        eng = info.get("corp_name_eng", "")
        # 음역차이인지 개명인지는 사람이 영문명을 보고 판정한다. 스크립트는
        # "이름이 다르다"까지만 말하고, 어느 쪽인지는 단정하지 않는다.
        name_verdict = "SAME" if name_same else "DIFFERS_REVIEW_REQUIRED"

        mark = "일치" if ok else "★불일치★"
        print(f"   {sid}  인계 {theirs}  내조회 {mine or '(미발견)'}  {mark}")
        if not name_same:
            print(f"           이름 다름 — 프로젝트 '{r['project_company_name']}'"
                  f" / DART '{info.get('stock_name', dart_name)}' / {eng}")
        rows.append({
            "security_id": sid,
            "project_company_name": r["project_company_name"],
            "dart_corp_name": dart_name,
            "dart_stock_name": info.get("stock_name", ""),
            "dart_corp_name_eng": eng,
            "name_verdict": name_verdict,
            "corp_code_handoff": theirs,
            "corp_code_qa_lookup": mine,
            "corp_code_verdict": "MATCH" if ok else "MISMATCH",
            "corp_name_note": "SAME" if name_same else "NOTATION_DIFFERS",
            "handoff_source": r["corp_code_reference_status"],
            "qa_source": "OPENDART_CORPCODE_XML",
            "independence_grade": grade,
            "prior_record": note,
            # 확인하지 않은 것을 빈칸으로 남기면 확인한 것처럼 읽힌다. 명시한다.
            "theme_eligibility": "NOT_REVIEWED_BY_QA",
            "gate_status": "NOT_REVIEWED_BY_QA",
            "rcept_no_completeness": "NOT_REVIEWED_BY_QA",
            "promotion_status": "NOT_PROMOTED",
        })

    dst = os.path.join(OUT, "kr9_corp_code_crosscheck.csv")
    with open(dst, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    print(f"\n   차이표 -> {os.path.relpath(dst, P.ROOT)}")
    print("\n" + "=" * 62)
    if mismatch:
        print(f"대조 결과 — 불일치 {mismatch}건. 차이표를 근거로 원인부터 확인할 것.")
        return 1
    print(f"대조 결과 — corp_code {len(rows)}건 전부 일치.")
    print("  단, 확인한 것은 식별번호 전사 정확성뿐이다.")
    print("  테마 적격성·gate_status·rcept_no 완전성은 검토하지 않았다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
