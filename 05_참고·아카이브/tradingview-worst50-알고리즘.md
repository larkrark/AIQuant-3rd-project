# TradingView "최악(Worst) 50" 알고리즘 · 위험 유형 조사

> **관점 전환**: 여기서 "최악"은 지표 자체가 무가치하다는 뜻이 아니라, **단독 사용 시 손실 위험이 크거나 · 구조적으로 백테스트를 왜곡하거나 · 과신·오용을 유발하는** 알고리즘/전략 유형을 뜻합니다. 유능한 트레이더가 도구로 쓰면 유용한 것도, 초보가 "성배"로 오해하면 계좌를 날립니다.
> 
> **조사일**: 2026-07-08 · **출처**: TradingView Pine Script 문서, PineCoders, EarnForex, 백테스트 실패 사례 리뷰
> 
> ⚠️ 정보 제공 목적이며 투자 조언이 아닙니다. 특정 저자·스크립트를 비방하려는 의도가 아니라, **위험 패턴을 식별해 회피**하도록 돕는 자료입니다.

---

## "최악"의 5가지 근본 원인 (분류 축)
1. **리페인팅(Repainting)** — 신호가 마감 후 사라지거나 이동. 백테스트는 완벽, 실거래는 붕괴
2. **룩어헤드 편향(Lookahead Bias)** — 미래 데이터를 몰래 참조. "타임머신" 백테스트
3. **과최적화(Overfitting/Curve-fitting)** — 과거에만 맞춰진 화려한 파라미터
4. **구조적 파산 위험** — 마틴게일·그리드·무손절 등 꼬리위험(tail risk)
5. **주관성/유사과학** — 해석 여지가 커 사후확증편향을 부르는 도구

---

## Part 1 — 리페인팅·룩어헤드 계열 (Worst 1~12)

| # | 알고리즘/유형 | 근본 문제 | 왜 위험한가 | 참조 |
|---|---|---|---|---|
| 1 | **Repainting 다중시간프레임(MTF) 신호 스크립트** | 리페인팅 | `security()` 미완성 바 참조로 신호가 실시간에 이동/소멸. 백테스트 승률 인위적 팽창 | [🔗](https://blog.traderspost.io/article/what-is-repainting-in-tradingview) |
| 2 | **lookahead_on을 쓴 HTF 추세필터** | 룩어헤드 | 9:31에 당일 4PM EMA를 "미리 앎". 42:1 수익/DD 같은 통계적 불가능 결과 | [🔗](https://medium.com/@techacademies/why-your-perfect-tradingview-strategy-fails-in-live-trading-30a875226d6b) |
| 3 | **음수 offset으로 과거에 신호 그리는 스크립트** | 리페인팅(치팅) | 마감 시 없던 매수/매도 화살표를 몇 봉 뒤에 소급 표시. PineCoders가 "명백한 부정"으로 규정 | [🔗](https://tradingwhale.io/what-is-trading-indicator-repainting/) |
| 4 | **"Recalculate on every tick" 켠 전략** | 룩어헤드 | 봉 중간 조건으로 진입 후 마감 시 조건 소멸. 백테스트≠실거래 | [🔗](https://grandalgo.com/blog/non-repaint-tradingview-indicators) |
| 5 | **ZigZag 기반 실시간 신호** | 리페인팅 | ZigZag는 마지막 다리를 계속 다시 그림. 실시간 진입점으로 쓰면 필연적 왜곡 | [🔗](https://blog.pickmytrade.trade/tradingview-repainting-indicator-reliability-signal-accuracy/) |
| 6 | **barstate.isrealtime로 로직 분기 스크립트** | 리페인팅(악성) | 실시간과 과거에 다른 계산 실행. 리뷰 때와 라이브 때가 완전히 다름 | [🔗](https://grandalgo.com/blog/non-repaint-tradingview-indicators) |
| 7 | **Bar Magnifier 끄고 검증한 인트라바 전략** | 룩어헤드 | 저TF 틱 데이터 의존을 감춤. Magnifier 켜면 성과 급락 | [🔗](https://grandalgo.com/blog/non-repaint-tradingview-indicators) |
| 8 | **"비리페인팅" 광고만 믿는 유료 스크립트** | 마케팅 함정 | 모든 유료 스크립트가 "non-repaint" 주장. 라벨 자체는 수익성·정확도를 전혀 보장 안 함 | [🔗](https://grandalgo.com/blog/non-repaint-tradingview-indicators) |
| 9 | **미래봉 참조 커스텀 오실레이터** | 리페인팅 | 과거 바의 값이 새 데이터로 소급 변경. 자동매매에 치명적 | [🔗](https://speedbot.tech/blog/tradingview-16/what-is-repainting-in-tradingview-and-how-do-i-find-it-and-avoid-it-206) |
| 10 | **HTF 캔들 미완성 데이터 사용 스크립트** | 리페인팅 | 30분봉 절반 값을 "완성된 값"처럼 사용. 세 유형 중 가장 흔함 | [🔗](https://tradingwhale.io/what-is-trading-indicator-repainting/) |
| 11 | **과도한 alert 남발 실시간 신호기** | 오용 | 봉 중간 신호로 알림 폭탄 → 과잉매매. "Once Per Bar Close" 미설정 | [🔗](https://blog.pickmytrade.trade/tradingview-repainting-indicator-reliability-signal-accuracy/) |
| 12 | **95% 지표가 가진 미묘한 리페인팅 무시** | 인지 부족 | MACD·RSI조차 실시간 현재봉은 변동. 이를 신호로 오해하면 20~30% 승률 하락 | [🔗](https://blog.pickmytrade.trade/tradingview-repainting-indicator-reliability-signal-accuracy/) |

## Part 2 — 구조적 파산 위험 계열 (Worst 13~22)

| # | 알고리즘/유형 | 근본 문제 | 왜 위험한가 | 참조 |
|---|---|---|---|---|
| 13 | **마틴게일 물타기 전략(1.8×~2× 스케일)** | 꼬리위험 | 손실 시 배로 베팅. 대부분 이기다가 한 번의 깊은 하락에 계좌 전멸 | [🔗](https://www.tradingview.com/scripts/page-3/?script_type=strategies) |
| 14 | **무손절(No Stop-Loss) DCA 그리드** | 무제한 위험 | 손절 없이 평단만 낮춤. 추세 반전 지속 시 마진콜 | [🔗](https://www.tradingview.com/scripts/page-3/?script_type=strategies) |
| 15 | **고정편차 그리드 봇(그리드 트레이딩)** | 방향위험 | 레인지 가정. 강한 추세에서 반대편 물량이 무한 누적 | [🔗](https://www.tradingview.com/scripts/) |
| 16 | **레버리지 마틴게일 스캘퍼** | 청산위험 | 물타기+레버리지 결합. 소액 역행에도 강제청산 | [🔗](https://www.tradingview.com/scripts/page-3/?script_type=strategies) |
| 17 | **"거래수 62개" 저표본 마틴게일 백테스트** | 통계 부족 | 100 거래 미만은 통계적 무의미. 승률·PF를 결론으로 오해 | [🔗](https://www.tradingview.com/scripts/page-3/?script_type=strategies) |
| 18 | **평단 물타기 "절대 지지" 매수봇** | 확증편향 | "여기가 바닥" 가정. 바닥은 계속 갱신됨 | [🔗](https://www.tradingview.com/scripts/page-3/?script_type=strategies) |
| 19 | **고정 3% TP + 얇은 엣지 전략** | 수수료 취약 | 미세 엣지라 수수료 불일치만으로 음의 기대값 전환 | [🔗](https://www.tradingview.com/scripts/page-3/?script_type=strategies) |
| 20 | **트레일링·손절 전무 래더 전략** | 구조적 노출 | 래더 소진 후 TP만 기다림. 더 깊은 하락 시 대형 DD | [🔗](https://www.tradingview.com/scripts/page-3/?script_type=strategies) |
| 21 | **올인 단일진입 "몰빵" 신호기** | 리스크관리 부재 | 포지션 사이징 없음. 한 번의 오신호가 치명적 | [🔗](https://bullpen.fi/bullpen-blog/best-tradingview-indicators) |
| 22 | **레버리지 3x+ ETF 데이 스윙 전략** | 변동성 붕괴 | 일일 리밸런싱 감쇠(decay) 무시. 횡보만 해도 손실 | [🔗](https://blog.pickmytrade.trade/best-tradingview-indicators/) |

## Part 3 — 주관성·유사과학 계열 (Worst 23~32)

| # | 알고리즘/유형 | 근본 문제 | 왜 위험한가 | 참조 |
|---|---|---|---|---|
| 23 | **Gann Angles / Gann Square** | 유사과학·주관성 | 기하학적 각도의 이론적 근거 취약. EarnForex 독자 선정 최악 도구 상위 | [🔗](https://www.earnforex.com/guides/worst-forex-indicator/) |
| 24 | **Elliott Wave (자동 카운트)** | 주관성 | 카운트가 사람마다 다르고 계속 재계산. "그럴듯해 보여서" 더 위험 | [🔗](https://www.earnforex.com/guides/worst-forex-indicator/) |
| 25 | **금융 점성술(Astro-Gann, 행성 각도)** | 유사과학 | 행성 위치로 반전 예측. 인과관계 전무 | [🔗](https://www.tradingview.com/scripts/gann/) |
| 26 | **Fibonacci를 "정확한 가격 자석"으로 쓰기** | 오용 | 되돌림 레벨을 정밀 진입점으로 맹신. 컨플루언스로만 유효 | [🔗](https://bullpen.fi/bullpen-blog/best-tradingview-indicators) |
| 27 | **Harmonic 패턴(Gartley·Bat 등) 단독매매** | 주관성 | ZigZag 앵커 의존, 패턴 완성 판정이 사후적 | [🔗](https://www.tradingview.com/scripts/fibonacci/) |
| 28 | **Elliott+Fib "1년 매크로 예측"** | 과신 | 장기 파동 예측을 확정처럼 제시. 무효화 잦음 | [🔗](https://www.tradingview.com/scripts/search/elliott/) |
| 29 | **"Turtle Soup" 유동성 스윕 단독 진입** | 사후확증 | 사후엔 명확, 실시간엔 노이즈와 구분 난망 | [🔗](https://www.tradingview.com/scripts/fibonacci/) |
| 30 | **행성 속도 기반 추세 기울기** | 유사과학 | Astro 지표의 전형. 검증 불가 | [🔗](https://www.tradingview.com/scripts/gann/) |
| 31 | **"신성한 비율" VWAP 변형(비검증)** | 임의 파라미터 | 표준편차 밴드를 피보나치로 대체하나 근거 부족, 신호 아님 명시 | [🔗](https://www.tradingview.com/scripts/fibonacci/) |
| 32 | **Pi Cycle 등 단일지표 "고점/저점 예언"** | 소표본 과신 | 역사상 몇 번의 적중을 법칙화. 표본 극소 | [🔗](https://github.com/EngineeredSuccess/ultimate-trading-indicators/blob/master/elliott_wave_crypto_indicator.pine) |

## Part 4 — 과최적화·지표 남용 계열 (Worst 33~42)

| # | 알고리즘/유형 | 근본 문제 | 왜 위험한가 | 참조 |
|---|---|---|---|---|
| 33 | **파라미터 20개+ "만능" 커스텀 전략** | 과최적화 | 자유도 과다로 과거에만 완벽 피팅. 아웃샘플 붕괴 | [🔗](https://www.quantum-algo.com/blog/guides/tradingview-backtesting-complete-guide/) |
| 34 | **75% 승률·5:1 R:R "매끄러운 곡선" 전략** | 커브피팅 신호 | 이 조합 자체가 과최적화의 스모킹건 | [🔗](https://www.quantum-algo.com/blog/guides/tradingview-backtesting-complete-guide/) |
| 35 | **RSI·MACD·Stoch·CCI·Williams 동시 5중첩** | 중복 신호 | 모두 모멘텀 측정. 상호 모순으로 의사결정 마비 | [🔗](https://investingengineer.com/10-best-tradingview-indicators-for-beginners/) |
| 36 | **단일 자산·단일 기간 최적화 스크립트** | 과최적화 | 하나의 심볼/기간에만 튜닝. 국면 바뀌면 전멸 | [🔗](https://lunefi.com/blog/best-tradingview-indicators-2026-backtested-win-rates) |
| 37 | **후행 MA만으로 진입하는 크로스 전략** | 지연(Lag) | 신호 지연으로 추세 끝물 진입. 레인지 휩쏘 다발 | [🔗](https://bullpen.fi/bullpen-blog/best-tradingview-indicators) |
| 38 | **SuperTrend 단독 초단타 진입** | 휩쏘 | 레인지에서 잦은 색전환이 연속 손실로. 필터 필수 | [🔗](https://bullpen.fi/bullpen-blog/best-tradingview-indicators) |
| 39 | **Stochastic 단독 강추세 역매매** | 조기신호 | 강추세에서 과매수·과매도가 오래 지속. 역진입 파멸 | [🔗](https://bullpen.fi/bullpen-blog/best-tradingview-indicators) |
| 40 | **저유동성 자산 볼륨지표(MFI·OBV)** | 데이터 신뢰성 | 부정확한 볼륨으로 엉뚱한 신호. TMF 등 에러 다발 | [🔗](https://in.tradingview.com/scripts/lazybear/) |
| 41 | **"AI/ML" 라벨만 붙인 블랙박스 신호기** | 검증 불가 | 내부 로직 비공개. 과최적화·리페인팅 은폐 가능 | [🔗](https://www.luxalgo.com/blog/code-tradingview-indicators-with-quant-the-best-ai-for-pine-script-2/) |
| 42 | **지표 위 지표 무한 중첩 "대시보드"** | 클러터 | 신호 과다로 판단 마비, 과잉매매 유발 | [🔗](https://investingengineer.com/10-best-tradingview-indicators-for-beginners/) |

## Part 5 — 오용·과신 유발 계열 (Worst 43~50)

| # | 알고리즘/유형 | 근본 문제 | 왜 위험한가 | 참조 |
|---|---|---|---|---|
| 43 | **"99% 승률" 광고 buy/sell 화살표기** | 허위 성과 | 어떤 지표도 99% 정확 불가. 대개 리페인팅·룩어헤드 | [🔗](https://blog.pickmytrade.trade/best-tradingview-indicators/) |
| 44 | **성배(Holy Grail) 마케팅 유료 스위트** | 과신 | "100% 승률" 성배는 존재하지 않음(WeMasterTrade 명시) | [🔗](https://wemastertrade.com/the-most-popular-tradingview-strategy/) |
| 45 | **TradingView 데이터=실체결 가정 스크립트** | 슬리피지 무시 | TV 데이터와 실제 브로커 체결은 다름. MT4/5 재검증 필요 | [🔗](https://wemastertrade.com/the-most-popular-tradingview-strategy/) |
| 46 | **News/이벤트 무시 상시가동 스캘퍼** | 이벤트 위험 | 지표 신뢰도가 뉴스 스파이크에 붕괴. 회피 조건 부재 | [🔗](https://www.tradingview.com/scripts/page-53/) |
| 47 | **1~5분 초저TF 미세튜닝 신호기** | 노이즈 | 저TF는 노이즈 지배. 미세조정 없이는 오신호 폭증 | [🔗](https://www.tradingview.com/scripts/page-53/) |
| 48 | **커미션·슬리피지 미반영 백테스트 전략** | 비용 누락 | 실비용 반영 시 수익이 손실로 역전 | [🔗](https://www.quantum-algo.com/blog/guides/tradingview-backtesting-complete-guide/) |
| 49 | **단일 국면(강세장)만 검증한 전략** | 국면 취약 | 약세·횡보 미검증. regime-specific는 견고하지 않음 | [🔗](https://www.quantum-algo.com/blog/guides/tradingview-backtesting-complete-guide/) |
| 50 | **자동매매 직결 전 미검증 커뮤니티 스크립트** | 실행 위험 | 리페인팅 여부 미확인 채 브로커 연결. 유령 체결 손실 | [🔗](https://blog.traderspost.io/article/what-is-repainting-in-tradingview) |

---

## 위험 회피 체크리스트 (출처 종합)

### 리페인팅·룩어헤드 탐지
- **바 리플레이(Alt+Shift+R)**: 신호가 이동/소멸하면 리페인팅
- **페이지 새로고침 테스트**: 실시간 10~20봉 후 리로드 → 플롯 사라지면 위험
- **알림 로깅**: "Once Per Bar Close" 설정, 로그와 차트 불일치 조사
- **포워드 테스트**: 데모 50거래 이상, 백테스트와의 격차가 리페인트 신호
- **Bar Magnifier 켜기**(전략): 성과 급락 시 인트라바 의존 의심
- **`lookahead_on` 금지**: offset은 security 호출 "밖"에 적용

### 과최적화 회피
- 인샘플(70%)/아웃샘플(30%) 분리, 커미션·슬리피지 반영
- 강세·약세·횡보·고변동·저변동 등 **다양한 국면**에서 PF 1.3+ 유지 확인
- 75% 승률·5:1 R:R·매끄러운 곡선 = 커브피팅 경고
- 파라미터 최소화, 총 거래 200+ 확보

### 구조·심리
- 마틴게일·그리드·무손절은 "대부분 이기다 한 번에 파산"하는 구조임을 인지
- "성배"·"99% 승률"·"AI 예측" 마케팅은 회피 신호
- 지표는 카테고리당 1개(추세 1 + 모멘텀 1 + 타이밍 1). 3~5개 이하 사용
- 주관적 도구(Elliott·Gann·Harmonic·Astro)는 단독 매매 금지, 컨플루언스로만

## 핵심 요약
"최악"의 공통분모는 **백테스트에서 화려하지만 실거래에서 무너지는 구조**입니다. 리페인팅·룩어헤드는 성과를 위조하고, 마틴게일·그리드는 꼬리위험을 숨기며, Elliott·Gann·Astro는 주관성으로 사후확증편향을 부릅니다. TradingView 15만+ 스크립트 중 꾸준히 수익 나는 것은 20~30개 수준이라는 평가를 기억하고, 검증되지 않은 커뮤니티 스크립트를 자동매매에 직결하기 전 반드시 리페인팅·비용·국면 검증을 거치세요.

## 참조 링크 모음
- 리페인팅 개념·탐지: https://blog.traderspost.io/article/what-is-repainting-in-tradingview
- 비리페인팅 라벨의 한계: https://grandalgo.com/blog/non-repaint-tradingview-indicators
- 룩어헤드 편향 실패 사례: https://medium.com/@techacademies/why-your-perfect-tradingview-strategy-fails-in-live-trading-30a875226d6b
- PineCoders 리페인팅 3유형: https://tradingwhale.io/what-is-trading-indicator-repainting/
- 최악의 포렉스 도구(독자 선정): https://www.earnforex.com/guides/worst-forex-indicator/
- 백테스팅 검증 가이드: https://www.quantum-algo.com/blog/guides/tradingview-backtesting-complete-guide/
- 초보 지표 남용 경고: https://investingengineer.com/10-best-tradingview-indicators-for-beginners/
- 인기 전략 검증 주의: https://wemastertrade.com/the-most-popular-tradingview-strategy/
