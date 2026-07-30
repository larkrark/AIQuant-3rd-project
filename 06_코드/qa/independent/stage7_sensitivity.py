# -*- coding: utf-8 -*-
"""7단계 감도원장 — 미결 규칙의 선택지가 지수를 얼마나 바꾸는지

왜 '독립 재산출'이 아니라 '감도원장'인가
  7단계 산식은 아직 미의결이다(룰북 §13 위임 → 데이터사전 산식 없음 · §17 안건 I·J).
  규칙이 없는 상태에서 내가 한 방식을 골라 짜면 두 가지가 무너진다.
    ① 룰북 R2 — 미결 항목을 확정처럼 쓰지 않는다
    ② 검증의 의미 — 엔진과 값이 달라도 그것이 엔진 오류인지 내 선택 차이인지
       구분할 수 없다. 대조가 아무것도 알려주지 못한다.

  그래서 '고르지 않는다'. 대신 **선택지를 전부 계산해 차이를 표로 낸다.**
  이 표는 안건 16의 `영향범위` 칸에 그대로 들어가고, 의결이 끝나면
  --pick 인자로 그 조합을 지정해 독립 재산출을 즉시 완료할 수 있다.

독립성
  가중치는 engine 산출물이 아니라 **내 6단계 독립 재산출 결과**를 쓴다
  (independent/out/weights_*.csv, weighting_rule_version=v0.9-pilot-independent).
  corrected_run/rebuild_index.py 는 공표 weights 를 썼으므로 이 점이 다르다.
  engine 모듈은 import 하지 않는다.

기준선(baseline)의 의미
  표의 기준선은 run_meta.json 에 기록된 **엔진의 현재 선택**이다.
  이것은 '엔진이 무엇을 하고 있는가'라는 사실이며 '그것이 규칙'이라는 뜻이 아니다.
  채택 근거로 인용하지 말 것 — MIGYEOL.md F-3 과 같은 취지다.

실행
  python stage7_sensitivity.py                 # 감도원장 산출
  python stage7_sensitivity.py --pick fx=PREV_DAY,ca=SPLIT_5_ON_LISTING
"""
import argparse
import itertools
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import paths as P  # noqa: E402

INPUT = P.PILOT_INPUT
PUBLISHED = os.path.join(P.PILOT, "output_f1")
MINE = os.path.join(HERE, "out")
OUT = os.path.join(HERE, "out_stage7")

BASE_LEVEL = 1000.0
ROUND = "2026-03-31"          # 지수구간(4/1~6/30)에 적용된 회차

# ── 미결 축과 선택지 ─────────────────────────────────────────────
# 기준선(첫 항목)은 엔진 현재값이다. 우열 판단이 아니라 표시 순서일 뿐이다.
AXES = {
    # B-2 환율 적용 시점 (룰북 §12.3 미결)
    "fx": ["SAME_DAY", "PREV_DAY", "BASE_DATE_FIXED"],
    # B-3 산출일 축 (룰북 §12.3 미결)
    "days": ["COMMON_OPEN_ONLY", "UNION_CARRY"],
    # B-1 연결 방식 (룰북 §13.5 "연결계수 또는 제수 조정")
    "link": ["SEGMENT_RELINK", "DIVISOR_ADJUST"],
    # B-5 기업행사 (룰북 §17 안건 I·J) — 경계일·비율축 두 판단이 섞여 있다
    "ca": ["NONE", "SPLIT_5_ON_LISTING", "SPLIT_5_ON_EFFECTIVE", "SPLIT_333_ON_LISTING"],
    # BM 미국분 환율 환산 (어느 문서에도 없음 — 신규 안건 대상)
    "bmfx": ["CONVERT", "LEVEL_ONLY"],
}
BASELINE = {k: v[0] for k, v in AXES.items()}

CA_SPEC = {
    "NONE": None,
    "SPLIT_5_ON_LISTING": (5.0, "2026-04-13"),      # 신주권상장·거래재개일
    "SPLIT_5_ON_EFFECTIVE": (5.0, "2026-04-10"),    # 신주 효력발생일
    "SPLIT_333_ON_LISTING": (1000 / 300, "2026-04-13"),  # 원공시 주식수 기준(정정 전)
}
CA_SID = "010120"


def load():
    st = pd.read_csv(os.path.join(PUBLISHED, "daily_market_state.csv"),
                     dtype={"security_id": str}, parse_dates=["market_date"])
    fx = pd.read_csv(os.path.join(INPUT, "fx.csv"),
                     parse_dates=["market_date"]).set_index("market_date")["fx_rate"]
    cal = pd.read_csv(os.path.join(INPUT, "calendar.csv"), parse_dates=["market_date"])
    bk = pd.read_csv(os.path.join(INPUT, "bm_kr.csv"),
                     parse_dates=["market_date"]).set_index("market_date")["close"]
    bu = pd.read_csv(os.path.join(INPUT, "bm_us.csv"),
                     parse_dates=["market_date"]).set_index("market_date")["close"]
    wp = P.require(os.path.join(MINE, f"weights_{ROUND}.csv"),
                   "내 6단계 독립 재산출 가중 (먼저 recompute.py 를 실행할 것)")
    w = pd.read_csv(wp, dtype={"security_id": str})
    pub = pd.read_csv(os.path.join(PUBLISHED, "index_vs_benchmark.csv"),
                      parse_dates=["market_date"])
    return st, fx, cal, bk, bu, w, pub


def calc_days(cal, start, end, mode):
    kr = set(cal[(cal.market == "KR") & (cal.is_market_open == 1)]["market_date"])
    us = set(cal[(cal.market == "US") & (cal.is_market_open == 1)]["market_date"])
    sel = (kr & us) if mode == "COMMON_OPEN_ONLY" else (kr | us)
    return [d for d in sorted(sel) if start <= d <= end]


def fx_series(fx, days, mode):
    """평가일에 적용할 환율 계열.

    PREV_DAY 는 '직전 환율 관측일'이다. 달력 하루 전이 주말이면 값이 없으므로
    관측 계열 자체에서 한 칸 밀어야 한다 — reindex 후 shift 하면 결측 구간에서
    엉뚱한 값이 붙는다.
    """
    if mode == "SAME_DAY":
        return fx.reindex(days).ffill()
    if mode == "PREV_DAY":
        prev = fx.shift(1)                      # 관측 계열에서 한 칸 밀기
        return prev.reindex(days).ffill()
    if mode == "BASE_DATE_FIXED":
        v = fx.reindex(days).ffill().iloc[0]
        return pd.Series(v, index=pd.Index(days, name="market_date"))
    raise ValueError(mode)


def prices_krw(st, w, days, fxs, ca):
    ids = w["security_id"].tolist()
    px = (st[st.security_id.isin(ids)]
          .pivot(index="market_date", columns="security_id", values="raw_close")
          .reindex(days).ffill())

    spec = CA_SPEC[ca]
    if spec and CA_SID in px.columns:
        ratio, eff = spec
        e = pd.Timestamp(eff)
        # 분할 전용 조정 — 경계일 '이전' 가격을 비율로 나눈다 (데이터사전 4.1)
        px.loc[px.index < e, CA_SID] = px.loc[px.index < e, CA_SID] / ratio

    mkt = w.set_index("security_id")["market"]
    for sid in px.columns:
        if mkt.get(sid) == "US":
            px[sid] = px[sid] * fxs.values
    return px


def index_level(px, w, link):
    """지수 레벨.

    SEGMENT_RELINK  구간 시작가 대비 가중평균 수익률 × 기준값
    DIVISOR_ADJUST  주식수 고정 후 시가총액 ÷ 제수. 기준일에 제수를 맞춘다.

    파일럿 지수구간에는 유효 리밸런싱 적용일이 없어 단일 구간이므로 두 방식이
    수학적으로 같아진다. 그 '같다'는 것이 안건 16 의 영향범위 답이다.
    """
    ww = w.set_index("security_id")["final_target_weight"].reindex(px.columns)
    base = px.iloc[0]
    if link == "SEGMENT_RELINK":
        return (px.divide(base, axis=1) * ww.values).sum(axis=1) * BASE_LEVEL
    if link == "DIVISOR_ADJUST":
        shares = ww.values / base.values          # 기준일 비중을 주식수로 환산
        mcap = (px * shares).sum(axis=1)
        return mcap / mcap.iloc[0] * BASE_LEVEL
    raise ValueError(link)


def bm_level(bk, bu, fxs, days, mode):
    kr = bk.reindex(days).ffill()
    us = bu.reindex(days).ffill()
    if mode == "CONVERT":
        us = us * fxs.values                     # 원화·무헤지 지수와 통화 기준을 맞춤
    return (0.5 * kr / kr.iloc[0] + 0.5 * us / us.iloc[0]) * BASE_LEVEL


def run(st, fx, cal, bk, bu, w, start, end, cfg, pub=None):
    days = calc_days(cal, start, end, cfg["days"])
    fxs = fx_series(fx, days, cfg["fx"])
    px = prices_krw(st, w, days, fxs, cfg["ca"])
    idx = index_level(px, w, cfg["link"])
    bm = bm_level(bk, bu, fxs, days, cfg["bmfx"])
    ir = idx.iloc[-1] / BASE_LEVEL - 1.0
    br = bm.iloc[-1] / BASE_LEVEL - 1.0

    # 경로 지표 — 터미널값만 보면 놓치는 것을 잡는다.
    # 조정 경계일을 효력발생일로 잡으면 유령 하락이 위치만 옮겨가므로 최종 레벨은
    # 같지만 일간수익률·변동성·낙폭이 달라진다. 그 차이가 여기서만 드러난다.
    ri = idx.pct_change().dropna()
    rb = bm.reindex(idx.index).pct_change().dropna()
    common = ri.index.intersection(rb.index)
    te = float((ri[common] - rb[common]).std(ddof=1) * np.sqrt(252) * 100) if len(common) > 1 else np.nan
    dd = float((idx / idx.cummax() - 1.0).min() * 100)

    out = {
        "n_days": len(days),
        "index_last": float(idx.iloc[-1]),
        "index_ret_pct": float(ir * 100),
        "bm_last": float(bm.iloc[-1]),
        "bm_ret_pct": float(br * 100),
        "excess_pp": float((ir - br) * 100),
        "fx_missing": int(pd.Series(fxs).isna().sum()),
        "ann_vol_pct": float(ri.std(ddof=1) * np.sqrt(252) * 100),
        "tracking_err_pct": te,
        "max_drawdown_pct": dd,
        "max_daily_ret_pct": float(ri.max() * 100),
        "min_daily_ret_pct": float(ri.min() * 100),
    }
    if pub is not None:
        # 공표 산출물을 재현하는 조합이 어느 것인지 식별한다. 이것은 '엔진이
        # 무엇을 구현했는가'를 독립 구현으로 확인하는 것이며, 규칙 채택이 아니다.
        p = pub.set_index("market_date")["index_level"].reindex(idx.index)
        ok = p.notna()
        out["repro_max_rel_err"] = (float(((idx[ok] - p[ok]).abs() / p[ok]).max())
                                    if ok.any() else np.nan)
        out["reproduces_published"] = bool(ok.sum() == len(pub)
                                           and out["repro_max_rel_err"] < 1e-9)
    return out


def main():
    P.force_utf8_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("--pick", default="", help="예: fx=PREV_DAY,ca=SPLIT_5_ON_LISTING")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    st, fx, cal, bk, bu, w, pub = load()
    start, end = pub.market_date.min(), pub.market_date.max()
    print(f"[구간] {start.date()} ~ {end.date()}")
    print(f"[가중] 내 6단계 독립 재산출 {len(w)}종목 · "
          f"{w.weighting_rule_version.iloc[0]}")
    print(f"[가중합] {w.final_target_weight.sum():.12f}\n")

    if args.pick:
        cfg = dict(BASELINE)
        for kv in args.pick.split(","):
            k, v = kv.split("=")
            if k not in AXES or v not in AXES[k]:
                raise SystemExit(f"[중단] 선택지 아님: {k}={v}")
            cfg[k] = v
        r = run(st, fx, cal, bk, bu, w, start, end, cfg)
        print("[지정 조합]", cfg)
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return 0

    # ── 기준선 ────────────────────────────────────────────────
    b = run(st, fx, cal, bk, bu, w, start, end, BASELINE)
    print("[기준선] run_meta.json 의 엔진 현재 선택 — 사실이며 채택 근거가 아니다")
    for k, v in BASELINE.items():
        print(f"    {k:6s} = {v}")
    print(f"    산출일 {b['n_days']}일 · 환율결측 {b['fx_missing']}일")
    print(f"    지수 {b['index_last']:.4f} ({b['index_ret_pct']:+.4f}%) · "
          f"BM 대비 {b['excess_pp']:+.4f}%p\n")

    # ── 한 축씩만 바꾼다 (one-at-a-time) ──────────────────────
    print("[감도] 한 축만 바꿨을 때의 변화")
    rows = []
    for ax, opts in AXES.items():
        for o in opts:
            cfg = dict(BASELINE)
            cfg[ax] = o
            r = run(st, fx, cal, bk, bu, w, start, end, cfg)
            d_idx = r["index_last"] - b["index_last"]
            d_pp = r["excess_pp"] - b["excess_pp"]
            rows.append({
                "axis": ax, "option": o, "is_baseline": o == BASELINE[ax],
                "n_days": r["n_days"], "index_last": r["index_last"],
                "index_ret_pct": r["index_ret_pct"], "excess_pp": r["excess_pp"],
                "delta_index": d_idx, "delta_excess_pp": d_pp,
                "no_effect_in_pilot": abs(d_pp) < 1e-9,
            })
            mark = "  (기준선)" if o == BASELINE[ax] else ""
            eff = "영향 없음" if abs(d_pp) < 1e-9 else f"{d_pp:+.4f}%p"
            print(f"    {ax:6s} {o:22s} 지수 {r['index_last']:10.4f}  {eff}{mark}")
        print()

    df = pd.DataFrame(rows)
    dst = os.path.join(OUT, "stage7_sensitivity.csv")
    df.to_csv(dst, index=False, encoding="utf-8-sig")

    # ── 경로 지표 — 터미널값이 같아도 갈리는 축을 드러낸다 ─────
    print("[경로] 최종 레벨이 같아도 경로가 다른 경우")
    shown = False
    for ax, opts in AXES.items():
        base_r = run(st, fx, cal, bk, bu, w, start, end, BASELINE)
        for o in opts:
            if o == BASELINE[ax]:
                continue
            cfg = dict(BASELINE); cfg[ax] = o
            r = run(st, fx, cal, bk, bu, w, start, end, cfg)
            same_level = abs(r["index_last"] - base_r["index_last"]) < 1e-9
            diff_path = (abs(r["ann_vol_pct"] - base_r["ann_vol_pct"]) > 1e-6
                         or abs(r["max_drawdown_pct"] - base_r["max_drawdown_pct"]) > 1e-6)
            if same_level and diff_path:
                shown = True
                print(f"    {ax}={o}  최종레벨 동일인데 경로가 다름")
                print(f"      변동성 {base_r['ann_vol_pct']:.4f}% -> {r['ann_vol_pct']:.4f}%"
                      f" · 최대낙폭 {base_r['max_drawdown_pct']:.4f}% -> {r['max_drawdown_pct']:.4f}%"
                      f" · 최저 일간 {base_r['min_daily_ret_pct']:.4f}% -> {r['min_daily_ret_pct']:.4f}%")
    if not shown:
        print("    해당 없음")
    print()

    # ── 전체 조합을 공표 산출물과 대조 ────────────────────────
    print("[전수] 96개 조합 중 공표 산출물을 재현하는 조합")
    keys = list(AXES)
    full, hits = [], []
    for combo in itertools.product(*[AXES[k] for k in keys]):
        cfg = dict(zip(keys, combo))
        r = run(st, fx, cal, bk, bu, w, start, end, cfg, pub=pub)
        row = dict(cfg); row.update(r); full.append(row)
        if r.get("reproduces_published"):
            hits.append(cfg)
    pd.DataFrame(full).to_csv(os.path.join(OUT, "stage7_full_grid.csv"),
                              index=False, encoding="utf-8-sig")
    print(f"    재현 조합 {len(hits)}개 / 전체 {len(full)}개")
    for h in hits:
        print("      " + " · ".join(f"{k}={v}" for k, v in h.items()))
    if len(hits) == 1:
        print("    -> 공표 산출물이 어느 규칙으로 만들어졌는지 독립 구현으로 특정됨.")
        print("       '엔진이 무엇을 했는가'의 확인이며 '그것이 규칙'이라는 뜻은 아니다.")
    elif not hits:
        print("    -> 어느 조합도 재현하지 못했다. 명세 밖 처리가 있다는 뜻이므로 확인 필요.")
    print()

    # ── 미결 축이 만드는 전체 폭 ──────────────────────────────
    print("[폭] 각 축이 BM 대비 초과수익에 만드는 최대 격차")
    span = (df.groupby("axis")["excess_pp"].agg(["min", "max"])
              .assign(span_pp=lambda x: x["max"] - x["min"])
              .sort_values("span_pp", ascending=False))
    for ax, r in span.iterrows():
        tag = "  <- 파일럿 구간에서 영향 없음" if r.span_pp < 1e-9 else ""
        print(f"    {ax:6s} {r.span_pp:8.4f}%p{tag}")

    total = len(list(itertools.product(*AXES.values())))
    print(f"\n[조합] 미결 축 {len(AXES)}개 → 가능한 조합 {total}가지")
    print(f"[산출] {os.path.relpath(dst, P.ROOT)}")
    print("\n인용 제한 — 이 표는 안건 16의 '영향범위' 자료다.")
    print("  어느 행도 공표 성과가 아니며, 기준선을 채택 근거로 쓰지 않는다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
