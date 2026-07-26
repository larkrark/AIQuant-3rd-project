# -*- coding: utf-8 -*-
"""엔진 불변식 스모크 테스트 — 합성 표본으로 파이프라인을 관통시켜 룰북 핵심 규칙을 검사.
실행: python engine/tests/test_invariants.py   (pytest 불필요)

검사 항목
  R9  일별 상태코드가 확정 6종 집합에 속하는가
  R9  trading_value_source가 {EXCHANGE_PROVIDED, RECONSTRUCTED} 뿐인가
  R10 리밸런싱 회차별 final_target_weight 합계가 1.0인가 (허용오차 1e-9)
  기본 정합: 지수·BM 값이 모두 양수이고 날짜가 단조 증가
"""
import os, sys, subprocess, tempfile, glob
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try: _s.reconfigure(encoding="utf-8")   # Windows cp949 콘솔에서 —·→ 등 출력 깨짐 방지
    except Exception: pass
import pandas as pd

TESTS = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(TESTS)
MAKE_SAMPLE = os.path.join(TESTS, "make_sample.py")
RUN_PILOT = os.path.join(ENGINE, "run_pilot.py")

STATE_CODES = {"TRADED", "ZERO_VOLUME", "TRADING_HALT", "MARKET_CLOSED", "DATA_MISSING", "NOT_LISTED"}
TV_SOURCES = {"EXCHANGE_PROVIDED", "RECONSTRUCTED"}


def _run_pipeline(work):
    # 1) 합성 표본 생성 (cwd=work → work/sample_data)
    subprocess.run([sys.executable, MAKE_SAMPLE], cwd=work, check=True,
                   stdout=subprocess.DEVNULL)
    sample = os.path.join(work, "sample_data")
    out = os.path.join(work, "out")
    # 2) 엔진 실행 (cwd=ENGINE → 평면 임포트 성립)
    subprocess.run([sys.executable, RUN_PILOT, sample, out], cwd=ENGINE, check=True,
                   stdout=subprocess.DEVNULL)
    return out


def check(out):
    fails = []
    st = pd.read_csv(os.path.join(out, "daily_market_state.csv"))
    bad = set(st["daily_market_state"].dropna().unique()) - STATE_CODES
    if bad:
        fails.append(f"R9 상태코드 집합 위반: {bad}")
    bad_tv = set(st["trading_value_source"].dropna().unique()) - TV_SOURCES
    if bad_tv:
        fails.append(f"R9 trading_value_source 위반: {bad_tv}")

    wfiles = glob.glob(os.path.join(out, "weights_*.csv"))
    if not wfiles:
        fails.append("weights_*.csv 산출 없음")
    for wf in wfiles:
        w = pd.read_csv(wf)
        total = w["final_target_weight"].sum()
        if abs(total - 1.0) > 1e-9 and len(w) > 0:
            fails.append(f"R10 가중합≠1.0 ({os.path.basename(wf)}: {total})")

    iv = pd.read_csv(os.path.join(out, "index_vs_benchmark.csv"))
    if not (iv["index_level"] > 0).all():
        fails.append("지수값에 0/음수 존재")
    if not (iv["benchmark_level"] > 0).all():
        fails.append("BM값에 0/음수 존재")
    if list(iv["market_date"]) != sorted(iv["market_date"]):
        fails.append("날짜 단조 증가 아님")
    return fails


def main():
    with tempfile.TemporaryDirectory() as work:
        out = _run_pipeline(work)
        fails = check(out)
    if fails:
        print("FAIL")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("PASS — 상태코드 6종·trading_value_source·가중합 1.0·지수 정합 모두 통과")
    sys.exit(0)


if __name__ == "__main__":
    main()
