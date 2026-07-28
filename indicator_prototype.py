import pandas as pd
import numpy as np

class CustomIndexEngine:
    def __init__(self, adtv_threshold_kr, adtv_threshold_us, cr_threshold):
        # 결정로그 및 분표포에 따라 확정될 임계값 (config.py 역할)
        self.adtv_threshold = {'KR': adtv_threshold_kr, 'US': adtv_threshold_us}
        self.cr_threshold = cr_threshold
        # R11: 테마 1:1:1, 지역 50:50 -> 6셀 각 1/6 비중 구조
        self.cell_target_weight = 1.0 / 6.0 

    def calculate_adtv90(self, price_df):
        """
        [인디케이터 A-1] ADTV90 산출 모듈
        - R4(PIT): 과거 90일 관측치만 사용
        - R5: KRX 공식 거래대금 우선, 없으면 원종가 x 실제거래량 (수정주가 사용 금지)
        - R6: DATA_MISSING은 NA 유지, ZERO_VOLUME 및 TRADING_HALT는 0 반영
        """
        df = price_df.copy()
        
        # 1. 거래대금(Trading Value) 재구성 (R5)
        # trading_value_krx 컬럼이 존재하고 결측치가 아니면 우선 사용, 아니면 close * volume
        if 'trading_value_krx' in df.columns:
            df['trading_value'] = np.where(
                df['trading_value_krx'].notnull(),
                df['trading_value_krx'],
                df['close'] * df['volume']
            )
        else:
            df['trading_value'] = df['close'] * df['volume']

        # 2. 상태코드별 예외 처리 (R6)
        # TRADING_HALT, ZERO_VOLUME -> 0으로 반영하여 ADTV를 깎음
        df.loc[df['status'].isin(['TRADING_HALT', 'ZERO_VOLUME']), 'trading_value'] = 0
        # DATA_MISSING -> NA로 유지하여 분모에서 제외
        df.loc[df['status'] == 'DATA_MISSING', 'trading_value'] = np.nan

        # 3. 90거래일 롤링 윈도우 계산 (PIT)
        df = df.sort_values(by=['security_id', 'date'])
        df['adtv90'] = df.groupby('security_id')['trading_value'].transform(
            lambda x: x.rolling(window=90, min_periods=1).mean()
        )
        return df

    def diagnostic_macd(self, price_df):
        """
        [인디케이터 A-2] MACD 진단 모듈
        - 인디케이터 역할분류표 명시: 판정에 사용하지 않고 단순 저장/관찰(진단)용
        """
        df = price_df.copy()
        df = df.sort_values(by=['security_id', 'date'])
        
        # 주봉 12/26/9 MACD 산출 (여기서는 일간 데이터를 주간으로 변환했다고 가정)
        ema_12 = df.groupby('security_id')['adj_close'].transform(lambda x: x.ewm(span=12, adjust=False).mean())
        ema_26 = df.groupby('security_id')['adj_close'].transform(lambda x: x.ewm(span=26, adjust=False).mean())
        
        df['macd_line'] = ema_12 - ema_26
        df['macd_signal'] = df.groupby('security_id')['macd_line'].transform(lambda x: x.ewm(span=9, adjust=False).mean())
        df['macd_osc'] = df['macd_line'] - df['macd_signal']
        
        return df

    def apply_gates(self, universe_df):
        """
        후보 선별 및 리스크 분석 (하한 게이트 통과 판정)
        - R7: 테마관련성, 유동성, 재무건전성을 분리하여 독립 판정
        """
        df = universe_df.copy()
        
        # 1. 테마 노출도 게이트 (직접, 핵심지원 등)
        # seed_basket 및 판정 결과 기준
        pass_theme = df['theme_exposure'].isin(['DIRECT', 'CORE_SUPPORT']) 
        
        # 2. 유동성 게이트 (ADTV90 >= 하한 L_m)
        df['adtv_threshold'] = df['market'].map(self.adtv_threshold)
        pass_liquidity = df['adtv90'] >= df['adtv_threshold']
        
        # 3. 재무건전성 게이트 (당좌비율 >= 하한)
        pass_financial = df['current_ratio'] >= self.cr_threshold
        
        # 게이트 종합 판정
        df['gate_passed'] = pass_theme & pass_liquidity & pass_financial
        
        return df[df['gate_passed']].copy()

    def construct_portfolio(self, eligible_df):
        """
        포트폴리오 비중 구성
        - R11: 테마 1:1:1, 6셀(우주/AI/에너지 x 한/미), 1/6 구조 배정
        - R10: 배정 후 비중 합계 1.0 검산
        """
        portfolio = eligible_df.copy()
        
        # 셀(테마 + 시장) 별 종목 수 계산
        portfolio['cell_count'] = portfolio.groupby(['primary_theme', 'market'])['security_id'].transform('count')
        
        # 동일가중(Equal Weight) 적용: (1/6) / 셀 내 통과 종목 수
        portfolio['weight'] = self.cell_target_weight / portfolio['cell_count']
        
        # R10: 비중 합계 1.0 검산 로직
        total_weight = portfolio['weight'].sum()
        if not np.isclose(total_weight, 1.0, atol=1e-5):
            raise ValueError(f"CRITICAL ERROR [R10 위반]: 비중 합계가 {total_weight}입니다. (1.0이어야 함). 6셀 중 비어있는 셀이 존재하는지 확인하세요.")
            
        return portfolio

# --- 실행 예시 (Mock Data 기반) ---
if __name__ == "__main__":
    # 임계값 세팅 (예시 수치)
    engine = CustomIndexEngine(adtv_threshold_kr=1000000000, adtv_threshold_us=5000000, cr_threshold=1.0)
    
    # 1. 가격 데이터 로드 및 유동성 인디케이터 산출
    # price_df = pd.read_csv('prices.csv') 
    # price_df = engine.calculate_adtv90(price_df)
    # price_df = engine.diagnostic_macd(price_df)
    
    # 2. 유니버스 데이터 병합 (ADTV, 재무데이터, 테마 노출도 조인)
    # universe_df = pd.merge(seed_basket_df, price_df_latest_date, on='security_id')
    
    # 3. 리스크/선별 게이트 통과
    # passed_universe = engine.apply_gates(universe_df)
    
    # 4. 포트폴리오 산출 (R11 6셀 1:1:1 반영 및 R10 검산)
    # final_portfolio = engine.construct_portfolio(passed_universe)
    # final_portfolio.to_csv('final_portfolio.csv', index=False)