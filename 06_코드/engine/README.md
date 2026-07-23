# 커스텀 인덱스 엔진 v0 (파일럿 골격, rule_version = v0.9-pilot)

유니버스 상태 → 시즈닝·ADTV90 → 정량 게이트 → 6셀 배정·재배분 → 동일가중(잠정) → PR 지수 + 공식 합성 BM 동시 산출

## 구성

| 파일 | 역할 | 근거 |
|---|---|---|
| `config.py` | 잠정값 동결표 (D-13 의결 대상) — 숫자는 전부 이 파일에만 | 결정로그 D-06~D-12 |
| `market_state.py` | 일별 상태코드 6종 부여 + 거래대금(한국 KRX 제공값 우선·`trading_value_source`·오차비율) | D-07, #15, 제59조 복원 |
| `indicators.py` | 시즈닝(유효관측일수)·ADTV90 이중 산식(0 반영 공식 + 분모 제외 진단, missing=0 조건) + P10 잠정 하한 | D-06·D-07, #15·#16 |
| `composition.py` | 정량 게이트 → 셀 배정 → 빈 셀 같은 테마 타지역 재배분 → 셀 내 동일가중, 총합=1 검산 | D-10, #21 |
| `index_calc.py` | 효력발생일 가중 재설정·구간 연쇄 방식 PR 지수, 합성 BM(KOSPI200+Russell3000 원화) 동일 리베이스 | D-08·D-09·D-10 |
| `run_pilot.py` | 파이프라인 실행 진입점 (`python run_pilot.py <입력폴더> <출력폴더>`) | — |
| `check_data_paths.py` | **로컬에서 실행** — pykrx·yfinance·^RUA·KRX300·ECOS 경로 실체 확인 | 계획서 C항 |
| `make_sample.py` | 합성 표본 생성 (관통 시험 전용, 실데이터 아님) | — |

## 실행

```bash
pip install pandas pykrx yfinance
python check_data_paths.py            # 1) 로컬 경로 확인 (5/5 통과 필요)
python make_sample.py                 # 2) 합성 데이터로 관통 시험
python run_pilot.py sample_data output
# 3) 실데이터 수집 후 입력 CSV를 같은 스키마로 만들어 다시 실행
```

입력 CSV 스키마는 `run_pilot.py` 상단 주석 참조 — 필드명은 데이터사전 v0.2 기준.

## 관통 시험 결과 (2026-07-23, 합성 데이터)

- 상태코드 6종 정상 부여 (TRADING_HALT 우선 적용·DATA_MISSING NA 유지·NOT_LISTED 포함)
- 시즈닝 미달 종목 제외, P10 잠정 하한 미달 제외, 사유코드 기록 확인
- 빈 셀(US_ENERGY_POWER) → 같은 테마 타지역 재배분 발동, 가중 총합 1.0 검산 통과
- 지수·BM 기준값 1,000 리베이스, 리밸 2회 연쇄 산출 확인

## 주의

- **합성 데이터 산출물은 어떤 문서에도 인용 금지** — 파이프라인 검증 전용
- 실행 전 D-13(잠정값 동결) 전원 [O] 필요. `config.py` 값 변경은 결정로그 기록을 거친다
- 성과를 본 뒤 `config.py`를 조정하는 것은 금지 (성과 기반 규칙 조정 금지 원칙)
- 폴더 위치(06_코드)는 잠정 — repo 구조 확정(계획서 E항) 시 이동 가능
