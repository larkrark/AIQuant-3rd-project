# -*- coding: utf-8 -*-
"""데이터 수집 개요 시각화 — 수집한 원본 입력을 엔진 투입 전 눈으로 검수.

목적: data_loader 가 만든 입력 폴더(prices·fx·bm·sources)를 읽어
     '무엇을·얼마나·어떤 출처로' 수집했는지 한 장으로 확인 (수집 단계 자체의 피겨).
설계: report.py 팔레트·스타일 재사용, 테마색 막대·단일축·억제된 격자.
"""
import os
import sys
import json
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import report as R

C = R.C
THEME_C = R.THEME_C


def make_data_overview(input_dir: str, fig_path: str) -> dict:
    """입력 폴더 → 종목별 관측일수·환율·BM 개요 대시보드 저장. 요약 dict 반환."""
    prices = pd.read_csv(os.path.join(input_dir, "prices.csv"), dtype={"security_id": str})
    basket = pd.read_csv(os.path.join(input_dir, "seed_basket.csv"), dtype={"security_id": str})
    theme_of = dict(zip(basket["security_id"], basket["primary_theme"]))
    src = {}
    sp = os.path.join(input_dir, "sources.json")
    if os.path.exists(sp):
        src = json.load(open(sp, encoding="utf-8"))

    # 종목별 관측일수·기간 (커버리지 요약)
    cov = (prices.groupby("security_id")
           .agg(rows=("market_date", "size"), start=("market_date", "min"), end=("market_date", "max"))
           .reset_index())
    cov["theme"] = cov["security_id"].map(theme_of).fillna("ETC")
    cov = cov.sort_values(["theme", "rows"], ascending=[True, False]).reset_index(drop=True)

    fig = plt.figure(figsize=(12, 8.5), facecolor=C["surface"], dpi=130)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.5, 1.0], hspace=0.42, wspace=0.18,
                          left=0.10, right=0.95, top=0.85, bottom=0.08)
    fig.suptitle("데이터 수집 개요 — 엔진 투입 전 원본 검수", x=0.10, y=0.955,
                 ha="left", fontsize=15, color=C["ink"], fontweight="bold")
    win = src.get("window", ["", ""])
    fig.text(0.10, 0.905, f"{win[0]}~{win[1]} · 종목 {len(cov)}개 · fx: {src.get('fx','-')} · "
             f"bm_kr: {src.get('bm_kr','-')} · 인용금지",
             ha="left", fontsize=8.8, color=C["muted"])

    # (1) 종목별 관측일수 — 테마색 막대. 짧은 이력(시즈닝 미달 후보)을 한눈에.
    ax = fig.add_subplot(gs[0, :])
    y = range(len(cov))
    ax.barh(list(y), cov["rows"], color=[THEME_C.get(t, C["muted"]) for t in cov["theme"]],
            height=0.66, zorder=3)
    for i, r in enumerate(cov.itertuples()):
        ax.text(r.rows + max(cov["rows"]) * 0.01, i, f"{r.rows}일 · {r.start}~{r.end}",
                va="center", fontsize=8.3, color=C["ink2"])
    ax.set_yticks(list(y)); ax.set_yticklabels(cov["security_id"], fontsize=9)
    ax.invert_yaxis()
    R._style(ax); ax.grid(axis="x", color=C["grid"], linewidth=0.8); ax.grid(axis="y", visible=False)
    ax.set_xlim(0, max(cov["rows"]) * 1.28)
    ax.set_title("종목별 관측일수 (테마색 · 짧으면 시즈닝 미달 후보)", fontsize=11,
                 color=C["ink"], fontweight="bold", loc="left", pad=8)

    # (2) 환율(ECOS)
    ax2 = fig.add_subplot(gs[1, 0])
    fp = os.path.join(input_dir, "fx.csv")
    if os.path.exists(fp):
        fx = pd.read_csv(fp); fx["market_date"] = pd.to_datetime(fx["market_date"])
        ax2.plot(fx["market_date"], fx["fx_rate"], color=C["index"], linewidth=1.8)
    R._style(ax2); ax2.xaxis.set_major_locator(MaxNLocator(4, prune="both"))
    ax2.set_title("환율 — ECOS 원/달러", fontsize=11, color=C["ink"], fontweight="bold", loc="left", pad=8)

    # (3) BM 오버레이 — 각 첫날 100 리베이스(스케일 상이 → 지수화 비교, 이중축 금지)
    ax3 = fig.add_subplot(gs[1, 1])
    for f, col, name in (("bm_kr.csv", THEME_C["AI_ROBOTICS"], "KOSPI200"),
                         ("bm_us.csv", C["bm"], "Russell3000")):
        p = os.path.join(input_dir, f)
        if os.path.exists(p):
            b = pd.read_csv(p); b["market_date"] = pd.to_datetime(b["market_date"])
            ax3.plot(b["market_date"], b["close"] / b["close"].iloc[0] * 100, color=col,
                     linewidth=1.8, label=name)
    R._style(ax3); ax3.xaxis.set_major_locator(MaxNLocator(4, prune="both"))
    ax3.legend(loc="upper left", frameon=False, fontsize=8.5, labelcolor=C["ink2"])
    ax3.set_title("BM — 각 첫날 100 리베이스", fontsize=11, color=C["ink"], fontweight="bold", loc="left", pad=8)

    fig.savefig(fig_path, facecolor=C["surface"], bbox_inches="tight")
    plt.close(fig)
    return {"securities": len(cov), "min_rows": int(cov["rows"].min()), "max_rows": int(cov["rows"].max())}


if __name__ == "__main__":
    in_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "engine", "real_data")
    fig_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
    os.makedirs(fig_dir, exist_ok=True)
    out = os.path.join(fig_dir, "data_overview.png")
    print(make_data_overview(in_dir, out))
    print(f"→ 수집 개요: {out}")
