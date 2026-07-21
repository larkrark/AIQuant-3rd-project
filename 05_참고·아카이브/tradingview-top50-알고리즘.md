# TradingView 성과 검증 · 인기 Top 50 알고리즘 (보강판)

> **조사 기준**: 성과(백테스트 승률·Profit Factor·DD) · 검증 신뢰도(Pine Wizard/공식/공개 백테스트) · 조회수·인기(팔로워·부스트·커뮤니티 랭킹)
> 
> **조사일**: 2026-07-08 · **출처**: TradingView Community Scripts / Pine Wizards Hall of Fame / 독립 백테스트 리뷰
> 
> ⚠️ 과거 성과는 미래 수익을 보장하지 않습니다. 표의 승률·PF는 각 출처 백테스트 조건의 참고치이며 시장·기간에 따라 달라집니다.

---

## 등급 · 범례
- **검증 신뢰도**: ★★★★★ = Pine Wizard 저자 + 표준/공식 지표 또는 공개 백테스트 / ★★★★☆ = 저명 저자·다수 독립 리뷰 검증 / ★★★☆☆ = 커뮤니티 인기·부분 검증
- **유형**: 추세추종 · 모멘텀/오실레이터 · 변동성 · 볼륨 · 시장구조(SMC) · 평균회귀 · 머신러닝 · 종합/복합

---

## Part 1 — Top 1~20 (핵심 티어)

| # | 알고리즘 (저자) | 유형 | 핵심 아이디어 | 성과(참고) | 검증 | 인기 | 링크 |
|---|---|---|---|---|---|---|---|
| 1 | **Squeeze Momentum** (LazyBear) | 변동성/모멘텀 | BB가 Keltner 내부 → 스퀴즈, 해제 시 폭발 돌파 방향 진입 (TTM Squeeze 변형) | 돌파 포착 우수 | ★★★★★ | 최상위 | [🔗](https://www.tradingview.com/u/LazyBear/) |
| 2 | **Smart Money Concepts** (LuxAlgo) | SMC | OB·FVG·CHoCH/BOS·유동성 스윕 등 기관흐름 자동감지 | 프롭펌 선호(낮은 DD) | ★★★★★ | #1 근접·80만+ | [🔗](https://www.luxalgo.com/blog/smart-money-concepts-indicator-now-reaching-1-on-tradingview/) |
| 3 | **SuperTrend** (KivancOzbilgic) | 추세추종 | ATR 트레일링 스톱 색전환 신호, 변동성 적응 | 일봉 PF≈1.8·DD<15% | ★★★★★ | 최상위 | [🔗](https://www.tradingview.com/u/KivancOzbilgic/) |
| 4 | **WaveTrend Oscillator** (LazyBear) | 오실레이터 | 노이즈 적은 크로스·다이버전스 반전 (TCI 기원) | NQ 저변동 70% 승률 | ★★★★★ | Top5 | [🔗](https://in.tradingview.com/scripts/lazybear/) |
| 5 | **WaveTrend 3D** (jdehorty) | 모멘텀/ML | WT 재설계, 다중룩백 사이클·다이버전스 강화 | 다이버전스 개선 | ★★★★☆ | 높음 | [🔗](https://in.tradingview.com/scripts/lazybear/) |
| 6 | **RSI (+Adaptive/Divergence)** (내장) | 모멘텀 | 과매수/과매도+다이버전스, Adaptive T3 변형 | EUR/USD 4H 75% 정확도 | ★★★★★ | 최상위 | [🔗](https://blog.pickmytrade.trade/best-tradingview-indicators-2025-backtest-results/) |
| 7 | **MACD (Enhanced)** (ChrisMoody) | 모멘텀 | 12/26/9 히스토그램, 색상바·RSI 블렌딩 | SPY 히스토+RSI 안정 | ★★★★★ | 최상위 | [🔗](https://pineify.app/resources/blog/best-scripts-on-tradingview-ultimate-guide-to-top-indicators-and-trading-tools) |
| 8 | **Volume Profile HD** (TradingView) | 볼륨/S&R | 고거래량 노드로 지지/저항 매핑 | 공급/수요존 최상 | ★★★★★ | 매우높음 | [🔗](https://www.liberatedstocktrader.com/best-tradingview-indicators/) |
| 9 | **VWAP** (내장) | 볼륨/평균가 | 거래량가중평균, 기관 벤치마크·평균회귀 | 볼륨지표 상위 | ★★★★★ | 매우높음 | [🔗](https://www.liberatedstocktrader.com/best-tradingview-indicators/) |
| 10 | **Ichimoku Cloud** (내장) | 종합 | 9/26/52 구름으로 추세·S/R·모멘텀 동시 표현 | USD/JPY 포렉스 엣지 | ★★★★★ | 높음 | [🔗](https://blog.pickmytrade.trade/best-tradingview-indicators-2025-backtest-results/) |
| 11 | **Bollinger+RSI 반전 전략** | 평균회귀 | 하단밴드+RSI<30+반전캔들 매수 | 안정 승률(스윙) | ★★★★☆ | 높음 | [🔗](https://wemastertrade.com/the-most-popular-tradingview-strategy/) |
| 12 | **SuperTrend+EMA200 전략** | 추세추종 | 녹색전환+EMA200 상단 매수(추세필터) | 인기 Top3 셋업 | ★★★★☆ | 높음 | [🔗](https://wemastertrade.com/the-most-popular-tradingview-strategy/) |
| 13 | **QQE Mod** | 모멘텀 | 노이즈 저감 모멘텀, 크로스+볼륨 확인 | 타이밍 트리거 신뢰 | ★★★★☆ | 높음 | [🔗](https://bullpen.fi/bullpen-blog/best-tradingview-indicators) |
| 14 | **SSL Channel** | 추세 | 색전환 추세라벨링·청산, 플립 시 스톱 조정 | 명확한 신호 | ★★★★☆ | 높음 | [🔗](https://bullpen.fi/bullpen-blog/best-tradingview-indicators) |
| 15 | **Lorentzian Classification** (jdehorty) | ML/분류 | Lorentzian 거리 KNN으로 과거국면 매칭 방향예측 | ML 실증 | ★★★★☆ | 매우높음 | [🔗](https://supa.is/article/tradingview-pine-script-wizards-2026-best-community-indicators) |
| 16 | **ATR / Relative Volatility** (내장) | 변동성 | 변동성·스톱·사이징 정규화, 리스크관리 핵심 | 필수 도구 | ★★★★★ | 높음 | [🔗](https://www.liberatedstocktrader.com/best-tradingview-indicators/) |
| 17 | **Golden/Death Cross** (MexPayne) | 추세추종 | 50/200MA 교차 자동감지 스캔 | BTC 1H 연 20% | ★★★★☆ | 높음 | [🔗](https://blog.pickmytrade.trade/best-tradingview-indicators-2025-backtest-results/) |
| 18 | **3-Bar Reversal** (LazyBear) | 패턴/반전 | 3봉 패턴 반전 감지 (스윙) | 반전 포착 | ★★★★☆ | 높음 | [🔗](https://blog.pickmytrade.trade/best-tradingview-indicators-strategies/) |
| 19 | **LuxAlgo Dynamic S/R** (LuxAlgo) | S&R/변동성 | 국면적응 동적 S/R, ES/NQ 스캘핑 | 볼륨결합 스캘핑 우수 | ★★★★★ | 매우높음 | [🔗](https://lunefi.com/blog/best-tradingview-indicators-2026-backtested-win-rates) |
| 20 | **Zeiierman Trend / Liquidity Hunter** (Zeiierman) | 추세/유동성 | 적응형 추세+유동성존·스톱헌트 식별 (SMC 대안) | 프롭 인기 대안 | ★★★★☆ | 매우높음 | [🔗](https://blog.pickmytrade.trade/best-tradingview-indicators-strategies/) |

## Part 2 — Top 21~35 (표준 지표 · 강력 검증 티어)

| # | 알고리즘 (저자) | 유형 | 핵심 아이디어 | 성과(참고) | 검증 | 인기 | 링크 |
|---|---|---|---|---|---|---|---|
| 21 | **ADX / DMI** (내장) | 추세강도 | +DI/-DI 방향 + ADX 강도. >25 강추세, <20 레인지 모드 전환 | 추세/레인지 판별 핵심 | ★★★★★ | 매우높음 | [🔗](https://www.tradingview.com/scripts/averagedirectionalindex/) |
| 22 | **Stochastic Oscillator** (내장) | 모멘텀 | 14,3,3 %K/%D 크로스, <20 과매도/>80 과매수 반전 | 조기 신호(ATR 필터 권장) | ★★★★★ | 매우높음 | [🔗](https://investingengineer.com/10-best-tradingview-indicators-for-beginners/) |
| 23 | **Stochastic RSI** (내장) | 모멘텀 | RSI에 Stochastic 적용, 더 민감한 과매수/과매도 | 진입 트리거로 인기 | ★★★★☆ | 높음 | [🔗](https://www.tradingview.com/scripts/page-53/) |
| 24 | **Bollinger Bands** (내장) | 변동성 | 20SMA ±2SD 밴드로 변동성·평균회귀·돌파 판단 | 표준 변동성 도구 | ★★★★★ | 최상위 | [🔗](https://tradenation.com/en-gb/articles/tradingview-indicators/) |
| 25 | **Fibonacci Retracement (Auto)** (내장) | S&R | 23.6/38.2/50/61.8% 되돌림 레벨, 컨플루언스 존 | 진입·스톱 배치 표준 | ★★★★★ | 최상위 | [🔗](https://tradenation.com/en-gb/articles/tradingview-indicators/) |
| 26 | **Pivot Points (S/R)** (내장) | S&R | 일/주 피벗(S1·S2·R1·R2)으로 전환점 예측 | 전환점 참조 | ★★★★☆ | 높음 | [🔗](https://blog.pickmytrade.trade/best-tradingview-indicators/) |
| 27 | **EMA Ribbon (9/21/50/200)** (내장) | 추세추종 | 다중 EMA 배열·크로스로 추세 강도·방향 시각화 | 골든/데드크로스 20% 연수익 변형 | ★★★★★ | 매우높음 | [🔗](https://blog.pickmytrade.trade/best-tradingview-indicators-2025-backtest-results/) |
| 28 | **Hull Moving Average (HMA)** | 추세추종 | 지연 최소화한 부드러운 MA, 추세 조기 포착 | 반응성 우수 | ★★★★☆ | 높음 | [🔗](https://www.liberatedstocktrader.com/best-tradingview-indicators/) |
| 29 | **Chandelier Exit** (Le Beau/Elder) | 변동성/청산 | ATR 기반 트레일링 스톱으로 추세 청산점 계산 | 리스크 청산 표준 | ★★★★☆ | 높음 | [🔗](https://www.tradingview.com/support/solutions/43000773013-chandelier-exit/) |
| 30 | **Donchian Channels** (내장) | 추세/돌파 | N기간 고저 채널 돌파(터틀 시스템 기반) | 돌파 추종 클래식 | ★★★★☆ | 높음 | [🔗](https://www.liberatedstocktrader.com/best-tradingview-indicators/) |
| 31 | **Keltner Channels** (내장) | 변동성 | EMA ± ATR 채널, 추세·돌파·스퀴즈 판단 | BB와 스퀴즈 결합 | ★★★★☆ | 높음 | [🔗](https://blog.pickmytrade.trade/best-tradingview-indicators-2025-backtest-results/) |
| 32 | **On-Balance Volume (OBV)** (내장) | 볼륨 | 누적 거래량으로 매집/분산 추적, 다이버전스 | 스윙 볼륨 확인 | ★★★★☆ | 높음 | [🔗](https://www.liberatedstocktrader.com/best-tradingview-indicators/) |
| 33 | **Money Flow Index (MFI)** (내장) | 볼륨/모멘텀 | 가격+거래량 결합 RSI, 자금흐름 과매수/과매도 | 볼륨 가중 모멘텀 | ★★★★☆ | 높음 | [🔗](https://www.liberatedstocktrader.com/best-tradingview-indicators/) |
| 34 | **CCI (Commodity Channel Index)** (내장) | 모멘텀 | 평균가 대비 편차로 과매수/과매도·추세강도 | 반전·추세 판단 | ★★★★☆ | 높음 | [🔗](https://www.liberatedstocktrader.com/best-tradingview-indicators/) |
| 35 | **Williams %R** (내장) | 모멘텀 | 최근 고저 대비 종가 위치, -20/-80 과매수·과매도 | 조기 반전 신호 | ★★★★☆ | 높음 | [🔗](https://investingengineer.com/10-best-tradingview-indicators-for-beginners/) |

## Part 3 — Top 36~50 (전문/복합 · ML/SMC 확장 티어)

| # | 알고리즘 (저자) | 유형 | 핵심 아이디어 | 성과(참고) | 검증 | 인기 | 링크 |
|---|---|---|---|---|---|---|---|
| 36 | **VuManChu Cipher A/B** | 복합/모멘텀 | WaveTrend+MFI+다이버전스+신호 통합 크립토 인기 대시보드 | 크립토 스캘핑 인기 | ★★★★☆ | 매우높음 | [🔗](https://www.tradingview.com/scripts/page-53/) |
| 37 | **Machine Learning: kNN** (커뮤니티) | ML/분류 | k-최근접이웃으로 과거 패턴 유사도 기반 방향 예측 | ML 실증 | ★★★☆☆ | 높음 | [🔗](https://supa.is/article/tradingview-pine-script-wizards-2026-best-community-indicators) |
| 38 | **Nadaraya-Watson Envelope** (LuxAlgo) | ML/평균회귀 | 커널 회귀로 부드러운 동적 S/R 엔벨로프, 반전 존 | 반전 존 인기 | ★★★★☆ | 매우높음 | [🔗](https://www.luxalgo.com/blog/code-tradingview-indicators-with-quant-the-best-ai-for-pine-script-2/) |
| 39 | **Order Blocks / FVG (커뮤니티)** | SMC | 기관 주문블록·공정가치갭 자동 표시, ICT 진입존 | 프롭 진입존 인기 | ★★★★☆ | 매우높음 | [🔗](https://www.luxalgo.com/blog/smart-money-concepts-indicator-now-reaching-1-on-tradingview/) |
| 40 | **Market Structure BOS/CHoCH (커뮤니티)** | SMC | 구조 붕괴(BOS)·성격변화(CHoCH) 자동 라벨링 | 추세 전환 포착 | ★★★★☆ | 매우높음 | [🔗](https://www.luxalgo.com/blog/smart-money-concepts-indicator-now-reaching-1-on-tradingview/) |
| 41 | **Technical Ratings** (TradingView) | 종합 | MA+오실레이터 11종 종합 매수/매도 등급 히스토그램 | 종합 스코어 | ★★★★★ | 높음 | [🔗](https://www.liberatedstocktrader.com/best-tradingview-indicators/) |
| 42 | **Awesome Oscillator (AO)** (내장) | 모멘텀 | 5/34 SMA 차이 히스토그램, 모멘텀 전환·새터데이 | 모멘텀 확인 | ★★★★☆ | 높음 | [🔗](https://www.liberatedstocktrader.com/best-tradingview-indicators/) |
| 43 | **Parabolic SAR** (내장) | 추세/청산 | 가속계수 기반 점으로 추세 방향·트레일링 스톱 | 추세 청산 클래식 | ★★★★☆ | 높음 | [🔗](https://tradenation.com/en-gb/articles/tradingview-indicators/) |
| 44 | **Choppiness / Efficiency Ratio Regime** (커뮤니티) | 종합/필터 | ADX+효율비율+Choppiness 2/3 투표로 추세/레인지 분류 | 국면 필터 | ★★★★☆ | 높음 | [🔗](https://www.tradingview.com/scripts/averagedirectionalindex/) |
| 45 | **Elliott Wave (Auto)** (커뮤니티) | 패턴 | W3-W4-W5 파동 구조+피보나치 되돌림 진입 | 파동 트레이더용 | ★★★☆☆ | 높음 | [🔗](https://www.tradingview.com/scripts/page-53/) |
| 46 | **SuperTrend + ADX + StochRSI 전략** (커뮤니티) | 복합 | 다중MA 추세+ADX 강도필터+StochRSI 트리거 풀백 진입 | 정직한 통계(WR/PF/DD) 표시 | ★★★★☆ | 높음 | [🔗](https://www.tradingview.com/scripts/page-53/) |
| 47 | **Multi-Timeframe RSI Dashboard** (ChrisMoody) | 모멘텀/MTF | 여러 타임프레임 RSI 동시 표시로 오신호 감소 | EUR/USD 65% 승률(고볼륨) | ★★★★★ | 매우높음 | [🔗](https://lunefi.com/blog/best-tradingview-indicators-2026-backtested-win-rates) |
| 48 | **BigBeluga Commodity Trend Reactor** (BigBeluga) | 추세/모멘텀 | CCI 기반 오실레이터+자동 트레일링 스톱·반전 마커 | 명확한 추세 확인 | ★★★★☆ | 매우높음 | [🔗](https://blog.pickmytrade.trade/best-tradingview-indicators-strategies/) |
| 49 | **Flux Charts Supply/Demand** (Flux Charts) | S&R/MTF | 다중TF 공급/수요 존+가격행동+자동 신호 통합 시스템 | 존 기반 진입 | ★★★★☆ | 높음 | [🔗](https://blog.pickmytrade.trade/best-tradingview-indicators-strategies/) |
| 50 | **PineCoders Backtesting Template** (PineCoders) | 도구/검증 | 커스텀 전략을 Strategy Tester로 표준 검증하는 템플릿 | 검증 인프라 표준 | ★★★★★ | 높음 | [🔗](https://blog.pickmytrade.trade/best-tradingview-indicators-strategies/) |

---

## 핵심 아이디어 카테고리별 정리

### 1. 추세추종 (Trend-Following)
SuperTrend·EMA Ribbon·Golden/Death Cross·Hull MA·Donchian·Parabolic SAR·Ichimoku. 공통 프레임은 "추세 방향 확정 → 순방향 진입 → 반대 신호 시 청산". 단독 사용 시 레인지에서 휩쏘가 최대 약점이라 ADX·상위 타임프레임 필터를 얹는 것이 정석.

### 2. 모멘텀/오실레이터 (Momentum)
RSI·MACD·Stochastic·StochRSI·CCI·Williams %R·AO·WaveTrend·QQE Mod·MFI. 과매수/과매도와 다이버전스가 공통 엔진. 이들은 방향(bias)을 만드는 도구가 아니라 **이미 정한 추세 안에서 진입 타이밍**을 잡는 데 최적. 여러 개를 겹치면 같은 정보를 반복해 모순 신호만 늘어나므로 카테고리당 1개 권장.

### 3. 변동성 (Volatility)
ATR·Bollinger Bands·Keltner Channels·Chandelier Exit·Squeeze Momentum. 변동성 수축→팽창 전환(스퀴즈)을 노리거나, 스톱·포지션 사이징을 정규화하는 리스크 관리 핵심.

### 4. 볼륨 (Volume)
Volume Profile HD·VWAP·OBV·MFI. 실제 유동성이 있는 가격대와 기관 벤치마크를 파악해 다른 신호의 확인 레이어로 사용. 값 영역(Value Area) 안 체결 선호, 고거래량 노드 돌파 시 시장가.

### 5. 시장구조/스마트머니 (SMC)
LuxAlgo SMC·Zeiierman·Order Blocks/FVG·BOS/CHoCH. ICT 이론(기관 주문흐름)을 자동화. 지연 오실레이터를 버리고 순수 가격행동으로 전환하는 흐름이 프롭펌 챌린지 씬에서 급부상, LuxAlgo SMC가 SuperTrend·Squeeze Momentum을 추월하며 #1 근접.

### 6. 머신러닝 (ML)
Lorentzian Classification·WaveTrend 3D·kNN·Nadaraya-Watson (jdehorty·LuxAlgo). Pine 내에서 거리기반 분류·커널 회귀로 국면 매칭. ML 스크립트 확산의 기폭제.

### 7. 종합/복합 (Composite)
Technical Ratings·Regime Classifier·VuManChu Cipher·복합 전략(SuperTrend+ADX+StochRSI). 추세+모멘텀+변동성+세션 필터를 순차 게이트로 결합해 오신호를 거르는 방향.

---

## 검증·백테스트 시 유의사항 (출처 종합)
- **평가 우선순위**: Profit Factor(1.5+) → Max Drawdown(<20%) → 총 거래수(200+) → 국면별 일관성 → R:R(1.5+) → Sharpe(1.0+). 승률은 마지막에 본다.
- **커브피팅 경고**: 75% 승률·5:1 R:R·매끄러운 자산곡선은 거의 과최적화 신호. 현실적 전략은 **45~65% 승률 + 1.5~3:1 R:R** + 상당한 드로다운 구간 존재.
- **검증 절차**: 인샘플(70%)/아웃오브샘플(30%) 분리, 커미션·슬리피지 반영, 강세·약세·횡보·고변동·저변동 등 다양한 국면에서 테스트. 30~90일 롤링 라이브 검증으로 순기대값 측정.
- **현실**: TradingView 15만+ 스크립트 중 꾸준히 수익 나는 것은 **20~30개 수준**으로 평가. 클래식 2~3개 + 가격행동 조합 권장. 프로는 3~5개 이하만 사용(추세 1 + 모멘텀 1 + 타이밍 1).
- **품질 필터**: Pine Wizard(Hall of Fame, 2026년 3월 기준 28명)와 Editor's Pick를 1차 필터로 활용.

## 주요 저자·프로필
- **LazyBear** — Squeeze Momentum·WaveTrend·3-Bar Reversal (역대 최다 인기): https://www.tradingview.com/u/LazyBear/
- **KivancOzbilgic** — SuperTrend 등 ATR 추세 도구: https://www.tradingview.com/u/KivancOzbilgic/
- **LuxAlgo** — SMC·Dynamic S/R·Nadaraya-Watson (Wizard 유일 팀, 80만+): https://www.luxalgo.com/
- **jdehorty** — Lorentzian Classification·WaveTrend 3D (Pine ML 선구자)
- **ChrisMoody** — Multi-TF RSI·MACD 강화판
- **Zeiierman / BigBeluga / Flux Charts** — SMC·모멘텀·공급수요 프리미엄

## 참조 링크 모음
- Pine Wizards Hall of Fame: https://www.tradingview.com/pine-wizards/
- LuxAlgo SMC #1 분석: https://www.luxalgo.com/blog/smart-money-concepts-indicator-now-reaching-1-on-tradingview/
- Pine Wizards 2026 가이드: https://supa.is/article/tradingview-pine-script-wizards-2026-best-community-indicators
- 2026 백테스트 승률 리뷰: https://lunefi.com/blog/best-tradingview-indicators-2026-backtested-win-rates
- 103개 무료 지표 테스트: https://www.liberatedstocktrader.com/best-tradingview-indicators/
- 초보 10대 지표 셋업: https://investingengineer.com/10-best-tradingview-indicators-for-beginners/
- 14대 자주 쓰는 지표: https://tradenation.com/en-gb/articles/tradingview-indicators/
- TradingView 백테스팅 가이드: https://www.quantum-algo.com/blog/guides/tradingview-backtesting-complete-guide/
- 인기 전략 Top3 검증: https://wemastertrade.com/the-most-popular-tradingview-strategy/
- 커뮤니티 스크립트 라이브러리: https://www.tradingview.com/scripts/
