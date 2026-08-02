# -*- coding: utf-8 -*-
"""장기 백테스트 피겨 산출 — 발표용.

성과 인용 제한이 그림 안에 박혀 나온다. 잘라 쓰더라도 경고가 따라가도록 한 것이다.
Seed18 은 2026년 시점 선택이므로 과거 구간 결과는 선택편향·생존편향을 포함한다.
본 그림의 용도는 성과 제시가 아니라 규칙 기전 실증이다.

사용: python make_figures.py            # out/ 을 읽어 figures/ 에 PNG 저장
"""
import glob
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
FIG = os.path.join(HERE, "figures")
os.makedirs(FIG, exist_ok=True)

for f in ("Malgun Gothic", "AppleGothic", "NanumGothic"):
    if any(f == x.name for x in matplotlib.font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = f
        break
plt.rcParams["axes.unicode_minus"] = False

NAVY, RED, GRAY = "#1E2761", "#C0392B", "#6B6B66"
WARN = ("성과 인용 금지 — Seed18은 2026년 시점 선택이므로 과거 구간 결과는 "
        "선택편향·생존편향을 포함한다. 본 그림은 규칙 기전 실증용이다.")


def save(fig, name, bottom=0.16):
    """경고문은 축 라벨 아래에 따로 자리를 잡아 둔다 — 겹치면 둘 다 못 읽는다."""
    fig.subplots_adjust(bottom=bottom)
    fig.text(0.5, 0.015, WARN, ha="center", fontsize=7.5, color=RED)
    fig.savefig(os.path.join(FIG, name), dpi=160, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    print(f"  {name}")


idx = pd.read_csv(os.path.join(OUT, "index_vs_benchmark.csv"), parse_dates=["market_date"])
cells = pd.read_csv(os.path.join(OUT, "cell_shortage.csv"))
wfiles = sorted(glob.glob(os.path.join(OUT, "weights_*.csv")))
rounds = [os.path.basename(f)[8:18] for f in wfiles]
sets = [set(pd.read_csv(f, dtype={"security_id": str}).security_id) for f in wfiles]
changes = [rounds[i] for i in range(1, len(sets)) if sets[i] != sets[i - 1]]

print(f"figures/ ({len(idx)}일 · {len(rounds)}회차 · 구성변경 {len(changes)}회)")

# ── 1. 누적 곡선 ──────────────────────────────────────────
fig, ax = plt.subplots(figsize=(11, 5.2))
ax.plot(idx.market_date, idx.index_level, color=NAVY, lw=1.6, label="테마지수 (Seed18)")
ax.plot(idx.market_date, idx.benchmark_level, color=GRAY, lw=1.4, ls="--",
        label="합성 BM (KOSPI200 PR + Russell 3000 PR, 50:50)")
for c in changes:
    ax.axvline(pd.Timestamp(c), color=RED, alpha=0.12, lw=0.8)
ax.set_yscale("log")
ax.set_title(f"규칙 기반 산출 {len(idx):,}일 · 정기변경 {len(rounds)}회 중 구성변경 {len(changes)}회",
             color=NAVY, fontsize=13, pad=12)
ax.set_ylabel("지수 (기준 1,000 · 로그축)")
ax.legend(loc="upper left", fontsize=9)
ax.grid(alpha=0.25)
ax.text(0.99, 0.03, "붉은 세로선 = 구성이 실제로 바뀐 정기변경일",
        transform=ax.transAxes, ha="right", fontsize=8, color=RED)
save(fig, "01_누적곡선.png")

# ── 2. 편입 히트맵 ────────────────────────────────────────
ids = sorted({s for st in sets for s in st})
mat = np.array([[1 if i in st else 0 for st in sets] for i in ids])
fig, ax = plt.subplots(figsize=(12, 5.6))
ax.imshow(mat, aspect="auto", cmap="Blues", vmin=0, vmax=1.4, interpolation="nearest")
ax.set_yticks(range(len(ids)))
ax.set_yticklabels(ids, fontsize=8)
step = max(1, len(rounds) // 14)
ax.set_xticks(range(0, len(rounds), step))
ax.set_xticklabels([rounds[i][:7] for i in range(0, len(rounds), step)],
                   rotation=45, ha="right", fontsize=8)
ax.set_title("종목별 편입 구간 — 규칙이 스스로 넣고 뺀 기록", color=NAVY, fontsize=13, pad=12)
save(fig, "02_편입히트맵.png")

# ── 3. 셀 부족 재배분 ─────────────────────────────────────
sh = cells[cells.cell_shortage_flag == 1]
fig, ax = plt.subplots(figsize=(10, 4.4))
if len(sh):
    g = sh.groupby(["cell_id", "resolution"]).size().sort_values()
    ax.barh([f"{a}\n→ {b.split('->')[-1]}" for a, b in g.index], g.values,
            color=NAVY, height=0.55)
    ax.set_xlim(0, g.values.max() * 1.15)
    for i, v in enumerate(g.values):
        ax.text(v + g.values.max() * 0.02, i, f"{v}회", va="center",
                fontsize=11, color=NAVY, fontweight="bold")
ax.set_title(f"셀 부족 재배분 (D-10 ③) — 총 {len(sh)}회 발동",
             color=NAVY, fontsize=13, pad=12)
ax.text(0.5, -0.16, "빈 셀의 몫을 같은 테마 타지역 셀로 넘긴 정기변경 회차 수",
        transform=ax.transAxes, ha="center", fontsize=9, color=GRAY)
ax.grid(axis="x", alpha=0.25)
save(fig, "03_셀부족재배분.png", bottom=0.26)

# ── 4. 롤링 추적오차 ──────────────────────────────────────
r_i = idx.index_level.pct_change()
r_b = idx.benchmark_level.pct_change()
te = (r_i - r_b).rolling(252).std() * np.sqrt(252) * 100
fig, ax = plt.subplots(figsize=(11, 4.2))
ax.plot(idx.market_date, te, color=NAVY, lw=1.3)
ax.fill_between(idx.market_date, 0, te, color=NAVY, alpha=0.10)
ax.set_title("롤링 12개월 추적오차 (연율 %)", color=NAVY, fontsize=13, pad=12)
ax.set_ylabel("%")
ax.grid(alpha=0.25)
save(fig, "04_추적오차.png")

# ── 5. 낙폭 ──────────────────────────────────────────────
dd_i = (idx.index_level / idx.index_level.cummax() - 1) * 100
dd_b = (idx.benchmark_level / idx.benchmark_level.cummax() - 1) * 100
fig, ax = plt.subplots(figsize=(11, 4.2))
ax.fill_between(idx.market_date, dd_i, 0, color=NAVY, alpha=0.35, label="테마지수")
ax.plot(idx.market_date, dd_b, color=GRAY, lw=1.2, ls="--", label="합성 BM")
ax.set_title(f"최대낙폭 — 지수 {dd_i.min():.1f}% · BM {dd_b.min():.1f}%",
             color=NAVY, fontsize=13, pad=12)
ax.set_ylabel("%")
ax.legend(fontsize=9)
ax.grid(alpha=0.25)
save(fig, "05_낙폭.png")

# ── 6. P10 하한 시계열 ────────────────────────────────────
rows = []
for f in sorted(glob.glob(os.path.join(OUT, "thresholds_*.json"))):
    j = json.load(open(f, encoding="utf-8"))
    for mk, v in j.get("provisional_P10", {}).items():
        rows.append({"selection_date": j["selection_date"], "market": mk, "p10": v})
th = pd.DataFrame(rows)
# 단위가 다르다 — 한국은 원, 미국은 달러. 축에 명시하지 않으면 두 그림을 비교해 읽게 된다.
UNIT = {"KR": ("일평균 거래대금 (억 원)", 1e8), "US": ("일평균 거래대금 (백만 USD)", 1e6)}
fig, ax = plt.subplots(1, 2, figsize=(12, 4.4))
for i, mk in enumerate(["KR", "US"]):
    d = th[th.market == mk]
    lbl, div = UNIT[mk]
    ax[i].plot(pd.to_datetime(d.selection_date), d.p10 / div,
               color=NAVY, marker="o", ms=3.5, lw=1.3)
    ax[i].set_title(f"{mk} 유동성 하한 P10", color=NAVY, fontsize=11)
    ax[i].set_ylabel(lbl, fontsize=9)
    ax[i].set_yscale("log")
    ax[i].grid(alpha=0.25, which="both")
    ax[i].tick_params(labelrotation=30, labelsize=8)
fig.suptitle("규칙이 산출한 유동성 하한의 시간 변화 — 고정값이 아니다",
             color=NAVY, fontsize=13)
fig.text(0.5, 0.075, "두 축은 통화가 다르다. 좌우 높이를 비교하지 말 것.",
         ha="center", fontsize=8.5, color=GRAY)
save(fig, "06_P10하한.png", bottom=0.30)

print(f"\n완료 — {FIG}")
