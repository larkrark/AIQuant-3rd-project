# input_ca16_4 — 16-4 기업행사 보정 입력 (v0.9-pilot)

기반: data/pilot_run/input/ (F-1 사용본)과 동일. **prices.csv 한 파일만 변경.**

변경 내용: adj_close 열 추가.
- 010120(LS ELECTRIC) market_date < 2026-04-13 행: adj_close = raw_close / 5 (5:1 액면분할, 04-08~10 정지, 04-13 재개)
- 그 외 전 행: adj_close = raw_close
- raw_close·volume·exchange_trading_value 원본 불변 → ADTV·상태코드·거래대금 무영향(KRX 거래대금은 분할 불변)

근거: DART 공시(QA 발견) — 이론가 157,600 = 788,000/5, 재개종가 179,200(+13.71%).
규칙: R3 비저촉(입력 오류 정정), D-1 가격연속성, L-③ 재산출 사유 = 입력 오류 정정.
전체 해시 대장: ../output_ca16_4/HASHES_16-4.txt
