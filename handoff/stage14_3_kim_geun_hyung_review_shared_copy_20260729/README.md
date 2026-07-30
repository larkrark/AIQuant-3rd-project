# Stage 14-3 김근형 독립 원자료 검토 공유용 사본

## 1. 목적

이 폴더는 미국 공시자료의 출처·시점·회사 식별정보 및 정정계보 검증 작업 중
김근형이 수행한 원자료 검토 결과를 팀 저장소에서 확인할 수 있도록 만든 공유용 사본이다.

로컬에서 완료·동결한 원본 검토 결과의 개인 PC 절대경로를 제거했으며,
원본 동결본 자체를 수정하거나 지수 산출 프로그램 입력자료로 승격하지 않았다.

## 2. 검토 범위와 상태

- 전체 검토대상: 42건
- CIK 검토대상: 27건
- 날짜 의미 검토대상: 15건
- 김근형 원자료 검토: 완료 및 로컬 동결
- 공식 기준자료 승인: 미완료
- PIT 운영규칙 승인: 미완료
- 지수 산출규칙 자료 반영: 미수행
- 지수 산출 프로그램 입력자료 승격: 미수행
- 추주원 독립 원자료 검토 및 동결: 별도 진행
- 김근형·추주원 결과 대조: 미수행

이 공유본은 김근형의 독립 검토 결과를 전달하기 위한 것이며,
팀 승인·최종 판정·자동 적용을 의미하지 않는다.

## 3. 주요 파일

### 검토 결과

- `data/USER_REVIEW_RESULT_TABLE_WORKING_NOT_APPROVED_NOT_PROMOTED.csv`
  - 42개 검토대상의 원자료 확인값·판정상태·미결사항을 기록한 결과표
- `data/SOURCE_EVIDENCE_REVIEW_JUDGMENT_TABLE_WORKING_NOT_APPROVED_NOT_PROMOTED.csv`
  - 확인질문·관찰·판정·남은 확인사항을 포함한 사람 검토 판정표

### 확인용 HTML 뷰어

- `viewer/260729_김근형_독립원자료검토_탭형뷰어_v0.1.html`
  - 결과 CSV를 탭·검색·필터 방식으로 확인하는 로컬 뷰어
  - 검토 데이터는 HTML에 내장되어 있지 않음
  - 브라우저에서 연 뒤 결과표 CSV를 사용자가 직접 불러와야 함

### 검증·통제 기록

- `controls/USER_REVIEW_COMPLETION_CHECKPOINT.csv`
- `controls/USER_REVIEW_COMPLETION_FREEZE_MANIFEST.csv`
- `controls/SHARED_COPY_TRANSFORMATION_LOG.csv`
- `controls/PATH_HASH_SEMANTICS_CORRECTION_LOG.csv`
- `controls/VIEWER_COPY_MANIFEST.csv`
- `controls/SOURCE_FREEZE_SHA256SUMS_ORIGINAL.txt`

원본 동결 해시와 로컬 경로를 제거한 공유본 해시는 서로 다른 역할을 가진다.

- 원본 동결 해시: 로컬 동결본의 무결성 확인
- 공유본 해시: Git 공유 파일의 무결성 확인

두 해시는 `SHARED_COPY_TRANSFORMATION_LOG.csv`에서 파일별로 연결한다.

## 4. 로컬 경로 처리

- 원자료 위치는 accession과 record locator를 이용하도록 고정 표식으로 대체하였다.
- 원본 동결 폴더와 파일 경로는 원본 파일명만 남긴 비식별 표식으로 대체하였다.
- 공유본에 포함하지 않은 보조파일은 미포함 상태를 표시하였다.
- 원본 동결 파일은 수정하지 않았다.

## 5. 공식 2인 독립 검토 경계

1. 김근형 결과 작성 및 동결
2. 추주원 결과 독립 작성 및 동결
3. 두 결과를 accession 단위로 대조
4. 차이표 작성
5. 두 결과표와 차이표를 권보성에게 전달

추주원의 독립 검토가 동결되기 전에는 본 브랜치의 결과를 미리 열람하지 않는 것이
독립검토 절차를 유지하는 데 필요하다. 저장소 브랜치는 기술적으로 공개되어 있으므로,
이 경계는 팀 검토 절차로 관리한다.

## 6. 이 공유본이 의미하지 않는 상태

- 공식 기준자료 승인 완료
- data_available_date 또는 PIT 운영규칙 확정
- 테마 적격성 판정
- gate_status 판정
- 최종 구성종목 편입
- 지수 산출 프로그램 입력자료 승격
- 추주원 검토 완료
- 공식 김근형·추주원 교차검토 완료
- 팀 승인 완료
