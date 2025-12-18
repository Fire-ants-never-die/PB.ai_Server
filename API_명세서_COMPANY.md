# 기업 분석 API 명세서

## Base URL
```
/api/v1
```

## 공통 사항
- **응답 포맷**: `application/json; charset=utf-8`
- **통화**: KRW (원화)
- **타임스탬프**: ISO 8601 형식
- **에러 응답**:
  ```json
  {
    "error": {
      "code": "ERROR_CODE",
      "message": "에러 메시지"
    }
  }
  ```

### 공통 에러 코드
| 코드 | HTTP Status | 설명 |
|------|-------------|------|
| `COMPANY_NOT_FOUND` | 404 | 기업 코드가 존재하지 않음 |
| `INVALID_PARAMETER` | 400 | 잘못된 파라미터 |
| `INTERNAL_SERVER_ERROR` | 500 | 서버 내부 오류 |

---

## 1️⃣ 기업 Overview 페이지 API

### 1.1. 기업 프로필

**GET** `/companies/{companyCode}/profile`

**설명**: 기업 프로필 표 - 동적 키-값 구조 (개수 미정)

**Path Parameters**:
- `companyCode` (string, required): 기업 코드

**Response 200**:
```json
{
  "companyCode": "001234",
  "companyName": "농심",
  "profile": [
    { "label": "시가총액", "value": "2조 3,266억원" },
    { "label": "상장일자", "value": "1976년 6월 30일" },
    { "label": "설립일자", "value": "1965년" },
    { "label": "종업원수", "value": "5,401명" },
    { "label": "대표 이사", "value": "이병학" },
    { "label": "발행주식수", "value": "6,082,642주 (25년 7월 29일 기준)" },
    { "label": "주요 계열사/관계사", "value": "농심홀딩스, 농심켈로그, 농심엔지니어링, 태경농산, 호텔농심" }
  ]
}
```

**필드 설명**:
- `companyCode`: 기업 코드
- `companyName`: 기업명
- `profile`: 배열 길이 및 항목 동적
  - `label`: 구분 항목명
  - `value`: 내용 (괄호 부분 포함 가능)

**프론트엔드 하드코딩 사항**:
- `logoUrl`: 프론트엔드에서 `companyCode`에 따라 하드코딩 (예: `/nongshim_logo.svg`)
- `titleImageUrl`: 프론트엔드에서 `companyCode`에 따라 하드코딩 (예: `/nongshim_title.png`)

---

### 1.2. 매출 산업 구성

**GET** `/companies/{companyCode}/sales-composition`

**설명**: 원그래프 데이터 - 동적 키-값-색상 구조 (개수 미정)

**Path Parameters**:
- `companyCode` (string, required): 기업 코드

**Response 200**:
```json
{
  "totalRevenue": "34,387억",
  "totalRevenueRaw": 3438700000000,
  "items": [
    { "name": "라면", "value": 81.8, "percentage": "81.8%", "color": "#5797F7" },
    { "name": "기타", "value": 18.4, "percentage": "18.4%", "color": "#FFA353" },
    { "name": "스낵", "value": 14.4, "percentage": "14.4%", "color": "#8DD3BB" },
    { "name": "매출 에누리등", "value": 14.5, "percentage": "-14.5%", "color": "#FFD666" }
  ]
}
```

**필드 설명**:
- `totalRevenue`: 총 매출액 (포맷팅된 문자열)
- `totalRevenueRaw`: 총 매출액 원본 숫자값
- `items`: 배열 길이 동적
  - `name`: 항목명
  - `value`: 차트용 수치 (양수, 실제 퍼센트 값)
  - `percentage`: 표시용 퍼센트 문자열 (음수 표기 가능, 예: "-14.5%")
  - `color`: 차트 색상 (HEX 코드)

---

### 1.3. 재무 현황

**GET** `/companies/{companyCode}/financial-overview`

**설명**: 차트 2개 + 표 데이터

**Path Parameters**:
- `companyCode` (string, required): 기업 코드

**Query Parameters**:
- `periodType` (string, optional): `annual` | `quarterly`, 기본값: `annual`

**Response 200**:
```json
{
  "revenueChart": [
    { "year": "2021", "value": 246800000000 },
    { "year": "2022", "value": 230500000000 },
    { "year": "2023", "value": 268900000000 },
    { "year": "2024", "value": 298400000000 },
    { "year": "2025/06", "value": 275600000000 }
  ],
  "netIncomeChart": [
    { "year": "2021", "netIncome": 141500000000, "netIncomeRate": 12.5 },
    { "year": "2022", "netIncome": 123800000000, "netIncomeRate": 10.8 },
    { "year": "2023", "netIncome": 158900000000, "netIncomeRate": 18.2 },
    { "year": "2024", "netIncome": 201300000000, "netIncomeRate": 21.4 },
    { "year": "2025/06", "netIncome": 178200000000, "netIncomeRate": 15.2 }
  ],
  "financialTable": [
    {
      "year": "2021",
      "revenue": 246800000000,
      "totalAssets": 1890000000000,
      "totalLiabilities": 645000000000,
      "totalEquity": 1245000000000,
      "operatingIncome": 168500000000,
      "netIncome": 141500000000
    },
    {
      "year": "2022",
      "revenue": 230500000000,
      "totalAssets": 1950000000000,
      "totalLiabilities": 678000000000,
      "totalEquity": 1272000000000,
      "operatingIncome": 145300000000,
      "netIncome": 123800000000
    }
  ]
}
```

**필드 설명**:
- `revenueChart`: 매출액 차트 데이터 (왼쪽 그래프)
  - 배열 길이 동적
  - `year`: 연도 (문자열, 예: "2021", "2025/06")
  - `value`: 매출액 (숫자, 원 단위)

- `netIncomeChart`: 순이익&순이익률 차트 데이터 (오른쪽 그래프)
  - 배열 길이 동적
  - `year`: 연도
  - `netIncome`: 순이익 (숫자, 원 단위, 차트 세로축에 표시)
  - `netIncomeRate`: 순이익률 (백분율 숫자, 차트에 함께 표시)

- `financialTable`: 재무 데이터 표
  - 배열 길이 동적
  - `year`: 연도 (문자열)
  - `revenue`: 매출액 (숫자, 원 단위)
  - `totalAssets`: 자산 총계 (숫자, 원 단위)
  - `totalLiabilities`: 부채 총계 (숫자, 원 단위)
  - `totalEquity`: 자본 총계 (숫자, 원 단위)
  - `operatingIncome`: 영업이익 (숫자, 원 단위)
  - `netIncome`: 순이익 (숫자, 원 단위)

**참고**: 모든 금액은 원 단위로 전달하며, 프론트엔드에서 포맷팅 처리

---

### 1.4. 재무건전성

**GET** `/companies/{companyCode}/financial-health`

**설명**: 프로그레스바 + 6개 박스

**Path Parameters**:
- `companyCode` (string, required): 기업 코드

**Response 200**:
```json
{
  "description": "농심의 재무건전성은 필수소비재 섹터 업종 중위수와 시계열 점수로 판정됩니다",
  "scoreValue": 0.855,
  "scoreRange": {
    "min": -1,
    "max": 1,
    "thresholds": [-1, -0.5, 0, 0.5, 1]
  },
  "healthCategories": [
    { "label": "유동성", "status": "안전" },
    { "label": "레버리지", "status": "안전" },
    { "label": "투자수익성", "status": "안전" },
    { "label": "판매마진", "status": "안전" },
    { "label": "활동성", "status": "안전" },
    { "label": "성장성", "status": "안전" }
  ]
}
```

**필드 설명**:
- `description`: 재무건전성 설명 텍스트
- `scoreValue`: 재무건전성 점수 (number, -1 ~ 1 사이 값, 동적)
- `scoreRange`: 점수 범위 정보
  - `min`: 최소값 (고정: -1)
  - `max`: 최대값 (고정: 1)
  - `thresholds`: 프로그레스바 기준선 배열 (고정: [-1, -0.5, 0, 0.5, 1])
- `healthCategories`: 6개 카테고리 (고정 개수)
  - `label`: 카테고리명 (고정값: "유동성" | "레버리지" | "투자수익성" | "판매마진" | "활동성" | "성장성")
  - `status`: 상태 (고정값: "안전" | "경고" | "위험")

**UI 매핑 가이드**:

프로그레스바 색상:
- 빨간색(위험): `#EB0E0E` (0~25% 구간, scoreValue < -0.5)
- 주황색(경고): `#FFA353` (25~73% 구간, -0.5 ≤ scoreValue < 0.5)
- 파란색(안전): `#0042FB` (73~100% 구간, scoreValue ≥ 0.5)

화살표 색상:
- `scoreValue < -0.5`: 빨간색 `#EB0E0E`
- `-0.5 ≤ scoreValue < 0.5`: 노란색 `#F59E0B`
- `scoreValue ≥ 0.5`: 파란색 `#0042FB`

박스 테두리 색상:
- `status === "안전"`: 파란색 `#0042FB`
- `status === "경고"`: 노란색 `#F59E0B`
- `status === "위험"`: 빨간색 `#EB0E0E`

위치 계산:
```typescript
const scorePosition = ((scoreValue + 1) / 2) * 100; // -1~1 → 0~100%
```

---

### 1.5. 산업 설명

**GET** `/companies/{companyCode}/industry-description`

**설명**: 산업 설명 표 - 동적 키-값 구조

**Path Parameters**:
- `companyCode` (string, required): 기업 코드

**Response 200**:
```json
{
  "items": [
    { "label": "산업명", "value": "식료품 제조업(C10)" },
    { "label": "평가기준일", "value": "2025.06" },
    { "label": "산업평가 종합등급", "value": "2(양호)" }
  ]
}
```

**필드 설명**:
- `items`: 배열 길이 동적
  - `label`: 구분 항목명 (문자열)
  - `value`: 내용 (문자열)

---

## 2️⃣ 재무현황분석 페이지 API

### 2.1. 재무 상황 (섹션 1)

**설명**: Overview의 `1.3. 재무 현황` API를 **재사용**합니다.

**재사용 API**: `GET /companies/{companyCode}/financial-overview`

**프론트엔드 하드코딩 사항**:
- 섹션 설명 텍스트: "농심의 기업의 재무상황을 종합적으로 보여주는 자료입니다. 한 해 동안 벌어들인 매출액, 보유하고 있는 자산의 규모, 갚아야 할 부채, 주주의 몫인 자본, 그리고 본업에서 발생한 영업이익과 최종적으로 남은 순이익을 알 수 있습니다."

---

### 2.2. 재무 비율 판정 (섹션 2)

**GET** `/companies/{companyCode}/financial-ratio-judgment`

**설명**: 재무건전성 정보 + 재무 비율 판정 표

**Path Parameters**:
- `companyCode` (string, required): 기업 코드

**Response 200**:
```json
{
  "financialHealth": {
    "scoreValue": 0.855,
    "scoreRange": {
      "min": -1,
      "max": 1,
      "thresholds": [-1, -0.5, 0, 0.5, 1]
    },
    "healthCategories": [
      { "label": "유동성", "status": "안전" },
      { "label": "레버리지", "status": "안전" },
      { "label": "투자수익성", "status": "안전" },
      { "label": "판매마진", "status": "안전" },
      { "label": "활동성", "status": "안전" },
      { "label": "성장성", "status": "안전" }
    ]
  },
  "ratioJudgmentTable": [
    {
      "indicator": "지표 점수",
      "stability": "0.667",
      "leverage": "-0.333",
      "investmentProfitability": "0.833",
      "salesMargin": "0.667",
      "activity": "0.5",
      "growth": "-0.167"
    },
    {
      "indicator": "지표 판정",
      "stability": "99%",
      "leverage": "67%",
      "investmentProfitability": "99%",
      "salesMargin": "99%",
      "activity": "99%",
      "growth": "67%"
    }
  ]
}
```

**필드 설명**:
- `financialHealth`: 재무건전성 데이터 (`1.4. 재무건전성` API와 동일 구조, `description` 제외)
  - `scoreValue`: 점수 (-1 ~ 1)
  - `scoreRange`: 범위 정보
  - `healthCategories`: 6개 카테고리 배열

- `ratioJudgmentTable`: 재무 비율 판정 표 데이터
  - 배열 길이 동적 (일반적으로 2개 행: "지표 점수", "지표 판정")
  - `indicator`: 지표 행 구분 (문자열)
  - `stability`: 유동성 값 (문자열)
  - `leverage`: 레버리지 값 (문자열)
  - `investmentProfitability`: 투자수익성 값 (문자열)
  - `salesMargin`: 판매마진 값 (문자열)
  - `activity`: 활동성 값 (문자열)
  - `growth`: 성장성 값 (문자열)

**프론트엔드 하드코딩 사항**:
- 섹션 설명 텍스트: "농심의 재무건전성은 필수소비재 섹터 업종 중위수와 시계열 점수로 판정됩니다. 농심은 필수소비재 섹터 내에서 재무 안정성과 수익성이 뛰어난 기업으로 평가됩니다. 전반적인 재무 건전성 점수는 0.855로 '안전 구간'에 위치하며, 업계 평균을 상회하는 안정성을 보여주고 있습니다."

**테이블 헤더 구조** (고정):
```
┌────────┬─────────────────┬─────────────────┬──────────┬──────────┐
│  지표  │     안정성      │     수익성      │ 활동성   │ 성장성   │
│        ├────────┬────────┼────────┬────────┤          │          │
│        │ 유동성 │레버리지│투자수익│판매마진│          │          │
├────────┼────────┼────────┼────────┼────────┼──────────┼──────────┤
│지표 점수│ 0.667  │-0.333  │ 0.833  │ 0.667  │   0.5    │  -0.167  │
│지표 판정│  99%   │  67%   │  99%   │  99%   │   99%    │   67%    │
└────────┴────────┴────────┴────────┴────────┴──────────┴──────────┘
```

---

### 2.3. 안정성/수익성/성장성/활동성 분석 (섹션 3~6)

**GET** `/companies/{companyCode}/financial-analysis-details`

**설명**: 3번 이후 확장 가능한 표들 (트리 구조)

**Path Parameters**:
- `companyCode` (string, required): 기업 코드

**Response 200**:
```json
{
  "sections": [
    {
      "id": "stability",
      "title": "3. 안정성 분석",
      "subsections": [
        {
          "title": "3.1. 유동성 분석",
          "tableHeaders": [
            { "key": "indicator", "label": "" },
            { "key": "year2023", "label": "2023" },
            { "key": "timeSeriesAverage", "label": "시계열평균" },
            { "key": "industryMedian", "label": "업종중위수" },
            { "key": "timeSeriesScore", "label": "시계열점수" },
            { "key": "industryScore", "label": "업종점수" }
          ],
          "items": [
            {
              "name": "유동비율",
              "values": {
                "year2023": "203.85%",
                "timeSeriesAverage": "199.85%",
                "industryMedian": "152.60%",
                "timeSeriesScore": 1,
                "industryScore": 1
              },
              "children": [
                {
                  "name": "유동자산",
                  "values": {
                    "year2023": "15,234억",
                    "timeSeriesAverage": "14,567억",
                    "industryMedian": "12,345억",
                    "timeSeriesScore": 1,
                    "industryScore": 1
                  },
                  "children": []
                },
                {
                  "name": "유동부채",
                  "values": {
                    "year2023": "7,467억",
                    "timeSeriesAverage": "7,289억",
                    "industryMedian": "8,091억",
                    "timeSeriesScore": 1,
                    "industryScore": 1
                  },
                  "children": []
                }
              ]
            },
            {
              "name": "당좌비율",
              "values": {
                "year2023": "156.23%",
                "timeSeriesAverage": "152.45%",
                "industryMedian": "128.90%",
                "timeSeriesScore": 1,
                "industryScore": 1
              },
              "children": []
            },
            {
              "name": "현금비율",
              "values": {
                "year2023": "89.45%",
                "timeSeriesAverage": "87.23%",
                "industryMedian": "75.60%",
                "timeSeriesScore": 1,
                "industryScore": 1
              },
              "children": []
            }
          ]
        },
        {
          "title": "3.2. 레버리지 분석",
          "tableHeaders": [
            { "key": "indicator", "label": "" },
            { "key": "year2023", "label": "2023" },
            { "key": "timeSeriesAverage", "label": "시계열평균" },
            { "key": "industryMedian", "label": "업종중위수" },
            { "key": "timeSeriesScore", "label": "시계열점수" },
            { "key": "industryScore", "label": "업종점수" }
          ],
          "items": [
            {
              "name": "부채비율",
              "values": {
                "year2023": "34.56%",
                "timeSeriesAverage": "36.78%",
                "industryMedian": "45.67%",
                "timeSeriesScore": 1,
                "industryScore": 1
              },
              "children": []
            },
            {
              "name": "차입금의존도",
              "values": {
                "year2023": "12.34%",
                "timeSeriesAverage": "13.45%",
                "industryMedian": "18.90%",
                "timeSeriesScore": 1,
                "industryScore": 1
              },
              "children": []
            }
          ]
        }
      ]
    },
    {
      "id": "profitability",
      "title": "4. 수익성 분석",
      "subsections": [
        {
          "title": "4.1. 투자수익성 분석",
          "tableHeaders": [
            { "key": "indicator", "label": "" },
            { "key": "year2023", "label": "2023" },
            { "key": "timeSeriesAverage", "label": "시계열평균" },
            { "key": "industryMedian", "label": "업종중위수" },
            { "key": "timeSeriesScore", "label": "시계열점수" },
            { "key": "industryScore", "label": "업종점수" }
          ],
          "items": [
            {
              "name": "총자산세전이익률",
              "values": {
                "year2023": "8.45%",
                "timeSeriesAverage": "8.12%",
                "industryMedian": "7.23%",
                "timeSeriesScore": 1,
                "industryScore": 1
              },
              "children": []
            },
            {
              "name": "총자산순이익률 (ROA)",
              "values": {
                "year2023": "6.78%",
                "timeSeriesAverage": "6.45%",
                "industryMedian": "5.67%",
                "timeSeriesScore": 1,
                "industryScore": 1
              },
              "children": []
            }
          ]
        },
        {
          "title": "4.2. 판매마진 분석",
          "tableHeaders": [
            { "key": "indicator", "label": "" },
            { "key": "year2024", "label": "2024" },
            { "key": "avg5Years", "label": "5개년 평균" },
            { "key": "sectorMedian", "label": "섹터중위수" },
            { "key": "scoreA", "label": "점수A" },
            { "key": "scoreB", "label": "점수B" }
          ],
          "items": [
            {
              "name": "매출액세전이익률",
              "values": {
                "year2024": "9.12%",
                "avg5Years": "8.89%",
                "sectorMedian": "8.12%",
                "scoreA": 1,
                "scoreB": 1
              },
              "children": []
            },
            {
              "name": "매출액순이익률",
              "values": {
                "year2024": "7.34%",
                "avg5Years": "7.12%",
                "sectorMedian": "6.45%",
                "scoreA": 1,
                "scoreB": 1
              },
              "children": []
            }
          ]
        }
      ]
    },
    {
      "id": "growth",
      "title": "5. 성장성 분석",
      "subsections": [
        {
          "title": "",
          "tableHeaders": [
            { "key": "indicator", "label": "" },
            { "key": "year2023", "label": "2023" },
            { "key": "timeSeriesAverage", "label": "시계열평균" },
            { "key": "industryMedian", "label": "업종중위수" },
            { "key": "timeSeriesScore", "label": "시계열점수" },
            { "key": "industryScore", "label": "업종점수" }
          ],
          "items": [
            {
              "name": "총자산증가율",
              "values": {
                "year2023": "8.45%",
                "timeSeriesAverage": "7.89%",
                "industryMedian": "6.78%",
                "timeSeriesScore": 1,
                "industryScore": 1
              },
              "children": []
            },
            {
              "name": "유형자산증가율",
              "values": {
                "year2023": "5.67%",
                "timeSeriesAverage": "5.23%",
                "industryMedian": "4.56%",
                "timeSeriesScore": 1,
                "industryScore": 1
              },
              "children": []
            }
          ]
        }
      ]
    },
    {
      "id": "activity",
      "title": "6. 활동성 분석",
      "subsections": [
        {
          "title": "",
          "tableHeaders": [
            { "key": "indicator", "label": "" },
            { "key": "year2023", "label": "2023" },
            { "key": "timeSeriesAverage", "label": "시계열평균" },
            { "key": "industryMedian", "label": "업종중위수" },
            { "key": "timeSeriesScore", "label": "시계열점수" },
            { "key": "industryScore", "label": "업종점수" }
          ],
          "items": [
            {
              "name": "총자산회전율",
              "values": {
                "year2023": "0.89",
                "timeSeriesAverage": "0.87",
                "industryMedian": "0.82",
                "timeSeriesScore": 1,
                "industryScore": 1
              },
              "children": []
            },
            {
              "name": "자기자본회전율",
              "values": {
                "year2023": "1.23",
                "timeSeriesAverage": "1.19",
                "industryMedian": "1.12",
                "timeSeriesScore": 1,
                "industryScore": 1
              },
              "children": []
            }
          ]
        }
      ]
    }
  ]
}
```

**필드 설명**:
- `sections`: 최상위 섹션 배열 (안정성, 수익성, 성장성, 활동성)
  - `id`: 섹션 식별자 (string, 예: "stability", "profitability", "growth", "activity")
  - `title`: 섹션 제목 (string, 예: "3. 안정성 분석")
  - `subsections`: 하위 섹션 배열
    - `title`: 하위 섹션 제목 (string, 예: "3.1. 유동성 분석", 없으면 빈 문자열)
    - `tableHeaders`: **동적 헤더 배열** (컬럼 개수와 key, label 모두 변동 가능)
      - `key`: 컬럼 키 (string, `values` 객체의 key와 매칭)
      - `label`: 컬럼 표시명 (string, 첫 번째는 빈 문자열)
    - `items`: 트리 구조 데이터 배열
      - `name`: 지표명 (string)
      - `values`: 객체 (key는 `tableHeaders[].key`와 매칭, value는 string 또는 number)
      - `children`: 하위 항목 배열 (재귀 구조, 없으면 빈 배열 `[]`)

**프론트엔드 하드코딩 사항**:
각 섹션별 설명 텍스트 (`description`):
- **안정성 분석**: "안정성 분석은 기업의 재무 구조가 얼마나 건전한지를 보여주는 지표입니다. 재무상태표의 자산·부채·자본 관계를 바탕으로 평가하며, 기업의 단기지급 능력인 유동성 분석과 자본조달구조에 대한 대응능력인 레버리지 분석으로 구분됩니다."

- **수익성 분석**: "수익성 분석은 일정기간 동안 기업의 경영성과를 나타내는 지표입니다. 투자된 자산 또는 자본 대비 창출한 이익의 정도를 의미하는 투자수익성 분석과 매출에 상응하여 창출한 이익의 정도를 나타내는 판매마진 분석으로 분류됩니다."

- **성장성 분석**: "성장성 지표는 기업의 규모와 경영성과가 전년도와 비교하여 얼마나 증가하였는가를 나타내는 지표입니다. 이를 통해 기업의 미래 경쟁력과 수익 창출 능력을 간접적으로 알 수 있어요."

- **활동성 분석**: "활동성 분석은 기업이 보유한 자산이나 자본을 얼마나 효율적으로 활용하고 있는지를 보여주는 지표입니다. 일반적으로 효율성 비율 또는 회전율이라고 부릅니다. 매출액은 투하된 자산이나 자본을 통해 만들어지는 가장 핵심적인 성과물이기 때문에, 활동성 지표는 투하 자산이나 자본 대비 얼마만큼의 매출을 창출했는지를 배수로 측정합니다."

**트리 구조 렌더링 가이드**:

1. **확장/축소 아이콘**:
   - `children.length > 0`이고 확장 상태: `/minus_square.svg` 표시
   - `children.length > 0`이고 축소 상태: `/square.svg` 표시
   - `children.length === 0`: 아이콘 없음

2. **들여쓰기**:
   - 최상위 항목 (level 0): 왼쪽 패딩 16px
   - 1단계 하위 (level 1): 왼쪽 패딩 40px (16 + 24)
   - 2단계 하위 (level 2): 왼쪽 패딩 64px (16 + 24*2)
   - 공식: `paddingLeft = 16 + level * 24`

3. **값 포맷팅**:
   - 숫자형: `toLocaleString('ko-KR')` 적용
   - 문자형: 그대로 표시

**예시 테이블 구조**:
```
┌─────────────┬────────┬────────────┬────────────┬────────────┬────────────┐
│             │  2023  │ 시계열평균 │ 업종중위수 │ 시계열점수 │ 업종점수   │
├─────────────┼────────┼────────────┼────────────┼────────────┼────────────┤
│ [−] 유동비율│203.85% │  199.85%   │  152.60%   │     1      │     1      │
│   ㄴ유동자산│15,234억│  14,567억  │  12,345억  │     1      │     1      │
│   ㄴ유동부채│ 7,467억│   7,289억  │   8,091억  │     1      │     1      │
│ [+] 당좌비율│156.23% │  152.45%   │  128.90%   │     1      │     1      │
└─────────────┴────────┴────────────┴────────────┴────────────┴────────────┘
```

---

## 📌 API 엔드포인트 요약

| API 엔드포인트 | 용도 | 동적 요소 | Overview | 분석 |
|---|---|---|:---:|:---:|
| `GET /companies/{code}/profile` | 기업 프로필 표 | 키-값 개수 동적 | ✅ | |
| `GET /companies/{code}/sales-composition` | 매출 산업구성 원그래프 | 항목 개수, 색상 동적 | ✅ | |
| `GET /companies/{code}/financial-overview` | 재무 현황 (차트+표) | 연도 개수 동적 | ✅ | ✅ |
| `GET /companies/{code}/financial-health` | 재무건전성 | scoreValue 동적, 6개 카테고리 고정 | ✅ | |
| `GET /companies/{code}/industry-description` | 산업 설명 표 | 키-값 개수 동적 | ✅ | |
| `GET /companies/{code}/financial-ratio-judgment` | 재무 비율 판정 | 테이블 행 동적 | | ✅ |
| `GET /companies/{code}/financial-analysis-details` | 상세 분석 (3~6번) | 헤더, 항목, 트리 구조 전부 동적 | | ✅ |

---

## 🎨 프론트엔드 구현 가이드

### 재무건전성 프로그레스바

```typescript
// 점수 위치 계산 (-1~1 → 0~100%)
const scorePosition = ((scoreValue + 1) / 2) * 100;

// 화살표 색상 결정
const getArrowColor = (score: number): string => {
  if (score < -0.5) return '#EB0E0E'; // 빨간색 (위험)
  if (score < 0.5) return '#F59E0B';  // 노란색 (경고)
  return '#0042FB';                    // 파란색 (안전)
};

// 박스 테두리 색상
const getStatusColor = (status: string): string => {
  switch (status) {
    case '안전': return '#0042FB';
    case '경고': return '#F59E0B';
    case '위험': return '#EB0E0E';
    default: return '#0042FB';
  }
};
```

### 트리 테이블 확장 로직

```typescript
const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

const toggleExpand = (itemName: string) => {
  const newExpanded = new Set(expandedItems);
  if (newExpanded.has(itemName)) {
    newExpanded.delete(itemName);
  } else {
    newExpanded.add(itemName);
  }
  setExpandedItems(newExpanded);
};

// 렌더링
{item.children && item.children.length > 0 && (
  <button onClick={() => toggleExpand(item.name)}>
    {expandedItems.has(item.name) ? (
      <img src="/minus_square.svg" alt="축소" />
    ) : (
      <img src="/square.svg" alt="확장" />
    )}
  </button>
)}
```

### 동적 테이블 헤더 렌더링

```typescript
// tableHeaders 배열을 순회하여 헤더 생성
<thead>
  <tr>
    {subsection.tableHeaders.map((header) => (
      <th key={header.key}>{header.label}</th>
    ))}
  </tr>
</thead>
<tbody>
  {subsection.items.map((item) => (
    <tr key={item.name}>
      <td>{item.name}</td>
      {subsection.tableHeaders.slice(1).map((header) => (
        <td key={header.key}>
          {typeof item.values[header.key] === 'number'
            ? item.values[header.key].toLocaleString('ko-KR')
            : item.values[header.key]}
        </td>
      ))}
    </tr>
  ))}
</tbody>
```

---

## 📝 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0.0 | 2025-12-18 | 초안 작성 |

---

## 📞 문의

API 관련 문의사항은 백엔드 팀에 문의해주세요.
