## PB.ai 데이터분석
### 2025 게임웍스 Flow 불개미팀
---


# 임시 백엔드. Fast api로 개발합니다.

---

### (1) 실행법
#### 사전준비

필요한 패키지를 설치합니다. 본 문서 (3)번 참조

.env 파일과 data폴더를 따로 전달받아서 최상위 디렉토리에 넣어두고, 프로그램을 실행해야 합니다

#### 실행

터미널에 다음 명령어 입력
uvicorn main:app --reload 

### (2) 개발 상황

#### 1) 재무제표 분석
리포트_투자지표, 리포트_주식가치평가 해야함.

#### 2) 생성형 AI를 이용한 응답구조
백엔드(혹은 클라이언트)에게 response 전달하는 로직 추가하면 완성

그 외에 메모리 출력함수 적용, 질답 저장db 과도하게 쌓이지 않게끔 하는 로직 추가하면 좋음


### (3) 설치가 필요한 파이썬 패키지
1.OpenDataReader : pip install opendartreader          재무데이터 크롤링

2.json  : json              (이거 기본 패키지인가..?)     메타 데이터 관리

3.pandas            pip install pandas                 데이터 가공

4.openai            pip install opneai                 gpt 연결, 임베딩 api

5.chromadb          pip install chromadb               임베딩 벡터 저장을 위한 벡터db

5.tiktoken          pip install tiktoken               open api 사용을 위한 토큰 분리

6.financedatareader pip install finance-datareader     주가정보크롤링1

7.pykrx :           pip install pykrx                  주가정보크롤링2

8.env :             pip install python-dotenv          api_key 환경변수로 관리 (아나콘다는 기본설치됨을 확인)

### (4) 기타

#### Dart api 사용 규칙
호출 한도 : 일 20000건

호출 분당 한도 : 1000회/분

#### data폴더 구조

data/

  meta/

    meta.json (api key, 파싱할 항목관리)

    crawled_set.pkl (크롤한 재무제표 확인용)

    parsed_set.pkl (파싱한 재무제표 확인용)

  extracted.db (파싱 데이터)

  market.db (국내증권시장티커,이름등)

  raw.db (크롤링한 원본 재무제표데이터)

  user_ai_qna.db (사용자 질답 저장)

  calculation.db (파싱된 데이터를 바탕으로 가공된 데이터)

  company.db (회사별 개황정보 저장)



