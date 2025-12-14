## PB.ai 데이터분석
### 2025 게임웍스 Flow 불개미팀
---

### 0) 공지
파일 구조

아래 파일들은 .gitignore추가가 안되어 있어 따로 전달받은 다음 프로그램을 실행해야 합니다

data/
  meta/
    meta.json (api key, 파싱할 항목관리)
    crawled_set.pkl (크롤한 재무제표 확인용)
    parsed_set.pkl (파싱한 재무제표 확인용)
  extracted.db (파싱 데이터)
  market.db (국내증권시장티커,이름등)
  raw.db (크롤링한 원본 재무제표데이터)


0. crawled_set.pkl , parsed_set.pkl
  재무제표를 크롤하면, 혹은 파싱하면 각각, 
  (year)(ticker)(property) 의 문자열로 set에 추가합니다. property 규정은 1번 extrated.db와 같음
  ex) 2024005930Q4

1. extracted.db
  table : 티커명+@으로 되어있음. @가 I는 손익계산서, B는 재무상태표 ex) 005930I
  칼럼명 : 파싱항목
  행 : 연도+Property (property 규정: m이라면 시계열평균, Q4,Q3...)
  ex) 2024Q3 : 3분기
  ex) 2024m : 2021~2023 시계열 평균

2. market.db
  table : kospi, kosdaq, konex
  모두 ticker, name의 칼럼 아래에서 관리되고 있습니다.

3. raw.db
  table 이름 규칙
  티커명 + 분기명
  ex) 005930Q1  : 삼성전자 1분기 테이블

  /extracted
    2021
    2022...
    (year)
      재무제표에서 1차가공한 데이터(DB001, DB002등의 결과물)
  /raw
    (year)
      재무제표 크롤링한 raw 데이터
  /market
    증권회사 정보

#### 파일 이름 규칙
디렉토리로 연도는 구분하지만, 관리 편의성을 위해 이름에도 연도,속성등을 넣겠습니다.
1. 크롤링한 재무제표
Y(year)T(ticker)P(property).feather
여기서 property는 분기 속성을 나타냅니다.
Q1 : 1분기 Q2: 반기, Q3:3분기, Q4: 사업보고서
ex)삼성전자 2024년도 사업보고서 기준
Y2024T005930PQ4.feather

2. 1차가공 데이터
feather 말고 sqlite3 db로 저장할지 고민중
Y(year)T(ticker)P(property).feather
property는 분기속성,재무상태표or손익계산서 인지를 나타냅니다.
분기속성은 크롤링한 재무제표 속성과 동일
재무상태표는 B , 손익계산서는 I
ex) 삼성전자 2024년도 사업보고서의 재무상태표
Y2024T005930PQ4B

3. 시계열 평균 데이터
Y(currentyear)T(ticker)P(property).feather
property 항목은 B (Before march) A (After March) 로 나뉩니다.

#### 1) 재무제표 분석
기능요구사항 명세서 대로 구현중
DB001 (5개년 재무상태표 파싱) : 러프하게 구현중 (90%완료). 재무상태표에 없는 내용은 주석을 확인해야 하는데 이는 상당한 시간이 걸릴 것으로 판단, MVP에서 빼고 추후 품질 업그레이드하는 바를 요청했음
DB002 (5개년 재무상태표 파싱) : 구현 시작 안함. DB001에 api 호출 함수만 수정하면 바로 완성 가능

#### 2) 생성형 AI를 이용한 응답구조
구현 방법 파악중
프론트/백/DB구조를 팀원과 의논후 구현 들어갈 예정

### 패키지 설치
1.OpenDataReader : pip install opendartreader          재무데이터 크롤링
2.json  : json              (이거 기본 패키지인가..?)     메타 데이터 관리
3.pandas            pip install pandas                 데이터 가공
4.openai            pip install opneai                 gpt 연결, 임베딩 api
5.chromadb          pip install chromadb               임베딩 벡터 저장을 위한 벡터db
5.tiktoken          pip install tiktoken               open api 사용을 위한 토큰 분리
6.financedatareader pip install finance-datareader     주가정보크롤링1
7.pykrx :           pip install pykrx                  주가정보크롤링2

### api key
파일경로 아래에 data 폴더를 생성, data/meta.json 파일을 생성한다
json 파일에 "api_key" : "본인의 Dart api key" 를 저장한다.

### Dart api 사용 규칙
호출 한도 : 일 20000건
호출 분당 한도 : 1000회/분
...



