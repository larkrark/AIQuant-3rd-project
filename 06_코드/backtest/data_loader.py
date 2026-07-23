# -*- coding: utf-8 -*-
"""데이터 로더 — 실데이터 수집·정제 → engine 입력 스키마 CSV 생성.

★ 이 파일만 실데이터에 의존한다. 지금은 미구현 stub.
   개발 순서상 마지막에 채운다. 그 전까지는 engine/make_sample.py(합성)가 대체한다.

원칙: 여기서 만드는 CSV의 '스키마'가 make_sample.py 출력과 동일하면,
      engine·metrics·report 코드는 한 줄도 바꾸지 않고 실데이터로 재실행된다.
      (가짜 CSV ─교체─▶ 진짜 CSV, 같은 스키마)

목표 스키마 (데이터사전 v0.2 · run_pilot.py 상단 주석 기준):
  seed_basket.csv  security_id, entity_id, market, primary_theme, gate_status
  prices.csv       security_id, market, market_date, raw_close, volume[, exchange_trading_value]
  calendar.csv     market, market_date, is_market_open
  listings.csv     security_id, listing_date[, delisting_date]
  halts.csv        security_id, market_date, full_day_halt        (없으면 생략 가능)
  fx.csv           market_date, fx_rate                           (ECOS 원/달러)
  bm_kr.csv        market_date, close                             (KOSPI200 PR)
  bm_us.csv        market_date, close                             (Russell3000 PR, USD)

데이터 출처 (계획서 C항 · check_data_paths.py 로 경로 실체 확인됨):
  - KR 가격·거래대금 : pykrx  (거래대금은 KRX 제공값 우선 — config.TRADING_VALUE_SOURCES)
  - US 가격          : yfinance
  - BM (Russell3000) : ^RUA (yfinance)
  - 환율             : ECOS (한국은행)
"""
import os


def build_inputs(out_dir: str, start: str, end: str) -> None:
    """실데이터를 수집·정제해 out_dir 에 engine 입력 CSV 8종을 쓴다.

    구현 시 체크리스트:
      1) point-in-time 준수 — 각 필드는 관측시점 이후 값이 섞이지 않도록 (미래참조 금지)
      2) 거래대금은 KRX 제공값 우선, 미국은 근사(trading_value_source 기록)
      3) 컬럼명·형식을 위 목표 스키마와 정확히 일치시킬 것
      4) 산출 후 engine/check_data_paths.py 검증(5/5) 통과 확인
    """
    raise NotImplementedError(
        "실데이터 수집 미구현. 현재는 engine/make_sample.py(합성)로 대체. "
        "실데이터 확보 후 이 함수를 채우면 engine/metrics/report 변경 없이 재실행된다."
    )


if __name__ == "__main__":
    os.makedirs("real_data", exist_ok=True)
    build_inputs("real_data", "2020-01-01", "2026-06-30")
