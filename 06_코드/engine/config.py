# -*- coding: utf-8 -*-
"""파일럿 규칙 동결값 — 결정로그 D-13 의결 대상. 실행 전 팀 [O] 필요.
필드명은 데이터사전 v0.2 기준. 이 파일 외의 모듈에 숫자 하드코딩 금지."""

RULE_VERSION = "v0.9-pilot"

# --- 잠정값 (D-13 동결표) ---
ADTV90_OFFICIAL_METHOD = "ZERO"          # D-07 기본안: 정지일 0 반영 (EXCLUDE_HALT는 진단 병기)
ADTV90_OPEN_DAYS_TARGET = 90             # 관측창: 최근 90개 시장 개장일
SEASONING_MIN_OBS_DAYS = 90              # 상장 후 유효관측일수 (D-06)
LIQUIDITY_THRESHOLD_PERCENTILE = 10      # 잠정 하한 = 시장별 분포 P10 (분포 산출 후 고정·기록)
COMPOSITION_METHOD = "A_ALL_ELIGIBLE"    # 파일럿: 대안 A 전부 편입, 상한 없음
CAP_SCENARIO = "NO_CAP"
CELL_TARGET_WEIGHT = 1.0 / 6.0           # 테마 1:1:1 × 지역 50:50 (D-10 확정)
INTRA_CELL_WEIGHTING = "EQUAL"           # 잠정 셀 내 동일가중 (H 확정 전, TEMPORARY)
WEIGHTING_STATUS = "TEMPORARY"
INDEX_BASE_VALUE = 1000.0                # D-09 확정
RETURN_TYPE = "PR"                       # D-08 확정
BASE_CURRENCY = "KRW"
FX_TREATMENT = "UNHEDGED"
BM_WEIGHT_KR = 0.5                       # 공식 합성 BM: KOSPI200 PR + Russell3000 PR (D-08 확정 유지)
BM_WEIGHT_US = 0.5

THEMES = ["AI_ROBOTICS", "ENERGY_POWER", "SPACE_DEFENSE"]   # 고정순서 1·2·3 (#27 확정)
REGIONS = ["KR", "US"]

# 파일럿 달력 잠정값 (#30 세부는 적용시험 후 확정)
SELECTION_DATES = ["2026-03-31", "2026-06-30"]   # 대표 검토일 후보 연동 (팀 확인 대기)
CUTOFF_LAG_TRADING_DAYS = 5                       # data_cutoff_date = 선정일 - 5거래일 (잠정)

# 거래대금 (제59조 복원 확정: 한국 KRX 제공값 우선, 미국 근사)
TRADING_VALUE_SOURCES = ("EXCHANGE_PROVIDED", "RECONSTRUCTED")

# 일별 시장상태 6종 (D-07 확정 — NOT_LISTED 포함)
STATE_TRADED = "TRADED"
STATE_ZERO_VOLUME = "ZERO_VOLUME"
STATE_TRADING_HALT = "TRADING_HALT"
STATE_MARKET_CLOSED = "MARKET_CLOSED"
STATE_DATA_MISSING = "DATA_MISSING"
STATE_NOT_LISTED = "NOT_LISTED"
