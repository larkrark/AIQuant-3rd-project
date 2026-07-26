# 커스텀 인덱스 엔진 v0 (본체 파이프라인, rule_version = v0.9-pilot)

유니버스 상태 → 시즈닝·ADTV90 → 정량 게이트 → 6셀 배정·재배분 → 동일가중(잠정) → PR 지수 + 공식 합성 BM 동시 산출

> 수집·리포팅·QA·분석은 형제 폴더로 분리됨 — `../ingest`, `../report`, `../qa`, `../analysis`, 데이터는 `../data`. (`06_코드/README.md` 참조)

## 구성 (코어 모듈만)

| 파일 | 역할 | 근거 |
|---|---|---|
| `config.py` | 잠정값 동결표 (D-13 의결 대상) — 숫자는 전부 이 파일에만 | 결정로그 D-06~D-12 |
| `market_state.py` | 일별 상태코드 6종 + 거래대금(한국 KRX 제공값 우선·`trading_value_source`·오차비율) | D-07, D-13 ②, 룰북 8.1 |
| `indicators.py` | 시즈닝(유효관측일수)·ADTV90 이중 산식(0 반영 공식 + 분모 제외 진단) + P10 잠정 하한 | D-06·D-07, D-12 ⑤ |
| `composition.py` | 정량 게이트 → 셀 배정 → 빈 셀 같은 테마 타지역 재배분 → 셀 내 동일가중, 총합=1 검산 | D-10, D-12 ⑦ |
| `index_calc.py` | 효력발생일 가중 재설정·구간 연쇄 PR 지수, 합성 BM(KOSPI200+Russell3000 원화) 동일 리베이스 | D-08·D-09·D-10 |
| `run_pilot.py` | 파이프라인 실행 진입점 | — |
| `tests/test_invariants.py` | 합성 표본 관통 스모크 테스트 (상태코드·가중합 1.0·정합) | 룰북 R9·R10 |
| `tests/make_sample.py` | 합성 표본 생성 (관통 시험 전용, 실데이터 아님) | — |

## 실행

```bash
pip install -r ../requirements.txt
# 반드시 engine/ 에서 실행 (모듈은 서로 평면 임포트)
python run_pilot.py ../data/pilot_run/input_krxbm ../data/pilot_run/output_krxbm
python tests/test_invariants.py     # 불변식 검증
```

입력 CSV 스키마는 `run_pilot.py` 상단 주석 참조 — 필드명은 데이터사전 기준.

## 주의

- **합성 데이터 산출물은 어떤 문서에도 인용 금지** — 파이프라인 검증 전용 (룰북 R12)
- 실행 전 D-13(잠정값 동결) 전원 [O] 필요. `config.py` 값 변경은 결정로그 기록을 거친다 (R3)
- 성과를 본 뒤 `config.py`를 조정하는 것은 금지 (성과 기반 규칙 조정 금지)
- 데이터 경로 확인은 `../ingest/check_data_paths.py`(로컬 실행). 실패 경로는 실행계획 §4(리스크와 대비)로 전환
