# -*- coding: utf-8 -*-
"""백테스트 진입점 — 얇은 오케스트레이터.
규칙 로직은 여기 없다. engine을 '호출'만 하고, 평가(metrics)·시각화(report)를 묶는다.

사용:
  python run_backtest.py                 # 기존 engine 산출물(output/)로 평가만
  python run_backtest.py --run-engine    # 합성데이터 생성 → engine 실행 → 평가까지 한 번에

개발 순서상 지금은 --run-engine 이 make_sample(가짜 데이터)로 돈다.
실데이터가 오면 data_loader 로 같은 스키마 CSV만 갈아끼우면 코드 변경 없이 재실행된다.
"""
import os
import sys
import subprocess
import argparse
import json

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.abspath(os.path.join(HERE, "..", "engine"))
sys.path.insert(0, HERE)      # metrics, report 임포트용
import report as R


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
    ap.add_argument("--output-dir", default=os.path.join(ENGINE, "output"),
                    help="engine 산출물 폴더 (index_vs_benchmark.csv 위치)")
    ap.add_argument("--fig-dir", default=os.path.join(HERE, "figures"))
    ap.add_argument("--run-engine", action="store_true",
                    help="데이터 생성 + engine 실행부터 수행")
    ap.add_argument("--source", choices=["sample", "real"], default="sample",
                    help="sample=합성(make_sample) · real=실데이터(data_loader)")
    args = ap.parse_args()

    if args.run_engine:
        if args.source == "real":
            print("[1/3] 실데이터 수집(data_loader) + engine 실행 …")
            real_dir = os.path.join(ENGINE, "real_data")
            import data_loader
            data_loader.build_inputs(real_dir)
            in_name, out_name = "real_data", "output_real"
        else:
            print("[1/3] 합성데이터 생성(make_sample) + engine 실행 …")
            subprocess.run([sys.executable, "make_sample.py"], cwd=ENGINE, check=True)
            in_name, out_name = "sample_data", "output"
        subprocess.run([sys.executable, "run_pilot.py", in_name, out_name],
                       cwd=ENGINE, check=True)
        args.output_dir = os.path.join(ENGINE, out_name)

    os.makedirs(args.fig_dir, exist_ok=True)
    fig_path = os.path.join(args.fig_dir, "backtest_dashboard.png")

    print("[2/3] 성과·위험 지표 계산 + 대시보드 생성 …")
    note = ("실데이터·데모 유니버스(검증용, 인용금지)" if args.source == "real"
            else "합성데이터(검증용, 인용금지)")
    s = R.make_dashboard(args.output_dir, fig_path, data_note=note)

    # 턴오버 (weights_*.csv 존재 시)
    try:
        to = R.M.compute_turnover(args.output_dir)
        s["turnover"] = to.to_dict("records")
    except Exception:
        pass

    with open(os.path.join(args.fig_dir, "metrics_summary.json"), "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)

    print("[3/3] 완료\n")
    print(_fmt(s))
    if "turnover" in s:
        print("  ─────────────────────────────  턴오버(단방향)")
        for r in s["turnover"]:
            print(f"  {r['rebalance_date']}   {r['one_way_turnover']*100:6.1f}%")
    print(f"\n  → 대시보드: {fig_path}")
    print(f"  → 지표 JSON: {os.path.join(args.fig_dir, 'metrics_summary.json')}")


if __name__ == "__main__":
    main()
