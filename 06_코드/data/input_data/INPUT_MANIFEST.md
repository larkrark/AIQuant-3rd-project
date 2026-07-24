# input_data 출처 매니페스트 (v0.9-pilot)

각 입력 파일의 생성 주체·원천·상태. QA 스냅샷과 재현성 검증의 기준 문서. 갱신일: 2026-07-23

| 파일 | 생성 주체 | 원천 | 상태 | 후속 |
|---|---|---|---|---|
| `prices_us.csv` | collect_pilot_inputs.py | 야후(yfinance, auto_adjust=False) | 사용 가능 | — |
| `bm_us.csv` | collect_pilot_inputs.py | 야후 ^RUA (Russell 3000) | 사용 가능 | — |
| `bm_kr.csv` | collect_pilot_inputs.py | 야후 ^KS200 — **예비 경로** (pykrx 로그인 문제로 자동 대체) | 사용 가능 | KRX 로그인 확보됨 → 재실행 시 KRX 공식값으로 교체·기록 |
| `calendar.csv` | collect_pilot_inputs.py | bm_kr·bm_us 시계열에서 유도 (공통 개장일 175일) | 사용 가능 | bm_kr 교체 시 rebuild_calendar() 재생성 |
| `fx.csv` | collect_pilot_inputs.py | 한국은행 ECOS API (계열 731Y001 잠정) | 사용 가능 | 계열코드 데이터사전 확정 대기 |
| `listings_us_draft.csv` | collect_pilot_inputs.py | 야후 firstTradeDate | **폐기** (5종목 epoch 파싱 실패) | listings_us_fixed.csv로 대체 |
| `listings_us_fixed.csv` | 스크립트 산출 + Claude 보정 | 야후 epoch 복구 — `YAHOO_REFERENCE(EPOCH_MS_FIXED)` | **드라이런 사용본** | SPCX 상장일(2026-06-12)만 EDGAR 원출처 확인(REVIEW_REQUIRED) |
| `bm_kr_krx300_reserve.csv` | (미생성) | — | 보류 | KRX 재실행 시 생성 (파일럿 비필수, BM 재확인 표결용) |
| `../seed_basket.csv` | 수기 (권보성 — 미국 9종목분) | 팀 Seed Basket 기록 | 사용 가능 | 김근형 마스터(한국 9종목)와 병합 후 고정 |
| `prices_kr.csv` | 도착 대기 (김근형) | KRX — 거래대금 포함 (제59조 공식 경로) | — | KRX 로그인 설정 공유됨 |
| `listings.csv` / `halts.csv` / `pit_check.csv` | 도착 대기 (김근형) | KRX·KIND·DART 공시 | — | 인계 스키마 = 데이터사전 부록 A |

> 원칙: 야후·예비 경로 산출물은 파일럿 한정 사용이며 공식 원출처의 대체가 아니다(D-13 ①). `.env`는 개인 로컬 파일로 커밋 금지.
