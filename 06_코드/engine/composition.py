# -*- coding: utf-8 -*-
"""정량 게이트 → 6셀 배정 → 부족 시 재배분(D-10 ③) → 셀 내 동일가중(잠정).
파일럿: 대안 A 전부 편입·상한 없음. 데이터사전 v0.2 10·12·13장 필드."""
import pandas as pd
import config as C


def select_constituents(basket: pd.DataFrame, ledger: pd.DataFrame, thresholds: dict) -> pd.DataFrame:
    """basket: [security_id, entity_id, market, primary_theme, gate_status(테마 게이트 결과)]
    ledger: indicators 출력. 반환: 종목별 selected_flag·selection_status·사유"""
    df = basket.merge(ledger, on=["security_id", "market"], how="left")
    reasons = []
    for _, r in df.iterrows():
        why = []
        if r.get("gate_status") != "CANDIDATE":
            why.append("THEME_GATE")
        if r.get("seasoning_status") != "SEASONED":
            why.append("SEASONING")
        if r.get("adtv90_status") != "CALCULATED":
            why.append(f"ADTV90_{r.get('adtv90_status')}")
        elif float(r["official_adtv90"]) < thresholds.get(r["market"], 0.0):
            why.append("LIQUIDITY_BELOW_P10")
        reasons.append(";".join(why))
    df["exclusion_reasons"] = reasons
    df["selected_flag"] = (df["exclusion_reasons"] == "").astype(int)
    df["selection_status"] = df["selected_flag"].map({1: "SELECTED", 0: "NOT_SELECTED"})
    df["composition_method"] = C.COMPOSITION_METHOD
    df["cap_scenario"] = C.CAP_SCENARIO
    df["selection_rule_version"] = C.RULE_VERSION
    df["cell_id"] = df["market"] + "_" + df["primary_theme"]
    return df


def assign_weights(selected: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """6셀 각 1/6, 셀 내 동일가중. 빈 셀은 같은 테마 타지역 재배분(D-10 ③), 사유코드 기록.
    반환: (종목별 가중표, 셀 요약표)"""
    sel = selected[selected["selected_flag"] == 1].copy()
    cells = [(m, t) for t in C.THEMES for m in C.REGIONS]
    cell_w, notes = {}, []
    for m, t in cells:
        cell_w[(m, t)] = C.CELL_TARGET_WEIGHT
    for m, t in cells:
        n = len(sel[(sel["market"] == m) & (sel["primary_theme"] == t)])
        if n == 0:
            other = "US" if m == "KR" else "KR"
            n_other = len(sel[(sel["market"] == other) & (sel["primary_theme"] == t)])
            if n_other > 0:                       # 같은 테마 타지역으로 재배분
                cell_w[(other, t)] += cell_w[(m, t)]
                cell_w[(m, t)] = 0.0
                notes.append({"cell_id": f"{m}_{t}", "cell_shortage_flag": 1,
                              "cell_shortage_reason": "INSUFFICIENT_ELIGIBLE_COUNT",
                              "resolution": f"SAME_THEME_CROSS_REGION->{other}_{t}"})
            else:                                  # 테마 전체 공백 → G 예외절차 이관
                notes.append({"cell_id": f"{m}_{t}", "cell_shortage_flag": 1,
                              "cell_shortage_reason": "INSUFFICIENT_ELIGIBLE_COUNT",
                              "resolution": "EXCEPTION_TRANSFER(G)"})
        else:
            notes.append({"cell_id": f"{m}_{t}", "cell_shortage_flag": 0,
                          "cell_shortage_reason": "", "resolution": ""})
    rows = []
    for (m, t), w in cell_w.items():
        g = sel[(sel["market"] == m) & (sel["primary_theme"] == t)]
        for _, r in g.iterrows():
            rows.append({"security_id": r["security_id"], "market": m, "primary_theme": t,
                         "cell_id": f"{m}_{t}", "cell_target_weight": w,
                         "final_target_weight": w / len(g),
                         "weighting_status": C.WEIGHTING_STATUS,
                         "weighting_rule_version": C.RULE_VERSION})
    weights = pd.DataFrame(rows)
    total = weights["final_target_weight"].sum()
    assert abs(total - 1.0) < 1e-9 or len(weights) == 0, f"가중 총합 검산 실패: {total}"
    return weights, pd.DataFrame(notes)
