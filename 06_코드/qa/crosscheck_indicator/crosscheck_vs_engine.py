# -*- coding: utf-8 -*-
"""v5 교차구현 vs 엔진 원장 대조 — 규칙 문서 기준 재현성 검증.
사용: python crosscheck_vs_engine.py <output_run_dir>   (예: ../../data/pilot_run/output_f1)
대조: daily_market_state.csv를 입력으로 v5가 재산출한 ADTV90 원장을
      같은 폴더의 adtv90_ledger.csv(엔진 산출)와 비교한다."""
import sys, json
import pandas as pd
import importlib.util

def main(run_dir):
    spec = importlib.util.spec_from_file_location("v5", __file__.replace("crosscheck_vs_engine.py", "indicator_prototype_v5.py"))
    v5 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v5)
    states = pd.read_csv(f"{run_dir}/daily_market_state.csv", dtype={"security_id": str})
    eng_ledger = pd.read_csv(f"{run_dir}/adtv90_ledger.csv", dtype={"security_id": str})
    results = []
    for cutoff, e in eng_ledger.groupby("data_cutoff_date"):
        eng = v5.CustomIndexEngineV5()
        led = eng.calculate_adtv90(states, observation_end_date=cutoff)
        m = led.merge(e[["security_id", "official_adtv90", "adtv90_status", "seasoning_status"]],
                      on="security_id", suffixes=("_v5", "_engine"))
        m["official_adtv90_engine"] = pd.to_numeric(m["official_adtv90_engine"], errors="coerce")
        both = m[m["adtv90_status_engine"] == "CALCULATED"]
        rel = ((both["official_adtv90_v5"] - both["official_adtv90_engine"]).abs()
               / both["official_adtv90_engine"]).max()
        results.append({
            "data_cutoff_date": cutoff, "securities": len(m),
            "status_match": bool((m["adtv90_status_v5"] == m["adtv90_status_engine"]).all()),
            "seasoning_match": bool((m["seasoning_status_v5"] == m["seasoning_status_engine"]).all()),
            "max_relative_error": float(rel), "qa_tolerance": 1e-12,
            "qa_pass": bool(rel <= 1e-12),
        })
    out = {"crosscheck_target": run_dir, "note": "규칙 문서 기준 독립 재구성(v5) — 엔진 코드 미참조 주장 아님(리뷰 수정본)", "cycles": results}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    with open(f"{__file__.rsplit('/', 1)[0]}/crosscheck_result.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return out

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../../data/pilot_run/output_f1")
