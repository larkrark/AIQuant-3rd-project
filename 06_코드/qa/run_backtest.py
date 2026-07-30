# -*- coding: utf-8 -*-
"""성과 평가 진입점 — 실산출물을 읽어 지표·대시보드를 만든다.

입력은 engine 산출 폴더 하나(`index_vs_benchmark.csv` + `weights_*.csv`)뿐이다.
여기서 engine 을 실행하거나 import 하지 않는다 — qa 트랙 독립성 규칙(06_코드/qa/README.md).

사용:
  python run_backtest.py                     # git 등록 실산출(data/pilot_run/output_krxbm) 평가
  python run_backtest.py --alt               # 예비 BM 산출(data/pilot_run/output) 평가
  python run_backtest.py --output-dir <경로>  # 임의 산출 폴더 (내 독립 재산출 등)

합성 표본(engine/tests/make_sample.py) 경로는 제거했다 — 룰북 R12(합성 산출물 인용 금지)와
"실데이터로 본다"는 현재 단계에 맞춘다. 파이프라인 스모크는 engine 트랙 tests/ 가 담당한다.
"""
import os
import sys
import argparse
import json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)      # paths, metrics, report 임포트용
import paths as P
import report as R

P.force_utf8_stdout()


def _fmt(s: dict) -> str:
    """콘솔용 요약표."""
    idx, bm, rel = s["index"], s["benchmark"], s["relative"]
    def p(x): return f"{x*100:+6.2f}%"
    lines = [
        f"  기간            {s['meta']['start']} ~ {s['meta']['end']}  ({s['meta']['n_days']}거래일)",
        "  ─────────────────────────────  지수        BM",
        f"  누적수익률       {p(idx['total_return']):>10}  {p(bm['total_return']):>10}",
        f"  CAGR(연율)       {p(idx['cagr']):>10}  {p(bm['cagr']):>10}",
        f"  연변동성         {idx['ann_vol']*100:9.2f}%  {bm['ann_vol']*100:9.2f}%",
        f"  Sharpe           {idx['sharpe']:10.2f}  {bm['sharpe']:10.2f}",
        f"  최대낙폭(MDD)    {p(idx['mdd']):>10}  {p(bm['mdd']):>10}",
        "  ─────────────────────────────  상대(초과성과)",
        f"  추적오차(TE)     {rel['tracking_error']*100:9.2f}%",
        f"  정보비율(IR)     {rel['information_ratio']:10.2f}",
        f"  BM 상회일 비율   {rel['hit_ratio']*100:9.1f}%",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=None,
                    help="engine 산출 폴더 (기본: data/pilot_run/output_krxbm)")
    ap.add_argument("--alt", action="store_true",
                    help="예비 BM 산출(data/pilot_run/output)을 평가")
    ap.add_argument("--fig-dir", default=P.FIGURES)
    args = ap.parse_args()

    out_dir = args.output_dir or (P.PILOT_OUTPUT_ALT if args.alt else P.PILOT_OUTPUT)
    P.require(os.path.join(out_dir, "index_vs_benchmark.csv"), "engine 산출(index_vs_benchmark.csv)")

    os.makedirs(args.fig_dir, exist_ok=True)
    fig_path = os.path.join(args.fig_dir, "backtest_dashboard.png")

    rel = os.path.relpath(out_dir, P.ROOT)
    print(f"[1/2] 실산출 로드 → {rel}")
    print("[2/2] 성과·위험 지표 계산 + 대시보드 생성 …")
    note = f"실데이터 v0.9-pilot · {rel} · 파일럿 잠정치(인용 시 rule_version 병기)"
    s = R.make_dashboard(out_dir, fig_path, data_note=note)
    s["meta"]["source_dir"] = rel

    # 턴오버 (weights_*.csv 존재 시)
    try:
        s["turnover"] = R.M.compute_turnover(out_dir).to_dict("records")
    except Exception as ex:
        print(f"  - 턴오버 생략({type(ex).__name__})")

    with open(os.path.join(args.fig_dir, "metrics_summary.json"), "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)

    print("완료\n")
    print(_fmt(s))
    if "turnover" in s:
        print("  ─────────────────────────────  턴오버(단방향)")
        for r in s["turnover"]:
            print(f"  {r['rebalance_date']}   {r['one_way_turnover']*100:6.1f}%")
    print(f"\n  → 대시보드: {fig_path}")
    print(f"  → 지표 JSON: {os.path.join(args.fig_dir, 'metrics_summary.json')}")


if __name__ == "__main__":
    main()
