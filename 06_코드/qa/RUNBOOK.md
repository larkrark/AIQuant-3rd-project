# qa 실행 설명서 (RUNBOOK)

engine이 낸 지수·BM 시계열을 받아 **독립 검산하고 성과·위험을 평가·시각화**한다.
독립성 규칙과 트랙 정의는 [README.md](README.md), 전체 흐름은 [DATAFLOW.md](../DATAFLOW.md).

> 2026-07-24 팀 리팩터(`7b084ae`)로 `06_코드/backtest/` → `06_코드/qa/` 이동.
> 데이터 경로도 `engine/input_data`·`engine/pilot_run` → `data/` 로 바뀌어, 전 파일이 `paths.py` 하나만 참조하도록 정리했다.

## 설계 원칙

1. **규칙과 평가의 분리** — 평가·시각화 코드(`metrics.py`, `report.py`)는 리밸 규칙 값에
   의존하지 않는다. 입력이 `index_vs_benchmark.csv`(날짜·지수·BM) 하나뿐이라, 규칙이
   잠정이든 확정이든 코드는 바뀌지 않는다.
2. **성과 기반 규칙 변경 금지** — 평가는 산출과 분리한다. 결과를 보고 `engine/config.py`를
   되돌아가 고치지 않는다(룰북 R3 · 과적합 방지).
3. **재현성** — 같은 입력 → 항상 같은 결과. 무작위·현재시각 미사용.
4. **engine 비의존** — engine을 import하지도, 실행하지도 않는다. 비교 대상은 engine이 **이미 낸 산출물**이다.

## 구성

| 파일 | 역할 | 네트워크 |
|---|---|---|
| `paths.py` | 경로 상수 단일 정의 (구조가 또 바뀌면 여기만 고친다) | — |
| `metrics.py` | 수익률·CAGR·변동성·Sharpe·MDD·추적오차·정보비율·턴오버 | — |
| `report.py` | 성과 대시보드 PNG (성장곡선·수중곡선·초과성과·롤링·셀구성 + KPI 타일) | — |
| `data_report.py` | 입력 검수 PNG (종목별 관측일수·환율·BM) | — |
| `run_backtest.py` | 진입점 — 실산출 폴더 → 지표·대시보드 | — |
| `compare_runs.py` | 교차검증 — 두 산출의 지수 시계열 대조 | — |
| `data_loader.py` | 팀과 독립 경로로 유니버스 재수집 → 엔진 입력 스키마 CSV | ★필요 |

## 실행

```bash
pip install -r ../requirements.txt   # + matplotlib
cd 06_코드/qa

python run_backtest.py               # data/pilot_run/output_krxbm 평가 (기본)
python run_backtest.py --alt         # data/pilot_run/output (예비 BM 세트) 평가
python run_backtest.py --output-dir <경로>

python data_report.py                # data/pilot_run/input_krxbm 검수 (기본)
python data_report.py <입력폴더>

python compare_runs.py               # 기준 output_krxbm vs 내 재산출(engine/output_real)
python compare_runs.py --mine <내 산출> --team <기준 산출>
python compare_runs.py --no-align    # 요약표를 각 전체구간으로 (관측창 차이 노출)
```

독립 수집(네트워크·자격증명 필요, `.env`는 `ingest/.env`):

```bash
python data_loader.py                # → qa/collected/ + sources.json
python data_loader.py <출력폴더>
```

산출: `figures/backtest_dashboard.png`, `figures/data_overview.png`,
`figures/compare_dashboard.png`, `figures/metrics_summary.json`.

## 주의

- `figures/`·`collected/`는 git 미추적이다. 재현하면 같은 결과가 나오므로 저장소에 넣지 않는다.
- 합성 표본 경로는 제거했다 — 실데이터 단계이며, 합성 산출물 수치는 어떤 문서에도 인용 금지(룰북 R12).
  파이프라인 관통 스모크는 engine 트랙의 `engine/tests/test_invariants.py`가 담당한다.
- 현재 산출은 59거래일·2회 리밸런스의 파일럿 잠정치다. 인용 시 `rule_version=v0.9-pilot`과
  [DATAFLOW.md §7 한계](../DATAFLOW.md)를 함께 붙인다.
