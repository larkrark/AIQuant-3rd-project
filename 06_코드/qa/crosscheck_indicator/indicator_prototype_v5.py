# -*- coding: utf-8 -*-
"""
file_status: PILOT_IMPLEMENTATION
method_status: APPROVAL_PENDING
merge_status: READY_FOR_REVIEW
purpose: 통합 인디케이터 엔진 v5.2 — v4 리뷰 + 김민호 v3 리뷰 7건 대조 보완(INPUT_NOT_AVAILABLE 분리·THEME_NOT_REVIEWED·QA값 주입식) + MARKET_CLOSED 창 제외(260731 QA 재리뷰)
반영 사항:
  [F1] 빈 셀 재배분 복원 — D-10 ③ 확정 규칙(같은 테마 타지역 재배분, 전 지역 공백 시 G 예외절차 이관).
       v4의 "빈 셀 정책 결정 필요" 에러는 이미 결정된 규칙의 미구현이었음.
  [F2] gate 판정을 실패 개수 방식(CANDIDATE/OBSERVE/EXCLUDE)에서 축별 사유 기록으로 변경 — R7 3축 분리.
       3단계 출력상태는 테마 적격성 게이트 전용(D-01)이며 판정 코드 매핑은 D-2 의결 대상이라 임의 매핑 금지.
  [F3] 하드코딩 상태값 제거 — 존재하지 않는 결정ID·CONFIRMED·COMPLETE·NOT_REQUIRED·FROZEN 출력 금지(R2).
       성과동결 판정은 팀 게이트(QA 판정식)이므로 코드는 게이트 현황만 보고한다.
  [F4] ADTV90 시계열 산출 복원 — 데이터사전 5장·D-06·D-07 기본안 기준(daily_market_state 입력).
       v4의 사전 집계값 입력 방식은 산출이 아니라 기록이라 교차구현 가치가 없었음.
  [F5] 임계값 정리 — thresholds JSON에서 P10과 data_cutoff_date를 함께 읽음(T-5 결합).
       재무 임계값은 미의결(UNAPPROVED_PLACEHOLDER), 결측은 행 단위 CALCULATION_HOLD(탈락 아님).
"""
import json
import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Config — 엔진 정본(06_코드/engine/config.py) 우선, 부재 시 내부 폴백
# ---------------------------------------------------------------------------
try:
    import config as ENGINE_CONFIG            # engine 폴더 안에서 실행되는 경우
    _CFG_SOURCE = "ENGINE_CONFIG"
except ImportError:
    ENGINE_CONFIG = None
    _CFG_SOURCE = "INTERNAL_FALLBACK"


class Config:
    OPEN_DAYS_TARGET = getattr(ENGINE_CONFIG, "ADTV90_OPEN_DAYS_TARGET", 90)
    SEASONING_MIN_OBS_DAYS = getattr(ENGINE_CONFIG, "SEASONING_MIN_OBS_DAYS", 90)
    P10_PERCENTILE = getattr(ENGINE_CONFIG, "LIQUIDITY_THRESHOLD_PERCENTILE", 10)
    CELL_TARGET_WEIGHT = getattr(ENGINE_CONFIG, "CELL_TARGET_WEIGHT", 1.0 / 6.0)
    THEMES = list(getattr(ENGINE_CONFIG, "THEMES", ["AI_ROBOTICS", "ENERGY_POWER", "SPACE_DEFENSE"]))
    REGIONS = list(getattr(ENGINE_CONFIG, "REGIONS", ["KR", "US"]))
    RULE_VERSION = getattr(ENGINE_CONFIG, "RULE_VERSION", "v0.9-pilot")
    QA_TOLERANCE = 1e-12          # 데이터사전 qa_tolerance 등재값 (수식부록 정식 등재는 의안 6-3)
    R10_TOLERANCE = 1e-9          # 엔진 assign_weights 검산과 동일. 일원화는 의안 6-3
    FINANCIAL_GATE_THRESHOLD = 1.0        # ⚠ UNAPPROVED_PLACEHOLDER — 하한 미의결(R2). 게이트 판정에 단독 사용 금지
    FINANCIAL_GATE_THRESHOLD_STATUS = "UNAPPROVED_PLACEHOLDER"

VALID_OBS_STATES = {"TRADED", "ZERO_VOLUME"}      # 유효관측일 = 무거래 포함, 정지·휴장·결측 제외 (D-06)


class CustomIndexEngineV5:
    def __init__(self, thresholds_json_path=None):
        self.p10_thresholds, self.data_cutoff_date = None, None
        if thresholds_json_path:
            try:
                with open(thresholds_json_path, "r", encoding="utf-8") as f:
                    j = json.load(f)
                self.p10_thresholds = j.get("provisional_P10")          # [F5] 중첩 구조
                self.data_cutoff_date = j.get("data_cutoff_date")       # [F5] T-5 결합
            except FileNotFoundError:
                print("[알림] threshold JSON 없음 — 진단용 자체 P10 사용 (공식 판정 아님)")

    # ------------------------------------------------------------------ [F4]
    def calculate_adtv90(self, states_df, observation_end_date=None):
        """일별 시장상태 시계열 → 종목별 ADTV90 원장 1행.
        입력: daily_market_state.csv 스키마
          [security_id, market, market_date, daily_market_state, daily_trading_value]
        산식(데이터사전 5장·D-07 기본안): 관측창 = 관측종료일 이전 최근 90개 개장일 행.
          정지·무거래 = 0 반영, 분모 = 90 − 결측일수(NA는 0 대체 금지, R6)."""
        cutoff = observation_end_date or self.data_cutoff_date
        if cutoff is None:
            raise ValueError("observation_end_date 또는 thresholds JSON의 data_cutoff_date가 필요합니다 (R4 PIT)")
        rows = []
        for sec, g in states_df.groupby("security_id"):
            g = g[g["market_date"] <= cutoff].sort_values("market_date")
            # 관측창 = 개장일 행만. NOT_LISTED(미상장)·MARKET_CLOSED(휴장)는 창 구성에서 제외
            # (엔진 그리드는 휴장 행을 생성하지 않으나, 임의 입력 방어 — 260731 QA 리뷰 반영)
            listed = g[~g["daily_market_state"].isin(["NOT_LISTED", "MARKET_CLOSED"])]
            seasoning_days = int(listed["daily_market_state"].isin(VALID_OBS_STATES).sum())
            win = listed.tail(Config.OPEN_DAYS_TARGET)
            n = len(win)
            s = win["daily_market_state"]
            halt = int((s == "TRADING_HALT").sum())
            zero = int((s == "ZERO_VOLUME").sum())
            miss = int((s == "DATA_MISSING").sum())
            traded_sum = win.loc[s == "TRADED", "daily_trading_value"].sum()
            row = {
                "security_id": sec, "market": g["market"].iloc[0],
                "observation_end_date": cutoff, "observed_open_days": n,
                "open_days_target": Config.OPEN_DAYS_TARGET,
                "halt_days_90": halt, "zero_volume_days_90": zero, "missing_days_90": miss,
                "traded_days_90": n - halt - zero - miss,
                "seasoning_days": seasoning_days,
                "seasoning_status": "SEASONED" if seasoning_days >= Config.SEASONING_MIN_OBS_DAYS
                                    else "SEASONING_INCOMPLETE",
                "official_adtv90": np.nan, "adtv90_exclude_halt_diagnostic": np.nan,
                "rule_version": Config.RULE_VERSION, "config_source": _CFG_SOURCE,
            }
            if n < Config.OPEN_DAYS_TARGET:
                row["adtv90_status"] = "SEASONING_INCOMPLETE"
            elif miss > 0 and (n - miss) == 0:
                row["adtv90_status"] = "CALCULATION_HOLD"
            else:
                row["adtv90_status"] = "CALCULATED"
                row["official_adtv90"] = float(traded_sum) / (n - miss)
                if miss == 0 and (n - halt) > 0:                      # 분모 제외값은 진단 병기(D-12 ⑤)
                    row["adtv90_exclude_halt_diagnostic"] = float(traded_sum) / (n - halt)
            rows.append(row)
        return pd.DataFrame(rows)

    # ------------------------------------------------------------------ [F2]
    def apply_gates(self, ledger, basket, selection_date=None):
        """축별 게이트 판정 — 단일 합산 점수·실패 개수 방식 금지(R7).
        basket: [security_id, market, primary_theme, gate_status(테마 적격성 판정 원장값)]
        테마 3단계(통과 후보/관찰/제외)는 판정 원장의 값을 그대로 사용한다. 자체 enum 부여 금지(D-2 의결 대상)."""
        df = basket.merge(ledger, on=["security_id", "market"], how="left")
        df["pilot_basket_scope"] = "SEED18_LIMITED_PILOT"
        df["production_promotion_status"] = "NOT_PROMOTED"
        df["approval_status"] = "APPROVAL_PENDING"                     # [F3] CONFIRMED 하드코딩 제거
        df["decision_id"] = "DECISION_ID_PENDING"                      # [F3] 존재하지 않는 결정ID 금지

        # P10 — 공식은 JSON, 없으면 진단용 자체 산출(구조상 시장 최솟값은 항상 미달함을 명시)
        if self.p10_thresholds:
            df["p10_value"] = df["market"].map(self.p10_thresholds)
            df["p10_source"] = "THRESHOLDS_JSON_OFFICIAL"
        else:
            calc = df[df["adtv90_status"] == "CALCULATED"]
            diag = calc.groupby("market")["official_adtv90"].apply(
                lambda x: np.percentile(x.astype(float), Config.P10_PERCENTILE, method="linear"))
            df["p10_value"] = df["market"].map(diag)
            df["p10_source"] = "SELF_DIAGNOSTIC_ONLY"   # 선형보간 특성상 시장 최솟값 1종목은 항상 미달

        reasons, fin_status = [], []
        for _, r in df.iterrows():
            why = []
            if pd.isna(r.get("gate_status")):
                why.append("THEME_NOT_REVIEWED")           # 판정 원장 부재 — 미통과와 구분
            elif r.get("gate_status") != "CANDIDATE":
                why.append("THEME_GATE")
            if r.get("seasoning_status") != "SEASONED":
                why.append("SEASONING")
            if r.get("adtv90_status") != "CALCULATED":
                why.append(f"ADTV90_{r.get('adtv90_status')}")
            elif float(r["official_adtv90"]) < float(r["p10_value"]):
                why.append("LIQUIDITY_BELOW_P10")
            # 재무 축 — 원장 부재/행 결측/평가를 분리. 어느 경우도 탈락 아님(R6)
            if "quick_ratio" not in df.columns:
                fin_status.append("INPUT_NOT_AVAILABLE")   # 원장 자체 부재(MISSING_INPUT_LEDGER)
            elif pd.isna(r.get("quick_ratio", np.nan)):
                fin_status.append("CALCULATION_HOLD")      # 원장은 있으나 해당 행 결측
            else:
                fin_status.append("EVALUATED_UNAPPROVED_THRESHOLD")    # 임계 미의결 — 참고 판정만
                # 미의결 임계로는 탈락시키지 않는다(R2). 승인 후 why.append 활성화.
            if selection_date and "data_available_date" in df.columns \
                    and pd.notna(r.get("data_available_date")) \
                    and str(r["data_available_date"]) > str(selection_date):
                why.append("PIT_NOT_AVAILABLE")
            reasons.append(";".join(why))
        df["financial_gate_status"] = fin_status
        df["exclusion_reasons"] = reasons
        df["selected_flag"] = (df["exclusion_reasons"] == "").astype(int)
        df["selection_status"] = df["selected_flag"].map({1: "SELECTED", 0: "NOT_SELECTED"})
        return df

    # ------------------------------------------------------------------ [F1]
    def construct_portfolio(self, evaluated_df):
        """6셀 각 1/6 · 셀 내 동일가중 · 빈 셀은 D-10 ③ 재배분.
        같은 테마 타지역 재배분 → 그래도 공백이면 G 예외절차 이관(산출 중단, ALLOCATION_HOLD)."""
        sel = evaluated_df[evaluated_df["selected_flag"] == 1].copy()
        cells = [(m, t) for t in Config.THEMES for m in Config.REGIONS]
        cell_w = {c: Config.CELL_TARGET_WEIGHT for c in cells}
        notes = []
        for m, t in cells:
            n = len(sel[(sel["market"] == m) & (sel["primary_theme"] == t)])
            if n == 0:
                other = "US" if m == "KR" else "KR"
                n_other = len(sel[(sel["market"] == other) & (sel["primary_theme"] == t)])
                if n_other > 0:
                    cell_w[(other, t)] += cell_w[(m, t)]
                    cell_w[(m, t)] = 0.0
                    notes.append({"cell_id": f"{m}_{t}", "cell_shortage_flag": 1,
                                  "resolution": f"SAME_THEME_CROSS_REGION->{other}_{t}"})
                else:
                    raise ValueError(
                        f"ALLOCATION_HOLD [G 예외절차 이관]: 테마 {t} 전 지역 공백 — "
                        f"재배분 불가. 팀 예외절차(G) 의결 전 산출 중단(D-10 ③)")
            else:
                notes.append({"cell_id": f"{m}_{t}", "cell_shortage_flag": 0, "resolution": ""})
        rows = []
        for (m, t), w in cell_w.items():
            g = sel[(sel["market"] == m) & (sel["primary_theme"] == t)]
            for _, r in g.iterrows():
                rows.append({"security_id": r["security_id"], "market": m, "primary_theme": t,
                             "cell_id": f"{m}_{t}", "cell_target_weight": w,
                             "final_target_weight": w / len(g)})
        weights = pd.DataFrame(rows)
        total = weights["final_target_weight"].sum()
        if not np.isclose(total, 1.0, atol=Config.R10_TOLERANCE):
            raise ValueError(f"CRITICAL ERROR [R10 위반]: 비중 합계 {total:.12f} ≠ 1.0 — 재배분 후에도 불일치, 구현 결함")
        return weights, pd.DataFrame(notes)

    # ------------------------------------------------------------------ [F3]
    def qa_gate_report(self, engine_val, independent_val, gate_statuses,
                       manual_validation_status=None, run_id=None):
        """QA 오차 산출 + 동결 게이트 현황 보고. 동결 '판정'은 팀 의결 몫 — 코드는 FROZEN을 출력하지 않는다."""
        if independent_val != 0:
            err = abs((engine_val - independent_val) / independent_val)
        else:
            err = 0.0 if engine_val == 0 else float("inf")
        gates = {k: bool(gate_statuses.get(k, False)) for k in ("P", "C", "FX", "BM", "CAL")}
        gates["Q"] = err <= Config.QA_TOLERANCE
        return {
            "max_relative_error": err,
            "qa_pass_flag": gates["Q"],
            "freeze_gate_status": gates,
            "all_gates_passed_informational": all(gates.values()),
            "performance_status": "PERFORMANCE_NOT_FROZEN",   # 해제는 팀 의결로만
            # QA 판정값은 코드가 만들지 않는다 — 검증 기록에서 호출자가 전달(미전달 시 NOT_PROVIDED)
            "manual_validation_status": manual_validation_status or "NOT_PROVIDED_SEE_QA_RECORDS",
            "run_id": run_id or "RUN_ID_NOT_PROVIDED",
        }


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import io

    def make_states(sec, mkt, days, tv, n=100, start="2026-01-05"):
        dates = pd.bdate_range(start, periods=n).strftime("%Y-%m-%d")
        return pd.DataFrame({"security_id": sec, "market": mkt, "market_date": dates,
                             "daily_market_state": "TRADED", "daily_trading_value": tv})

    SECS = [("010120", "KR", "ENERGY_POWER", 9e10), ("012450", "KR", "SPACE_DEFENSE", 5e10),
            ("064400", "KR", "AI_ROBOTICS", 4.5e10), ("GEV", "US", "ENERGY_POWER", 8e8),
            ("LMT", "US", "SPACE_DEFENSE", 4.5e8), ("NVDA", "US", "AI_ROBOTICS", 6e8)]
    states = pd.concat([make_states(s, m, None, tv) for s, m, _, tv in SECS])
    basket = pd.DataFrame([{"security_id": s, "market": m, "primary_theme": t, "gate_status": "CANDIDATE"}
                           for s, m, t, _ in SECS])
    eng = CustomIndexEngineV5()
    eng.p10_thresholds = {"KR": 1e10, "US": 1e8}          # 공식 threshold 주입(테스트용) — 전 종목 통과 수준

    print("--- [TEST 1] 정상 통과 (공식 threshold 사용, 6셀 전부 존재) ---")
    led = eng.calculate_adtv90(states, observation_end_date="2026-05-29")
    ev = eng.apply_gates(led, basket)
    w, notes = eng.construct_portfolio(ev)
    print("선정:", int(ev.selected_flag.sum()), "| 총비중:", w.final_target_weight.sum())

    print("--- [TEST 2] 빈 셀 재배분 (KR ENERGY 탈락 → US ENERGY로 재배분, D-10 ③) ---")
    b2 = basket.copy(); b2.loc[b2.security_id == "010120", "gate_status"] = "OBSERVE"
    ev2 = eng.apply_gates(led, b2)
    w2, notes2 = eng.construct_portfolio(ev2)
    print("선정:", int(ev2.selected_flag.sum()), "| 총비중:", round(w2.final_target_weight.sum(), 12))
    print(notes2[notes2.cell_shortage_flag == 1].to_string(index=False))

    print("--- [TEST 3] 재무 결측 = 행 단위 CALCULATION_HOLD (탈락 아님) ---")
    b3 = basket.copy(); b3["quick_ratio"] = [np.nan, 1.5, 2.0, 1.1, np.nan, 2.5]
    ev3 = eng.apply_gates(led, b3)
    print(ev3[["security_id", "financial_gate_status", "selection_status"]].to_string(index=False))

    print("--- [TEST 4] 테마 전 지역 공백 → G 예외절차 이관(ALLOCATION_HOLD) ---")
    b4 = basket.copy(); b4.loc[b4.primary_theme == "SPACE_DEFENSE", "gate_status"] = "EXCLUDE"
    try:
        eng.construct_portfolio(eng.apply_gates(led, b4))
    except ValueError as e:
        print("[정상 감지]", e)
