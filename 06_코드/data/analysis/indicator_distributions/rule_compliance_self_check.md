# ADTV90·당좌비율 분포표 산출 — 룰 준수 자가점검

대상 변경:
- `06_코드/engine/config.py`
- `06_코드/analysis/build_indicator_distributions.py`
- `06_코드/analysis/README.md`
- `06_코드/data/analysis/indicator_distributions/*`

| 규칙 | 검사 항목 | 준수(O/X/NA) | 근거(파일:줄 + 코드) | 위반 시 수정안 |
|---|---|---|---|---|
| R1 | 임계값·비중·기간·기준값이 config.py에만 있고, 다른 모듈에 리터럴 숫자 하드코딩 없음 | O | `06_코드/engine/config.py:12` `DISTRIBUTION_PERCENTILES = (5, 10, 25, 50, 75)` / `06_코드/analysis/build_indicator_distributions.py:45` `for p in C.DISTRIBUTION_PERCENTILES` |  |
| R2 | 미결·잠정 값을 임의 숫자로 확정하지 않고 TEMPORARY/PENDING 상태로 표시·유지 | O | `06_코드/analysis/build_indicator_distributions.py:105` `"approval_status": "APPROVAL_PENDING"` / `06_코드/analysis/build_indicator_distributions.py:157` `"approval_status": "DATA_PENDING"` |  |
| R3 | 성과·순위 결과를 본 뒤 config·경계값을 바꾸는 로직/흔적 없음 | O | `06_코드/data/analysis/indicator_distributions/README.md:22` `확정 규칙값이 아니다` |  |
| R4 | PIT 준수 — 자료마감일 이후 자료·미래값 참조 없음 | O | `06_코드/analysis/build_indicator_distributions.py:29` `ADTV_LEDGER_PATH = PILOT_OUTPUT_DIR / "adtv90_ledger.csv"` / `06_코드/analysis/build_indicator_distributions.py:115` `"data_cutoff_date"` |  |
| R5 | ADTV90 거래대금 원천·수정주가 오용 금지 | O | `06_코드/analysis/build_indicator_distributions.py:64` `official = pd.to_numeric(group["official_adtv90"]` |  |
| R6 | DATA_MISSING은 NA 유지, ZERO_VOLUME·TRADING_HALT만 0 반영 | O | `06_코드/analysis/build_indicator_distributions.py:121` `"missing_days_90"` / `06_코드/analysis/build_indicator_distributions.py:122` `"halt_days_90"` / `06_코드/analysis/build_indicator_distributions.py:123` `"zero_volume_days_90"` |  |
| R7 | 테마·유동성·재무·가격 축 분리 | O | `06_코드/analysis/build_indicator_distributions.py:54` `def build_adtv90_distribution()` / `06_코드/analysis/build_indicator_distributions.py:141` `def build_quick_ratio_distribution()` |  |
| R8 | 표준 날짜 필드명 사용 | O | `06_코드/analysis/build_indicator_distributions.py:113` `"selection_date"` / `06_코드/analysis/build_indicator_distributions.py:115` `"data_cutoff_date"` |  |
| R9 | 시장 상태코드 6종 외 코드 생성 없음 | NA | 본 산출 러너는 `daily_market_state`를 새로 판정하지 않고 기존 `adtv90_ledger.csv`를 읽는다. `06_코드/analysis/build_indicator_distributions.py:55` `pd.read_csv(ADTV_LEDGER_PATH` |  |
| R10 | 가중 총합 1.0 검산 | NA | 본 작업은 분포표 산출이며 셀 배정·가중을 변경하지 않는다. |  |
| R11 | 테마 1:1:1·6셀 구조 준수 | NA | 본 작업은 시장별 분포표 산출이며 테마·지역 가중 구조를 변경하지 않는다. |  |
| R12 | 합성/샘플 데이터 공식 인용 금지 | O | `06_코드/data/analysis/indicator_distributions/README.md:22` `확정 규칙값이 아니다` |  |
| R13 | AI 산출 요약을 공식 근거로 직접 인용하지 않음 | O | `06_코드/data/analysis/indicator_distributions/README.md:7` `output_f1/adtv90_ledger.csv` 기준 |  |
| R14 | 결정 단일 원본 대조 | O | `06_코드/engine/config.py:12` `룰북 8.1·D-12 ⑥` / `06_코드/analysis/README.md:20` `ADTV90·당좌비율 시장별 분포표` |  |
| R15 | 파일·폴더·네이밍 규칙 준수 | O | `06_코드/analysis/README.md:20` `../data/analysis/indicator_distributions/` |  |
| R16 | 비밀정보 커밋 금지 | O | `06_코드/analysis/build_indicator_distributions.py:29` 로컬 CSV만 읽고 `.env`·토큰 참조 없음 |  |

## 위반(X) 개수

0개.

## 자동 검산

- `python -m py_compile 06_코드/analysis/build_indicator_distributions.py 06_코드/engine/config.py`
- `adtv90_market_distribution.csv`의 P10이 `output_f1/thresholds_*.json`의 `provisional_P10`과 일치하는지 확인.
- `quick_ratio_market_distribution.csv`가 입력 원장 미확보 시 `CALCULATION_HOLD`와 `INPUT_LEDGER_NOT_FOUND`만 기록하는지 확인.

## 사람확인

- 당좌비율 원장 `06_코드/data/input_data/quick_ratio_ledger.csv`는 현재 미확보다. 실제 공시 기반 원장이 들어오면 같은 스크립트로 P5·P10·P25·P50·P75를 재산출해야 한다.
