# 규칙 기반 한·미 3테마 패시브 커스텀 인덱스 상품화 마스터 v1.0

## 목적

프로젝트의 아이디어·결정·데이터·PIT·테마 적격성·정량 게이트·기업행사·선정·가중·지수산출·독립 QA·3방향 인계·상품 운영을 세 문서로 통합한 구조완결본입니다.

## 마스터 문서

1. `상품화마스터룰북_v1.0`
   - 무엇을 왜 어떤 절차와 승인경계로 수행하는지 규정
2. `상품화마스터데이터사전_v1.0`
   - 법인·증권·문서·PIT·테마·기업행사·산출·QA·운영 380개 필드의 단일 정의
3. `상품화마스터수식정리부록_v1.0`
   - 시장상태·PIT·ADTV90·재무·테마·가중·환율·BM·지수·기업행사·QA의 공식 계산 정의

DOCX와 Markdown mirror를 함께 제공합니다.

## “완결판”의 의미

```text
STRUCTURALLY_COMPLETE_MASTER
= 상품화를 위해 필요한 규칙·필드·수식·승인절차·운영통제가 모두 문서 구조에 존재

≠ 모든 수치와 소스가 팀 승인됨
≠ 금융상품 출시의 법률·규제·라이선스 승인 완료
≠ production 지수와 공식 성과가 동결됨
```

현재 미결값은 `CONFIG_REQUIRED`, `APPROVAL_PENDING`, `NOT_PERFORMED`, `NOT_PROMOTED`로 보존합니다.

## 근거와 추가층

### 프로젝트 기록에서 직접 통합한 내용

- 3테마×2지역·6셀 구조
- PIT·정정계보·DART/SEC·KRX/거래소 역할
- 90 유효관측일·ADTV90·시장상태 6종
- 테마 적격성 3축과 2인 독립판정
- PR·KRW·무헤지, KOSPI 200 PR·Russell 3000 PR 검토구조
- 기업행사 영향축, CHAIN_REBASE, 독립 QA 1e-12
- 김민호·권보성·추주원 3방향 인계

### 상품화에 필요하여 새로 구조화한 통제층

- 지수관리자·계산에이전트·법률·라이선스·운영책임
- 데이터·BM·상표·배포 라이선스
- 게시 SLA·정정·restatement·Incident·BCP
- production 승격·중단·후속지수·공개방법론 관리

이 추가층은 현재 `PRODUCTIZATION_CONTROL_PROPOSED`이며 별도 승인이 필요합니다.

## 지원 파일

- `SOURCE_AND_COVERAGE_REGISTER.csv`: 근거자료와 SHA-256
- `MASTER_COVERAGE_MATRIX.csv`: 프로젝트 생애주기별 문서 위치
- `PRODUCTIZATION_APPROVAL_GATES.csv`: 상품화 전 열려 있는 승인게이트
- `MASTER_DOCUMENT_QA_REPORT.md`: 렌더·구조 검수기록
- `PACKAGE_FILE_INDEX.csv`: 패키지 파일별 SHA-256

## 현재 상태

```text
master_document_status = STRUCTURALLY_COMPLETE_MASTER
team_approval_status = PENDING
legal_review_status = NOT_PERFORMED
license_status = NOT_COMPLETED
production_status = NOT_PROMOTED
performance_status = PERFORMANCE_NOT_FROZEN
```
