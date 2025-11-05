## PB.ai 데이터분석
### 2025 게임웍스 Flow 불개미팀
---

### 0) 공지
파일 구조 변경사항
raw 데이터/가공데이터 /연도별 데이터 / fast api 관리 등등 파일 규칙이 필요해서 급하게 설정하고 공지합니다

data/
  2021
  2022...
  (year)
    크롤링한 재무제표
    재무제표에서 1차가공한 데이터(DB001, DB002등의 결과물)

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
1.OpenDataReader : pip install opendartreader  (conda 채널에 없음.)
2.json
3.pandas
4.requests

### api key
파일경로 아래에 data 폴더를 생성, data/meta.json 파일을 생성한다
json 파일에 "api_key" : "본인의 Dart api key" 를 저장한다.
...



