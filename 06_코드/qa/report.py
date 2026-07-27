# -*- coding: utf-8 -*-
"""백테스트 시각화 — 지수 vs BM 성장곡선 · 수중곡선(낙폭) · 초과성과.
설계: 검증된 CVD-안전 팔레트, 얇은 마크, 억제된 격자, 직접 라벨, 단일 축(이중축 금지).
색: 지수=파랑 #2a78d6, BM=주황 #eb6834 (팔레트 슬롯1·2, 인접쌍 통과)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator
import pandas as pd
import metrics as M

# 한글 폰트 (Windows 기본). 없으면 자동 대체.
for _f in ("Malgun Gothic", "AppleGothic", "NanumGothic", "DejaVu Sans"):
    try:
        plt.rcParams["font.family"] = _f
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False

# --- 팔레트 (references/palette.md, light) ---
C = {
    "surface": "#fcfcfb", "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#898781",
    "grid": "#e1e0d9", "axis": "#c3c2b7",
    "index": "#2a78d6", "bm": "#eb6834",       # 카테고리 슬롯 1·2
    "good": "#006300", "bad": "#d03b3b",       # 다이버징(초과성과 +/-)
}
# 테마별 색 (셀 구성 막대) — 팔레트 카테고리 슬롯
THEME_C = {"AI_ROBOTICS": "#2a78d6", "ENERGY_POWER": "#1baf7a", "SPACE_DEFENSE": "#eda100"}


def _style(ax):
    """공통 축 스타일: 상/우 스파인 제거, 수평 격자만, 억제된 색."""
    ax.set_facecolor(C["surface"])
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(C["axis"])
    ax.tick_params(colors=C["muted"], labelsize=9, length=0)
    ax.grid(axis="y", color=C["grid"], linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.xaxis.set_major_locator(MaxNLocator(nbins=5, prune="both"))


def _pct(x):
    return f"{x*100:+.1f}%"


def _kpi_strip(ax, s):
    """상단 KPI 타일: 핵심 숫자 5개를 큰 글씨로."""
    ax.axis("off")
    idx, rel = s["index"], s["relative"]
    tiles = [
        ("누적수익률", _pct(idx["total_return"]), C["good"] if idx["total_return"] >= 0 else C["bad"]),
        ("연변동성", f"{idx['ann_vol']*100:.1f}%", C["ink"]),
        ("Sharpe", f"{idx['sharpe']:.2f}", C["ink"]),
        ("최대낙폭(MDD)", _pct(idx["mdd"]), C["bad"]),
        ("정보비율(IR)", f"{rel['information_ratio']:.2f}", C["ink"]),
    ]
    n = len(tiles)
    for i, (label, val, col) in enumerate(tiles):
        x = (i + 0.5) / n
        ax.text(x, 0.72, val, ha="center", va="center", fontsize=20,
                color=col, fontweight="bold", transform=ax.transAxes)
        ax.text(x, 0.24, label, ha="center", va="center", fontsize=9.5,
                color=C["ink2"], transform=ax.transAxes)


def _growth(ax, df):
    """지수 vs BM 성장곡선 (기준값 시작). 끝점 직접 라벨 + 범례."""
    d = df["market_date"]
    ax.plot(d, df["index_level"], color=C["index"], linewidth=2.0, label="커스텀 지수", zorder=3)
    ax.plot(d, df["benchmark_level"], color=C["bm"], linewidth=2.0, label="합성 BM", zorder=2)
    for col, key, name in ((C["index"], "index_level", "지수"), (C["bm"], "benchmark_level", "BM")):
        y = df[key].iloc[-1]
        ax.scatter([d.iloc[-1]], [y], s=28, color=col, zorder=4)
        ax.annotate(f"{name} {y:,.0f}", (d.iloc[-1], y), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=9,
                    color=col, fontweight="bold")
    _style(ax)
    ax.set_title("성장곡선 — 기준값 1,000 리베이스", fontsize=12,
                 color=C["ink"], fontweight="bold", loc="left", pad=8)
    ax.legend(loc="upper left", frameon=False, fontsize=9, labelcolor=C["ink2"])
    ax.margins(x=0.02)


def _underwater(ax, df):
    """수중곡선: 지수의 직전 최고점 대비 낙폭(0 이하)을 채움."""
    d, dd = df["market_date"], M.drawdown(df["index_level"]) * 100
    ax.fill_between(d, dd, 0, color=C["bad"], alpha=0.14, zorder=2)
    ax.plot(d, dd, color=C["bad"], linewidth=1.4, zorder=3)
    mdd_i = dd.idxmin()
    ax.scatter([d.iloc[mdd_i]], [dd.iloc[mdd_i]], s=30, color=C["bad"], zorder=4)
    ax.annotate(f"MDD {dd.iloc[mdd_i]:.1f}%", (d.iloc[mdd_i], dd.iloc[mdd_i]),
                xytext=(6, -2), textcoords="offset points", fontsize=9,
                color=C["bad"], fontweight="bold")
    _style(ax)
    ax.axhline(0, color=C["axis"], linewidth=1)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_title("수중곡선 — 지수 낙폭", fontsize=11, color=C["ink"],
                 fontweight="bold", loc="left", pad=8)
    ax.margins(x=0.02)


def _excess(ax, df):
    """초과성과(지수−BM 레벨차)를 부호별로 다이버징 채움: 상회=녹색, 하회=적색."""
    d, a = df["market_date"], df["index_level"] - df["benchmark_level"]
    ax.fill_between(d, a, 0, where=(a >= 0), color=C["good"], alpha=0.18, zorder=2)
    ax.fill_between(d, a, 0, where=(a < 0), color=C["bad"], alpha=0.18, zorder=2)
    ax.plot(d, a, color=C["ink2"], linewidth=1.2, zorder=3)
    _style(ax)
    ax.axhline(0, color=C["axis"], linewidth=1)
    ax.set_title("초과성과 — 지수 - BM (0 위=상회)", fontsize=11, color=C["ink"],
                 fontweight="bold", loc="left", pad=8)
    ax.margins(x=0.02)


def _rolling_vol(ax, output_dir, df):
    """롤링 20일 연율 변동성 — 지수 vs BM (위험이 언제 커졌나)."""
    r = M.rolling_metrics(df)
    ax.plot(r["market_date"], r["roll_vol_index"] * 100, color=C["index"], linewidth=1.8, label="지수")
    ax.plot(r["market_date"], r["roll_vol_bm"] * 100, color=C["bm"], linewidth=1.8, label="BM")
    _style(ax)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_title("롤링 변동성 — 20일 연율", fontsize=11, color=C["ink"],
                 fontweight="bold", loc="left", pad=8)
    ax.legend(loc="upper left", frameon=False, fontsize=8.5, labelcolor=C["ink2"], ncol=2)
    ax.margins(x=0.02)


def _rolling_sharpe(ax, output_dir, df):
    """롤링 20일 Sharpe (지수) — 0 기준선 위/아래로 위험조정성과 추이."""
    r = M.rolling_metrics(df)
    d, sh = r["market_date"], r["roll_sharpe_index"]
    ax.plot(d, sh, color=C["ink2"], linewidth=1.4, zorder=3)
    ax.fill_between(d, sh, 0, where=(sh >= 0), color=C["good"], alpha=0.16, zorder=2)
    ax.fill_between(d, sh, 0, where=(sh < 0), color=C["bad"], alpha=0.16, zorder=2)
    _style(ax)
    ax.axhline(0, color=C["axis"], linewidth=1)
    ax.set_title("롤링 Sharpe — 20일 (지수)", fontsize=11, color=C["ink"],
                 fontweight="bold", loc="left", pad=8)
    ax.margins(x=0.02)


def _cell_composition(ax, output_dir):
    """최신 리밸 셀별 목표비중 — 6셀 배정·재배분 결과 (테마색·지역 라벨)."""
    g = M.cell_composition(output_dir)
    labels = [f"{r.primary_theme[:4]}·{r.market}" for r in g.itertuples()]
    colors = [THEME_C.get(r.primary_theme, C["muted"]) for r in g.itertuples()]
    y = range(len(g))
    ax.barh(list(y), g["weight"] * 100, color=colors, height=0.66, zorder=3)
    for i, w in enumerate(g["weight"] * 100):
        ax.text(w + 0.4, i, f"{w:.1f}%", va="center", fontsize=8.5, color=C["ink2"])
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.invert_yaxis()
    _style(ax)
    ax.grid(axis="x", color=C["grid"], linewidth=0.8, zorder=0)
    ax.grid(axis="y", visible=False)
    ax.xaxis.set_major_locator(MaxNLocator(nbins=5))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_title("셀 구성 비중 — 최신 리밸 (테마×지역)", fontsize=11, color=C["ink"],
                 fontweight="bold", loc="left", pad=8)


def make_dashboard(output_dir: str, fig_path: str, data_note: str = "합성데이터(검증용, 인용금지)") -> dict:
    """engine 산출물 → 성과 지표 계산 → 대시보드 PNG 저장. 지표 dict 반환."""
    df = M.load_index_series(output_dir)
    s = M.performance_summary(df)

    fig = plt.figure(figsize=(12, 14.5), facecolor=C["surface"], dpi=130)
    gs = fig.add_gridspec(5, 2, height_ratios=[0.42, 1.7, 1.15, 1.15, 1.15],
                          hspace=0.5, wspace=0.16, left=0.07, right=0.94, top=0.94, bottom=0.05)
    fig.suptitle("백테스트 리포트 — 커스텀 지수 vs 합성 BM",
                 x=0.07, y=0.975, ha="left", fontsize=15, color=C["ink"], fontweight="bold")
    fig.text(0.07, 0.953, f"{s['meta']['start']} ~ {s['meta']['end']}  ·  "
             f"{s['meta']['n_days']}거래일  ·  {data_note}",
             ha="left", fontsize=9.5, color=C["muted"])

    _kpi_strip(fig.add_subplot(gs[0, :]), s)
    _growth(fig.add_subplot(gs[1, :]), df)
    _underwater(fig.add_subplot(gs[2, 0]), df)
    _excess(fig.add_subplot(gs[2, 1]), df)
    _rolling_vol(fig.add_subplot(gs[3, 0]), output_dir, df)
    _rolling_sharpe(fig.add_subplot(gs[3, 1]), output_dir, df)
    _cell_composition(fig.add_subplot(gs[4, :]), output_dir)

    fig.savefig(fig_path, facecolor=C["surface"], bbox_inches="tight")
    plt.close(fig)
    return s
