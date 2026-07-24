# -*- coding: utf-8 -*-
"""PR 지수·공식 합성 BM 산출 — 원화·무헤지·기준값 1,000 (D-08·D-09·D-10).
방법: 효력발생일에 목표가중으로 가상 보유수량 설정 → 리밸 간 가격변동으로 가치 연쇄 → 다음 효력발생일 재설정."""
import pandas as pd
import config as C


def _krw_close(prices: pd.DataFrame, fx: pd.DataFrame) -> pd.DataFrame:
    """미국 종목·BM 다리를 ECOS 환율로 원화 환산 (fx: [market_date, fx_rate]).
    지수·수익률 산출가는 adj_close(수정주가) 사용 — 액면분할 전후 연속성 확보(팀 결정).
    adj_close 미제공 입력은 raw_close 로 하위호환 폴백. (거래대금 재구성은 market_state 가 raw_close 사용)"""
    df = prices.merge(fx, on="market_date", how="left")
    price = df["adj_close"] if "adj_close" in df.columns else df["raw_close"]
    df["close_krw"] = price.where(df["market"] == "KR", price * df["fx_rate"])
    return df


def _chain(holding_frames: list, base_value: float) -> pd.DataFrame:
    """구간별 (날짜, 포트폴리오가치) 시퀀스를 기준값으로 리베이스해 연결"""
    levels, factor = [], base_value
    for seg in holding_frames:
        seg = seg.sort_values("market_date")
        v0 = seg["pv"].iloc[0]
        seg = seg.assign(index_level=factor * seg["pv"] / v0)
        factor = seg["index_level"].iloc[-1]
        levels.append(seg[["market_date", "index_level"]])
    out = pd.concat(levels).drop_duplicates("market_date", keep="last")
    return out.reset_index(drop=True)


def compute_portfolio_index(weight_sets: dict, prices: pd.DataFrame, fx: pd.DataFrame,
                            common_dates: list) -> pd.DataFrame:
    """weight_sets: {effective_date: 종목별 final_target_weight DF}
    prices: 전 구성종목 일별 close (양시장). common_dates: 산출일 목록(오름차순).
    반환: [market_date, index_level]"""
    px = _krw_close(prices, fx)
    px = px[px["market_date"].isin(common_dates)]
    wide = px.pivot_table(index="market_date", columns="security_id", values="close_krw").sort_index()
    wide = wide.ffill()   # 개별 휴장·정지일은 직전가 평가 (D-11 #24)
    eff_dates = sorted(weight_sets.keys())
    segs = []
    for i, ed in enumerate(eff_dates):
        w = weight_sets[ed].set_index("security_id")["final_target_weight"]
        start = wide.index[wide.index >= ed]
        if len(start) == 0:
            continue
        end = eff_dates[i + 1] if i + 1 < len(eff_dates) else None
        seg_idx = wide.index[(wide.index >= start[0]) & ((wide.index <= end) if end else True)]
        p = wide.loc[seg_idx, w.index]
        shares = (w / p.iloc[0]).values          # 가치 1 기준 가상 수량
        pv = (p * shares).sum(axis=1)
        segs.append(pd.DataFrame({"market_date": seg_idx, "pv": pv.values}))
    return _chain(segs, C.INDEX_BASE_VALUE)


def compute_benchmark(bm_kr: pd.DataFrame, bm_us: pd.DataFrame, fx: pd.DataFrame,
                      eff_dates: list, common_dates: list,
                      w_kr: float = C.BM_WEIGHT_KR, w_us: float = C.BM_WEIGHT_US) -> pd.DataFrame:
    """공식 합성 BM: KOSPI200 PR + Russell3000 PR(원화 환산), 지역비중 연동, 동일 리베이스.
    bm_*: [market_date, close]. 예외 목표비중 발생 시 w_kr/w_us에 규칙 산출값 전달(D-10 ④)."""
    kr = bm_kr.rename(columns={"close": "kr"})
    us = bm_us.merge(fx, on="market_date", how="left")
    us["us"] = us["close"] * us["fx_rate"]
    both = kr.merge(us[["market_date", "us"]], on="market_date", how="inner")
    both = both[both["market_date"].isin(common_dates)].sort_values("market_date")
    segs = []
    for i, ed in enumerate(eff_dates):
        end = eff_dates[i + 1] if i + 1 < len(eff_dates) else None
        seg = both[(both["market_date"] >= ed) & ((both["market_date"] <= end) if end else True)]
        if seg.empty:
            continue
        pv = w_kr * seg["kr"] / seg["kr"].iloc[0] + w_us * seg["us"] / seg["us"].iloc[0]
        segs.append(pd.DataFrame({"market_date": seg["market_date"].values, "pv": pv.values}))
    out = _chain(segs, C.INDEX_BASE_VALUE)
    return out.rename(columns={"index_level": "benchmark_level"})
