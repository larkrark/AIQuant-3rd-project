# -*- coding: utf-8 -*-
"""독립 재산출 교차검증 — 팀 수집본 vs 내 수집본을 각각 engine 에 통과시켜 지수 시계열 대조.

목적: 동일 룰북·동일 유니버스(seed_basket)로 '독립 수집한 두 입력'이 같은 지수를 내는지 확인.
      일치 = 재현성 확보(양측 배관 신뢰), 불일치 = 원인(입력 출처·창·결측)을 룰북 대조로 규명.
전제: 두 경로 모두 KR 인계 대기(US only)·KRX 로그인 미보유(^KS200 예비) 상태이므로 근접 예상.

산출: 겹치는 거래일 구간의 (내 지수 vs 팀 지수) 오버레이·차이·요약표 대시보드 + 콘솔 리포트.
"""
import os
import sys
import shutil
import subprocess
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.abspath(os.path.join(HERE, "..", "engine"))
sys.path.insert(0, HERE)
import metrics as M
import report as R   # 팔레트·스타일 재사용 (동일 디자인 시스템)

C = R.C
TEAM_C = "#1baf7a"   # 팀 = 아쿠아(팔레트 슬롯3, 슬롯1 파랑과 CVD 안전)


def assemble_team_input(input_data: str, out_dir: str) -> None:
    """팀 input_data/* 를 run_pilot 입력계약으로 조립 (파일명·컬럼 정합).
    분리 저장된 팀 산출(prices_us·listings_us_fixed 등)을 engine 이 기대하는 이름으로 매핑."""
    os.makedirs(out_dir, exist_ok=True)
    cp = lambda src, dst: shutil.copy(os.path.join(input_data, src), os.path.join(out_dir, dst))
    # US 전용 현황: prices_us → prices (KR 인계 시 concat 확장 지점)
    pd.read_csv(os.path.join(input_data, "prices_us.csv"), dtype={"security_id": str}) \
        .to_csv(os.path.join(out_dir, "prices.csv"), index=False)
    # 상장일: fixed 본에서 계약 컬럼만 추출
    pd.read_csv(os.path.join(input_data, "listings_us_fixed.csv"), dtype={"security_id": str}) \
        [["security_id", "listing_date"]].to_csv(os.path.join(out_dir, "listings.csv"), index=False)
    for f in ("calendar.csv", "fx.csv", "bm_kr.csv", "bm_us.csv"):
        cp(f, f)
    shutil.copy(os.path.join(ENGINE, "seed_basket.csv"), os.path.join(out_dir, "seed_basket.csv"))
    pd.DataFrame(columns=["security_id", "market_date", "full_day_halt"]) \
        .to_csv(os.path.join(out_dir, "halts.csv"), index=False)   # KR 정지 인계 대기


def _run_engine(in_dir: str, out_dir: str) -> None:
    """engine(run_pilot) 실행 — 입력폴더 → 산출폴더."""
    subprocess.run([sys.executable, "run_pilot.py", in_dir, out_dir], cwd=ENGINE, check=True)


def _load(out_dir: str) -> pd.DataFrame:
    df = pd.read_csv(os.path.join(out_dir, "index_vs_benchmark.csv"))
    df["market_date"] = pd.to_datetime(df["market_date"])
    return df.sort_values("market_date")


def _cmp_row(name, s):
    idx = s["index"]
    return (f"  {name:6}  누적 {idx['total_return']*100:+6.2f}%  "
            f"변동성 {idx['ann_vol']*100:5.1f}%  Sharpe {idx['sharpe']:5.2f}  "
            f"MDD {idx['mdd']*100:6.2f}%")


def make_comparison(mine_dir: str, team_dir: str, fig_path: str) -> dict:
    """두 산출을 겹치는 구간으로 정렬·대조 → 비교 대시보드 저장. 요약 dict 반환."""
    mine, team = _load(mine_dir), _load(team_dir)
    # 겹치는 거래일만 비교 (수집 창 차이 흡수). 양측 첫 공통일 기준 재리베이스로 형태 비교.
    merged = mine.merge(team, on="market_date", suffixes=("_mine", "_team"), how="inner")
    base_m, base_t = merged["index_level_mine"].iloc[0], merged["index_level_team"].iloc[0]
    merged["idx_mine"] = merged["index_level_mine"] / base_m * 1000
    merged["idx_team"] = merged["index_level_team"] / base_t * 1000
    merged["diff_pct"] = (merged["idx_mine"] / merged["idx_team"] - 1) * 100   # 상대 괴리(%)

    s_mine = M.performance_summary(mine)
    s_team = M.performance_summary(team)
    corr = merged["idx_mine"].pct_change().corr(merged["idx_team"].pct_change())
    max_gap = merged["diff_pct"].abs().max()

    # --- 피겨: 3단 (오버레이 · 상대괴리 · 요약표) ---
    fig = plt.figure(figsize=(12, 10), facecolor=C["surface"], dpi=130)
    gs = fig.add_gridspec(3, 1, height_ratios=[2.0, 1.1, 0.9], hspace=0.5,
                          left=0.08, right=0.95, top=0.83, bottom=0.07)
    fig.suptitle("독립 재산출 교차검증 — 내 수집 vs 팀 수집 (겹치는 구간)",
                 x=0.08, y=0.965, ha="left", fontsize=15, color=C["ink"], fontweight="bold")
    fig.text(0.08, 0.925, f"공통 거래일 {len(merged)}일 · 수익률 상관 {corr:.4f} · "
             f"최대 상대괴리 {max_gap:.2f}%  ·  seed_basket(US, KR 인계대기)·인용금지",
             ha="left", fontsize=9.5, color=C["muted"])

    # (1) 지수 오버레이 — 팀은 점선으로 위에 겹쳐 '일치' 가독화 (완전 일치 시 실선끼리는 가려짐)
    ax = fig.add_subplot(gs[0]); d = merged["market_date"]
    ax.plot(d, merged["idx_mine"], color=C["index"], linewidth=2.4, label="내 수집", zorder=2)
    ax.plot(d, merged["idx_team"], color=TEAM_C, linewidth=1.6, linestyle=(0, (5, 4)),
            label="팀 수집(점선)", zorder=3)
    R._style(ax)
    ax.set_title("지수 오버레이 — 공통 첫날 1,000 재리베이스 (겹치면 동일)", fontsize=12, color=C["ink"],
                 fontweight="bold", loc="left", pad=8)
    ax.legend(loc="upper left", frameon=False, fontsize=9, labelcolor=C["ink2"])
    ax.margins(x=0.02)

    # (2) 상대 괴리(%) — 값이 0 근방이면 축을 ±1%로 고정하고 '일치' 주석 (degenerate 축 방지)
    ax2 = fig.add_subplot(gs[1])
    ax2.fill_between(d, merged["diff_pct"], 0, color=C["index"], alpha=0.14, zorder=2)
    ax2.plot(d, merged["diff_pct"], color=C["ink2"], linewidth=1.3, zorder=3)
    R._style(ax2)
    ax2.axhline(0, color=C["axis"], linewidth=1)
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:+.2f}%"))
    if max_gap < 0.05:
        ax2.set_ylim(-1, 1)
        ax2.text(0.5, 0.62, f"괴리 0 (두 수집 동일 · 최대 {max_gap:.3f}%)", ha="center",
                 va="center", transform=ax2.transAxes, fontsize=11, color=C["good"], fontweight="bold")
    ax2.set_title("상대 괴리 — (내 지수 / 팀 지수 - 1)", fontsize=11, color=C["ink"],
                  fontweight="bold", loc="left", pad=8)
    ax2.margins(x=0.02)

    # (3) 요약표 (텍스트 타일)
    ax3 = fig.add_subplot(gs[2]); ax3.axis("off")
    rows = [
        ("지표", "내 수집", "팀 수집"),
        ("누적수익률", f"{s_mine['index']['total_return']*100:+.2f}%", f"{s_team['index']['total_return']*100:+.2f}%"),
        ("연변동성", f"{s_mine['index']['ann_vol']*100:.1f}%", f"{s_team['index']['ann_vol']*100:.1f}%"),
        ("Sharpe", f"{s_mine['index']['sharpe']:.2f}", f"{s_team['index']['sharpe']:.2f}"),
        ("MDD", f"{s_mine['index']['mdd']*100:.2f}%", f"{s_team['index']['mdd']*100:.2f}%"),
    ]
    for i, (a, b, c) in enumerate(rows):
        y = 0.9 - i * 0.2
        head = (i == 0)
        ax3.text(0.02, y, a, fontsize=10, color=C["ink"] if head else C["ink2"],
                 fontweight="bold" if head else "normal", transform=ax3.transAxes)
        ax3.text(0.42, y, b, fontsize=10, color=C["index"], fontweight="bold" if head else "normal",
                 transform=ax3.transAxes, ha="right")
        ax3.text(0.72, y, c, fontsize=10, color=TEAM_C, fontweight="bold" if head else "normal",
                 transform=ax3.transAxes, ha="right")

    fig.savefig(fig_path, facecolor=C["surface"], bbox_inches="tight")
    plt.close(fig)
    return {"common_days": len(merged), "return_corr": float(corr),
            "max_abs_gap_pct": float(max_gap),
            "final_gap_pct": float(merged["diff_pct"].iloc[-1])}


def main():
    team_in = os.path.join(ENGINE, "team_input")
    team_out = os.path.join(ENGINE, "output_team")
    mine_out = os.path.join(ENGINE, "output_real")   # 내 data_loader→engine 산출(선행 필요)

    print("[1/3] 팀 input_data 조립 → engine 실행 …")
    assemble_team_input(os.path.join(ENGINE, "input_data"), team_in)
    _run_engine("team_input", "output_team")

    if not os.path.exists(os.path.join(mine_out, "index_vs_benchmark.csv")):
        print("[!] 내 산출(output_real) 없음 — 먼저 data_loader + run_pilot 실행 필요")
        sys.exit(1)

    print("[2/3] 두 산출 대조 + 비교 대시보드 생성 …")
    fig_dir = os.path.join(HERE, "figures")
    os.makedirs(fig_dir, exist_ok=True)
    fig_path = os.path.join(fig_dir, "compare_dashboard.png")
    r = make_comparison(mine_out, team_out, fig_path)

    print("[3/3] 완료\n")
    print(_cmp_row("내수집", M.performance_summary(_load(mine_out))))
    print(_cmp_row("팀수집", M.performance_summary(_load(team_out))))
    print(f"\n  공통 거래일 {r['common_days']}일 · 수익률 상관 {r['return_corr']:.4f}")
    print(f"  최대 상대괴리 {r['max_abs_gap_pct']:.2f}% · 최종 괴리 {r['final_gap_pct']:+.2f}%")
    print(f"  → 비교 대시보드: {fig_path}")


if __name__ == "__main__":
    main()
