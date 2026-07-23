# 백테스트 모듈 (backtest/)

engine이 산출한 지수·BM 시계열을 받아 **성과·위험을 평가하고 시각화**한다.
담당: 백테스팅. rule_version 연동 = `engine/config.py`.

## 설계 원칙

1. **규칙과 평가의 분리** — 평가·시각화 코드(`metrics.py`, `report.py`)는 리밸 규칙 값에
   의존하지 않는다. 입력이 `index_vs_benchmark.csv`(날짜·지수·BM) 하나뿐이라, 규칙이
   잠정이든 확정이든 코드는 바뀌지 않는다.
2. **성과 기반 규칙 변경 금지** — 평가는 산출과 분리한다. 결과를 보고 `config.py`를
   되돌아가 고치지 않는다(과적합 방지 · 프로젝트 원칙).
3. **재현성** — 같은 입력 → 항상 같은 결과. 무작위·현재시각 미사용.

## 구성

| 파일 | 역할 | 실데이터 의존 |
|---|---|---|
| `metrics.py` | 수익률·CAGR·변동성·Sharpe·MDD·추적오차·정보비율·턴오버 | 없음 |
| `report.py` | 대시보드 PNG (성장곡선·수중곡선·초과성과 + KPI 타일) | 없음 |
| `run_backtest.py` | 진입점 — engine 호출 + 평가 + 리포트를 묶는 얇은 오케스트레이터 | 없음 |
| `data_loader.py` | 실데이터 → engine 입력 스키마 CSV (**미구현 stub**) | ★있음 |

## 실행

```bash
pip install pandas numpy matplotlib
python run_backtest.py --run-engine   # 합성데이터 생성 → engine 실행 → 평가·대시보드
python run_backtest.py                # 기존 engine 산출물(output/)로 평가만
```

산출: `figures/backtest_dashboard.png`, `figures/metrics_summary.json`

## 개발 순서

```
① make_sample(합성) → engine → index_vs_benchmark.csv
② metrics.py  ← 규칙 없이 지금 완성   ✅
③ report.py   ← 규칙 없이 지금 완성   ✅
④ run_backtest.py 로 묶기            ✅
⑤ data_loader.py (실데이터)          ← 데이터 확보 후. 스키마만 맞추면 ①~④ 그대로 재사용
```

## 주의

- `figures/`, `engine/output/`, `engine/sample_data/` 는 **합성 산출물 → 인용 금지**.
  git 미추적(`.gitignore`). 코드 검증 전용이며 어떤 문서에도 수치 인용 금지.
- 현재 지표는 **합성 데이터 기준**이라 의미 없는 숫자다. 파이프라인이 도는지만 본다.
