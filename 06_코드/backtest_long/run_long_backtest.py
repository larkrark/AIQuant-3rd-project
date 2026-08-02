# -*- coding: utf-8 -*-
"""장기 백테스트 실행기 — 수집 구간·선정일만 바꿔 기존 엔진을 그대로 돌린다.

무엇을 바꿨나 (규칙은 한 줄도 안 바꿨다)
  ingest/collect_pilot_inputs.py   START·END 를 환경변수로 덮어쓸 수 있게 함 (기본값 불변)
                                   ECOS 페이징 추가 — 다년 구간은 1회 요청으로 다 못 받는다
  engine/config.py                 SELECTION_DATES 를 환경변수로 덮어쓸 수 있게 함 (기본값 불변)

  선정·게이트·가중·연결·환율 규칙은 전부 그대로다. `git diff` 로 확인 가능하다.

왜 필요했나
  파일럿은 2025-10-01~2026-07-01 (공통 개장일 59일) 이라 리밸런싱 적용 이벤트가 0회였다.
  선정은 2회 돌았고 결과도 달랐지만(3/31 KTOS -> 6/30 ATI) 6/30 선정의 효력발생일이
  구간 밖이라 지수에 반영된 적이 없다. 구간을 늘리면 같은 규칙으로 리밸런싱이 실제 발동한다.

사용 — 기간만 바꾸면 된다
  python run_long_backtest.py                                  # 기본 2013-01-01 ~ 2026-07-24
  python run_long_backtest.py --start 2018-01-01               # 시작만 변경
  python run_long_backtest.py --start 2020-01-01 --end 2024-12-31
  python run_long_backtest.py --skip-collect                   # 이미 받은 입력으로 엔진만 재실행
  python run_long_backtest.py --freq A                         # 연 1회 선정 (기본 Q = 분기)

성과 인용 제한 — 반드시 읽을 것
  Seed18 은 2026년 시점에 고른 종목이다. 이를 과거로 되돌린 결과는 선택편향·생존편향을
  포함하므로 성과(수익률·알파·초과수익)를 근거로 인용해서는 안 된다.
  본 산출의 목적은 성과가 아니라 **규칙 기전의 실증** 이다.
    리밸런싱이 실제로 발동하는가 · 셀 부족 재배분이 도는가 ·
    연결이 경계에서 연속인가 · 상태코드가 실제 이벤트를 잡는가
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(CODE, "qa"))
sys.path.insert(0, os.path.join(CODE, "ingest"))

INPUT_LONG = os.path.join(CODE, "data", "input_long")
OUT = os.path.join(HERE, "out")
PILOT_INPUT = os.path.join(CODE, "data", "pilot_run", "input_krxbm")

DEFAULT_START, DEFAULT_END = "2013-01-01", "2026-07-24"


def load_env():
    """.env 를 찾아 환경변수로 올린다. 값은 출력하지 않는다(저장소 공개)."""
    from paths import env_path
    p = env_path()
    if not p:
        return False
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
    return True


def selection_dates(start: str, end: str, freq: str) -> list:
    """선정일 생성 — 분기말/연말. 규칙(분기 정기변경)은 그대로 두고 회차만 늘린다."""
    rng = pd.date_range(start, end, freq="QE" if freq == "Q" else "YE")
    return [d.strftime("%Y-%m-%d") for d in rng]


def drop_unseedable(sel_dates: list, prices: pd.DataFrame) -> tuple:
    """편입 가능 종목이 0개인 회차를 뺀다.

    엔진 결함 회피 — composition.assign_weights 는 편입 0개일 때
    rows=[] 로 만든 빈 DataFrame 에서 final_target_weight 를 찾다 KeyError 로 죽는다.
    (바로 아래 assert 가 len(weights)==0 을 예상하고 있으나 그 전에 예외가 난다.)
    구간 시작부는 어느 종목도 시즈닝 90일을 못 채우므로 지수 자체를 만들 수 없다.
    엔진을 고치지 않고 여기서 거른다 — 결함은 별도 보고한다.
    """
    cal = pd.read_csv(os.path.join(INPUT_LONG, "calendar.csv"))
    cal["market_date"] = cal["market_date"].astype(str)
    op = cal[cal["is_market_open"] == 1]
    kr = set(op[op["market"] == "KR"]["market_date"])
    us = set(op[op["market"] == "US"]["market_date"])
    common = sorted(kr & us)

    px = prices.copy()
    px["market_date"] = px["market_date"].astype(str)
    first_seen = px.groupby("security_id")["market_date"].min()

    keep, dropped = [], []
    for s in sel_dates:
        before = [d for d in common if d < s]
        if len(before) < 5:
            dropped.append((s, "공통 개장일 부족"))
            continue
        cutoff = before[-5]
        # 자료마감일까지 유효관측일이 90일 이상인 종목이 하나라도 있는가
        n_ok = 0
        for sid, f0 in first_seen.items():
            if f0 >= cutoff:
                continue
            obs = len(px[(px["security_id"] == sid) & (px["market_date"] > f0)
                         & (px["market_date"] <= cutoff)])
            if obs >= 90:
                n_ok += 1
        if n_ok:
            keep.append(s)
        else:
            dropped.append((s, "시즈닝 통과 종목 0"))
    return keep, dropped


def sha16(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def collect(start, end, basket_path):
    os.environ["COLLECT_START"], os.environ["COLLECT_END"] = start, end
    os.makedirs(INPUT_LONG, exist_ok=True)
    import collect_pilot_inputs as c
    print(f"[수집] {c.START} ~ {c.END}")
    basket = pd.read_csv(basket_path, dtype={"security_id": str})
    us = basket[basket["market"] == "US"]["security_id"].tolist()
    c.collect_us_prices(us, INPUT_LONG)
    c.collect_indices_and_calendar(INPUT_LONG)
    c.collect_fx(INPUT_LONG)


def build_inputs(basket_path):
    """엔진 입력계약(run_pilot.py)에 맞춰 입력 폴더를 조립한다.

    한국 가격은 공시·PIT 담당 인계본(2013-01-02~)을 그대로 쓴다. QA 는 수집하지 않는다.
    미국 가격만 이번에 확장 수집분으로 교체한다.
    """
    kr = pd.read_csv(os.path.join(PILOT_INPUT, "prices.csv"), dtype={"security_id": str})
    kr = kr[kr["market"] == "KR"]
    us = pd.read_csv(os.path.join(INPUT_LONG, "prices_us.csv"), dtype={"security_id": str})
    prices = pd.concat([kr, us], ignore_index=True).sort_values(["security_id", "market_date"])
    prices.to_csv(os.path.join(INPUT_LONG, "prices.csv"), index=False)
    print(f"[조립] prices.csv {len(prices)}행  (KR {len(kr)} 인계본 + US {len(us)} 확장수집)")

    for f in ("seed_basket.csv", "listings.csv", "halts.csv"):
        src = basket_path if f == "seed_basket.csv" else os.path.join(PILOT_INPUT, f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(INPUT_LONG, f))
    return prices


def run_engine(sel_dates):
    os.environ["SELECTION_DATES_OVERRIDE"] = ",".join(sel_dates)
    os.makedirs(OUT, exist_ok=True)
    print(f"[엔진] 선정일 {len(sel_dates)}회차  {sel_dates[0]} ~ {sel_dates[-1]}")
    r = subprocess.run([sys.executable, "run_pilot.py", INPUT_LONG, OUT],
                       cwd=os.path.join(CODE, "engine"), capture_output=True, text=True)
    print(r.stdout[-2500:] or r.stderr[-2500:])
    return r.returncode


def summarize(start, end, sel_dates):
    idx = pd.read_csv(os.path.join(OUT, "index_vs_benchmark.csv"))
    cells = pd.read_csv(os.path.join(OUT, "cell_shortage.csv"))
    short = int((cells["cell_shortage_flag"] == 1).sum())
    meta = {
        "artifact": "long_horizon_backtest",
        "status": "MECHANISM_EVIDENCE_ONLY",
        "citation_rule": ("성과(수익률·알파·초과수익) 인용 금지. Seed18 은 2026년 시점 선택이므로 "
                          "과거 구간 결과는 선택편향·생존편향을 포함한다. "
                          "본 산출은 규칙 기전 실증용이다."),
        "rule_changes": "없음 — 수집 구간(COLLECT_START/END)과 선정일(SELECTION_DATES_OVERRIDE)만 조정",
        "window": {"start": start, "end": end},
        "selection_rounds": len(sel_dates),
        "index_days": len(idx),
        "cell_shortage_events": short,
        "inputs_sha256_16": {f: sha16(os.path.join(INPUT_LONG, f))
                             for f in sorted(os.listdir(INPUT_LONG)) if f.endswith(".csv")},
    }
    with open(os.path.join(OUT, "long_run_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"\n{'='*64}")
    print(f"  산출일수 {len(idx)}일 · 선정 {len(sel_dates)}회 · 셀부족 {short}건")
    print(f"  {OUT}")
    print(f"{'='*64}")
    print("  성과 인용 금지 — 본 산출은 규칙 기전 실증용이다.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default=DEFAULT_START)
    ap.add_argument("--end", default=DEFAULT_END)
    ap.add_argument("--freq", default="Q", choices=["Q", "A"], help="Q=분기(기본) A=연1회")
    ap.add_argument("--basket", default=os.path.join(PILOT_INPUT, "seed_basket.csv"))
    ap.add_argument("--skip-collect", action="store_true")
    a = ap.parse_args()

    if not load_env():
        print("[경고] .env 미발견 — ECOS 환율 수집이 실패할 수 있다")
    if not a.skip_collect:
        collect(a.start, a.end, a.basket)
    prices = build_inputs(a.basket)

    sel = selection_dates(a.start, a.end, a.freq)
    sel, dropped = drop_unseedable(sel, prices)
    if dropped:
        print(f"[제외] 선정 {len(dropped)}회차 — 편입 가능 종목 0 "
              f"({dropped[0][0]} ~ {dropped[-1][0]}, 사유: {dropped[0][1]})")
    if not sel:
        raise SystemExit("[중단] 편입 가능한 선정일이 0개다. 구간을 넓힐 것.")
    if run_engine(sel) != 0:
        raise SystemExit("[중단] 엔진 실행 실패")
    summarize(a.start, a.end, sel)


if __name__ == "__main__":
    main()
