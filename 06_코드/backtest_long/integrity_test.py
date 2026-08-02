# -*- coding: utf-8 -*-
"""PIT 무결성 · 결정론성 검사 — 수익률과 무관한 알고리즘 품질 검증.

[1] PIT 무결성 (look-ahead 검사)
    같은 선정 회차를, 미래 데이터가 있는 상태와 없는 상태에서 각각 산출해 비교한다.

      전체 데이터(2026년까지)로 산출한 2016-06-30 회차     -> 결과 A
      2016-07 이후를 통째로 잘라낸 뒤 산출한 같은 회차      -> 결과 B

    A == B 여야 한다. 다르면 그 시점에 알 수 없었던 정보가 판정에 들어간 것이다.

    이 검사가 강한 이유
      · 백테스트 성과와 무관하다 — 선택편향 논쟁에 걸리지 않는다
      · 통과/실패가 이분법이다 — 해석의 여지가 없다
      · 지수 사업자 감사에서 실제로 보는 항목이다

[2] 결정론성
    같은 입력으로 N회 재실행해 산출물 해시가 전부 같은지 본다.
    난수·딕셔너리 순서·부동소수 누적 순서가 섞이면 깨진다.
    "같은 입력이면 언제 돌려도 같은 값"은 규칙기반 지수의 최소 요건이다.

사용
  python integrity_test.py                    # 기본 4개 시점
  python integrity_test.py --rounds 2016-06-30,2020-06-30
  python integrity_test.py --repeats 5
"""
import argparse
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.path.join(HERE, ".."))
OUT = os.path.join(HERE, "out")
INPUT_LONG = os.path.join(CODE, "data", "input_long")
TMP = os.path.join(CODE, "data", "_integrity_tmp")

# 판정에 쓰이는 산출물만 비교한다. 지수 시계열은 구간이 달라 당연히 다르다.
JUDGMENT_FILES = ("weights_{r}.csv", "thresholds_{r}.json")

# constituents 는 파일 해시가 아니라 '판정 열'로 비교한다.
#   미상장 종목은 절단본에 가격 행 자체가 없어 원장 메타(observed_open_days 등)가
#   NaN 이 된다. 그 종목들은 어차피 편입 대상이 아니므로 메타 차이는 look-ahead 가
#   아니다. 판정(편입 여부·셀 배정)이 같은지가 검사 대상이다.
JUDGE_COLS = ["security_id", "selected_flag", "selection_status",
              "cell_id", "primary_theme", "market"]
DEFAULT_ROUNDS = ["2016-06-30", "2019-06-30", "2022-06-30", "2024-06-30"]
DATE_COLS = {"prices.csv": "market_date", "calendar.csv": "market_date",
             "fx.csv": "market_date", "bm_kr.csv": "market_date",
             "bm_us.csv": "market_date"}


def sha(path):
    return hashlib.sha256(open(path, "rb").read().replace(b"\r\n", b"\n")).hexdigest()[:16]


def require_inputs():
    """입력 세트가 없으면 무엇을 어떻게 만들어야 하는지 알려주고 멈춘다.

    data/input_long/ 은 .gitignore 대상이다(가격 4.3만행 등 용량). 코드는 전부
    저장소에 있으므로 아래 한 줄로 동일한 입력을 다시 만들 수 있다.
    """
    need = ["prices.csv", "calendar.csv", "fx.csv", "bm_kr.csv", "bm_us.csv",
            "seed_basket.csv", "listings.csv"]
    miss = [f for f in need if not os.path.exists(os.path.join(INPUT_LONG, f))]

    # 입력이 없으면 저장소에 커밋된 스냅샷을 자동으로 푼다.
    # 외부 API(KRX·ECOS) 접속 없이도 검증을 재현할 수 있어야 한다.
    snap = os.path.join(HERE, "input_snapshot.zip")
    if miss and os.path.exists(snap):
        import zipfile
        os.makedirs(INPUT_LONG, exist_ok=True)
        with zipfile.ZipFile(snap) as z:
            z.extractall(INPUT_LONG)
        print(f"[스냅샷] {os.path.basename(snap)} 을 풀었다 — 외부 접속 없이 재현한다")
        miss = [f for f in need if not os.path.exists(os.path.join(INPUT_LONG, f))]

    if not miss and os.path.exists(os.path.join(OUT, "weights_2026-06-30.csv")):
        return
    print("=" * 70)
    print("[중단] 검증에 필요한 입력·산출물이 없다")
    print("=" * 70)
    if miss:
        print(f"  없는 입력  {INPUT_LONG}")
        for f in miss:
            print(f"     · {f}")
        print("\n  data/input_long/ 은 .gitignore 대상이다(용량). 코드는 전부 저장소에 있으므로")
        print("  아래 한 줄로 동일한 입력을 다시 만들 수 있다. .env(ECOS_API_KEY·KRX_ID·KRX_PW) 필요.")
    print("\n  실행 순서")
    print("    cd 06_코드/backtest_long")
    print("    python run_long_backtest.py --skip-collect   # 스냅샷으로 엔진만 (1분)")
    print("    python integrity_test.py                     # 본 검증")
    print("\n  원자료부터 다시 받으려면 (KRX·ECOS 접속 필요)")
    print("    python run_long_backtest.py                  # 수집 + 엔진 (10~15분)")
    print("\n  같은 입력인지 확인하려면 out/long_run_meta.json 의 inputs_sha256_16 을")
    print("  재수집분과 대조한다. 값이 같으면 동일 입력이다.")
    sys.exit(2)


def truncate_inputs(cut: str, dst: str):
    """cut 이후 행을 전부 잘라낸 입력 세트를 만든다. 미래를 물리적으로 제거한다."""
    os.makedirs(dst, exist_ok=True)
    for f in os.listdir(INPUT_LONG):
        if not f.endswith(".csv"):
            continue
        src = os.path.join(INPUT_LONG, f)
        col = DATE_COLS.get(f)
        if col is None:
            shutil.copy2(src, os.path.join(dst, f))     # 유니버스·상장일 등 시계열 아님
            continue
        df = pd.read_csv(src, dtype={"security_id": str})
        df = df[df[col].astype(str) <= cut]
        df.to_csv(os.path.join(dst, f), index=False)


def run_engine(input_dir, out_dir, sel_dates):
    env = dict(os.environ, SELECTION_DATES_OVERRIDE=",".join(sel_dates))
    os.makedirs(out_dir, exist_ok=True)
    r = subprocess.run([sys.executable, "run_pilot.py", input_dir, out_dir],
                       cwd=os.path.join(CODE, "engine"), capture_output=True,
                       text=True, env=env)
    return r.returncode, (r.stderr or "")[-400:]


def all_rounds():
    return sorted(os.path.basename(f)[8:18]
                  for f in glob.glob(os.path.join(OUT, "weights_*.csv")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", default=",".join(DEFAULT_ROUNDS))
    ap.add_argument("--repeats", type=int, default=3)
    a = ap.parse_args()
    test_rounds = [x.strip() for x in a.rounds.split(",") if x.strip()]
    require_inputs()
    full = all_rounds()

    print("=" * 70)
    print("PIT 무결성 · 결정론성 검사")
    print("=" * 70)
    print(f"  전체 산출 회차 {len(full)}개  ·  검사 시점 {len(test_rounds)}개\n")

    res = {"artifact": "pit_and_determinism_test", "full_rounds": len(full)}

    # ── [1] PIT 무결성 ───────────────────────────────────────
    print("[1] PIT 무결성 — 미래를 잘라내도 같은 판정이 나오는가")
    pit, ok_all = [], True
    for r in test_rounds:
        if r not in full:
            print(f"    {r}  전체 산출에 없는 회차 — 건너뜀")
            continue
        cut = (pd.Timestamp(r) + pd.Timedelta(days=10)).strftime("%Y-%m-%d")
        sel = [x for x in full if x <= r]
        tmp_in = os.path.join(TMP, f"in_{r}")
        tmp_out = os.path.join(TMP, f"out_{r}")
        shutil.rmtree(tmp_in, ignore_errors=True)
        shutil.rmtree(tmp_out, ignore_errors=True)
        truncate_inputs(cut, tmp_in)
        rc, err = run_engine(tmp_in, tmp_out, sel)
        if rc != 0:
            print(f"    {r}  ★엔진 실패★ {err[:120]}")
            ok_all = False
            pit.append({"round": r, "status": "ENGINE_FAIL"})
            continue

        diffs, meta_only, n_rows = [], [], 0
        for rr in sel:
            for pat in JUDGMENT_FILES:
                fn = pat.format(r=rr)
                pa, pb = os.path.join(OUT, fn), os.path.join(tmp_out, fn)
                if not (os.path.exists(pa) and os.path.exists(pb)):
                    diffs.append(f"{fn}(파일없음)")
                elif sha(pa) != sha(pb):
                    diffs.append(fn)
            fn = f"constituents_{rr}.csv"
            pa, pb = os.path.join(OUT, fn), os.path.join(tmp_out, fn)
            if not (os.path.exists(pa) and os.path.exists(pb)):
                diffs.append(f"{fn}(파일없음)")
                continue
            ca = pd.read_csv(pa, dtype={"security_id": str}).set_index("security_id").sort_index()
            cb = pd.read_csv(pb, dtype={"security_id": str}).set_index("security_id").sort_index()
            n_rows += len(ca)
            for c in JUDGE_COLS[1:]:
                if not ca[c].astype(str).equals(cb[c].astype(str)):
                    diffs.append(f"{fn}::{c}")
            if sha(pa) != sha(pb):
                meta_only.append(fn)
        mark = "일치" if not diffs else f"★불일치 {len(diffs)}건★"
        print(f"    {r}  데이터 {cut} 까지만 · 회차 {len(sel)}개 · 판정 {n_rows}행"
              f"  ->  {mark}")
        if meta_only:
            print(f"        (참고) 원장 메타만 다른 파일 {len(meta_only)}건 — "
                  f"미상장 종목의 NaN. 판정 아님")
        for d in diffs[:5]:
            print(f"        ★ {d}")
        ok_all &= not diffs
        pit.append({"round": r, "cut": cut, "rounds_compared": len(sel),
                    "judgment_rows": n_rows, "mismatches": diffs,
                    "metadata_only_diff_files": len(meta_only),
                    "status": "PASS" if not diffs else "FAIL"})
    res["pit"] = {"cases": pit, "verdict": "PASS" if ok_all else "FAIL"}
    print(f"\n    판정  {'PASS — look-ahead 없음' if ok_all else '★FAIL★'}")

    # ── [2] 결정론성 ─────────────────────────────────────────
    print(f"\n[2] 결정론성 — 같은 입력으로 {a.repeats}회 재실행")
    hashes = []
    for i in range(a.repeats):
        d = os.path.join(TMP, f"det_{i}")
        shutil.rmtree(d, ignore_errors=True)
        rc, err = run_engine(INPUT_LONG, d, full)
        if rc != 0:
            print(f"    {i+1}회차 실패 {err[:100]}")
            hashes.append(None)
            continue
        h = {f: sha(os.path.join(d, f)) for f in sorted(os.listdir(d))
             if f.endswith((".csv", ".json"))}
        hashes.append(h)
        print(f"    {i+1}회차  산출 {len(h)}파일  결합해시 "
              f"{hashlib.sha256(json.dumps(h, sort_keys=True).encode()).hexdigest()[:16]}")
    det_ok = all(h == hashes[0] for h in hashes if h) and all(hashes)
    if not det_ok and all(hashes):
        for f in hashes[0]:
            if any(h.get(f) != hashes[0][f] for h in hashes[1:]):
                print(f"        ★ 회차마다 다름: {f}")
    res["determinism"] = {"repeats": a.repeats,
                          "verdict": "PASS" if det_ok else "FAIL",
                          "files": len(hashes[0]) if hashes[0] else 0}
    print(f"\n    판정  {'PASS — 재실행 시 비트 단위 동일' if det_ok else '★FAIL★'}")

    res["note"] = ("본 검사는 수익률과 무관하다. 선택편향 논쟁의 영향을 받지 않는 "
                   "알고리즘 품질 지표다.")
    with open(os.path.join(OUT, "integrity_test.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    shutil.rmtree(TMP, ignore_errors=True)
    print(f"\n  {os.path.join(OUT, 'integrity_test.json')}")
    return 0 if (ok_all and det_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
