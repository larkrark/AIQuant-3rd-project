# -*- coding: utf-8 -*-
"""일별 시장상태 부여 — 데이터사전 v0.2 4장.
입력: 시장 달력(개장일), 종목별 일별 가격·거래량, 종일정지 목록, 상장일.
출력: security_id × market_date 별 daily_market_state (6종) + 거래대금 필드."""
import pandas as pd
import config as C


def assign_daily_states(prices: pd.DataFrame, calendar: pd.DataFrame,
                        listings: pd.DataFrame, halts: pd.DataFrame | None = None) -> pd.DataFrame:
    """prices: [security_id, market, market_date, raw_close, volume, exchange_trading_value(선택)]
    calendar: [market, market_date, is_market_open]
    listings: [security_id, listing_date, delisting_date(선택)]
    halts:    [security_id, market_date, full_day_halt]  (공식 확인분만)
    반환: 개장일 전체 그리드에 상태·거래대금·trading_value_source·오차비율 부여
    """
    cal = calendar[calendar["is_market_open"] == 1][["market", "market_date"]]
    secs = listings[["security_id"]].merge(prices[["security_id", "market"]].drop_duplicates(), on="security_id")
    grid = secs.merge(cal, on="market", how="left")
    df = grid.merge(prices, on=["security_id", "market", "market_date"], how="left")
    df = df.merge(listings, on="security_id", how="left")
    if halts is not None and len(halts):
        df = df.merge(halts[["security_id", "market_date", "full_day_halt"]],
                      on=["security_id", "market_date"], how="left")
    else:
        df["full_day_halt"] = 0
    df["full_day_halt"] = df["full_day_halt"].fillna(0).astype(int)

    d = df["market_date"]
    state = pd.Series(C.STATE_DATA_MISSING, index=df.index)          # 개장일인데 자료 없음 → 결측
    state[d < df["listing_date"]] = C.STATE_NOT_LISTED
    if "delisting_date" in df:
        state[(df["delisting_date"].notna()) & (d > df["delisting_date"])] = C.STATE_NOT_LISTED
    has_row = df["raw_close"].notna() & df["volume"].notna()
    # 우선 적용 규칙(#15 확정): 종일정지 공식 확인 시 거래량 0이어도 TRADING_HALT 우선
    m_listed = state == C.STATE_DATA_MISSING
    state[m_listed & (df["full_day_halt"] == 1)] = C.STATE_TRADING_HALT
    m_open = m_listed & (df["full_day_halt"] == 0) & has_row
    state[m_open & (df["volume"] > 0)] = C.STATE_TRADED
    state[m_open & (df["volume"] == 0)] = C.STATE_ZERO_VOLUME
    df["daily_market_state"] = state
    # (MARKET_CLOSED는 개장일 그리드 밖 — 관측창 제외라 행 자체가 생성되지 않음. 필요 시 별도 조회)

    # 거래대금 — 제59조 복원: 한국 KRX 제공값 우선, 없으면 재구성. 미국 상시 재구성
    recon = df["raw_close"] * df["volume"]
    provided = df["exchange_trading_value"] if "exchange_trading_value" in df else pd.Series(pd.NA, index=df.index)
    use_provided = provided.notna() & (df["market"] == "KR")
    df["daily_trading_value"] = recon.where(~use_provided, provided)
    df["trading_value_source"] = pd.Series("RECONSTRUCTED", index=df.index).where(~use_provided, "EXCHANGE_PROVIDED")
    # 검산 오차비율 |근사-KRX|/KRX — KRX 제공값>0인 한국 행만, 그 외 NA (임계 플래그는 분포 확인 후)
    ok = use_provided & (provided > 0)
    df["trading_value_discrepancy_ratio"] = ((recon - provided).abs() / provided).where(ok)
    df.loc[df["daily_market_state"] != C.STATE_TRADED, "daily_trading_value"] = \
        df.loc[df["daily_market_state"] != C.STATE_TRADED, "daily_market_state"].map(
            {C.STATE_ZERO_VOLUME: 0.0}).astype(float)   # ZERO_VOLUME=0, 그 외 상태는 NA
    return df
