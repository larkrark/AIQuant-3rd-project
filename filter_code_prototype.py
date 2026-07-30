import pandas as pd
import numpy as np
import os

# ==========================================
# 1. Configuration (AGENTS.md R1: 숫자 하드코딩 금지)
# 모든 임계값, 계산 기준, 타겟 분위수는 이곳에서 관리합니다.
# ==========================================
class Config:
    # 분포 확인용 타겟 백분위수 (5%, 10%, 25%, 50%, 75%)
    TARGET_QUANTILES = [0.05, 0.10, 0.25, 0.50, 0.75]
    
    # 분석 대상 컬럼
    COL_MARKET = 'market'
    COL_THEME = 'theme'
    COL_ADTV90 = 'adtv90'
    COL_QUICK_RATIO = 'quick_ratio'
    
    # 상태 코드 (R9: 시장 상태코드 6종 고정)
    STATUS_DATA_MISSING = 'DATA_MISSING'

# ==========================================
# 2. Data Loader Module
# ==========================================
def load_data(file_path: str) -> pd.DataFrame:
    """
    CSV 또는 MD 파일을 읽어 DataFrame으로 반환합니다.
    추후 DB 연동이나 API 호출 등으로 쉽게 교체(확장)할 수 있습니다.
    """
    if not os.path.exists(file_path):
        print(f"Warning: {file_path} 파일이 존재하지 않아 테스트용 빈 데이터프레임을 생성합니다.")
        return pd.DataFrame()
        
    ext = file_path.split('.')[-1].lower()
    
    if ext == 'csv':
        df = pd.read_csv(file_path)
    elif ext == 'md':
        # 마크다운 표 형태를 파싱하기 위한 간단한 로직 (가벼운 전처리)
        # 구분선(|---|)을 제외하고 읽어옵니다.
        df = pd.read_csv(file_path, sep='|', skipinitialspace=True).dropna(axis=1, how='all')
        df = df[~df.iloc[:, 0].astype(str).str.contains('---')]
        df.columns = df.columns.str.strip()
    else:
        raise ValueError("지원하지 않는 파일 형식입니다. (csv 또는 md 권장)")
        
    return df

# ==========================================
# 3. Distribution Analyzer (하한 후보 선별)
# ==========================================
def calculate_distribution(df: pd.DataFrame, target_col: str, group_col: str) -> pd.DataFrame:
    """
    특정 컬럼(target_col)의 값을 그룹(group_col)별로 묶어 분위수를 계산합니다.
    AGENTS.md R6에 따라 결측치(NA)는 0으로 채우지 않고 분석에서 자연스럽게 제외(pd.Series.quantile 기본 동작)합니다.
    """
    if df.empty or target_col not in df.columns or group_col not in df.columns:
        return pd.DataFrame()

    # 데이터 타입 변환 (문자열로 섞여 있을 경우를 대비)
    df[target_col] = pd.to_numeric(df[target_col], errors='coerce')
    
    # 그룹별로 타겟 분위수 계산
    distribution_results = []
    grouped = df.groupby(group_col)
    
    for name, group in grouped:
        # NA 제외 후 계산
        valid_data = group[target_col].dropna() 
        quantiles = valid_data.quantile(Config.TARGET_QUANTILES).to_dict()
        
        result_row = {group_col: name, 'valid_count': len(valid_data)}
        # 소수점 포맷팅 추가 (예: 25% -> q_0.25)
        result_row.update({f"q_{q}": quantiles.get(q, np.nan) for q in Config.TARGET_QUANTILES})
        
        distribution_results.append(result_row)
        
    return pd.DataFrame(distribution_results)

# ==========================================
# 4. Main Execution
# ==========================================
def run_pipeline(adtv_data_path: str, quick_ratio_data_path: str):
    print("--- 퀀트 인덱스 엔진 가동 ---")
    
    # 1. 데이터 로드
    df_adtv = load_data(adtv_data_path)
    df_qr = load_data(quick_ratio_data_path)
    
    # 2. ADTV90 분포 분석 (시장별 KR/US)
    print("\n[산출물 1] 시장별 ADTV90 하한 후보 분포:")
    df_adtv_dist = calculate_distribution(df_adtv, Config.COL_ADTV90, Config.COL_MARKET)
    print(df_adtv_dist.to_string(index=False) if not df_adtv_dist.empty else "데이터 없음")
    
    # 3. 당좌비율 분포 분석 (테마별)
    print("\n[산출물 2] 테마별 당좌비율 하한 후보 분포:")
    df_qr_dist = calculate_distribution(df_qr, Config.COL_QUICK_RATIO, Config.COL_THEME)
    print(df_qr_dist.to_string(index=False) if not df_qr_dist.empty else "데이터 없음")
    
    # 참고: 수주산업(방산, 중공업 등)의 특성으로 당좌비율 왜곡이 있을 수 있으므로
    # 위 출력된 25%나 5% 분위수를 기준으로 보수적인 예외 하한값을 팀 논의에 부치면 됩니다.

if __name__ == "__main__":
    # 실제 환경에 맞게 경로를 수정하여 실행합니다.
    run_pipeline("data/adtv90_distribution.csv", "data/quick_ratio_distribution.csv")