# -*- coding: utf-8 -*-
"""독립 재산출 — 규칙 상수. 근거는 전부 규칙 문서이며 engine/config.py 를 import하지 않는다.

독립성(qa/README.md): engine 코드를 재사용하면 '독립' 재산출이 아니다.
따라서 값이 같더라도 **문서에서 다시 읽어 여기 적는다.** 각 줄에 근거 조항을 병기한다.

근거 문서:
  룰북  = 01_운영문서/260724_커스텀인덱스_구성및산출_룰북_v0.4_결정반영본.md
  사전  = 01_운영문서/데이터사전.md
  로그  = 01_운영문서/결정로그.md
"""

RULE_VERSION = "v0.9-pilot-independent"   # 재산출본 식별자 — 팀 산출(v0.9-pilot)과 구분

# --- 회차·달력 (로그 D-13 ①⑧) ---
SELECTION_DATES = ["2026-03-31", "2026-06-30"]   # 로그 D-13 ① 대표 검토일 + 직전 분기
CUTOFF_LAG_TRADING_DAYS = 5                      # 로그 D-13 ⑧ 자료마감일 = 선정일 이전 제5거래일
CUTOFF_AXIS = "COMMON"                           # 로그 D-13 ⑧ 공통 거래일 축으로 역산

# --- 시즈닝 (룰북 §8.1 "상장 후 유효관측일수") ---
SEASONING_MIN_OBS_DAYS = 90
# 유효관측일 = 정상 개장일 + 상장 중 + 거래정지 아님.
# ZERO_VOLUME 포함 / TRADING_HALT·MARKET_CLOSED·DATA_MISSING 제외.

# --- ADTV90 (룰북 §8.1 · 로그 D-13 ①②) ---
ADTV90_OPEN_DAYS_TARGET = 90     # 상장 중인 최근 90 시장개장일 (시장별 개장일 축, D-13 ⑧)
ADTV90_OFFICIAL_METHOD = "ZERO"  # 로그 D-13 ① 공식 산식 = 정지일 0 반영 (분모 제외값은 진단 병기)
LIQUIDITY_THRESHOLD_PERCENTILE = 10   # 로그 D-13 ① 시장별 분포 P10 잠정

# --- 거래대금 원천 (룰북 §8.1 제59조 복원 · 로그 D-13 ②) ---
# 한국 = KRX 제공 거래대금 우선(없을 때만 원종가×원거래량), 미국 = 원종가×원거래량 근사.
TRADING_VALUE_EXCHANGE = "EXCHANGE_PROVIDED"
TRADING_VALUE_RECONSTRUCTED = "RECONSTRUCTED"

# --- 상태코드 6종 (룰북 §8.1 · 로그 D-07 · 체크리스트 #15) ---
S_TRADED = "TRADED"
S_ZERO_VOLUME = "ZERO_VOLUME"
S_TRADING_HALT = "TRADING_HALT"
S_MARKET_CLOSED = "MARKET_CLOSED"
S_DATA_MISSING = "DATA_MISSING"
S_NOT_LISTED = "NOT_LISTED"

# 판정 우선순위. 룰북이 명시한 것은 TRADING_HALT > ZERO_VOLUME 뿐이다(§8.1
# "거래량 0이어도 ZERO_VOLUME보다 우선"). 나머지 순서는 문서에 없어 아래를 가정으로 둔다.
#   시장 축(휴장) → 종목 존재 축(상장) → 종목 거래가능 축(정지) → 자료 축(결측) → 거래 축
# 이 가정은 미결 정리표 U-1 로 등록한다.
STATE_PRIORITY = [S_MARKET_CLOSED, S_NOT_LISTED, S_TRADING_HALT, S_DATA_MISSING,
                  S_ZERO_VOLUME, S_TRADED]

# --- 구성·가중 (룰북 §9·§10 · 로그 D-13 ①) ---
THEMES = ["AI_ROBOTICS", "ENERGY_POWER", "SPACE_DEFENSE"]   # 룰북 §10 테마 간 1:1:1 (D-04 ②)
REGIONS = ["KR", "US"]                                      # 룰북 §10 지역 50:50 (D-10 ①)
CELL_TARGET_WEIGHT = 1.0 / 6.0        # 룰북 §10 테마×지역 6셀 각 1/6 (D-10 ②)
INTRA_CELL_WEIGHTING = "EQUAL"        # 로그 D-13 ① 셀 내 동일가중 (TEMPORARY — 안건 H 확정 전)
WEIGHTING_STATUS = "TEMPORARY"        # 룰북 §10 "테마 내부 가중 [미결 — 안건 H]"
COMPOSITION_METHOD = "A_ALL_ELIGIBLE"  # 로그 D-13 ① 대안 A 전부 편입
CAP_SCENARIO = "NO_CAP"                # 로그 D-13 ① 상한 없음 (종목 상한은 안건 H 미결)

# 백분위 산출 방법은 룰북 §8.1이 "P5·P10·P25(Q1)·P50·P75로 산출"만 정하고 방법을 정하지 않는다.
# 선형보간(numpy 기본)을 가정으로 사용한다 — 미결 정리표 U-2.
PERCENTILE_METHOD = "linear"
