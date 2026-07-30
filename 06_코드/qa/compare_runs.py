# -*- coding: utf-8 -*-
"""독립 재산출 교차검증 — 두 실산출 폴더의 지수 시계열을 대조한다.

목적: 동일 룰북·동일 유니버스(seed_basket)에서 '독립 수집한 입력'이 같은 지수를 내는지 확인.
      일치 = 재현성 확보(양측 배관 신뢰), 불일치 = 원인(입력 출처·창·결측)을 룰북 대조로 규명.

기본 대조쌍 (둘 다 실데이터):
  기준(팀) = data/pilot_run/output_krxbm  — git 등록된 파일럿 본실행 산출(KR9+US9, KRX 공식 BM)
  내 재산출 = engine/output_real          — data_loader 독립 수집본을 통과시킨 산출(git 미추적)

이 스크립트는 engine 을 실행하거나 import 하지 않는다 — qa 트랙 독립성 규칙.
비교 대상은 '이미 산출된 결과'이며, 산출 자체는 각 트랙에서 별도로 수행한다.
(2026-07-24 팀 리팩터 전에는 여기서 팀 input_data 를 조립해 engine 을 직접 돌렸다.
 그 경로는 engine/input_data 이동으로 깨졌고, 독립성 규칙과도 어긋나 제거했다.)

산출: 겹치는 거래일 구간의 (내 지수 vs 기준 지수) 오버레이·차이·요약표 대시보드 + 콘솔 리포트.
"""
import os
import sys
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paths as P
import metrics as M
import report as R   # 팔레트·스타일 재사용 (동일 디자인 시스템)

P.force_utf8_stdout()

C = R.C
TEAM_C = "#1baf7a"   # 기준(팀) = 아쿠아(팔레트 슬롯3, 슬롯1 파랑과 CVD 안전)


def _load(out_dir: str) -> pd.DataFrame:
    df = pd.read_csv(os.path.join(out_dir, "index_vs_benchmark.csv"))
    df["market_date"] = pd.to_datetime(df["market_date"])
    return df.sort_values("market_date")


def _cmp_row(name, s):
    idx = s["index"]
    return (f"  {name:6}  누적 {idx['total_return']*100:+6.2f}%  "
            f"변동성 {idx['ann_vol']*100:5.1f}%  Sharpe {idx['sharpe']:5.2f}  "
            f"MDD {idx['mdd']*100:6.2f}%")


def make_comparison(mine_dir: str, team_dir: str, fig_path: str, align: bool = True) -> dict:
    """두 산출을 겹치는 구간으로 정렬·대조 → 비교 대시보드 저장. 요약 dict 반환.
    align=True: 요약표도 '겹치는 구간'으로 잘라 계산 → 종료일 차이(창) 착시 제거.
    align=False: 요약표는 각 전체구간(관측창 차이 그대로 노출)."""
    mine, team = _load(mine_dir), _load(team_dir)
    # 겹치는 거래일만 비교 (수집 창 차이 흡수). 양측 첫 공통일 기준 재리베이스로 형태 비교.
    merged = mine.merge(team, on="market_date", suffixes=("_mine", "_team"), how="inner")
    base_m, base_t = merged["index_level_mine"].iloc[0], merged["index_level_team"].iloc[0]
    merged["idx_mine"] = merged["index_level_mine"] / base_m * 1000
    merged["idx_team"] = merged["index_level_team"] / base_t * 1000
    merged["diff_pct"] = (merged["idx_mine"] / merged["idx_team"] - 1) * 100   # 상대 괴리(%)

    # 요약표 계산 구간: align 시 겹치는 날짜로 양측을 잘라 창 차이를 제거
    common = set(merged["market_date"])
    mine_s = mine[mine["market_date"].isin(common)] if align else mine
    team_s = team[team["market_date"].isin(common)] if align else team
    s_mine = M.performance_summary(mine_s)
    s_team = M.performance_summary(team_s)
    corr = merged["idx_mine"].pct_change().corr(merged["idx_team"].pct_change())
    max_gap = merged["diff_pct"].abs().max()

    # --- 피겨: 3단 (오버레이 · 상대괴리 · 요약표) ---
    fig = plt.figure(figsize=(12, 10), facecolor=C["surface"], dpi=130)
    gs = fig.add_gridspec(3, 1, height_ratios=[2.0, 1.1, 0.9], hspace=0.5,
                          left=0.08, right=0.95, top=0.83, bottom=0.07)
    fig.suptitle("독립 재산출 교차검증 — 내 수집 vs 팀 수집 (겹치는 구간)",
                 x=0.08, y=0.965, ha="left", fontsize=15, color=C["ink"], fontweight="bold")
    align_note = "요약표=겹치는구간 정렬" if align else "요약표=각 전체구간"
    fig.text(0.08, 0.925, f"공통 거래일 {len(merged)}일 · 수익률 상관 {corr:.4f} · "
             f"최대 상대괴리 {max_gap:.2f}% · {align_note}  ·  실데이터 v0.9-pilot(파일럿 잠정치)",
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
            "final_gap_pct": float(merged["diff_pct"].iloc[-1]),
            "summary_mine": s_mine, "summary_team": s_team, "aligned": align}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--mine", default=P.MINE_OUTPUT,
                    help="내 재산출 폴더 (기본: engine/output_real)")
    ap.add_argument("--team", default=P.PILOT_OUTPUT,
                    help="대조 기준 폴더 (기본: data/pilot_run/output_krxbm — git 등록 실산출)")
    ap.add_argument("--no-align", action="store_true",
                    help="요약표를 각 전체구간으로(창 차이 노출). 기본은 겹치는구간 정렬")
    args = ap.parse_args()

    team_out, mine_out = args.team, args.mine
    P.require(os.path.join(team_out, "index_vs_benchmark.csv"), "대조 기준 산출")
    if not os.path.exists(os.path.join(mine_out, "index_vs_benchmark.csv")):
        print(f"[!] 내 재산출 없음: {mine_out}")
        print("    독립 수집(python data_loader.py) → 그 입력으로 지수 산출 후 --mine 으로 지정.")
        sys.exit(1)

    print(f"[1/2] 대조 대상 로드")
    print(f"      기준(팀)   {os.path.relpath(team_out, P.ROOT)}")
    print(f"      내 재산출  {os.path.relpath(mine_out, P.ROOT)}")

    print("[2/2] 두 산출 대조 + 비교 대시보드 생성 …")
    fig_dir = P.FIGURES
    os.makedirs(fig_dir, exist_ok=True)
    fig_path = os.path.join(fig_dir, "compare_dashboard.png")
    r = make_comparison(mine_out, team_out, fig_path, align=not args.no_align)

    print("완료\n")
    print(f"  [{'겹치는구간 정렬' if r['aligned'] else '각 전체구간'}]")
    print(_cmp_row("내수집", r["summary_mine"]))
    print(_cmp_row("팀수집", r["summary_team"]))
    print(f"\n  공통 거래일 {r['common_days']}일 · 수익률 상관 {r['return_corr']:.4f}")
    print(f"  최대 상대괴리 {r['max_abs_gap_pct']:.2f}% · 최종 괴리 {r['final_gap_pct']:+.2f}%")
    print(f"  → 비교 대시보드: {fig_path}")


if __name__ == "__main__":
    main()
