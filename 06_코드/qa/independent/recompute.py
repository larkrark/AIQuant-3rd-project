# -*- coding: utf-8 -*-
"""독립 재산출 4~6단계 — 상태코드 → ADTV90·시즈닝 → 구성종목·가중.

engine 의 market_state·indicators·composition 을 **읽지 않고** 룰북 §8.1·§9·§10 과
데이터사전·결정로그만 근거로 별도 구현했다(qa/README.md 독립성 규칙).
7단계(지수 산출)는 PR 산식이 미결이라 구현하지 않는다 — 사유는 MIGYEOL.md.

사용:
  python recompute.py                            # 기본 입력·산출
  python recompute.py --input <입력폴더> --out <산출폴더>
  python recompute.py --observation-end selection  # 관측 종료일을 선정일로 (팀 산출 대조용)
"""
import os
import sys
import json
import argparse
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths as P
import rules as R

P.force_utf8_stdout()
OUT_DEFAULT = os.path.join(P.HERE, "independent", "out")


# ─────────────────────────────────────────────────────────────
# 입력
# ─────────────────────────────────────────────────────────────
def load_inputs(input_dir: str) -> dict:
    """엔진 입력계약 파일을 읽는다(데이터사전 필드명). 가격·달력·상장·정지·유니버스만 사용한다.
    fx·bm 은 7단계(지수·BM) 전용이라 여기서는 읽지 않는다."""
    rd = lambda n: pd.read_csv(os.path.join(input_dir, n), dtype={"security_id": str})
    basket = rd("seed_basket.csv")
    prices = rd("prices.csv")
    calendar = pd.read_csv(os.path.join(input_dir, "calendar.csv"))
    listings = rd("listings.csv")
    hp = os.path.join(input_dir, "halts.csv")
    halts = rd("halts.csv") if os.path.exists(hp) else pd.DataFrame(
        columns=["security_id", "market_date", "full_day_halt"])
    return {"basket": basket, "prices": prices, "calendar": calendar,
            "listings": listings, "halts": halts}


def _truthy(v) -> bool:
    """halts.full_day_halt 은 인계본에 따라 True/'True'/1 이 섞인다(인수인계 문서 지적사항)."""
    if pd.isna(v):
        return False
    if isinstance(v, str):
        return v.strip().lower() in ("true", "y", "yes", "1")
    return bool(v)


def market_axes(calendar: pd.DataFrame) -> dict:
    """시장별 개장일 축과 공통 거래일 축 (로그 D-13 ⑧ 축 구분)."""
    ax = {m: sorted(calendar[(calendar["market"] == m) & (calendar["is_market_open"] == 1)]
                    ["market_date"].astype(str)) for m in R.REGIONS}
    ax["COMMON"] = sorted(set(ax["KR"]) & set(ax["US"]))
    return ax


def cutoff_date(selection_date: str, axes: dict) -> str:
    """자료마감일 = 선정일 이전 제5거래일, 공통 개장일 축 역산 (로그 D-13 ⑧).

    PIT(룰북 R4·§5.2): 이 날짜까지 이용 가능했던 자료만으로 판정한다.
    """
    prior = [d for d in axes[R.CUTOFF_AXIS] if d < selection_date]
    if len(prior) < R.CUTOFF_LAG_TRADING_DAYS:
        raise ValueError(f"{selection_date}: 공통 거래일이 {R.CUTOFF_LAG_TRADING_DAYS}일 미만")
    return prior[-R.CUTOFF_LAG_TRADING_DAYS]


# ─────────────────────────────────────────────────────────────
# 4단계 — 일별 상태코드 6종 (룰북 §8.1)
# ─────────────────────────────────────────────────────────────
def daily_states(inp: dict, axes: dict) -> pd.DataFrame:
    """종목 × 시장개장일 격자에 상태코드와 일별 거래대금을 부여한다.

    상태 판정 (룰북 §8.1 · D-07 · D-12 ⑤):
      MARKET_CLOSED  시장 휴장일
      NOT_LISTED     상장일 이전 · 상장폐지일 이후
      TRADING_HALT   정규장 전체 매매정지 공식 확인일 (거래량 0이어도 ZERO_VOLUME보다 우선)
      DATA_MISSING   개장·상장 중인데 가격·거래량 자료가 없음 → 0으로 채우지 않는다(R6)
      ZERO_VOLUME    실제 무거래 (거래량 0)
      TRADED         그 외
    """
    basket, prices, listings = inp["basket"], inp["prices"], inp["listings"]
    lst = listings.set_index("security_id")
    halt_keys = {(r.security_id, str(r.market_date))
                 for r in inp["halts"].itertuples() if _truthy(r.full_day_halt)}
    px = prices.copy()
    px["market_date"] = px["market_date"].astype(str)
    px = px.set_index(["security_id", "market_date"])

    rows = []
    for b in basket.itertuples():
        sid, mkt = b.security_id, b.market
        listing = str(lst.at[sid, "listing_date"]) if sid in lst.index else ""
        delist = lst.at[sid, "delisting_date"] if sid in lst.index else None
        delist = str(delist) if pd.notna(delist) else None

        for d in axes[mkt]:                      # 시장별 개장일만 순회 → 휴장일은 아래에서 별도
            if listing and d < listing:
                state = R.S_NOT_LISTED
            elif delist and d > delist:
                state = R.S_NOT_LISTED
            elif (sid, d) in halt_keys:
                state = R.S_TRADING_HALT
            elif (sid, d) not in px.index:
                state = R.S_DATA_MISSING
            else:
                rec = px.loc[(sid, d)]
                vol, close = rec["raw_close"], rec["volume"]
                if pd.isna(vol) or pd.isna(close):
                    state = R.S_DATA_MISSING
                elif float(rec["volume"]) == 0:
                    state = R.S_ZERO_VOLUME
                else:
                    state = R.S_TRADED

            val, src, krx, approx = _trading_value(px, sid, mkt, d, state)
            rows.append({"security_id": sid, "market": mkt, "market_date": d,
                         "daily_market_state": state, "daily_trading_value": val,
                         "trading_value_source": src,
                         "exchange_trading_value": krx, "reconstructed_trading_value": approx})

    df = pd.DataFrame(rows)
    # 거래대금 오차비율 — KRX 공식값 > 0 인 날만 (로그 D-13 ②). QA 진단 전용, 판정 미사용.
    ok = df["exchange_trading_value"].notna() & (df["exchange_trading_value"] > 0) \
        & df["reconstructed_trading_value"].notna()
    df["trading_value_discrepancy_ratio"] = np.where(
        ok, (df["reconstructed_trading_value"] - df["exchange_trading_value"]).abs()
        / df["exchange_trading_value"].where(ok), np.nan)
    return df


def _trading_value(px, sid, mkt, d, state):
    """일별 거래대금과 산출 경로 (룰북 §8.1 제59조 복원 · 로그 D-13 ②).

    ZERO_VOLUME·TRADING_HALT 는 0 반영, DATA_MISSING 은 NA 유지(룰북 R6 — 둘을 섞지 않는다).
    한국 = KRX 제공값 우선(없을 때만 재구성), 미국 = 상시 재구성.
    """
    krx = approx = np.nan
    if (sid, d) in px.index:
        rec = px.loc[(sid, d)]
        if "exchange_trading_value" in rec.index and pd.notna(rec["exchange_trading_value"]):
            krx = float(rec["exchange_trading_value"])
        if pd.notna(rec["raw_close"]) and pd.notna(rec["volume"]):
            approx = float(rec["raw_close"]) * float(rec["volume"])

    if state in (R.S_ZERO_VOLUME, R.S_TRADING_HALT):
        src = R.TRADING_VALUE_EXCHANGE if (mkt == "KR" and not np.isnan(krx)) \
            else R.TRADING_VALUE_RECONSTRUCTED
        return 0.0, src, krx, approx
    if state != R.S_TRADED:
        return np.nan, "", krx, approx       # NOT_LISTED·DATA_MISSING·MARKET_CLOSED
    if mkt == "KR" and not np.isnan(krx):
        return krx, R.TRADING_VALUE_EXCHANGE, krx, approx
    return approx, R.TRADING_VALUE_RECONSTRUCTED, krx, approx


# ─────────────────────────────────────────────────────────────
# 5단계 — ADTV90 · 시즈닝 · 하한 (룰북 §8.1)
# ─────────────────────────────────────────────────────────────
def indicators(states: pd.DataFrame, observation_end: str) -> pd.DataFrame:
    """관측 종료일 기준 ADTV90·시즈닝 원장. 시장별 개장일 축으로 최근 90일(D-13 ⑧)."""
    rows = []
    for (sid, mkt), g in states.groupby(["security_id", "market"], sort=False):
        g = g[g["market_date"] <= observation_end].sort_values("market_date")
        listed = g[g["daily_market_state"] != R.S_NOT_LISTED]      # "상장 중인" 개장일

        # 시즈닝: 유효관측일 = 개장 + 상장 중 + 정지 아님. ZERO_VOLUME 포함, DATA_MISSING 제외.
        eff = listed[~listed["daily_market_state"].isin([R.S_TRADING_HALT, R.S_DATA_MISSING])]
        seasoning_days = len(eff)
        seasoned = seasoning_days >= R.SEASONING_MIN_OBS_DAYS

        w = listed.tail(R.ADTV90_OPEN_DAYS_TARGET)                 # 상장 중인 최근 90 개장일
        n_missing = int((w["daily_market_state"] == R.S_DATA_MISSING).sum())
        vals = w.loc[w["daily_market_state"] != R.S_DATA_MISSING, "daily_trading_value"]

        # 공식 산식 = 정지일 0 반영, 분모 = 90 − NA일수 (로그 D-13 ① · 룰북 R6)
        adtv_zero = float(vals.mean()) if len(vals) else np.nan
        # 진단 병기 = 정지일을 분모에서도 제외한 값 (로그 D-13 ① "분모 제외값 진단 병기")
        v_ex = w.loc[~w["daily_market_state"].isin([R.S_DATA_MISSING, R.S_TRADING_HALT]),
                     "daily_trading_value"]
        adtv_ex = float(v_ex.mean()) if len(v_ex) else np.nan

        incomplete = (not seasoned) or len(w) < R.ADTV90_OPEN_DAYS_TARGET
        rows.append({
            "security_id": sid, "market": mkt, "observation_end_date": observation_end,
            "open_days_target": R.ADTV90_OPEN_DAYS_TARGET, "observed_open_days": len(w),
            "halt_days_90": int((w["daily_market_state"] == R.S_TRADING_HALT).sum()),
            "zero_volume_days_90": int((w["daily_market_state"] == R.S_ZERO_VOLUME).sum()),
            "missing_days_90": n_missing,
            "traded_days_90": int((w["daily_market_state"] == R.S_TRADED).sum()),
            "seasoning_days": seasoning_days,
            "seasoning_status": "SEASONED" if seasoned else "SEASONING_INCOMPLETE",
            "adtv90_zero": adtv_zero, "adtv90_exclude_halt": adtv_ex,
            "official_adtv90": np.nan if incomplete else adtv_zero,
            "official_adtv90_method": R.ADTV90_OFFICIAL_METHOD,
            "adtv90_status": "SEASONING_INCOMPLETE" if incomplete else "CALCULATED",
            "rule_version": R.RULE_VERSION,
        })
    return pd.DataFrame(rows).sort_values(["market", "security_id"]).reset_index(drop=True)


def provisional_thresholds(ledger: pd.DataFrame) -> dict:
    """시장별 ADTV90 분포 P10 잠정 하한 (룰북 §8.1 · 로그 D-13 ①).
    모집단 = 시장별 시즈닝 통과 종목. 절대금액 승인은 분포표 후 별도 의결."""
    out = {}
    for mkt, g in ledger.groupby("market"):
        v = g["official_adtv90"].dropna()
        out[mkt] = float(np.percentile(v, R.LIQUIDITY_THRESHOLD_PERCENTILE,
                                       method=R.PERCENTILE_METHOD)) if len(v) else np.nan
    return out


def distribution_table(ledger: pd.DataFrame) -> pd.DataFrame:
    """시장별 P5·P10·P25·P50·P75 분포표 (룰북 §8.1 하한 설정 절차 — 추주원 담당분 대조용)."""
    rows = []
    for mkt, g in ledger.groupby("market"):
        v = g["official_adtv90"].dropna()
        r = {"market": mkt, "n": len(v)}
        for p in (5, 10, 25, 50, 75):
            r[f"P{p}"] = float(np.percentile(v, p, method=R.PERCENTILE_METHOD)) if len(v) else np.nan
        rows.append(r)
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────
# 6단계 — 구성종목 · 6셀 가중 (룰북 §9·§10)
# ─────────────────────────────────────────────────────────────
def select_constituents(basket, ledger, thresholds, states, selection_date) -> pd.DataFrame:
    """게이트: 시즈닝 통과 · ADTV90 ≥ 시장별 하한 · 선정일 현재 정지 아님.
    구성 방식 = 대안 A 전부 편입·상한 없음 (로그 D-13 ①). 제외사유는 주+추가 병기(룰북 §9)."""
    halted = set(states[(states["market_date"] == selection_date)
                        & (states["daily_market_state"] == R.S_TRADING_HALT)]["security_id"])
    m = basket.merge(ledger, on=["security_id", "market"], how="left")
    rows = []
    for r in m.itertuples():
        reasons = []
        if r.seasoning_status != "SEASONED":
            reasons.append("SEASONING_INCOMPLETE")
        th = thresholds.get(r.market, np.nan)
        if pd.isna(r.official_adtv90):
            reasons.append("ADTV90_NOT_CALCULABLE")
        elif not pd.isna(th) and r.official_adtv90 < th:
            reasons.append("BELOW_LIQUIDITY_THRESHOLD")
        if r.security_id in halted:
            reasons.append("HALTED_AT_SELECTION")   # 룰북 §9 신규 후보 = 관찰(다음 회차 재판정)
        rows.append({
            "security_id": r.security_id, "market": r.market, "primary_theme": r.primary_theme,
            "gate_status": r.gate_status, "observation_end_date": r.observation_end_date,
            "seasoning_days": r.seasoning_days, "seasoning_status": r.seasoning_status,
            "official_adtv90": r.official_adtv90, "liquidity_threshold": th,
            "selected_flag": int(not reasons),
            "selection_status": "SELECTED" if not reasons else "EXCLUDED",
            "exclusion_reason_primary": reasons[0] if reasons else "",
            "exclusion_reasons": "|".join(reasons),
            "cell_id": f"{r.market}_{r.primary_theme}",
            "composition_method": R.COMPOSITION_METHOD, "cap_scenario": R.CAP_SCENARIO,
            "selection_rule_version": R.RULE_VERSION,
        })
    return pd.DataFrame(rows)


def assign_weights(selected: pd.DataFrame):
    """6셀 각 1/6 → 셀 내 동일가중. 빈 셀은 같은 테마의 타지역 셀로 재배분(룰북 §10, D-10 ②③).

    반환: (weights, cell_notes). 총합 검산은 호출부에서 수행한다.
    """
    sel = selected[selected["selected_flag"] == 1]
    cells = {f"{m}_{t}": R.CELL_TARGET_WEIGHT for t in R.THEMES for m in R.REGIONS}
    notes = []

    for t in R.THEMES:                       # 테마 1:1:1 우선 — 같은 테마 안에서 먼저 흡수
        ids = [f"{m}_{t}" for m in R.REGIONS]
        empty = [c for c in ids if not len(sel[sel["cell_id"] == c])]
        alive = [c for c in ids if c not in empty]
        for c in empty:
            moved = cells[c]
            cells[c] = 0.0
            if alive:                        # 같은 테마의 타지역 셀로 균등 재배분
                for a in alive:
                    cells[a] += moved / len(alive)
                reason, res = "NO_ELIGIBLE_SECURITY", f"REDISTRIBUTED_TO:{'|'.join(alive)}"
            else:                            # 테마 전체가 비면 지역비중 이탈 — 사유코드 기록
                reason, res = "NO_ELIGIBLE_SECURITY", "THEME_FULLY_EMPTY_UNRESOLVED"
            notes.append({"cell_id": c, "cell_shortage_flag": 1,
                          "cell_shortage_reason": reason, "resolution": res})
        for a in alive:
            notes.append({"cell_id": a, "cell_shortage_flag": 0,
                          "cell_shortage_reason": "", "resolution": ""})

    rows = []
    for c, w in cells.items():
        members = sel[sel["cell_id"] == c]
        if not len(members) or w <= 0:
            continue
        for r in members.itertuples():       # 셀 내 동일가중 (TEMPORARY — 안건 H)
            rows.append({"security_id": r.security_id, "market": r.market,
                         "primary_theme": r.primary_theme, "cell_id": c,
                         "cell_target_weight": w, "final_target_weight": w / len(members),
                         "weighting_status": R.WEIGHTING_STATUS,
                         "weighting_rule_version": R.RULE_VERSION})
    order = {c: i for i, c in enumerate(cells)}
    weights = pd.DataFrame(rows).sort_values(
        ["cell_id", "security_id"], key=lambda s: s.map(order) if s.name == "cell_id" else s)
    return weights.reset_index(drop=True), pd.DataFrame(notes)


# ─────────────────────────────────────────────────────────────
# 실행
# ─────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=P.PILOT_INPUT)
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--observation-end", choices=["cutoff", "selection"], default="cutoff",
                    help="ADTV90 관측 종료일. cutoff=자료마감일(PIT 정합, 기본) / selection=선정일")
    args = ap.parse_args()

    P.require(os.path.join(args.input, "prices.csv"), "엔진 입력(prices.csv)")
    os.makedirs(args.out, exist_ok=True)
    inp = load_inputs(args.input)
    axes = market_axes(inp["calendar"])
    print(f"[독립 재산출] 입력 {os.path.relpath(args.input, P.ROOT)} · "
          f"유니버스 {len(inp['basket'])}종목 · 공통 거래일 {len(axes['COMMON'])}일")

    states = daily_states(inp, axes)
    states.to_csv(os.path.join(args.out, "daily_market_state.csv"), index=False)
    print("  4단계 상태코드 —", states["daily_market_state"].value_counts().to_dict())

    ledgers, summary = [], []
    for sel in R.SELECTION_DATES:
        obs = cutoff_date(sel, axes) if args.observation_end == "cutoff" else sel
        led = indicators(states, obs)
        led["review_cycle_id"] = f"RC-{sel}"
        ledgers.append(led)

        th = provisional_thresholds(led)
        dist = distribution_table(led)
        dist.to_csv(os.path.join(args.out, f"adtv90_distribution_{sel}.csv"), index=False)
        with open(os.path.join(args.out, f"thresholds_{sel}.json"), "w", encoding="utf-8") as f:
            json.dump({"provisional_P10": th, "observation_end_date": obs,
                       "percentile_method": R.PERCENTILE_METHOD,
                       "rule_version": R.RULE_VERSION}, f, ensure_ascii=False, indent=2)

        con = select_constituents(inp["basket"], led, th, states, sel)
        con.to_csv(os.path.join(args.out, f"constituents_{sel}.csv"), index=False)
        w, notes = assign_weights(con)
        notes["review_cycle_id"] = f"RC-{sel}"
        w.to_csv(os.path.join(args.out, f"weights_{sel}.csv"), index=False)

        total = float(w["final_target_weight"].sum()) if len(w) else 0.0
        assert abs(total - 1.0) < 1e-9, f"{sel}: 가중 총합 {total} ≠ 1.0 (룰북 §10 총합 검산)"
        summary.append({"selection_date": sel, "observation_end_date": obs,
                        "selected": int(con["selected_flag"].sum()), "candidates": len(con),
                        "weight_sum": total, **{f"P10_{k}": v for k, v in th.items()}})
        print(f"  5·6단계 {sel} (관측종료 {obs}) — 편입 {int(con['selected_flag'].sum())}/{len(con)} · "
              f"가중합 {total:.6f}")

    pd.concat(ledgers).to_csv(os.path.join(args.out, "adtv90_ledger.csv"), index=False)
    pd.DataFrame(summary).to_csv(os.path.join(args.out, "run_summary.csv"), index=False)
    print(f"→ 산출: {os.path.relpath(args.out, P.ROOT)}")
    print("  7단계(지수 산출)는 PR 산식 미결로 미구현 — independent/MIGYEOL.md")


if __name__ == "__main__":
    main()
