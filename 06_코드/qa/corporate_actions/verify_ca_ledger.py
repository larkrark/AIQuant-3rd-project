# -*- coding: utf-8 -*-
"""
기업행사 원장 수신 검증 — 공시·PIT 담당 인계본 vs QA 사전조회 봉인

배정 (2026-07-31 승인)
  원자료 수집·사건원장   공시·PIT 담당
  독립 검증             QA

  QA 는 승인 직전까지 진행하던 조회를 원장 수신 전에 봉인했다
  (SEAL_20260731_사전조회봉인.md · 커밋 345f43d). 본 스크립트는 그 봉인과
  수신 원장을 대조한다.

검사 항목
  1  스키마      데이터사전 v0.8 §4 필수 필드 존재 여부
  2  날짜 분리   effective_date_raw 와 listing_or_resume_date_raw 가 별도로 채워졌는가
  3  사건 대조   봉인 10건 ↔ 원장  (rcept_no 기준 3분류)
  4  미포착      봉인 전량 865건 중 원장에 없는 기업행사 의심건
  5  회귀        010120 기존 반영값(5:1 · 04-13 · 정지 04-08~10)과 일치하는가
  6  승인 경계   approved_* 가 채워졌다면 methodology_decision_id 가 함께 있는가

이 스크립트는 판정만 한다. 원장을 고치지 않고 approved_* 를 채우지 않는다.

실행
  python verify_ca_ledger.py <원장.csv>
  python verify_ca_ledger.py <원장.csv> --out out/ledger_verdict.csv
"""
import argparse
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
QA = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, QA)
from paths import force_utf8_stdout  # noqa: E402

SEAL_HITS = os.path.join(HERE, "out", "dart_ca_hits.csv")
SEAL_RAW = os.path.join(HERE, "out", "dart_filings_raw.csv")

# 데이터사전 v0.8 §4. 별칭은 팀 표기 흔들림을 흡수하되 무엇으로 맞췄는지 출력한다.
REQUIRED = {
    "security_id":                   ["security_id", "종목코드", "stock_code"],
    "corporate_action_type":         ["corporate_action_type", "action_type", "event_type"],
    "effective_date_raw":            ["effective_date_raw", "effective_date",
                                      "event_effective_date", "효력일"],
    "listing_or_resume_date_raw":    ["listing_or_resume_date_raw", "listing_date_raw",
                                      "listing_or_resume_date", "resume_date",
                                      "상장일", "거래재개일"],
    "rcept_no":                      ["rcept_no", "latest_event_rcept_no",
                                      "latest_primary_rcept_no", "original_rcept_no",
                                      "접수번호", "document_key"],
}
OPTIONAL = {
    "par_value_before_raw":          ["par_value_before_raw", "before_face_value", "액면가_전"],
    "par_value_after_raw":           ["par_value_after_raw", "after_face_value", "액면가_후"],
    "shares_before_raw":             ["shares_before_raw", "before_shares", "주식수_전"],
    "shares_after_raw":              ["shares_after_raw", "after_shares", "주식수_후"],
    "reviewed_split_ratio_candidate": ["reviewed_split_ratio_candidate",
                                       "split_ratio_candidate", "split_or_merger_ratio"],
    "candidate_review_basis":        ["candidate_review_basis", "source_value_raw", "근거"],
    "approved_adjustment_factor":    ["approved_adjustment_factor"],
    "adjustment_factor_candidate":   ["adjustment_factor_candidate"],
    "methodology_decision_id":       ["methodology_decision_id"],
    # 수집 범위 — PIT cutoff 가 파일럿 구간을 덮는지 검사하기 위해 읽는다.
    "query_end_date":                ["query_end_date", "collection_cutoff"],
    "pit_status":                    ["pit_status"],
}

# 파일럿에서 실제로 쓰인 구간. 원장 조회 종료일이 이보다 이르면 사각이 생긴다.
PILOT_INDEX_END = "2026-06-30"
DATA_CUTOFF_0630 = "2026-06-23"

# 기존 반영분 — corrected_run_meta.json 기준. 원장이 이것과 다르면 지수 재산출 대상.
BASELINE_010120 = {
    "ratio": "5",
    "listing_or_resume": "2026-04-13",
    "halt": ["2026-04-08", "2026-04-09", "2026-04-10"],
}

# §4 실증 — 보고서명 키워드로는 잡히지 않는 유형. 미포착 검사의 2차 대상.
SECONDARY_HINTS = ["주주총회", "정관", "기타경영사항"]

CA_KEYWORDS = ["분할", "병합", "액면", "증자", "감자", "합병", "주식배당"]

findings = []


def note(level, code, msg):
    findings.append((level, code, msg))
    mark = {"FAIL": "[불일치]", "WARN": "[확인]", "OK": "[일치]", "INFO": "[정보]"}[level]
    print(f"  {mark} {msg}")


def read_csv(path):
    if not os.path.exists(path):
        raise SystemExit(f"[중단] 없음: {path}")
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def resolve(cols, aliases):
    low = {c.strip().lower(): c for c in cols}
    for a in aliases:
        if a.lower() in low:
            return low[a.lower()]
    return None


def main():
    force_utf8_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("ledger", help="공시·PIT 담당 인계 원장 CSV")
    ap.add_argument("--out", default=os.path.join(HERE, "out", "ledger_verdict.csv"))
    args = ap.parse_args()

    led = read_csv(args.ledger)
    hits = read_csv(SEAL_HITS)
    raw = read_csv(SEAL_RAW)
    cols = list(led[0].keys()) if led else []

    print(f"원장   {args.ledger}  {len(led)}건")
    print(f"봉인   dart_ca_hits {len(hits)}건 · dart_filings_raw {len(raw)}건\n")

    # --- 1. 스키마 ---
    print("1. 스키마 — 데이터사전 v0.8 §4")
    field = {}
    for canon, aliases in REQUIRED.items():
        c = resolve(cols, aliases)
        field[canon] = c
        if c is None:
            note("FAIL", "SCHEMA", f"필수 필드 없음: {canon}")
        elif c != canon:
            note("WARN", "SCHEMA", f"{canon} ← 원장 '{c}' 로 매핑 (표기 상이)")
    for canon, aliases in OPTIONAL.items():
        field[canon] = resolve(cols, aliases)
    missing_opt = [k for k, v in field.items() if v is None and k in OPTIONAL]
    if missing_opt:
        note("WARN", "SCHEMA", f"선택 필드 없음: {' '.join(missing_opt)}")
    if not [f for f in findings if f[1] == "SCHEMA"]:
        note("OK", "SCHEMA", "필수·선택 필드 전부 존재")

    def g(row, canon):
        c = field.get(canon)
        return (row.get(c) or "").strip() if c else ""

    # --- 2. 날짜 분리 ---
    print("\n2. 날짜 분리 — 효력일 vs 상장·재개일")
    if field["effective_date_raw"] and field["listing_or_resume_date_raw"]:
        both = [r for r in led if g(r, "effective_date_raw") and g(r, "listing_or_resume_date_raw")]
        diff = [r for r in both
                if g(r, "effective_date_raw") != g(r, "listing_or_resume_date_raw")]
        empty = [r for r in led if not g(r, "listing_or_resume_date_raw")]
        if empty:
            note("WARN", "DATE", f"상장·재개일 공란 {len(empty)}건 — 값이 같은 것과 미기입은 다르다")
        note("INFO", "DATE", f"두 날짜 모두 기입 {len(both)}건 · 그중 서로 다른 건 {len(diff)}건")
        if both and not diff:
            note("WARN", "DATE",
                 "모든 건에서 두 날짜가 동일 — 한 칸을 복사했는지 확인 필요. "
                 "010120 은 04-10 ≠ 04-13 이어야 한다")
    else:
        note("FAIL", "DATE", "두 날짜 필드를 확인할 수 없어 검사 불가")

    # --- 3. 사건 대조 ---
    print("\n3. 사건 대조 — rcept_no 기준")
    seal_no = {r["rcept_no"]: r for r in hits}
    led_no = {g(r, "rcept_no"): r for r in led if g(r, "rcept_no")}
    only_qa = sorted(set(seal_no) - set(led_no))
    only_led = sorted(set(led_no) - set(seal_no))
    both_no = sorted(set(seal_no) & set(led_no))

    note("INFO", "MATCH", f"양쪽 포착 {len(both_no)}건 · QA만 {len(only_qa)}건 · 원장만 {len(only_led)}건")
    led_secs = {g(r, "security_id") for r in led}
    for n in only_qa:
        s = seal_no[n]
        nm = s["report_nm"].strip()
        # 원본·정정이 쌍으로 존재할 때 원장이 정정본만 담는 것은 정상이다(정정본 우선).
        paired = (s["security_id"] in led_secs
                  and any(x["security_id"] == s["security_id"]
                          and x["rcept_no"] in led_no
                          and nm.replace("[기재정정]", "") in x["report_nm"]
                          for x in hits))
        if paired:
            note("INFO", "MATCH",
                 f"QA만 포착이나 정정본이 원장에 있음 → 정상: {s['security_id']} {s['rcept_dt']} {nm}")
        else:
            note("WARN", "MATCH",
                 f"QA만 포착 → 원장 누락 후보: {s['security_id']} {s['rcept_dt']} {nm}")
    for n in only_led:
        r = led_no[n]
        note("INFO", "MATCH",
             f"원장만 포착 → QA 필터 한계 유형(SEAL §4): {g(r,'security_id')} {n}")

    # --- 3-b. 수집 범위 ---
    print("\n3-b. 수집 범위 — 조회 종료일이 파일럿 구간을 덮는가")
    ends = {g(r, "query_end_date") for r in led if g(r, "query_end_date")}
    pits = {g(r, "pit_status") for r in led if g(r, "pit_status")}
    if ends:
        e = max(ends)
        norm = e if "-" in e else f"{e[:4]}-{e[4:6]}-{e[6:]}"
        note("INFO", "SCOPE", f"원장 조회 종료일 {norm} · pit_status {sorted(pits)}")
        if norm < PILOT_INDEX_END:
            note("FAIL", "SCOPE",
                 f"조회 종료 {norm} < 파일럿 지수구간 종료 {PILOT_INDEX_END} — "
                 f"{norm} 이후 기업행사가 원장에 들어올 수 없다")
        if norm < DATA_CUTOFF_0630:
            note("FAIL", "SCOPE",
                 f"조회 종료 {norm} < 06-30 회차 자료마감일 {DATA_CUTOFF_0630} — "
                 "선정 근거 구간도 덮지 못한다")
    else:
        note("WARN", "SCOPE", "query_end_date 없음 — 수집 범위를 검사할 수 없다")

    # --- 4. 미포착 ---
    print("\n4. 미포착 — 봉인 전량에서 재검색")
    sus = [x for x in raw
           if x["rcept_no"] not in led_no
           and any(k in x["report_nm"] for k in CA_KEYWORDS + SECONDARY_HINTS)]
    prim = [x for x in sus if any(k in x["report_nm"] for k in CA_KEYWORDS)]
    seco = [x for x in sus if x not in prim]
    note("INFO", "SWEEP", f"원장 밖 후보 {len(sus)}건 (1차 키워드 {len(prim)} · 2차 총회·정관 {len(seco)})")
    for x in prim[:15]:
        note("WARN", "SWEEP", f"1차: {x['security_id']} {x['rcept_dt']} {x['report_nm'].strip()}")
    if len(prim) > 15:
        note("INFO", "SWEEP", f"1차 후보 {len(prim)-15}건 추가 — ledger_verdict.csv 참조")
    if seco:
        note("INFO", "SWEEP",
             f"2차 {len(seco)}건은 상호변경형(079550 사례) 확인용. 가격조정 사건이 아니면 무시 가능")

    # --- 5. 010120 회귀 ---
    print("\n5. 회귀 — 010120 기존 반영값")
    # 010120 은 물적분할(2022)도 원장에 있다. 회귀 대상은 파일럿에 반영된 액면분할뿐이다.
    rows = [r for r in led if g(r, "security_id") in ("010120", "10120")
            and "SPLIT" in g(r, "corporate_action_type").upper()
            and "SPIN" not in g(r, "corporate_action_type").upper()]
    if not rows:
        note("FAIL", "REGRESS", "010120 이 원장에 없다 — 이미 지수에 반영된 사건이다")
    else:
        for r in rows:
            ld = g(r, "listing_or_resume_date_raw")
            if ld and ld != BASELINE_010120["listing_or_resume"]:
                note("FAIL", "REGRESS",
                     f"010120 상장·재개일 {ld} ≠ 기존 반영 {BASELINE_010120['listing_or_resume']} "
                     "→ 지수 재산출 대상 (효력일 채택 시 연변동성 42.40% ↔ 71.77%)")
            # 비율(5)과 계수(0.2)는 표기 규약이 다르다. 둘 다 5:1 을 뜻하면 통과시키되
            # 어느 규약으로 적혔는지 남긴다.
            raw = [g(r, k) for k in ("reviewed_split_ratio_candidate",
                                     "adjustment_factor_candidate",
                                     "approved_adjustment_factor") if g(r, k)]
            okr = False
            for v in raw:
                s = v.replace(" ", "")
                if ("5" in s and "1" in s) or s.rstrip("0").rstrip(".") == "5":
                    okr = True
                    note("INFO", "REGRESS", f"010120 비율 표기 '{v}' → 5:1 로 해석")
                try:
                    if abs(float(s) - 0.2) < 1e-9:
                        okr = True
                        note("WARN", "REGRESS",
                             f"010120 값 {v} 는 비율(5)이 아니라 계수(1/5)다 — "
                             "데이터사전 §4 는 ratio 칸과 factor 칸을 나눈다. 표기 규약 확정 필요")
                except ValueError:
                    pass
            if raw and not okr:
                note("FAIL", "REGRESS", f"010120 분할비율 {raw} ≠ 기존 반영 5:1")
        if not [f for f in findings if f[1] == "REGRESS"]:
            note("OK", "REGRESS", "010120 기존 반영값과 일치 — 재산출 불필요")

    # --- 6. 승인 경계 ---
    print("\n6. 승인 경계 — 데이터사전 v0.8 §4")
    if field.get("approved_adjustment_factor"):
        appr = [r for r in led if g(r, "approved_adjustment_factor")]
        for r in appr:
            if not g(r, "methodology_decision_id"):
                note("FAIL", "GATE",
                     f"{g(r,'security_id')}: approved_adjustment_factor 가 채워졌는데 "
                     "methodology_decision_id 가 없다 — 임의 생성 금지 조항 위반")
        note("INFO", "GATE", f"승인값 기입 {len(appr)}건 / 전체 {len(led)}건")
    else:
        note("INFO", "GATE", "approved_adjustment_factor 미도입 — 팀 승인 전 단계로 간주")

    # --- 산출 ---
    outdir = os.path.dirname(args.out)
    if outdir:
        os.makedirs(outdir, exist_ok=True)
    with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["level", "code", "message"])
        w.writerows(findings)
        w.writerow([])
        w.writerow(["--- 원장 밖 후보 전량 ---"])
        w.writerow(["security_id", "rcept_dt", "rcept_no", "report_nm", "tier"])
        for x in sus:
            w.writerow([x["security_id"], x["rcept_dt"], x["rcept_no"],
                        x["report_nm"].strip(), "1차" if x in prim else "2차"])

    fail = sum(1 for f in findings if f[0] == "FAIL")
    warn = sum(1 for f in findings if f[0] == "WARN")
    print(f"\n{'='*60}")
    print(f"불일치 {fail}건 · 확인요망 {warn}건   →  {args.out}")
    if fail:
        print("불일치가 있으면 지수 재산출 여부를 먼저 판정한다. 원장을 QA 가 고치지 않는다.")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
