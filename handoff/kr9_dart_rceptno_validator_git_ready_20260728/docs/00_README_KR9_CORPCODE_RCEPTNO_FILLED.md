# KR9 DART corp_code / rcept_no 검증자 전달용 보정 패키지

생성시각: 2026-07-28 06:16:15

## 목적
업로드된 KR9 원자료-rcept_no 매핑 CSV들의 빈 회사 고유번호(corp_code)를 보강하고, rcept_no가 있는 행에는 검증자가 직접 열 수 있는 공식 DART URL을 붙였습니다.

## 수행
- 기존 CSV 행 수는 변경하지 않았습니다.
- `security_id` 기준 KR9 회사 corp_code를 채웠습니다.
- `rcept_no`가 있는 행에는 `official_dart_url = https://dart.fss.or.kr/dsaf001/main.do?rcpNo=<rcept_no>`를 생성했습니다.
- `source_url`이 비어 있고 `rcept_no`가 있는 행은 같은 공식 URL로 채웠습니다.
- `rcept_no`가 없는 행은 임의로 채우지 않고 `REVIEW_NO_RCEPT_NO`로 남겼습니다.

## 수행하지 않은 것
- OpenDART API 재호출
- API key 사용
- theme revenue 확정
- backlog 확정
- role_grade/evidence_grade/gate_status 부여
- 최종 편입판정

## 검증자에게 우선 전달할 파일
- `KR9_DART_SOURCE_FILE_TO_RCPNO_MAP_FINAL_CANDIDATES_LATEST_CORPCODE_URL_FILLED.csv`
- `KR9_FINAL_CANDIDATES_OFFICIAL_DART_URL_ROWS_FOR_VALIDATOR.csv`
- `KR9_COMPANY_CORPCODE_REFERENCE_FILLED.csv`
- `KR9_CORPCODE_RCEPTNO_FILL_SUMMARY.csv`
