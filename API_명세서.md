# PB.ai Server API 명세서

## 서버 정보
- **Base URL**: `http://127.0.0.1:8000` (기본값)
- **Framework**: FastAPI
- **CORS 허용 Origin**: `http://127.0.0.1:5500`
- **프로토콜**: HTTP/HTTPS
- **응답 형식**: JSON

---

## 목차
1. [AI 질의응답 API](#1-ai-질의응답-api)
2. [질답 기록 조회 API (회사별)](#2-질답-기록-조회-api-회사별)
3. [질답 기록 조회 API (세션별)](#3-질답-기록-조회-api-세션별)
4. [질답 세션 삭제 API](#4-질답-세션-삭제-api)

---

## 공통 요청 모델

### ClientRequest
모든 API에서 사용되는 공통 요청 모델입니다.

```json
{
  "user_id": "string",
  "question": "string",
  "tab_name": "string",
  "company_name": "string"
}
```

#### 필드 설명
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `user_id` | string | ✅ | 사용자 식별 ID |
| `question` | string | ✅ | 사용자 질문 (AI 질의 시) |
| `tab_name` | string | ✅ | 탭 이름 (예: "Overview", "주식가치평가" 등) |
| `company_name` | string | ✅ | 회사 이름 (예: "농심", "삼성전자" 등) |

---

## 1. AI 질의응답 API

### 엔드포인트
```
POST /ask
```

### 설명
사용자의 질문을 받아 AI(GPT-4.1-mini)가 RAG(Retrieval Augmented Generation) 기반으로 답변을 생성합니다.
- 질문은 우선순위 큐에 삽입되어 처리됩니다
- 사용자 레벨에 따라 우선순위가 결정됩니다 (현재 기본값: 1)
- 질답 내역은 자동으로 데이터베이스에 저장됩니다

### 요청 예시
```json
{
  "user_id": "user123",
  "question": "삼성전자의 유동비율이 어떻게 되나요?",
  "tab_name": "재무분석",
  "company_name": "삼성전자"
}
```

### 응답

#### 성공 응답 (200)
```json
{
  "status": "200",
  "user_id": "user123",
  "company_name": "삼성전자",
  "company_tab_name": "삼성전자 재무분석",
  "question": "삼성전자의 유동비율이 어떻게 되나요?",
  "answer": "삼성전자의 유동비율은 검색된 데이터를 기반으로..."
}
```

#### 실패 응답 (500)
```json
{
  "status": "500: {에러 메시지}"
}
```

### 응답 필드 설명
| 필드 | 타입 | 설명 |
|------|------|------|
| `status` | string | HTTP 상태 코드 ("200" 또는 "500: 에러메시지") |
| `user_id` | string | 요청한 사용자 ID |
| `company_name` | string | 회사 이름 |
| `company_tab_name` | string | "회사명 탭명" 형식의 조합 |
| `question` | string | 사용자의 질문 |
| `answer` | string | AI가 생성한 답변 |

### 내부 처리 과정
1. **큐 삽입**: 요청이 우선순위 큐에 삽입됨 (우선순위: -user_level)
2. **임베딩**: 질문과 컨텍스트 데이터를 임베딩 처리
3. **RAG**: ChromaDB를 사용하여 관련 컨텍스트 검색 (k=10)
4. **GPT 답변**: 검색된 컨텍스트와 함께 GPT API 호출
5. **대화 기록**: 최근 3개의 질답을 포함하여 컨텍스트 유지
6. **저장**: 질답을 `data/user_ai_qna.db`의 `qa_logs` 테이블에 저장

### 사용 모델
- **기본 모델**: `gpt-4.1-mini`
- **임베딩 모델**: `text-embedding-3-small`
- **벡터 DB**: ChromaDB (로컬 메모리)

---

## 2. 질답 기록 조회 API (회사별)

### 엔드포인트
```
POST /prevqna/company
```

### 설명
특정 사용자의 특정 회사/탭에 대한 이전 질답 기록을 조회합니다.

### 요청 예시
```json
{
  "user_id": "user123",
  "question": "",
  "tab_name": "재무분석",
  "company_name": "삼성전자"
}
```

### 응답

#### 성공 응답 (200)
```json
{
  "status": "200",
  "size": 5,
  "list": [
    {
      "user_id": "user123",
      "question": "유동비율이 뭔가요?",
      "answer": "유동비율은 기업의 단기 지급 능력을...",
      "company_tab_name": "삼성전자 재무분석",
      "created_time": "2025-12-18 14:30:00"
    },
    {
      "user_id": "user123",
      "question": "부채비율은?",
      "answer": "부채비율은 총부채를 총자본으로...",
      "company_tab_name": "삼성전자 재무분석",
      "created_time": "2025-12-18 14:25:00"
    }
  ]
}
```

### 응답 필드 설명
| 필드 | 타입 | 설명 |
|------|------|------|
| `status` | string | HTTP 상태 코드 |
| `size` | integer | 조회된 질답 기록의 총 개수 |
| `list` | array | 질답 기록 배열 (최신순 정렬) |
| `list[].user_id` | string | 사용자 ID |
| `list[].question` | string | 질문 내용 |
| `list[].answer` | string | 답변 내용 |
| `list[].company_tab_name` | string | "회사명 탭명" 조합 |
| `list[].created_time` | string | 생성 시간 (형식: "YYYY-MM-DD HH:MM:SS") |

### 정렬 순서
- **내림차순**: 최신 질답이 가장 먼저 반환됩니다 (`ORDER BY created_time DESC`)

---

## 3. 질답 기록 조회 API (세션별)

### 엔드포인트
```
POST /prevqna/session
```

### 설명
특정 사용자의 모든 질답 세션(모든 회사/탭)을 조회합니다.
채팅 라이브러리 탭에서 전체 대화 기록을 불러올 때 사용됩니다.

### 요청 예시
```json
{
  "user_id": "user123",
  "question": "",
  "tab_name": "",
  "company_name": ""
}
```

### 응답

#### 성공 응답 (200)
```json
{
  "status": "200",
  "size": 12,
  "list": [
    {
      "user_id": "user123",
      "question": "삼성전자 주가는?",
      "answer": "삼성전자의 현재 주가는...",
      "company_tab_name": "삼성전자 주식가치평가",
      "created_time": "2025-12-18 15:00:00"
    },
    {
      "user_id": "user123",
      "question": "농심 매출은?",
      "answer": "농심의 최근 매출은...",
      "company_tab_name": "농심 Overview",
      "created_time": "2025-12-18 14:55:00"
    }
  ]
}
```

### 응답 필드 설명
| 필드 | 타입 | 설명 |
|------|------|------|
| `status` | string | HTTP 상태 코드 |
| `size` | integer | 조회된 전체 질답 기록 개수 |
| `list` | array | 모든 세션의 질답 기록 배열 (최신순) |
| `list[].user_id` | string | 사용자 ID |
| `list[].question` | string | 질문 내용 |
| `list[].answer` | string | 답변 내용 |
| `list[].company_tab_name` | string | "회사명 탭명" 조합 |
| `list[].created_time` | string | 생성 시간 |

### 정렬 순서
- **내림차순**: 모든 세션의 질답이 시간순으로 정렬됩니다

---

## 4. 질답 세션 삭제 API

### 엔드포인트
```
POST /prevqna/delete
```

### 설명
특정 사용자의 특정 회사/탭에 대한 질답 세션을 삭제합니다.
현재는 전체 세션을 삭제하며 (remain=0), 향후 일부만 남기고 삭제하는 기능 확장 가능합니다.

### 요청 예시
```json
{
  "user_id": "user123",
  "question": "",
  "tab_name": "재무분석",
  "company_name": "삼성전자"
}
```

### 응답

#### 성공 응답
```json
{
  "status": "Sucess"
}
```

#### 실패 응답
```json
{
  "status": "Delete fail : {에러 메시지}"
}
```

### 응답 필드 설명
| 필드 | 타입 | 설명 |
|------|------|------|
| `status` | string | "Sucess" 또는 "Delete fail: 에러메시지" |

### 삭제 동작
- **삭제 범위**: 지정된 `user_id`와 `company_tab_name`에 해당하는 모든 질답 기록
- **보존 개수**: 현재 0개 (전체 삭제)
- **데이터베이스**: `data/user_ai_qna.db`의 `qa_logs` 테이블에서 삭제

---

## 큐 시스템 및 워커

### ServerQueueController
- **워커 수**: 2개 (기본값)
- **큐 크기**: 1000 (최대)
- **큐 타입**: 우선순위 큐 (PriorityQueue)
- **우선순위 결정**: `-user_level` (값이 높을수록 우선 처리)

### 큐 아이템 타입
- `question`: AI 질의응답
- `prev_qna_by_company`: 회사별 질답 조회
- `prev_qna_session`: 세션별 질답 조회
- `delete_session`: 세션 삭제

### 메모리 추적
큐는 `MemoryTrackingPriorityQueue`를 사용하여 메모리 사용량을 실시간으로 추적합니다.
- Bytes 단위
- KB 단위
- MB 단위

---

## 데이터베이스 스키마

### qa_logs 테이블
질답 기록을 저장하는 메인 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `user_id` | TEXT | 사용자 식별 ID |
| `question` | TEXT | 사용자 질문 |
| `answer` | TEXT | AI 답변 |
| `company_tab_name` | TEXT | "회사명 탭명" 조합 |
| `created_time` | TEXT | 생성 시간 ("%Y-%m-%d %H:%M:%S" 형식) |

### 데이터베이스 파일
- **위치**: `data/db/user_ai_qna.db`
- **엔진**: SQLite3

---

## 에러 처리

### 공통 에러 응답
모든 API는 예외 발생 시 다음과 같은 형식으로 응답합니다:

```json
{
  "status": "500: {에러 상세 메시지}"
}
```

### 주요 에러 케이스
1. **GPT API 연결 실패**: "GPT 답변이 없습니다."
2. **데이터베이스 조회 실패**: 빈 배열 반환
3. **임베딩 실패**: "검색된 데이터는 없습니다." 반환
4. **큐 처리 실패**: 500 에러와 함께 에러 메시지 반환

---

## AI 모델 정보

### GPT 모델 종류 및 가격 (1M 토큰당)
| 모델 | 컨텍스트 크기 | 입력 가격 | 출력 가격 | 설명 |
|------|--------------|----------|----------|------|
| `gpt-4.1-nano` | 1,047,576 | $0.1 | $0.4 | 일반형 |
| `gpt-4o-mini` | 128,000 | $0.15 | $0.6 | 표준 |
| `gpt-4.1-mini` | 1,047,576 | $0.4 | $1.6 | 유료형 (기본 사용) |
| `gpt-5-mini` | 400,000 | $0.25 | $2.0 | 고급형 |
| `gpt-5-nano` | 400,000 | $0.05 | $0.4 | 경량 고급형 |

### 시스템 프롬프트
```
너는 회사 '{company_name}'의 재무데이터를 잘 설명해주는 도우미야
```

### 대화 기록 유지
- **최근 질답**: 3개까지 컨텍스트에 포함
- **저장 위치**: `qa_logs` 테이블
- **조회 순서**: 최신순

---

## RAG (Retrieval Augmented Generation) 시스템

### 임베딩
- **모델**: `text-embedding-3-small`
- **벡터 DB**: ChromaDB (로컬 인메모리)
- **검색 결과 수(k)**: 10개
- **청킹**: Dictionary 기반 재귀 청킹

### 컨텍스트 구성
1. 질문과 탭 정보(context_dict)를 임베딩
2. ChromaDB에 임시 컬렉션 생성
3. 질문 임베딩과 유사한 상위 k개 문서 검색
4. 검색된 문서를 컨텍스트로 구성
5. "다음의 검색된 데이터를 참고하여 질문에 답변해주세요." + 컨텍스트 + "질문:" + 질문

---

## 환경 변수

### 필수 환경 변수
`.env` 파일에 다음 변수가 정의되어야 합니다:

```env
GPT_API_KEY=your_openai_api_key_here
```

---

## Lifespan 이벤트

### 서버 시작 시
- ServerQueueController 실행 (`scon.run()`)
- 워커 2개 생성 및 큐 처리 시작
- KrxCrawler 초기화 (시장 데이터 업데이트)

### 서버 종료 시
- ServerQueueController 정지 (`scon.stop()`)
- 모든 워커 취소 및 정리

---

## 추가 기능 (구현된 클래스)

### KrxCrawler
주식 시장 데이터 크롤링 클래스 (직접적인 API 엔드포인트는 없음)

#### 주요 기능
- 시장 종목 리스트 조회
- 종목 OHLCV 데이터 조회
- 펀더멘털 데이터 조회 (BPS, PER, PBR, EPS, DIV, DPS)
- 시가총액 및 발행주식수 조회

#### 사용 라이브러리
- `pykrx`: 한국거래소 데이터
- `FinanceDataReader`: 전체 상장종목 정보

#### 저장 위치
- `data/market.db`: 시장 데이터 저장

---

## CORS 설정

현재 CORS는 다음 설정으로 구성되어 있습니다:

```python
allow_origins=["http://127.0.0.1:5500"]
allow_credentials=True
allow_methods=["*"]
allow_headers=["*"]
```

프로덕션 환경에서는 `allow_origins`를 실제 프론트엔드 도메인으로 변경해야 합니다.

---

## 성능 및 제약사항

### 큐 시스템
- **최대 큐 크기**: 1000
- **동시 처리**: 워커 2개
- **메모리 추적**: 실시간 바이트 단위 추적

### 데이터베이스
- **타입**: SQLite3 (파일 기반)
- **동시성 제한**: SQLite의 동시 쓰기 제약 존재

### AI 처리 시간
- **평균 응답 시간**: 2-5초 (GPT API 호출 + 임베딩)
- **큐 대기 시간**: 큐 상태에 따라 가변적

---

## 버전 정보
- **FastAPI**: 최신 버전
- **Python**: 3.9+
- **OpenAI API**: 최신 버전
- **ChromaDB**: 최신 버전

---

## 문의 및 지원
API 사용 중 문제가 발생하거나 추가 기능이 필요한 경우 개발팀에 문의하시기 바랍니다.

---

**작성일**: 2025-12-18
**버전**: 1.0.0
