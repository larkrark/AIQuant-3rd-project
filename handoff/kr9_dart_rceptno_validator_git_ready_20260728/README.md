# KR9 DART rcept_no 검증자용 Git-ready 공유본

## 목적
이 패키지는 개인 PC 절대경로에 의존하지 않고, 검증자가 DART 공식 접수번호 기준으로 같은 공시 원문을 확인할 수 있도록 정리한 공유본입니다.

## 공통 검증 기준
공통 검증 기준은 개인 PC 경로가 아니라 다음 두 값입니다.

- `rcept_no`
- `official_dart_url`

## 로컬 경로 처리
기존 공유 ZIP 안의 로컬 컨테이너 경로 열과 개인 PC 절대경로 값은 Git 공유용으로 부적절하여 다음처럼 처리했습니다.

- 로컬 컨테이너 경로 열명 → `local_container_redacted`
- 개인 PC 절대경로 값 → `[LOCAL_PATH_REMOVED_USE_RCEPT_NO_AND_ZIP_ENTRY]`

## 입력 ZIP
- file_name: KR9_DART_CORPCODE_RCEPTNO_FILLED_FOR_VALIDATOR_20260728.zip
- sha256: 7DDABCB371D2A09D024DDD83EE60C59BD60412A42608038B64E1AE29A80DCFE4

## 미수행 항목
이 공유본은 원문 검증과 자료정합성 확인을 위한 것이며, 아래 판단은 수행하지 않았습니다.

- human theme review
- theme revenue confirmation
- backlog confirmation
- role_grade
- evidence_grade
- gate_status
- final inclusion decision
