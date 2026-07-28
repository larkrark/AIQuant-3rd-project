"""
file_status: PILOT_IMPLEMENTATION
method_status: APPROVAL_PENDING
merge_status: NOT_FOR_OFFICIAL_MERGE_YET
purpose: 절대 ADTV90 하한 선택지 검토용 (P10 임계값과 절대하한 병행/대체 검토)
"""

import pandas as pd
import numpy as np
import json

class CustomIndexEngine:
    def __init__(self, thresholds_json_path=None, adtv_threshold_kr=None, adtv_threshold_us=None, cr_threshold=1.0):
        # JSON 파일을 통한 P10 임계값 로드를 우선시하되, 테스트용 절대금액 입력도 지원
        if thresholds_json_path:
            with open(thresholds_json_path, 'r') as f:
                self.adtv_threshold = json.load(f)
        else:
            self.adtv_threshold = {'KR': adtv_threshold_kr, 'US': adtv_threshold_us}
            
        self.cr_threshold = cr_threshold
        # R11: 테마 1:1:1, 지역 50:50 -> 6셀 각 1/6 비중 구조
        self.cell_target_weight = 1.0 / 6.0 

    def calculate_adtv90(self, price_df, observation_end_date=None):
        """
        [인디케이터 A-1] ADTV90 산출 모듈
        - R4(PIT): 과거 90일 관측치만 사용 및 기준일 검증
        """
        df = price_df.copy()
        
        # PIT 기준일 명시적 적용
        if observation_end_date:
            df = df[df['date'] <= observation_end_date]
            
        # 개장일 그리드에서 상장되지 않은(NOT_LISTED) 상태 제외
        if 'status' in df.columns:
            df = df[df['status'] != 'NOT_LISTED']
        
        # 1. 거래대금(Trading Value) 재구성 (R5)
        if 'trading_value_krx' in df.columns:
            df['trading_value'] = np.where(
                df['trading_value_krx'].notnull(),
                df['trading_value_krx'],
                df['close'] * df['volume']
            )
        else:
            df['trading_value'] = df['close'] * df['volume']

        # 2. 상태코드별 예외 처리 (R6)
        df.loc[df['status'].isin(['TRADING_HALT', 'ZERO_VOLUME']), 'trading_value'] = 0
        df.loc[df['status'] == 'DATA_MISSING', 'trading_value'] = np.nan

        # 3. 90거래일 롤링 윈도우 및 관측일수 계산 (PIT)
        df = df.sort_values(by=['security_id', 'date'])
        
        # ADTV90 계산
        df['adtv90'] = df.groupby('security_id')['trading_value'].transform(
            lambda x: x.rolling(window=90, min_periods=1).mean()
        )
        # ADTV 관측일수 계산 (90일 미만 관측치 분리용)
        df['adtv_observation_count'] = df.groupby('security_id')['trading_value'].transform(
            lambda x: x.rolling(window=90, min_periods=1).count()
        )
        
        return df

    def diagnostic_macd(self, price_df, is_weekly_data=False):
        """
        [인디케이터 A-2] MACD 진단 모듈
        """
        # 입력 데이터가 주봉으로 변환되어 있는지 명시적 확인
        if not is_weekly_data:
            print("Warning: MACD 산출을 위해서는 입력 자료가 주봉이어야 하거나 별도 전처리가 필요합니다.")
            
        df = price_df.copy()
        df = df.sort_values(by=['security_id', 'date'])
        
        # 주봉 12/26/9 MACD 산출
        ema_12 = df.groupby('security_id')['adj_close'].transform(lambda x: x.ewm(span=12, adjust=False).mean())
        ema_26 = df.groupby('security_id')['adj_close'].transform(lambda x: x.ewm(span=26, adjust=False).mean())
        
        df['macd_line'] = ema_12 - ema_26
        df['macd_signal'] = df.groupby('security_id')['macd_line'].transform(lambda x: x.ewm(span=9, adjust=False).mean())
        df['macd_osc'] = df['macd_line'] - df['macd_signal']
        
        return df

    def apply_gates(self, universe_df, selection_date=None):
        """
        후보 선별 및 리스크 분석 (하한 게이트 통과 판정)
        - 통과하지 못한 종목의 탈락 사유(원장)를 보존함
        """
        df = universe_df.copy()
        
        # 데이터 가용일(Data Available Date) 컷오프 확인
        if selection_date and 'data_available_date' in df.columns:
            df = df[df['data_available_date'] <= selection_date]
        
        # 1. 테마 노출도 게이트
        pass_theme = df['theme_exposure'].isin(['DIRECT', 'CORE_SUPPORT']) 
        
        # 2. 유동성 게이트 (ADTV90 >= 하한 L_m 및 관측일수 충족)
        df['adtv_threshold'] = df['market'].map(self.adtv_threshold)
        pass_liquidity = (df['adtv90'] >= df['adtv_threshold']) & (df['adtv_observation_count'] >= 90)
        
        # 3. 재무건전성 게이트 (current_ratio -> quick_ratio로 정정)
        pass_financial = df['quick_ratio'] >= self.cr_threshold
        
        # 탈락 사유 플래그 보존
        df['THEME_GATE_FAIL'] = ~pass_theme
        df['LIQUIDITY_GATE_FAIL'] = ~pass_liquidity
        df['FINANCIAL_GATE_FAIL'] = ~pass_financial
        
        df['fail_count'] = df[['THEME_GATE_FAIL', 'LIQUIDITY_GATE_FAIL', 'FINANCIAL_GATE_FAIL']].sum(axis=1)
        df['MULTIPLE_GATE_FAIL'] = df['fail_count'] >= 2
        
        # 최종 통과 여부 기록
        df['gate_passed'] = df['fail_count'] == 0
        
        # 탈락한 종목도 원장에 남기기 위해 원본 전체를 반환
        return df

    def construct_portfolio(self, universe_df):
        """
        포트폴리오 비중 구성
        """
        # 게이트를 통과한 종목만 필터링하여 비중 배정
        portfolio = universe_df[universe_df['gate_passed']].copy()
        
        # 셀(테마 + 시장) 별 종목 수 계산
        portfolio['cell_count'] = portfolio.groupby(['primary_theme', 'market'])['security_id'].transform('count')
        
        # 동일가중(Equal Weight) 적용
        portfolio['weight'] = self.cell_target_weight / portfolio['cell_count']
        
        # R10: 비중 합계 1.0 검산 로직
        total_weight = portfolio['weight'].sum()
        if not np.isclose(total_weight, 1.0, atol=1e-5):
            raise ValueError(f"CRITICAL ERROR [R10 위반]: 비중 합계가 {total_weight}입니다. (1.0이어야 함). 6셀 중 비어있는 셀이 존재하는지 확인하세요.")
            
        return portfolio

# --- 실행 예시 (Mock Data 기반) ---
if __name__ == "__main__":
    # 임계값 세팅 (절대금액 방식)
    # 실제 환경에서는 thresholds_json_path='outputf1/thresholds.json' 사용 권장
    engine = CustomIndexEngine(adtv_threshold_kr=1000000000, adtv_threshold_us=5000000, cr_threshold=1.0)
    
    # 1. 가격 데이터 로드 및 유동성 인디케이터 산출 (PIT 기준일 적용)
    # price_df = pd.read_csv('daily_market_state.csv') 
    # price_df = engine.calculate_adtv90(price_df, observation_end_date='2023-12-31')
    # price_df = engine.diagnostic_macd(price_df, is_weekly_data=True)
    
    # 2. 유니버스 데이터 병합 (quick_ratio 사용 필수)
    # universe_df = pd.merge(seed_basket_df, price_df_latest_date, on='security_id')
    
    # 3. 리스크/선별 게이트 판정 (선정일 기준, 결과 원장 보존)
    # annotated_universe = engine.apply_gates(universe_df, selection_date='2024-01-05')
    
    # 4. 포트폴리오 산출 (R11 6셀 1:1:1 반영 및 R10 검산)
    # final_portfolio = engine.construct_portfolio(annotated_universe)
    # final_portfolio.to_csv('final_portfolio.csv', index=False)
    # annotated_universe.to_csv('rejection_ledger.csv', index=False) # 탈락사유 원장 저장
