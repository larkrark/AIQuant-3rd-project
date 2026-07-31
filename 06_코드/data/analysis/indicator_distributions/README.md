# ADTV90·당좌비율 시장별 분포표

생성 스크립트: `06_코드/analysis/build_indicator_distributions.py`

## 산출 범위

- ADTV90: `06_코드/data/pilot_run/output_f1/adtv90_ledger.csv` 기준 시장별 P5·P10·P25·P50·P75.
- 당좌비율: 계산보류: quick_ratio_ledger.csv 입력 원장 없음. 임의 대체값 없이 `CALCULATION_HOLD`로 기록.

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
