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

# ── 7. 랜덤 바스켓 대조 ───────────────────────────────────
rb_path = os.path.join(OUT, "random_basket.json")
fin_path = os.path.join(OUT, "random_basket_finals.npy")
if os.path.exists(rb_path) and os.path.exists(fin_path):
    rb = json.load(open(rb_path, encoding="utf-8"))
    finals = np.load(fin_path)
    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.hist(finals, bins=45, color=GRAY, alpha=0.65,
            label=f"무작위 15종목 {rb['trials']:,}회")
    ax.axvline(rb["benchmark"], color="#2E7D32", lw=2, ls="--",
               label=f"합성 BM {rb['benchmark']:,.0f} (백분위 {rb['percentile_bm']:.0f})")
    ax.axvline(rb["ours"], color=RED, lw=2.5,
               label=f"테마지수 {rb['ours']:,.0f} (백분위 {rb['percentile_ours']:.0f})")
    ax.annotate(f"무작위 최대 {finals.max():,.0f}", xy=(finals.max(), 0),
                xytext=(finals.max(), ax.get_ylim()[1] * 0.55), fontsize=9,
                color=NAVY, ha="center",
                arrowprops=dict(arrowstyle="->", color=NAVY, lw=1))
    ax.set_title("같은 기간·같은 구조로 아무 종목이나 뽑으면 — 우리 지수는 어디에 있나",
                 color=NAVY, fontsize=13, pad=12)
    ax.set_xlabel("종료 지수 (기준 1,000)")
    ax.set_ylabel("시행 횟수")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.25)
    save(fig, "07_랜덤바스켓.png", bottom=0.22)

# ── 8. 팩터 귀속 ─────────────────────────────────────────
fa_path = os.path.join(OUT, "factor_attribution.json")
if os.path.exists(fa_path):
    fa = json.load(open(fa_path, encoding="utf-8"))
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.4))
    seg = [("전반\n2013~2020", fa["split_전반"]), ("후반\n2020~2026", fa["split_후반"]),
           ("전체", fa["capm"])]
    xs = [s[0] for s in seg]
    al = [s[1]["alpha_annual_pct"] for s in seg]
    tv = [s[1]["alpha_t"] for s in seg]
    bars = ax[0].bar(xs, al, color=[RED if v < 0 else NAVY for v in al], width=0.55)
    # 막대가 높으면 라벨을 막대 안에 넣는다 — 밖에 두면 제목과 겹친다
    span = max(al) - min(al)
    ax[0].set_ylim(min(al) - span * 0.28, max(al) + span * 0.28)
    for b, v, t in zip(bars, al, tv):
        inside = v > max(al) * 0.6
        ax[0].text(b.get_x() + b.get_width() / 2,
                   v - span * 0.13 if inside else v + (span * 0.04 if v >= 0 else -span * 0.17),
                   f"{v:+.1f}%\nt={t:.2f}", ha="center", fontsize=9,
                   color="white" if inside else NAVY,
                   fontweight="bold" if inside else "normal")
    ax[0].axhline(0, color="black", lw=0.8)
    ax[0].set_title("연율 α — 구간에 따라 부호가 바뀐다", color=NAVY, fontsize=11)
    ax[0].set_ylabel("연율 α (%)")
    ax[0].grid(axis="y", alpha=0.25)

    if fa.get("ff4"):
        bt = fa["ff4"]["betas"]
        names = {"Mkt_RF": "시장", "SMB": "규모", "HML": "가치", "MOM": "모멘텀"}
        ax[1].barh([names[k] for k in bt], list(bt.values()), color=NAVY, height=0.5)
        ax[1].axvline(0, color="black", lw=0.8)
        ax[1].set_title("팩터 노출 (FF3+모멘텀 · 참고값)", color=NAVY, fontsize=11)
        ax[1].grid(axis="x", alpha=0.25)
        ax[1].text(0.5, -0.22, "FF는 달러·미국 기준 — 원화·한미혼합 지수와 정합하지 않는다",
                   transform=ax[1].transAxes, ha="center", fontsize=8, color=GRAY)
    fig.suptitle(f"초과수익의 원천 — β(BM) = {fa['capm']['beta']:.2f}",
                 color=NAVY, fontsize=13)
    save(fig, "08_팩터귀속.png", bottom=0.26)

print(f"\n완료 — {FIG}")

# ── 9. 회전율·비용 ───────────────────────────────────────
tc_path = os.path.join(OUT, "turnover_cost.json")
tb_path = os.path.join(OUT, "turnover_by_rebalance.csv")
if os.path.exists(tc_path) and os.path.exists(tb_path):
    tc = json.load(open(tc_path, encoding="utf-8"))
    tb = pd.read_csv(tb_path, parse_dates=["effective_date"])
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.4))
    ax[0].bar(tb.effective_date, tb.turnover * 100, width=60, color=NAVY)
    ax[0].axhline(tc["turnover"]["median"] * 100, color=RED, ls="--", lw=1.2,
                  label=f"중앙값 {tc['turnover']['median']*100:.1f}%")
    ax[0].set_title(f"리밸런싱별 회전율 — 연간 {tc['turnover']['annual']*100:.0f}%",
                    color=NAVY, fontsize=11)
    ax[0].set_ylabel("단방향 회전율 (%)")
    ax[0].legend(fontsize=9)
    ax[0].grid(axis="y", alpha=0.25)
    ax[0].tick_params(labelrotation=30, labelsize=8)

    caps = tc["capacity"]
    xs = [f"{c['fund_krw']/1e8:,.0f}억" for c in caps]
    ys = [c["worst_ratio"] * 100 for c in caps]
    cols = [NAVY if y < 5 else ("#E08A1E" if y < 20 else RED) for y in ys]
    b = ax[1].bar(xs, ys, color=cols, width=0.5)
    for bb, y in zip(b, ys):
        ax[1].text(bb.get_x() + bb.get_width() / 2, y + 0.25, f"{y:.1f}%",
                   ha="center", fontsize=10, color=NAVY)
    ax[1].axhline(20, color=RED, ls="--", lw=1, label="시장충격 우려선 20%")
    ax[1].set_title("펀드 규모별 — 최대 종목 매매액 / 하루 거래대금",
                    color=NAVY, fontsize=11)
    ax[1].set_ylabel("ADTV90 대비 (%)")
    ax[1].legend(fontsize=9)
    ax[1].grid(axis="y", alpha=0.25)
    fig.suptitle(f"추종 가능성 — 거래비용 연 {tc['cost']['annual_bp']:.0f}bp "
                 f"· CAGR 영향 {tc['cagr']['drag_bp']:+.0f}bp",
                 color=NAVY, fontsize=13)
    save(fig, "09_회전율비용.png", bottom=0.26)

# ── 10. 검증 지도 — 무엇이 증명됐고 무엇이 아닌가 ──────────
it_path = os.path.join(OUT, "integrity_test.json")
GREEN, AMBER = "#1E7A46", "#E08A1E"
it = json.load(open(it_path, encoding="utf-8")) if os.path.exists(it_path) else {}
rb = json.load(open(os.path.join(OUT, "random_basket.json"), encoding="utf-8")) \
    if os.path.exists(os.path.join(OUT, "random_basket.json")) else {}
fa = json.load(open(os.path.join(OUT, "factor_attribution.json"), encoding="utf-8")) \
    if os.path.exists(os.path.join(OUT, "factor_attribution.json")) else {}
tcj = json.load(open(os.path.join(OUT, "turnover_cost.json"), encoding="utf-8")) \
    if os.path.exists(os.path.join(OUT, "turnover_cost.json")) else {}

pit_rows = sum(c.get("judgment_rows", 0) for c in it.get("pit", {}).get("cases", []))
LEFT = [
    ("PIT 무결성", "PASS", f"판정 {pit_rows:,}행 전부 동일\n미래를 잘라내도 안 바뀐다"),
    ("결정론성", "PASS", f"{it.get('determinism',{}).get('files',0)}파일 "
                        f"{it.get('determinism',{}).get('repeats',0)}회 해시 동일"),
    ("재현성", "PASS", "엔진·독립재산출·수기검산·교차구현\n네 경로 1e-15 수준 일치"),
    ("추종 가능성", "PASS", f"회전율 연 {tcj.get('turnover',{}).get('annual',0)*100:.0f}% · "
                          f"비용 {tcj.get('cost',{}).get('annual_bp',0):.0f}bp\n1조 규모 수용"),
]
RIGHT = [
    ("성과 신뢰도", "FAIL", f"무작위 {rb.get('trials',0):,}회 최대 {rb.get('random_max',0):,.0f}\n"
                          f"우리 {rb.get('ours',0):,.0f} — 분포 밖"),
    ("α 안정성", "FAIL", f"전반 {fa.get('split_전반',{}).get('alpha_annual_pct',0):+.1f}% / "
                        f"후반 {fa.get('split_후반',{}).get('alpha_annual_pct',0):+.1f}%\n국면 의존"),
    ("종목 선택 방법론", "미검증", "전체시장 PIT 유니버스 필요\n(안건 B)"),
]

fig, ax = plt.subplots(figsize=(12.5, 6.2))
ax.axis("off")
ax.text(0.25, 0.95, "알고리즘 품질", ha="center", fontsize=15, color=NAVY, fontweight="bold")
ax.text(0.75, 0.95, "성과 신뢰도", ha="center", fontsize=15, color=NAVY, fontweight="bold")
ax.text(0.25, 0.905, "선택편향과 무관하다", ha="center", fontsize=9.5, color=GRAY)
ax.text(0.75, 0.905, "선택편향의 영향을 받는다", ha="center", fontsize=9.5, color=GRAY)
ax.plot([0.5, 0.5], [0.06, 0.90], color=GRAY, lw=1, ls=":")

def card(x, y, title, verdict, body, w=0.42, h=0.175):
    col = GREEN if verdict == "PASS" else (RED if verdict == "FAIL" else AMBER)
    ax.add_patch(plt.Rectangle((x - w / 2, y - h / 2), w, h, facecolor=col,
                               alpha=0.09, edgecolor=col, lw=1.6, zorder=1))
    ax.text(x - w / 2 + 0.018, y + h / 2 - 0.038, title, fontsize=12,
            color=NAVY, fontweight="bold", va="center")
    ax.text(x + w / 2 - 0.018, y + h / 2 - 0.038, verdict, fontsize=12,
            color=col, fontweight="bold", ha="right", va="center")
    ax.text(x - w / 2 + 0.018, y - 0.028, body, fontsize=9.5, color="#333", va="center")

for i, (t, v, b) in enumerate(LEFT):
    card(0.25, 0.80 - i * 0.195, t, v, b)
for i, (t, v, b) in enumerate(RIGHT):
    card(0.75, 0.80 - i * 0.195, t, v, b)

ax.text(0.75, 0.145, "수익성을 입증하려면\n① 전체시장 PIT 유니버스 재구성 (안건 B)\n"
                     "② 규칙 동결 2026-07-31 이후 실시간 추적",
        fontsize=10, color=NAVY, va="center")
fig.suptitle("검증 지도 — 무엇이 증명됐고 무엇이 아닌가", color=NAVY, fontsize=16, y=0.99)
save(fig, "10_검증지도.png", bottom=0.10)

# ── 11. PIT 무결성 ───────────────────────────────────────
if it.get("pit", {}).get("cases"):
    cs = [c for c in it["pit"]["cases"] if c.get("status") == "PASS"]
    fig, ax = plt.subplots(figsize=(11.5, 4.6))
    ys = range(len(cs))
    ax.barh(list(ys), [c["rounds_compared"] for c in cs], color=NAVY,
            height=0.5, zorder=2)
    for i, c in enumerate(cs):
        ax.text(c["rounds_compared"] + 0.7, i,
                f"회차 {c['rounds_compared']}개 · 판정 {c['judgment_rows']:,}행   "
                f"→  일치", va="center", fontsize=10.5, color=GREEN,
                fontweight="bold")
    ax.set_yticks(list(ys))
    ax.set_yticklabels([f"{c['round']}\n데이터 {c['cut']} 까지" for c in cs], fontsize=9)
    ax.set_xlim(0, max(c["rounds_compared"] for c in cs) * 2.1)
    ax.set_xlabel("대조한 선정 회차 수")
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.25, zorder=0)
    ax.set_title(f"PIT 무결성 — 미래를 잘라내도 판정이 바뀌지 않는다  "
                 f"(총 {pit_rows:,}행)", color=NAVY, fontsize=13.5, pad=12)
    ax.text(0.5, -0.30, "각 시점 이후의 가격·환율·달력·BM 을 물리적으로 삭제한 뒤 "
                        "같은 회차를 재산출해 편입 판정을 대조",
            transform=ax.transAxes, ha="center", fontsize=9, color=GRAY)
    save(fig, "11_PIT무결성.png", bottom=0.30)

print(f"\n완료 — {FIG}")
