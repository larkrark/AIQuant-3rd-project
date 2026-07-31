# -*- coding: utf-8 -*-
"""ADTV90 and quick-ratio distribution tables for agenda F.

This runner reads the frozen pilot output and writes diagnostic distribution
tables under ``06_코드/data/analysis/indicator_distributions``. It does not
change thresholds or make approval decisions.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

CODE_DIR = Path(__file__).resolve().parents[1]
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from engine import config as C


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = CODE_DIR / "data"
PILOT_OUTPUT_DIR = DATA_DIR / "pilot_run" / "output_f1"
OUTPUT_DIR = DATA_DIR / "analysis" / "indicator_distributions"

ADTV_LEDGER_PATH = PILOT_OUTPUT_DIR / "adtv90_ledger.csv"
QUICK_RATIO_LEDGER_PATH = DATA_DIR / "input_data" / "quick_ratio_ledger.csv"

QUICK_RATIO_REQUIRED_COLUMNS = (
    "security_id",
    "market",
    "selection_date",
    "quick_ratio_raw",
    "quick_ratio_status",
)


def _percentile_columns(values: pd.Series) -> dict[str, float]:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    return {
        f"P{p}": clean.quantile(p / C.PERCENTILE_SCALE, interpolation=C.PERCENTILE_METHOD)
        for p in C.DISTRIBUTION_PERCENTILES
    }


def _write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def build_adtv90_distribution() -> tuple[pd.DataFrame, pd.DataFrame]:
    ledger = pd.read_csv(ADTV_LEDGER_PATH, dtype={"security_id": str})
    calculated = ledger[ledger["adtv90_status"] == "CALCULATED"].copy()

    rows = []
    detail_rows = []
    for (selection_date, review_cycle_id, market), group in calculated.groupby(
        ["selection_date", "review_cycle_id", "market"],
        dropna=False,
    ):
        official = pd.to_numeric(group["official_adtv90"], errors="coerce")
        zero = pd.to_numeric(group["adtv90_zero"], errors="coerce")
        exclude = pd.to_numeric(group["adtv90_exclude_halt"], errors="coerce")
        pcols = _percentile_columns(official)
        p10 = pcols[f"P{C.LIQUIDITY_THRESHOLD_PERCENTILE}"]
        ranked = group.assign(_official_adtv90=official).sort_values(
            ["_official_adtv90", "security_id"],
            na_position="last",
        )
        below = ranked[ranked["_official_adtv90"] < p10]
        min_row = ranked.iloc[C.DISTRIBUTION_FIRST_POSITION]
        second_value = (
            ranked["_official_adtv90"].iloc[C.DISTRIBUTION_SECOND_POSITION]
            if len(ranked) > C.DISTRIBUTION_SECOND_POSITION
            else pd.NA
        )

        rows.append(
            {
                "selection_date": selection_date,
                "review_cycle_id": review_cycle_id,
                "market": market,
                "rule_version": group["rule_version"].iloc[0],
                "distribution_source": str(ADTV_LEDGER_PATH.relative_to(WORKSPACE_ROOT)),
                "metric": "official_adtv90",
                "percentile_method": C.PERCENTILE_METHOD,
                "n_calculated": int(official.notna().sum()),
                "n_seasoning_excluded": int(
                    len(
                        ledger[
                            (ledger["selection_date"] == selection_date)
                            & (ledger["market"] == market)
                            & (ledger["adtv90_status"] != "CALCULATED")
                        ]
                    )
                ),
                **pcols,
                "below_P10_count": int(len(below)),
                "below_P10_security_ids": ";".join(below["security_id"].astype(str)),
                "min_security_id": str(min_row["security_id"]),
                "min_value": min_row["_official_adtv90"],
                "second_value": second_value,
                "min_gap_to_P10_pct": (
                    min_row["_official_adtv90"] / p10 - C.PERCENT_CHANGE_BASE
                )
                * C.PERCENTILE_SCALE,
                "threshold_status": "TEMPORARY_P10_DIAGNOSTIC",
                "approval_status": "APPROVAL_PENDING",
            }
        )

        detail = group[
            [
                "security_id",
                "market",
                "selection_date",
                "review_cycle_id",
                "data_cutoff_date",
                "observation_end_date",
                "seasoning_status",
                "adtv90_status",
                "official_adtv90",
                "adtv90_zero",
                "adtv90_exclude_halt",
                "missing_days_90",
                "halt_days_90",
                "zero_volume_days_90",
                "rule_version",
            ]
        ].copy()
        detail["P10_candidate"] = p10
        detail["distance_to_P10"] = official - p10
        detail["distance_to_P10_pct"] = (
            official / p10 - C.PERCENT_CHANGE_BASE
        ) * C.PERCENTILE_SCALE
        detail["pass_P10_candidate"] = official >= p10
        detail["official_minus_exclude_halt"] = zero - exclude
        detail["threshold_status"] = "TEMPORARY_P10_DIAGNOSTIC"
        detail_rows.append(detail)

    return pd.DataFrame(rows), pd.concat(detail_rows, ignore_index=True)


def build_quick_ratio_distribution() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not QUICK_RATIO_LEDGER_PATH.exists():
        pending_percentiles = {f"P{p}": pd.NA for p in C.DISTRIBUTION_PERCENTILES}
        summary_rows = [
            {
                "selection_date": selection_date,
                "market": market,
                "rule_version": C.RULE_VERSION,
                "distribution_source": str(QUICK_RATIO_LEDGER_PATH.relative_to(WORKSPACE_ROOT)),
                "metric": "quick_ratio_raw",
                "quick_ratio_use": "DIAGNOSTIC_ONLY",
                "percentile_method": C.PERCENTILE_METHOD,
                "quick_ratio_status": "CALCULATION_HOLD",
                "n_calculated": pd.NA,
                **pending_percentiles,
                "hold_reason": "INPUT_LEDGER_NOT_FOUND",
                "approval_status": "DATA_PENDING",
            }
            for selection_date in C.SELECTION_DATES
            for market in C.REGIONS
        ]
        detail = pd.DataFrame(
            {
                "required_column": QUICK_RATIO_REQUIRED_COLUMNS,
                "status": "MISSING_INPUT_LEDGER",
                "expected_path": str(QUICK_RATIO_LEDGER_PATH.relative_to(WORKSPACE_ROOT)),
            }
        )
        return pd.DataFrame(summary_rows), detail

    ledger = pd.read_csv(QUICK_RATIO_LEDGER_PATH, dtype={"security_id": str})
    missing = [c for c in QUICK_RATIO_REQUIRED_COLUMNS if c not in ledger.columns]
    if missing:
        summary = pd.DataFrame(
            {
                "rule_version": [C.RULE_VERSION],
                "metric": ["quick_ratio_raw"],
                "quick_ratio_status": ["CALCULATION_HOLD"],
                "hold_reason": ["MISSING_REQUIRED_COLUMNS"],
                "missing_columns": [";".join(missing)],
                "approval_status": ["DATA_PENDING"],
            }
        )
        detail = pd.DataFrame(
            {
                "required_column": QUICK_RATIO_REQUIRED_COLUMNS,
                "present": [c in ledger.columns for c in QUICK_RATIO_REQUIRED_COLUMNS],
                "expected_path": str(QUICK_RATIO_LEDGER_PATH.relative_to(WORKSPACE_ROOT)),
            }
        )
        return summary, detail

    calculated = ledger[ledger["quick_ratio_status"].isin(["CALCULATED", "CALCULATED_LOWER_BOUND"])]
    rows = []
    for (selection_date, market), group in calculated.groupby(["selection_date", "market"], dropna=False):
        values = pd.to_numeric(group["quick_ratio_raw"], errors="coerce")
        rows.append(
            {
                "selection_date": selection_date,
                "market": market,
                "rule_version": C.RULE_VERSION,
                "distribution_source": str(QUICK_RATIO_LEDGER_PATH.relative_to(WORKSPACE_ROOT)),
                "metric": "quick_ratio_raw",
                "quick_ratio_use": "DIAGNOSTIC_ONLY",
                "percentile_method": C.PERCENTILE_METHOD,
                "n_calculated": int(values.notna().sum()),
                "n_lower_bound": int((group["quick_ratio_status"] == "CALCULATED_LOWER_BOUND").sum()),
                "n_hold": int(
                    len(
                        ledger[
                        (ledger["selection_date"] == selection_date)
                        & (ledger["market"] == market)
                        & (ledger["quick_ratio_status"] == "CALCULATION_HOLD")
                        ]
                    )
                ),
                **_percentile_columns(values),
                "approval_status": "DIAGNOSTIC_ONLY",
            }
        )
    return pd.DataFrame(rows), ledger


def write_readme(adtv_summary: pd.DataFrame, quick_summary: pd.DataFrame) -> None:
    readme = OUTPUT_DIR / "README.md"
    quick_status = (
        "계산보류: quick_ratio_ledger.csv 입력 원장 없음"
        if "hold_reason" in quick_summary.columns
        and (quick_summary["hold_reason"] == "INPUT_LEDGER_NOT_FOUND").any()
        else "산출 완료"
    )
    text = f"""# ADTV90·당좌비율 시장별 분포표

생성 스크립트: `06_코드/analysis/build_indicator_distributions.py`

## 산출 범위

- ADTV90: `06_코드/data/pilot_run/output_f1/adtv90_ledger.csv` 기준 시장별 P5·P10·P25·P50·P75.
- 당좌비율: {quick_status}. 임의 대체값 없이 `CALCULATION_HOLD`로 기록.

## 산출 파일

- `adtv90_market_distribution.csv`
- `adtv90_security_threshold_diagnostics.csv`
- `quick_ratio_market_distribution.csv`
- `quick_ratio_input_status.csv`
- `generation_manifest.json`

## 상태

- `threshold_status=TEMPORARY_P10_DIAGNOSTIC`
- `approval_status=APPROVAL_PENDING` 또는 `DATA_PENDING`
- 본 산출물은 하한 절대금액 승인(#16)과 당좌비율 확인표 산출(#17)의 입력이며, 확정 규칙값이 아니다.
"""
    readme.write_text(text, encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    adtv_summary, adtv_detail = build_adtv90_distribution()
    quick_summary, quick_detail = build_quick_ratio_distribution()

    _write_csv(adtv_summary, OUTPUT_DIR / "adtv90_market_distribution.csv")
    _write_csv(adtv_detail, OUTPUT_DIR / "adtv90_security_threshold_diagnostics.csv")
    _write_csv(quick_summary, OUTPUT_DIR / "quick_ratio_market_distribution.csv")
    _write_csv(quick_detail, OUTPUT_DIR / "quick_ratio_input_status.csv")

    manifest = {
        "rule_version": C.RULE_VERSION,
        "percentile_method": C.PERCENTILE_METHOD,
        "distribution_percentiles": list(C.DISTRIBUTION_PERCENTILES),
        "adtv90_source": str(ADTV_LEDGER_PATH.relative_to(WORKSPACE_ROOT)),
        "quick_ratio_source": str(QUICK_RATIO_LEDGER_PATH.relative_to(WORKSPACE_ROOT)),
        "outputs": [
            "adtv90_market_distribution.csv",
            "adtv90_security_threshold_diagnostics.csv",
            "quick_ratio_market_distribution.csv",
            "quick_ratio_input_status.csv",
        ],
    }
    (OUTPUT_DIR / "generation_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_readme(adtv_summary, quick_summary)


if __name__ == "__main__":
    main()
