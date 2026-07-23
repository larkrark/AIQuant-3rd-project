# -*- coding: utf-8 -*-
"""시즈닝·ADTV90 — 데이터사전 v0.2 5장. 관측창=관측 종료일 직전 90개 시장 개장일.
0 반영(공식 잠정)과 분모 제외(진단·#15 비교용)를 병기 산출."""
import pandas as pd
import config as C

VALID_OBS = {C.STATE_TRADED, C.STATE_ZERO_VOLUME}   # 유효관측일 (D-06: 무거래 포함, 정지·휴장·결측 제외)


def compute_indicators(states: pd.DataFrame, observation_end_date: str) -> pd.DataFrame:
    """states: market_state.assign_daily_states 출력. 반환: 종목별 ADTV90 원장 1행."""
    out = []
    for sec, g in states.groupby("security_id"):
        g = g[g["market_date"] <= observation_end_date].sort_values("market_date")
        listed = g[g["daily_market_state"] != C.STATE_NOT_LISTED]
        seasoning_days = int(listed["daily_market_state"].isin(VALID_OBS).sum())
        win = listed.tail(C.ADTV90_OPEN_DAYS_TARGET)                     # 최근 90개 개장일
        n = len(win)
        s = win["daily_market_state"]
        halt = int((s == C.STATE_TRADING_HALT).sum())
        zero = int((s == C.STATE_ZERO_VOLUME).sum())
        miss = int((s == C.STATE_DATA_MISSING).sum())
        traded_sum = win.loc[s == C.STATE_TRADED, "daily_trading_value"].sum()

        row = {
            "security_id": sec, "market": g["market"].iloc[0],
            "observation_end_date": observation_end_date,
            "open_days_target": C.ADTV90_OPEN_DAYS_TARGET, "observed_open_days": n,
            "halt_days_90": halt, "zero_volume_days_90": zero, "missing_days_90": miss,
            "traded_days_90": n - halt - zero - miss,
            "seasoning_days": seasoning_days,
            "seasoning_status": "SEASONED" if seasoning_days >= C.SEASONING_MIN_OBS_DAYS else "SEASONING_INCOMPLETE",
            "adtv90_zero": pd.NA, "adtv90_exclude_halt": pd.NA,
            "official_adtv90": pd.NA, "official_adtv90_method": C.ADTV90_OFFICIAL_METHOD,
            "rule_version": C.RULE_VERSION,
        }
        if n < C.ADTV90_OPEN_DAYS_TARGET:
            row["adtv90_status"] = "SEASONING_INCOMPLETE"
        elif miss > 0 and (n - miss) == 0:
            row["adtv90_status"] = "CALCULATION_HOLD"
        else:
            # 0 반영: 정지·무거래=0 포함, 분모 = 90 − 결측일수 (룰북 8.1: NA는 0 대체 금지)
            row["adtv90_zero"] = float(traded_sum) / (n - miss) if (n - miss) > 0 else pd.NA
            # 분모 제외(진단): TRADING_HALT만 제외. missing_days_90=0일 때만 산출 (#15 확정 조건)
            if miss == 0 and (n - halt) > 0:
                row["adtv90_exclude_halt"] = float(traded_sum) / (n - halt)
            row["adtv90_status"] = "CALCULATED"
            row["official_adtv90"] = row["adtv90_zero"] if C.ADTV90_OFFICIAL_METHOD == "ZERO" else row["adtv90_exclude_halt"]
        out.append(row)
    return pd.DataFrame(out)


def provisional_thresholds(ledger: pd.DataFrame) -> dict:
    """잠정 하한 = 시장별 official_adtv90 분포의 P10 (#16 절차 1단계 — 절대금액 승인은 정식 이월)"""
    th = {}
    calc = ledger[ledger["adtv90_status"] == "CALCULATED"]
    for mkt, g in calc.groupby("market"):
        th[mkt] = float(g["official_adtv90"].astype(float).quantile(C.LIQUIDITY_THRESHOLD_PERCENTILE / 100.0))
    return th
