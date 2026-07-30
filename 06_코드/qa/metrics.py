# -*- coding: utf-8 -*-
"""성과·위험 지표 계산 — 규칙과 무관(rule-agnostic).
입력은 engine 산출물 `index_vs_benchmark.csv`(날짜·지수값·BM값) 하나뿐이므로,
리밸 규칙이 잠정이든 확정이든 이 코드는 바뀌지 않는다.

핵심 원칙: 산출(engine)과 평가(여기)를 분리한다. 성과를 보고 규칙을 고치지 않기 위함.
"""
import os
import pandas as pd
import numpy as np

TRADING_DAYS = 252   # 연율화 기준 (거래일)


def load_index_series(output_dir: str) -> pd.DataFrame:
    """engine 산출 index_vs_benchmark.csv 로드 → [market_date(datetime), index_level, benchmark_level]"""
    df = pd.read_csv(os.path.join(output_dir, "index_vs_benchmark.csv"))
    df["market_date"] = pd.to_datetime(df["market_date"])
    return df.sort_values("market_date").reset_index(drop=True)


def drawdown(levels: pd.Series) -> pd.Series:
    """수중곡선(underwater): 각 시점의 직전 최고점 대비 하락률 (0 이하)."""
    return levels / levels.cummax() - 1.0


def _leg_stats(levels: pd.Series) -> dict:
    """단일 시계열의 성과·위험 지표. levels: 지수 레벨 시퀀스(기준값 시작)."""
    ret = levels.pct_change().dropna()
    n = len(ret)
    if n == 0 or levels.iloc[0] <= 0:
        return {k: float("nan") for k in
                ("total_return", "cagr", "ann_vol", "sharpe", "mdd")}
    years = n / TRADING_DAYS
    total_return = levels.iloc[-1] / levels.iloc[0] - 1.0
    cagr = (levels.iloc[-1] / levels.iloc[0]) ** (1 / years) - 1.0 if years > 0 else float("nan")
    ann_vol = ret.std(ddof=1) * np.sqrt(TRADING_DAYS)
    sharpe = (ret.mean() * TRADING_DAYS) / ann_vol if ann_vol > 0 else float("nan")   # rf=0 가정
    mdd = drawdown(levels).min()
    return {"total_return": total_return, "cagr": cagr, "ann_vol": ann_vol,
            "sharpe": sharpe, "mdd": mdd}


def performance_summary(df: pd.DataFrame) -> dict:
    """지수·BM 각각의 지표 + 상대(초과성과) 지표를 한 번에 계산.
    반환: {'index': {...}, 'benchmark': {...}, 'relative': {...}, 'meta': {...}}"""
    idx, bm = df["index_level"], df["benchmark_level"]
    idx_ret, bm_ret = idx.pct_change().dropna(), bm.pct_change().dropna()
    active = (idx_ret - bm_ret).dropna()   # 일별 초과수익 (지수 - BM)

    te = active.std(ddof=1) * np.sqrt(TRADING_DAYS)                      # 추적오차
    ir = (active.mean() * TRADING_DAYS) / te if te > 0 else float("nan")  # 정보비율
    hit = float((active > 0).mean()) if len(active) else float("nan")     # BM 상회일 비율

    return {
        "index": _leg_stats(idx),
        "benchmark": _leg_stats(bm),
        "relative": {
            "excess_total_return": (idx.iloc[-1] / idx.iloc[0]) - (bm.iloc[-1] / bm.iloc[0]),
            "tracking_error": te,
            "information_ratio": ir,
            "hit_ratio": hit,
            "final_alpha": idx.iloc[-1] - bm.iloc[-1],   # 레벨 차이 (기준값 동일 리베이스)
        },
        "meta": {
            "start": df["market_date"].iloc[0].date().isoformat(),
            "end": df["market_date"].iloc[-1].date().isoformat(),
            "n_days": len(df),
        },
    }


def rolling_metrics(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """이동창(기본 20거래일) 롤링 위험지표.
    반환: [market_date, roll_vol_index, roll_vol_bm, roll_sharpe_index] (창 충족 후부터)"""
    idx_ret = df["index_level"].pct_change()
    bm_ret = df["benchmark_level"].pct_change()
    ann = np.sqrt(TRADING_DAYS)
    out = pd.DataFrame({
        "market_date": df["market_date"],
        "roll_vol_index": idx_ret.rolling(window).std(ddof=1) * ann,
        "roll_vol_bm": bm_ret.rolling(window).std(ddof=1) * ann,
        "roll_sharpe_index": (idx_ret.rolling(window).mean() * TRADING_DAYS) /
                             (idx_ret.rolling(window).std(ddof=1) * ann),
    })
    return out.dropna().reset_index(drop=True)


def cell_composition(output_dir: str) -> pd.DataFrame:
    """최신 리밸의 셀별 목표비중 합 (6셀 배정·재배분 결과 시각화용).
    반환: [cell_id, market, primary_theme, weight] — weight 내림차순"""
    import glob
    paths = sorted(glob.glob(os.path.join(output_dir, "weights_*.csv")))
    if not paths:
        return pd.DataFrame(columns=["cell_id", "market", "primary_theme", "weight"])
    w = pd.read_csv(paths[-1], dtype={"security_id": str})
    g = (w.groupby(["cell_id", "market", "primary_theme"])["final_target_weight"]
         .sum().reset_index().rename(columns={"final_target_weight": "weight"}))
    return g.sort_values("weight", ascending=False).reset_index(drop=True)


def compute_turnover(output_dir: str) -> pd.DataFrame:
    """리밸 간 단방향 턴오버 = 0.5 · Σ|Δw|.
    weights_*.csv 들을 날짜순으로 읽어 연속 리밸 사이의 비중 변화를 집계.
    첫 리밸은 현금→편입이므로 1.0(전량 신규)로 본다.
    반환: [rebalance_date, one_way_turnover]"""
    import glob
    paths = sorted(glob.glob(os.path.join(output_dir, "weights_*.csv")))
    rows, prev = [], None
    for p in paths:
        date = os.path.basename(p)[len("weights_"):-len(".csv")]
        w = pd.read_csv(p, dtype={"security_id": str}).set_index("security_id")["final_target_weight"]
        if prev is None:
            to = float(w.sum())                       # 현금 → 편입 (전량 신규)
        else:
            aligned = w.reindex(prev.index.union(w.index)).fillna(0.0)
            prev_a = prev.reindex(aligned.index).fillna(0.0)
            to = 0.5 * float((aligned - prev_a).abs().sum())
        rows.append({"rebalance_date": date, "one_way_turnover": to})
        prev = w
    return pd.DataFrame(rows)
