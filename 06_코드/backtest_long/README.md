# 장기 백테스트 패키지

기간만 바꿔 **기존 엔진을 그대로** 돌리는 실행기다. 규칙은 한 줄도 바꾸지 않았다.

```bash
cd 06_코드/backtest_long
python run_long_backtest.py                              # 2013-01-01 ~ 2026-07-24
python run_long_backtest.py --start 2018-01-01           # 시작만 변경
python run_long_backtest.py --start 2020-01-01 --end 2024-12-31
python run_long_backtest.py --skip-collect               # 수집 생략, 엔진만 재실행
python run_long_backtest.py --freq A                     # 연 1회 선정 (기본 Q=분기)
python make_figures.py                                   # figures/ 에 PNG 6종
```

`.env`(`ECOS_API_KEY`·`KRX_ID`·`KRX_PW`)가 필요하다. 커밋 금지 파일이며 자동으로 찾는다.

## ★ pull 받은 직후에는 수집을 먼저 돌려야 한다

`06_코드/data/input_long/` 은 `.gitignore` 대상이다. 가격 42,972행·환율 3,342행 등
용량 때문인데, **코드는 전부 저장소에 있으므로 아래 한 줄로 동일한 입력을 다시 만든다.**

```bash
cd 06_코드/backtest_long
python run_long_backtest.py       # 수집 + 조립 + 엔진 (10~15분)
python integrity_test.py          # 그 다음에 검증
```

수집을 건너뛰고 검증부터 돌리면 `[중단] 검증에 필요한 입력·산출물이 없다` 가 뜨고
실행 순서를 안내한다.

**같은 입력인지 확인하는 방법** — `run_long_backtest.py` 는 수집 직후
`out/long_run_meta.json` 의 `inputs_sha256_16`(커밋돼 있음)과 이번 수집분 해시를
자동으로 대조해 출력한다. 전부 동일하면 같은 입력으로 같은 검증을 돌린 것이다.

구간이 다르면 해시가 달라진다. 기록과 맞추려면 `--start 2013-01-01 --end 2026-07-24`
를 명시할 것(기본값과 같다).

---

## 1. 무엇을 바꿨나 — 규칙은 불변

| 파일 | 변경 | 기본 동작 |
|---|---|---|
| `ingest/collect_pilot_inputs.py` | `START`·`END` 를 환경변수로 덮어쓰기 가능 | **불변** |
| | ECOS 페이징 추가 (다년 구간은 1회 요청으로 못 받음) | 3개월은 동일 |
| | **US 분할 이중조정 수정** — §4 참조 | 파일럿 무영향 |
| `engine/config.py` | `SELECTION_DATES` 를 환경변수로 덮어쓰기 가능 | **불변** |

선정·게이트·가중·연결·환율 규칙은 그대로다. `git diff` 로 확인 가능하다.

---

## 2. 왜 만들었나

파일럿은 공통 개장일 **59일**이라 리밸런싱 적용 이벤트가 **0회**였다.
선정은 2회 돌았고 결과도 달랐지만(`3/31 KTOS → 6/30 ATI`) 6/30 선정의 효력발생일이
구간 밖이라 지수에 반영된 적이 없다.

그래서 다음이 전부 미검증으로 남아 있었다.

```
index_linking      verification: NOT_EXERCISED
셀 부족 재배분      D-10 ③ 구현됨 · 발동 0회
상태코드            실제 정지·휴장 이벤트 표본 부족
```

**구간을 늘리면 같은 규칙으로 전부 발동한다.**

---

## 3. 결과 — 기전 실증

```
산출일수      3,076일        (파일럿 59일)
정기변경      53회           (파일럿 2회)
구성 변경     28회           실제로 종목이 바뀐 회차
셀 부족       22회 발동      D-10 ③ 재배분 — 파일럿 0회
```

셀 부족 내역

```
KR_AI_ROBOTICS   →  US_AI_ROBOTICS     8회
KR_ENERGY_POWER  →  US_ENERGY_POWER   14회
```

`018260`(2014-11 상장)·`267260`(2017-05)·`298040`(2018-07) 상장 이전 구간에서
한국 셀이 비어 같은 테마 미국 셀로 재배분됐다. **규칙이 설계대로 작동했다.**

---

## 4. 수집기 결함 1건 수정 — US 분할 이중조정

### 증상

`ANET` 2021-11-19 에 지수가 하루 **+34.4%** 튀었다. 정기변경일이 아니다.

```
ANET raw_close   32.95 → 33.02 → 33.14 → 32.24 → 32.04    연속
ANET adj_close    2.06 →  2.06 →  2.07 →  8.06 →  8.01    ← 계단
```

### 원인

`yfinance` 는 `auto_adjust=False` 에서도 **분할은 이미 반영한** `Close` 를 준다
(미조정인 것은 배당뿐이다). 기존 코드가 그 위에 분할계수를 또 적용해
분할일에 인위적 불연속을 만들었다.

확인된 사례 — `ANET` 2021-11-19(+289%)·2024-12-05(+305%), `APH` 2014-10-13(+99%).

### 수정

원계열이 분할일에 **실제로 튀는지 먼저 확인하고, 튈 때만** 역조정한다.
어느 쪽 동작이든 안전하다.

### 파일럿 영향 — 없음

```
파일럿 prices.csv 에 adj_close 열이 존재하지 않는다 → raw_close 평가
US 분할(ANET 2021·2024, APH 2014)이 전부 파일럿 구간(2025-10~) 밖이다
```

**파일럿 산출물은 재산출 대상이 아니다.**

---

## 5. 엔진 결함 1건 발견 — 미수정, 보고만

`composition.assign_weights` 는 편입 종목이 **0개**일 때 죽는다.

```python
rows = []                       # 편입 0개
weights = pd.DataFrame(rows)    # 열이 없는 빈 DataFrame
total = weights["final_target_weight"].sum()   # KeyError
assert abs(total - 1.0) < 1e-9 or len(weights) == 0
#                                  ^^^^^^^^^^^^^^^^ 빈 경우를 예상하고 있으나
#                                                   그 전 줄에서 예외가 난다
```

구간 시작부(2013-03-31)는 어느 종목도 시즈닝 90일을 못 채워 편입이 0이 된다.

**엔진은 고치지 않았다.** `run_long_backtest.py` 의 `drop_unseedable()` 이
해당 회차를 사전에 제외한다. 지수를 만들 수 없는 회차라 실질 손실은 없다.
수정 여부는 산출 담당의 판단이다.

---

## 6. ★ 성과 인용 금지

**Seed18 은 2026년 시점에 고른 종목이다.** 이를 과거로 되돌린 결과는
선택편향·생존편향을 포함한다. `ALAB`·`GEV` 는 2024년 상장이라 그 이전엔
존재하지 않았고, `SPCX` 는 2026-06 상장이라 사실상 전 구간 제외다.

```
말할 수 있는 것
  "같은 규칙이 13년간 53회 자동으로 굴러갔다"
  "셀 부족 재배분이 22회 실제로 발동했다"
  "구성이 28회 바뀌었고 연결은 경계에서 연속이었다"

말하면 안 되는 것
  "13년 백테스트에서 BM 을 이겼다"
  수익률·알파·초과수익을 근거로 한 모든 주장
```

`figures/` 의 모든 PNG 하단에 이 경고가 박혀 나온다. 잘라 써도 따라간다.

`out/long_run_meta.json` 에 `status: MECHANISM_EVIDENCE_ONLY` 와
입력 SHA-256 전량이 기록된다.

---

## 7. 산출물

```
out/     index_vs_benchmark.csv · daily_market_state.csv · adtv90_ledger.csv
         constituents_*.csv · weights_*.csv · thresholds_*.json (53회차)
         cell_shortage.csv · run_meta.json · long_run_meta.json

figures/ 01_누적곡선 · 02_편입히트맵 · 03_셀부족재배분
         04_추적오차 · 05_낙폭 · 06_P10하한
```

---

## 8. 독립성 표기

본 패키지는 QA(김민호)가 작성했다. 담당표상 원자료 수집·백테스팅은
산출 담당 몫이므로 **수집자와 검증자가 분리되지 않는다.**

```
수집(미국·BM·환율·달력)   POST_DISCLOSURE_MECHANICAL
지수 산출                 QA_PROVISIONAL — 산출 담당 재현 전까지
```

완화책 — 규칙 무변경(`git diff` 확인 가능) · 입력 SHA-256 전량 공개 ·
QA 독립 재산출(`qa/independent/`)은 엔진을 import 하지 않아 검증 경로는 여전히 분리.

산출 담당이 직접 재수집하면 본 산출물은 폐기하고 그쪽을 정본으로 삼는다.
그때 두 결과를 대조하면 3자 검증이 하나 늘어난다.
