import asyncio
import uuid,json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from program_tool import *
from ai.ai_chatting_queue_controller import *
from data.data_controller import DataController
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

class ClientRequest(BaseModel):
    user_id:str
    question:str
    tab_name:str
    company_name:str

#========[전처리]=====

scon = ServerQueueController(2,1000)
dcon = DataController()

# task_results = {}
active_connections = {}

#==========[execute server]========


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("server start")
    await scon.run()
    yield

    print("server shut down")
    await scon.stop()
    await asyncio.gather(*scon.workers,return_exceptions=True)


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://pb-ai-web.vercel.app",  # trailing slash 제거
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health Check (배포용)
@app.get('/health')
async def health_check():
    return {"status": "healthy", "message": "PB.ai Server is running"}

@app.get('/')
async def root():
    return {"message": "PB.ai Server API", "docs": "/docs"}

@app.post('/ask')
async def client_ask(req:ClientRequest):
    task_id = str(uuid.uuid4())
    queue_data = ServerQueueData(QueueItem(
        type = "question",
        user_id=req.user_id,
        question= req.question,
        tab_name= req.tab_name,
        company_name=req.company_name,
        user_level= 1))
    response = await scon.put_task(queue_data)

    return response

@app.post('/prevqna/company')
async def get_prev_qna_company(req:ClientRequest):
    task_id = str(uuid.uuid4())
    queue_data = ServerQueueData(QueueItem(
        type = "prev_qna_by_company",
        user_id=req.user_id,
        company_name=req.company_name,
        tab_name=req.tab_name,
        user_level= 1))
    response = await scon.put_task(queue_data)

    return response


@app.post('/prevqna/session')
async def get_prev_qna_session(req:ClientRequest):
    task_id = str(uuid.uuid4())
    queue_data = ServerQueueData(QueueItem(
        type = "prev_qna_session",
        user_id=req.user_id,
        user_level= 1))
    response = await scon.put_task(queue_data)

    return response

@app.post('/prevqna/delete')
async def delete_prev_qna_session(req:ClientRequest):
    task_id = str(uuid.uuid4())
    queue_data = ServerQueueData(QueueItem(
        type = "delete_session",
        user_id=req.user_id,
        company_name=req.company_name,
        tab_name=req.tab_name,
        user_level= 1,
        ))
    response = await scon.put_task(queue_data)

    return response

#=================

def get_company_data(ticker):
        try:
            with open(f'data/{ticker}.json', 'r', encoding='utf-8') as f:
                cdict = json.load(f)
            return cdict
        except FileNotFoundError:
            return None

@app.get('/api/v1/companies/{ticker}/profile')
def get_company_profile(ticker:str):
    data = get_company_data(ticker)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Company data not found for ticker: {ticker}")

    리포트오버뷰 = data.get("리포트오버뷰", {})
    profile = 리포트오버뷰.get("기업프로필", {})

    response = {
        "companyCode": profile.get("티커", ""),
        "companyName": profile.get("기업이름", ""),
        "profile": profile  # 기업프로필 전체를 그대로 포함
    }
    return response

@app.get('/api/v1/companies/{ticker}/sales-composition')
def get_company_sales_composition(ticker:str):
    data = get_company_data(ticker)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Company data not found for ticker: {ticker}")

    sales_comp = data["리포트오버뷰"].get("매출산업구성", {})

    # 색상 팔레트
    colors = ["#5797F7", "#FFA353", "#8DD3BB", "#FFD666", "#A78BFA", "#FB7185"]

    items = []
    for idx, (name, value) in enumerate(sales_comp.items()):
        items.append({
            "name": name,
            "value": abs(float(value)),
            "percentage": f"{value}%" if value >= 0 else f"-{abs(value)}%",
            "color": colors[idx % len(colors)]
        })

    # 총 매출액 계산
    financial_data = data["리포트오버뷰"].get("재무현황", {})
    latest_year = max(financial_data.keys()) if financial_data else "2024"
    total_revenue = financial_data.get(latest_year, {}).get("매출액", "0")

    response = {
        "totalRevenue": total_revenue,
        "totalRevenueRaw": 0,  # TODO: 실제 숫자값으로 변환 필요
        "items": items
    }
    return response

def safe_get(data, *keys, default="-"):
    """중첩된 딕셔너리에서 안전하게 값을 가져옵니다."""
    result = data
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key)
            if result is None:
                return default
        else:
            return default
    return result if result is not None else default

def safe_divide(numerator, denominator, default="-"):
    """안전하게 나눗셈을 수행합니다."""
    try:
        if denominator and float(denominator) != 0:
            return (float(numerator) / float(denominator)) * 100
        return default
    except (ValueError, TypeError, ZeroDivisionError):
        return default

def parse_korean_number(text):
    """한국어 숫자 표현을 숫자로 변환 (예: '29.36조' -> 29360000000000)"""
    import re
    if not text or text == "0":
        return 0

    text = str(text).replace(",", "").replace(" ", "")

    # 조, 억, 만 단위 처리
    multipliers = {"조": 1000000000000, "억": 100000000, "만": 10000}

    total = 0
    for unit, multiplier in multipliers.items():
        if unit in text:
            parts = text.split(unit)
            try:
                num = float(parts[0])
                total += num * multiplier
                text = parts[1] if len(parts) > 1 else ""
            except:
                pass

    # 남은 숫자 처리
    try:
        if text:
            total += float(text)
    except:
        pass

    return int(total)

@app.get('/api/v1/companies/{ticker}/financial-overview')
def get_company_financial_overview(ticker:str):
    data = get_company_data(ticker)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Company data not found for ticker: {ticker}")

    리포트오버뷰 = data.get("리포트오버뷰", {})
    financial_data = 리포트오버뷰.get("재무현황", {})
    response = {"revenueChart":[],"netIncomeChart":[],"financialTable":[]}

    # 연도별로 정렬
    for year in sorted(financial_data.keys()):
        values = financial_data[year]

        # 매출액 차트 데이터
        revenue_str = values.get("매출액", "0")
        revenue_value = parse_korean_number(revenue_str)
        response["revenueChart"].append({
            "year": year,
            "value": revenue_value
        })

        # 순이익 차트 데이터
        net_income_str = values.get("당기순이익", "0")
        net_income_value = parse_korean_number(net_income_str)
        net_income_rate = (net_income_value / revenue_value * 100) if revenue_value > 0 else 0

        response["netIncomeChart"].append({
            "year": year,
            "netIncome": net_income_value,
            "netIncomeRate": round(net_income_rate, 1)
        })

        # 재무 테이블 데이터
        operating_income_str = values.get("영업이익", "0")
        operating_income_value = parse_korean_number(operating_income_str)
        response["financialTable"].append({
            "year": year,
            "revenue": revenue_value,
            "totalAssets": parse_korean_number(values.get("자산총계", "0")),
            "totalLiabilities": parse_korean_number(values.get("부채총계", "0")),
            "totalEquity": parse_korean_number(values.get("자본총계", "0")),
            "operatingIncome": operating_income_value,
            "netIncome": net_income_value
        })

    return response

@app.get('/api/v1/companies/{ticker}/financial-health')
def get_company_financial_health(ticker:str):
    data = get_company_data(ticker)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Company data not found for ticker: {ticker}")
    리포트재무현황분석 = data.get("리포트재무현황분석", {})
    dt = 리포트재무현황분석.get("재무비율판정", {})
    judge = dt.get("지표판정", {})
    response = {
        "description": "재무건전성은 필수소비재 섹터 업종 중위수와 시계열 점수로 판정됩니다",
        "scoreValue": float(dt.get("점수", 0)),
        "scoreRange": {
            "min": -1,
            "max": 1,
            "thresholds": [-1, -0.5, 0, 0.5, 1]
        },
        "healthCategories": [
            { "label": "유동성", "status": judge.get("유동성", "-") },
            { "label": "레버리지", "status": judge.get("레버리지", "-") },
            { "label": "투자수익성", "status": judge.get("투자수익성", "-") },
            { "label": "판매마진", "status": judge.get("판매마진", "-") },
            { "label": "활동성", "status": judge.get("활동성", "-") },
            { "label": "성장성", "status": judge.get("성장성", "-") }
        ]
    }
    return response

@app.get('/api/v1/companies/{ticker}/industry-description')
def get_company_industry_description(ticker:str):
    data = get_company_data(ticker)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Company data not found for ticker: {ticker}")
    리포트오버뷰 = data.get("리포트오버뷰", {})
    dt = 리포트오버뷰.get("산업설명", {})
    response = {
        "items": [
            { "label": "산업명", "value": dt.get("산업명", "-") },
            { "label": "평가기준일", "value": dt.get("평가기준일", "-") },
            { "label": "산업평가 종합등급", "value": dt.get("산업평가종합등급", "-") }
        ]
    }
    return response

@app.get('/api/v1/companies/{ticker}/financial-ratio-judgment')
def get_company_financial_ratio_judgment(ticker:str):
    data = get_company_data(ticker)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Company data not found for ticker: {ticker}")
    리포트재무현황분석 = data.get("리포트재무현황분석", {})
    dt = 리포트재무현황분석.get("재무비율판정", {})
    judge = dt.get("지표판정", {})
    point = dt.get("지표점수", {})
    response = {
        "financialHealth": {
            "scoreValue": float(dt.get("점수", 0)),
            "scoreRange": {
            "min": -1,
            "max": 1,
            "thresholds": [-1, -0.5, 0, 0.5, 1]
            },
            "healthCategories": [
            { "label": "유동성", "status": judge.get("유동성", "-") },
            { "label": "레버리지", "status": judge.get("레버리지", "-") },
            { "label": "투자수익성", "status": judge.get("투자수익성", "-") },
            { "label": "판매마진", "status": judge.get("판매마진", "-") },
            { "label": "활동성", "status": judge.get("활동성", "-") },
            { "label": "성장성", "status": judge.get("성장성", "-") }
            ]
        },
        "ratioJudgmentTable": [
            {
            "indicator": "지표 점수",
            "stability": point.get("유동성", "-"),
            "leverage": point.get("레버리지", "-"),
            "investmentProfitability": point.get("투자수익성", "-"),
            "salesMargin": point.get("판매마진", "-"),
            "activity": point.get("활동성", "-"),
            "growth": point.get("성장성", "-")
            }
        ]
    }
    return response


@app.get('/api/v1/companies/{ticker}/financial-analysis-details')
def get_company_financial_analysis_details(ticker:str):
    data = get_company_data(ticker)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Company data not found for ticker: {ticker}")
    리포트재무현황분석 = data.get("리포트재무현황분석", {})
    st = 리포트재무현황분석.get("유동성분석", {})
    lv = 리포트재무현황분석.get("레버리지분석", {})
    pr = 리포트재무현황분석.get("투자수익성분석", {})
    mg = 리포트재무현황분석.get("판매마진분석", {})
    gr = 리포트재무현황분석.get("성장성분석", {})
    at = 리포트재무현황분석.get("활동성분석", {})

    response = {
    "sections": [
        {
        "id": "stability",
        "title": "3. 안정성 분석",
        "subsections": [
            {
            "title": "3.1. 유동성 분석",
            "tableHeaders": [
                { "key": "indicator", "label": "" },
                { "key": "year2024", "label": "2024" },
                { "key": "timeSeriesAverage", "label": "시계열평균" },
                { "key": "industryMedian", "label": "업종중위수" },
                { "key": "timeSeriesScore", "label": "시계열점수" },
                { "key": "industryScore", "label": "업종점수" }
            ],
            "items":
            [
                {
                    "name": "유동비율",
                    "values": {
                    "year2024": safe_get(st, "유동비율", "데이터", default="-"),
                    "timeSeriesAverage": f'{safe_divide(safe_get(st, "유동비율", "시계열평균분자", default="0"), safe_get(st, "유동비율", "시계열평균분모", default="1"), default=0)}%' if safe_get(st, "유동비율", "시계열평균분자") != "-" and safe_get(st, "유동비율", "시계열평균분모") != "-" else "-",
                    "industryMedian": f"{safe_get(st, '유동비율', '업종중위수', default='-')}%" if safe_get(st, '유동비율', '업종중위수') != "-" else "-",
                    "timeSeriesScore": safe_get(st, "유동비율", "시계열점수", default="-"),
                    "industryScore": safe_get(st, "유동비율", "업종점수", default="-")
                    },
                    "children": [
                    {
                        "name": "유동자산",
                        "values": {
                        "year2024": safe_get(st, "유동비율", "데이터분자값", default="-"),
                        "timeSeriesAverage": safe_get(st, "유동비율", "시계열평균분자", default="-"),
                        "industryMedian": "-",
                        "timeSeriesScore": "-",
                        "industryScore": "-"
                        },
                        "children": []
                    },
                    {
                        "name": "유동부채",
                        "values": {
                        "year2024": safe_get(st, "유동비율", "데이터분모값", default="-"),
                        "timeSeriesAverage": safe_get(st, "유동비율", "시계열평균분모", default="-"),
                        "industryMedian": "-",
                        "timeSeriesScore": "-",
                        "industryScore": "-"
                        },
                        "children": []
                    }
                    ]
                },
                {
                    "name": "당좌비율",
                    "values": {
                    "year2024": safe_get(st, "당좌비율", "데이터", default="-"),
                    "timeSeriesAverage": f'{safe_divide(safe_get(st, "당좌비율", "시계열평균분자", default="-"), safe_get(st, "당좌비율", "시계열평균분모", default="-"), default=0)}%' if safe_get(st, "당좌비율", "시계열평균분자", default="-") != "-" and safe_get(st, "당좌비율", "시계열평균분모", default="-") != "-" else "-",
                    "industryMedian": f"{st['당좌비율'].get('업종중위수', '-')}%" if st['당좌비율'].get('업종중위수') else "-",
                    "timeSeriesScore": st["당좌비율"].get("시계열점수", "-"),
                    "industryScore": st["당좌비율"].get("업종점수", "-")
                    },
                    "children": [
                    {
                        "name": "당좌자산",
                        "values": {
                        "year2024": safe_get(st, "당좌비율", "데이터분자값", default="-"),
                        "timeSeriesAverage": safe_get(st, "당좌비율", "시계열평균분자", default="-"),
                        "industryMedian": "-",
                        "timeSeriesScore": "-",
                        "industryScore": "-"
                        },
                        "children": []
                    },
                    {
                        "name": "유동부채",
                        "values": {
                        "year2024": safe_get(st, "당좌비율", "데이터분모값", default="-"),
                        "timeSeriesAverage": safe_get(st, "당좌비율", "시계열평균분모", default="-"),
                        "industryMedian": "-",
                        "timeSeriesScore": "-",
                        "industryScore": "-"
                        },
                        "children": []
                    }
                    ]
                },

                {
                    "name": "현금비율",
                    "values": {
                    "year2024": safe_get(st, "현금비율", "데이터", default="-"),
                    "timeSeriesAverage": f'{safe_divide(safe_get(st, "현금비율", "시계열평균분자", default="-"), safe_get(st, "현금비율", "시계열평균분모", default="-"), default=0)}%' if safe_get(st, "현금비율", "시계열평균분자", default="-") != "-" and safe_get(st, "현금비율", "시계열평균분모", default="-") != "-" else "-",
                    "industryMedian": f"{st['현금비율'].get('업종중위수', '-')}%" if st['현금비율'].get('업종중위수') else "-",
                    "timeSeriesScore": st["현금비율"].get("시계열점수", "-"),
                    "industryScore": st["현금비율"].get("업종점수", "-")
                    },
                    "children": [
                    {
                        "name": "현금및현금성자산",
                        "values": {
                        "year2024": safe_get(st, "현금비율", "데이터분자값", default="-"),
                        "timeSeriesAverage": safe_get(st, "현금비율", "시계열평균분자", default="-"),
                        "industryMedian": "-",
                        "timeSeriesScore": "-",
                        "industryScore": "-"
                        },
                        "children": []
                    },
                    {
                        "name": "유동부채",
                        "values": {
                        "year2024": safe_get(st, "현금비율", "데이터분모값", default="-"),
                        "timeSeriesAverage": safe_get(st, "현금비율", "시계열평균분모", default="-"),
                        "industryMedian": "-",
                        "timeSeriesScore": "-",
                        "industryScore": "-"
                        },
                        "children": []
                    }
                    ]
                },

                {
                    "name": "순운전자본대총자본",
                    "values": {
                    "year2024": safe_get(st, "순운전자본대총자본", "데이터", default="-"),
                    "timeSeriesAverage": f'{safe_divide(safe_get(st, "순운전자본대총자본", "시계열평균분자", default="-"), safe_get(st, "순운전자본대총자본", "시계열평균분모", default="-"), default=0)}%' if safe_get(st, "순운전자본대총자본", "시계열평균분자", default="-") != "-" and safe_get(st, "순운전자본대총자본", "시계열평균분모", default="-") != "-" else "-",
                    "industryMedian": f"{st['순운전자본대총자본'].get('업종중위수', '-')}%" if st['순운전자본대총자본'].get('업종중위수') else "-",
                    "timeSeriesScore": st["순운전자본대총자본"].get("시계열점수", "-"),
                    "industryScore": st["순운전자본대총자본"].get("업종점수", "-")
                    },
                    "children": [
                    {
                        "name": "유동자산+유동부채",
                        "values": {
                        "year2024": safe_get(st, "순운전자본대총자본", "데이터분자값", default="-"),
                        "timeSeriesAverage": safe_get(st, "순운전자본대총자본", "시계열평균분자", default="-"),
                        "industryMedian": "-",
                        "timeSeriesScore": "-",
                        "industryScore": "-"
                        },
                        "children": []
                    },
                    {
                        "name": "자산총계",
                        "values": {
                        "year2024": safe_get(st, "순운전자본대총자본", "데이터분모값", default="-"),
                        "timeSeriesAverage": safe_get(st, "순운전자본대총자본", "시계열평균분모", default="-"),
                        "industryMedian": "-",
                        "timeSeriesScore": "-",
                        "industryScore": "-"
                        },
                        "children": []
                    }
                    ]
                },

                {
                    "name": "비유동비율",
                    "values": {
                    "year2024": safe_get(st, "비유동비율", "데이터", default="-"),
                    "timeSeriesAverage": f'{safe_divide(safe_get(st, "비유동비율", "시계열평균분자", default="-"), safe_get(st, "비유동비율", "시계열평균분모", default="-"), default=0)}%' if safe_get(st, "비유동비율", "시계열평균분자", default="-") != "-" and safe_get(st, "비유동비율", "시계열평균분모", default="-") != "-" else "-",
                    "industryMedian": f"{st['비유동비율'].get('업종중위수', '-')}%" if st['비유동비율'].get('업종중위수') else "-",
                    "timeSeriesScore": st["비유동비율"].get("시계열점수", "-"),
                    "industryScore": st["비유동비율"].get("업종점수", "-")
                    },
                    "children": [
                    {
                        "name": "비유동자산",
                        "values": {
                        "year2024": safe_get(st, "비유동비율", "데이터분자값", default="-"),
                        "timeSeriesAverage": safe_get(st, "비유동비율", "시계열평균분자", default="-"),
                        "industryMedian": "-",
                        "timeSeriesScore": "-",
                        "industryScore": "-"
                        },
                        "children": []
                    },
                    {
                        "name": "자본총계",
                        "values": {
                        "year2024": safe_get(st, "비유동비율", "데이터분모값", default="-"),
                        "timeSeriesAverage": safe_get(st, "비유동비율", "시계열평균분모", default="-"),
                        "industryMedian": "-",
                        "timeSeriesScore": "-",
                        "industryScore": "-"
                        },
                        "children": []
                    }
                    ]
                },

                {
                    "name": "비유동장기적합률",
                    "values": {
                    "year2024": safe_get(st, "비유동장기적합률", "데이터", default="-"),
                    "timeSeriesAverage": f'{safe_divide(safe_get(st, "비유동장기적합률", "시계열평균분자", default="-"), safe_get(st, "비유동장기적합률", "시계열평균분모", default="-"), default=0)}%' if safe_get(st, "비유동장기적합률", "시계열평균분자", default="-") != "-" and safe_get(st, "비유동장기적합률", "시계열평균분모", default="-") != "-" else "-",
                    "industryMedian": f"{st['비유동장기적합률'].get('업종중위수', '-')}%" if st['비유동장기적합률'].get('업종중위수') else "-",
                    "timeSeriesScore": st["비유동장기적합률"].get("시계열점수", "-"),
                    "industryScore": st["비유동장기적합률"].get("업종점수", "-")
                    },
                    "children": [
                    {
                        "name": "비유동자산",
                        "values": {
                        "year2024": safe_get(st, "비유동장기적합률", "데이터분자값", default="-"),
                        "timeSeriesAverage": safe_get(st, "비유동장기적합률", "시계열평균분자", default="-"),
                        "industryMedian": "-",
                        "timeSeriesScore": "-",
                        "industryScore": "-"
                        },
                        "children": []
                    },
                    {
                        "name": "자본총계+비유동부채",
                        "values": {
                        "year2024": safe_get(st, "비유동장기적합률", "데이터분모값", default="-"),
                        "timeSeriesAverage": safe_get(st, "비유동장기적합률", "시계열평균분모", default="-"),
                        "industryMedian": "-",
                        "timeSeriesScore": "-",
                        "industryScore": "-"
                        },
                        "children": []
                    }
                    ]
                }
                ]

            },
            {
            "title": "3.2. 레버리지 분석",
            "tableHeaders": [
                { "key": "indicator", "label": "" },
                { "key": "year2024", "label": "2024" },
                { "key": "timeSeriesAverage", "label": "시계열평균" },
                { "key": "industryMedian", "label": "업종중위수" },
                { "key": "timeSeriesScore", "label": "시계열점수" },
                { "key": "industryScore", "label": "업종점수" }
            ],
            "items":
            [
    {
        "name": "부채비율",
        "values": {
        "year2024": safe_get(lv, "부채비율", "데이터", default="-"),
        "timeSeriesAverage": f'{safe_divide(safe_get(lv, "부채비율", "시계열평균분자", default="-"), safe_get(lv, "부채비율", "시계열평균분모", default="-"), default=0)}%' if safe_get(lv, "부채비율", "시계열평균분자", default="-") != "-" and safe_get(lv, "부채비율", "시계열평균분모", default="-") != "-" else "-",
        "industryMedian": f"{lv['부채비율'].get('업종중위수', '-')}%" if lv['부채비율'].get('업종중위수') else "-",
        "timeSeriesScore": lv["부채비율"].get("시계열점수", "-"),
        "industryScore": lv["부채비율"].get("업종점수", "-")
        },
        "children": [
        {
            "name": "부채총계",
            "values": {
            "year2024": safe_get(lv, "부채비율", "데이터분자값", default="-"),
            "timeSeriesAverage": safe_get(lv, "부채비율", "시계열평균분자", default="-"),
            "industryMedian": "-",
            "timeSeriesScore": "-",
            "industryScore": "-"
            },
            "children": []
        },
        {
            "name": "자본총계",
            "values": {
            "year2024": safe_get(lv, "부채비율", "데이터분모값", default="-"),
            "timeSeriesAverage": safe_get(lv, "부채비율", "시계열평균분모", default="-"),
            "industryMedian": "-",
            "timeSeriesScore": "-",
            "industryScore": "-"
            },
            "children": []
        }
        ]
    },

    {
        "name": "자기자본비율",
        "values": {
        "year2024": safe_get(lv, "자기자본비율", "데이터", default="-"),
        "timeSeriesAverage": f'{safe_divide(safe_get(lv, "자기자본비율", "시계열평균분자", default="-"), safe_get(lv, "자기자본비율", "시계열평균분모", default="-"), default=0)}%' if safe_get(lv, "자기자본비율", "시계열평균분자", default="-") != "-" and safe_get(lv, "자기자본비율", "시계열평균분모", default="-") != "-" else "-",
        "industryMedian": f"{lv['자기자본비율'].get('업종중위수', '-')}%" if lv['자기자본비율'].get('업종중위수') else "-",
        "timeSeriesScore": lv["자기자본비율"].get("시계열점수", "-"),
        "industryScore": lv["자기자본비율"].get("업종점수", "-")
        },
        "children": [
        {
            "name": "자본총계",
            "values": {
            "year2024": safe_get(lv, "자기자본비율", "데이터분자값", default="-"),
            "timeSeriesAverage": safe_get(lv, "자기자본비율", "시계열평균분자", default="-"),
            "industryMedian": "-",
            "timeSeriesScore": "-",
            "industryScore": "-"
            },
            "children": []
        },
        {
            "name": "자산총계",
            "values": {
            "year2024": safe_get(lv, "자기자본비율", "데이터분모값", default="-"),
            "timeSeriesAverage": safe_get(lv, "자기자본비율", "시계열평균분모", default="-"),
            "industryMedian": "-",
            "timeSeriesScore": "-",
            "industryScore": "-"
            },
            "children": []
        }
        ]
    },

    {
        "name": "유동부채비율",
        "values": {
        "year2024": safe_get(lv, "유동부채비율", "데이터", default="-"),
        "timeSeriesAverage": f'{safe_divide(safe_get(lv, "유동부채비율", "시계열평균분자", default="-"), safe_get(lv, "유동부채비율", "시계열평균분모", default="-"), default=0)}%' if safe_get(lv, "유동부채비율", "시계열평균분자", default="-") != "-" and safe_get(lv, "유동부채비율", "시계열평균분모", default="-") != "-" else "-",
        "industryMedian": f"{lv['유동부채비율'].get('업종중위수', '-')}%" if lv['유동부채비율'].get('업종중위수') else "-",
        "timeSeriesScore": lv["유동부채비율"].get("시계열점수", "-"),
        "industryScore": lv["유동부채비율"].get("업종점수", "-")
        },
        "children": [
        {
            "name": "유동부채",
            "values": {
            "year2024": safe_get(lv, "유동부채비율", "데이터분자값", default="-"),
            "timeSeriesAverage": safe_get(lv, "유동부채비율", "시계열평균분자", default="-"),
            "industryMedian": "-",
            "timeSeriesScore": "-",
            "industryScore": "-"
            },
            "children": []
        },
        {
            "name": "자본총계",
            "values": {
            "year2024": safe_get(lv, "유동부채비율", "데이터분모값", default="-"),
            "timeSeriesAverage": safe_get(lv, "유동부채비율", "시계열평균분모", default="-"),
            "industryMedian": "-",
            "timeSeriesScore": "-",
            "industryScore": "-"
            },
            "children": []
        }
        ]
    },

    {
        "name": "비유동부채비율",
        "values": {
        "year2024": safe_get(lv, "비유동부채비율", "데이터", default="-"),
        "timeSeriesAverage": f'{safe_divide(safe_get(lv, "비유동부채비율", "시계열평균분자", default="-"), safe_get(lv, "비유동부채비율", "시계열평균분모", default="-"), default=0)}%' if safe_get(lv, "비유동부채비율", "시계열평균분자", default="-") != "-" and safe_get(lv, "비유동부채비율", "시계열평균분모", default="-") != "-" else "-",
        "industryMedian": f"{lv['비유동부채비율'].get('업종중위수', '-')}%" if lv['비유동부채비율'].get('업종중위수') else "-",
        "timeSeriesScore": lv["비유동부채비율"].get("시계열점수", "-"),
        "industryScore": lv["비유동부채비율"].get("업종점수", "-")
        },
        "children": [
        {
            "name": "비유동부채",
            "values": {
            "year2024": safe_get(lv, "비유동부채비율", "데이터분자값", default="-"),
            "timeSeriesAverage": safe_get(lv, "비유동부채비율", "시계열평균분자", default="-"),
            "industryMedian": "-",
            "timeSeriesScore": "-",
            "industryScore": "-"
            },
            "children": []
        },
        {
            "name": "자본총계",
            "values": {
            "year2024": safe_get(lv, "비유동부채비율", "데이터분모값", default="-"),
            "timeSeriesAverage": safe_get(lv, "비유동부채비율", "시계열평균분모", default="-"),
            "industryMedian": "-",
            "timeSeriesScore": "-",
            "industryScore": "-"
            },
            "children": []
        }
        ]
    },

    {
        "name": "차입금의존도",
        "values": {
        "year2024": safe_get(lv, "차입금의존도", "데이터", default="-"),
        "timeSeriesAverage": f'{safe_divide(safe_get(lv, "차입금의존도", "시계열평균분자", default="-"), safe_get(lv, "차입금의존도", "시계열평균분모", default="-"), default=0)}%' if safe_get(lv, "차입금의존도", "시계열평균분자", default="-") != "-" and safe_get(lv, "차입금의존도", "시계열평균분모", default="-") != "-" else "-",
        "industryMedian": f"{lv['차입금의존도'].get('업종중위수', '-')}%" if lv['차입금의존도'].get('업종중위수') else "-",
        "timeSeriesScore": lv["차입금의존도"].get("시계열점수", "-"),
        "industryScore": lv["차입금의존도"].get("업종점수", "-")
        },
        "children": [
        {
            "name": "차입금(이자지급부채)",
            "values": {
            "year2024": safe_get(lv, "차입금의존도", "데이터분자값", default="-"),
            "timeSeriesAverage": safe_get(lv, "차입금의존도", "시계열평균분자", default="-"),
            "industryMedian": "-",
            "timeSeriesScore": "-",
            "industryScore": "-"
            },
            "children": []
        },
        {
            "name": "자산총계",
            "values": {
            "year2024": safe_get(lv, "차입금의존도", "데이터분모값", default="-"),
            "timeSeriesAverage": safe_get(lv, "차입금의존도", "시계열평균분모", default="-"),
            "industryMedian": "-",
            "timeSeriesScore": "-",
            "industryScore": "-"
            },
            "children": []
        }
        ]
    },

    {
        "name": "차입금대매출액",
        "values": {
        "year2024": safe_get(lv, "차입금대매출액", "데이터", default="-"),
        "timeSeriesAverage": f'{safe_divide(safe_get(lv, "차입금대매출액", "시계열평균분자", default="-"), safe_get(lv, "차입금대매출액", "시계열평균분모", default="-"), default=0)}%' if safe_get(lv, "차입금대매출액", "시계열평균분자", default="-") != "-" and safe_get(lv, "차입금대매출액", "시계열평균분모", default="-") != "-" else "-",
        "industryMedian": f"{lv['차입금대매출액'].get('업종중위수', '-')}%" if lv['차입금대매출액'].get('업종중위수') else "-",
        "timeSeriesScore": lv["차입금대매출액"].get("시계열점수", "-"),
        "industryScore": lv["차입금대매출액"].get("업종점수", "-")
        },
        "children": [
        {
            "name": "차입금(이자지급부채)",
            "values": {
            "year2024": safe_get(lv, "차입금대매출액", "데이터분자값", default="-"),
            "timeSeriesAverage": safe_get(lv, "차입금대매출액", "시계열평균분자", default="-"),
            "industryMedian": "-",
            "timeSeriesScore": "-",
            "industryScore": "-"
            },
            "children": []
        },
        {
            "name": "매출액",
            "values": {
            "year2024": safe_get(lv, "차입금대매출액", "데이터분모값", default="-"),
            "timeSeriesAverage": safe_get(lv, "차입금대매출액", "시계열평균분모", default="-"),
            "industryMedian": "-",
            "timeSeriesScore": "-",
            "industryScore": "-"
            },
            "children": []
        }
        ]
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
                { "key": "year2024", "label": "2024" },
                { "key": "timeSeriesAverage", "label": "시계열평균" },
                { "key": "industryMedian", "label": "업종중위수" },
                { "key": "timeSeriesScore", "label": "시계열점수" },
                { "key": "industryScore", "label": "업종점수" }
            ],
            "items":
            [
            {
                "name": "총자산세전수익률",
                "values": {
                "year2024": safe_get(pr, "총자산세전수익률", "데이터", default="-"),
                "timeSeriesAverage": f'{safe_divide(safe_get(pr, "총자산세전수익률", "시계열평균분자", default="-"), safe_get(pr, "총자산세전수익률", "시계열평균분모", default="-"), default=0)}%' if safe_get(pr, "총자산세전수익률", "시계열평균분자", default="-") != "-" and safe_get(pr, "총자산세전수익률", "시계열평균분모", default="-") != "-" else "-",
                "industryMedian": f"{pr['총자산세전수익률'].get('업종중위수', '-')}%" if pr['총자산세전수익률'].get('업종중위수') else "-",
                "timeSeriesScore": pr["총자산세전수익률"].get("시계열점수", "-"),
                "industryScore": pr["총자산세전수익률"].get("업종점수", "-")
                },
                "children": [
                {
                    "name": "법인세비용차감전순이익",
                    "values": {
                    "year2024": safe_get(pr, "총자산세전수익률", "데이터분자값", default="-"),
                    "timeSeriesAverage": safe_get(pr, "총자산세전수익률", "시계열평균분자", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "당기순이익",
                    "values": {
                    "year2024": safe_get(pr, "총자산세전수익률", "데이터분모값", default="-"),
                    "timeSeriesAverage": safe_get(pr, "총자산세전수익률", "시계열평균분모", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                }
                ]
            },

            {
                "name": "총자산순이익률",
                "values": {
                "year2024": safe_get(pr, "총자산순이익률", "데이터", default="-"),
                "timeSeriesAverage": f'{safe_divide(safe_get(pr, "총자산순이익률", "시계열평균분자", default="-"), safe_get(pr, "총자산순이익률", "시계열평균분모", default="-"), default=0)}%' if safe_get(pr, "총자산순이익률", "시계열평균분자", default="-") != "-" and safe_get(pr, "총자산순이익률", "시계열평균분모", default="-") != "-" else "-",
                "industryMedian": f"{pr['총자산순이익률'].get('업종중위수', '-')}%" if pr['총자산순이익률'].get('업종중위수') else "-",
                "timeSeriesScore": pr["총자산순이익률"].get("시계열점수", "-"),
                "industryScore": pr["총자산순이익률"].get("업종점수", "-")
                },
                "children": [
                {
                    "name": "당기순이익",
                    "values": {
                    "year2024": safe_get(pr, "총자산순이익률", "데이터분자값", default="-"),
                    "timeSeriesAverage": safe_get(pr, "총자산순이익률", "시계열평균분자", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "자산총계",
                    "values": {
                    "year2024": safe_get(pr, "총자산순이익률", "데이터분모값", default="-"),
                    "timeSeriesAverage": safe_get(pr, "총자산순이익률", "시계열평균분모", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                }
                ]
            },

            {
                "name": "기업세전순이익률",
                "values": {
                "year2024": safe_get(pr, "기업세전순이익률", "데이터", default="-"),
                "timeSeriesAverage": f'{safe_divide(safe_get(pr, "기업세전순이익률", "시계열평균분자", default="-"), safe_get(pr, "기업세전순이익률", "시계열평균분모", default="-"), default=0)}%' if safe_get(pr, "기업세전순이익률", "시계열평균분자", default="-") != "-" and safe_get(pr, "기업세전순이익률", "시계열평균분모", default="-") != "-" else "-",
                "industryMedian": f"{pr['기업세전순이익률'].get('업종중위수', '-')}%" if pr['기업세전순이익률'].get('업종중위수') else "-",
                "timeSeriesScore": pr["기업세전순이익률"].get("시계열점수", "-"),
                "industryScore": pr["기업세전순이익률"].get("업종점수", "-")
                },
                "children": [
                {
                    "name": "법인세비용차감전순이익+이자비용",
                    "values": {
                    "year2024": safe_get(pr, "기업세전순이익률", "데이터분자값", default="-"),
                    "timeSeriesAverage": safe_get(pr, "기업세전순이익률", "시계열평균분자", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "당기순이익+이자비용",
                    "values": {
                    "year2024": safe_get(pr, "기업세전순이익률", "데이터분모값", default="-"),
                    "timeSeriesAverage": safe_get(pr, "기업세전순이익률", "시계열평균분모", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                }
                ]
            },

            {
                "name": "기업순이익률",
                "values": {
                "year2024": safe_get(pr, "기업순이익률", "데이터", default="-"),
                "timeSeriesAverage": f'{safe_divide(safe_get(pr, "기업순이익률", "시계열평균분자", default="-"), safe_get(pr, "기업순이익률", "시계열평균분모", default="-"), default=0)}%' if safe_get(pr, "기업순이익률", "시계열평균분자", default="-") != "-" and safe_get(pr, "기업순이익률", "시계열평균분모", default="-") != "-" else "-",
                "industryMedian": f"{pr['기업순이익률'].get('업종중위수', '-')}%" if pr['기업순이익률'].get('업종중위수') else "-",
                "timeSeriesScore": pr["기업순이익률"].get("시계열점수", "-"),
                "industryScore": pr["기업순이익률"].get("업종점수", "-")
                },
                "children": [
                {
                    "name": "당기순이익+이자비용",
                    "values": {
                    "year2024": safe_get(pr, "기업순이익률", "데이터분자값", default="-"),
                    "timeSeriesAverage": safe_get(pr, "기업순이익률", "시계열평균분자", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "자산총계",
                    "values": {
                    "year2024": safe_get(pr, "기업순이익률", "데이터분모값", default="-"),
                    "timeSeriesAverage": safe_get(pr, "기업순이익률", "시계열평균분모", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                }
                ]
            },

            {
                "name": "자기자본세전순이익률",
                "values": {
                "year2024": safe_get(pr, "자기자본세전순이익률", "데이터", default="-"),
                "timeSeriesAverage": f'{safe_divide(safe_get(pr, "자기자본세전순이익률", "시계열평균분자", default="-"), safe_get(pr, "자기자본세전순이익률", "시계열평균분모", default="-"), default=0)}%' if safe_get(pr, "자기자본세전순이익률", "시계열평균분자", default="-") != "-" and safe_get(pr, "자기자본세전순이익률", "시계열평균분모", default="-") != "-" else "-",
                "industryMedian": f"{pr['자기자본세전순이익률'].get('업종중위수', '-')}%" if pr['자기자본세전순이익률'].get('업종중위수') else "-",
                "timeSeriesScore": pr["자기자본세전순이익률"].get("시계열점수", "-"),
                "industryScore": pr["자기자본세전순이익률"].get("업종점수", "-")
                },
                "children": [
                {
                    "name": "법인세비용차감전순이익",
                    "values": {
                    "year2024": safe_get(pr, "자기자본세전순이익률", "데이터분자값", default="-"),
                    "timeSeriesAverage": safe_get(pr, "자기자본세전순이익률", "시계열평균분자", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "자본총계",
                    "values": {
                    "year2024": safe_get(pr, "자기자본세전순이익률", "데이터분모값", default="-"),
                    "timeSeriesAverage": safe_get(pr, "자기자본세전순이익률", "시계열평균분모", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                }
                ]
            },

            {
                "name": "자본금세전순이익률",
                "values": {
                "year2024": safe_get(pr, "자본금세전순이익률", "데이터", default="-"),
                "timeSeriesAverage": f'{safe_divide(safe_get(pr, "자본금세전순이익률", "시계열평균분자", default="-"), safe_get(pr, "자본금세전순이익률", "시계열평균분모", default="-"), default=0)}%' if safe_get(pr, "자본금세전순이익률", "시계열평균분자", default="-") != "-" and safe_get(pr, "자본금세전순이익률", "시계열평균분모", default="-") != "-" else "-",
                "industryMedian": f"{pr['자본금세전순이익률'].get('업종중위수', '-')}%" if pr['자본금세전순이익률'].get('업종중위수') else "-",
                "timeSeriesScore": pr["자본금세전순이익률"].get("시계열점수", "-"),
                "industryScore": pr["자본금세전순이익률"].get("업종점수", "-")
                },
                "children": [
                {
                    "name": "법인세비용차감전순이익",
                    "values": {
                    "year2024": safe_get(pr, "자본금세전순이익률", "데이터분자값", default="-"),
                    "timeSeriesAverage": safe_get(pr, "자본금세전순이익률", "시계열평균분자", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "자본금",
                    "values": {
                    "year2024": safe_get(pr, "자본금세전순이익률", "데이터분모값", default="-"),
                    "timeSeriesAverage": safe_get(pr, "자본금세전순이익률", "시계열평균분모", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                }
                ]
            },

            {
                "name": "자본금순이익률",
                "values": {
                "year2024": safe_get(pr, "자본금순이익률", "데이터", default="-"),
                "timeSeriesAverage": f'{safe_divide(safe_get(pr, "자본금순이익률", "시계열평균분자", default="-"), safe_get(pr, "자본금순이익률", "시계열평균분모", default="-"), default=0)}%' if safe_get(pr, "자본금순이익률", "시계열평균분자", default="-") != "-" and safe_get(pr, "자본금순이익률", "시계열평균분모", default="-") != "-" else "-",
                "industryMedian": f"{pr['자본금순이익률'].get('업종중위수', '-')}%" if pr['자본금순이익률'].get('업종중위수') else "-",
                "timeSeriesScore": pr["자본금순이익률"].get("시계열점수", "-"),
                "industryScore": pr["자본금순이익률"].get("업종점수", "-")
                },
                "children": [
                {
                    "name": "당기순이익",
                    "values": {
                    "year2024": safe_get(pr, "자본금순이익률", "데이터분자값", default="-"),
                    "timeSeriesAverage": safe_get(pr, "자본금순이익률", "시계열평균분자", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "자본금",
                    "values": {
                    "year2024": safe_get(pr, "자본금순이익률", "데이터분모값", default="-"),
                    "timeSeriesAverage": safe_get(pr, "자본금순이익률", "시계열평균분모", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                }
                ]
            },

            {
                "name": "자기자본순이익률",
                "values": {
                "year2024": safe_get(pr, "자기자본순이익률", "데이터", default="-"),
                "timeSeriesAverage": f'{safe_divide(safe_get(pr, "자기자본순이익률", "시계열평균분자", default="-"), safe_get(pr, "자기자본순이익률", "시계열평균분모", default="-"), default=0)}%' if safe_get(pr, "자기자본순이익률", "시계열평균분자", default="-") != "-" and safe_get(pr, "자기자본순이익률", "시계열평균분모", default="-") != "-" else "-",
                "industryMedian": f"{pr['자기자본순이익률'].get('업종중위수', '-')}%" if pr['자기자본순이익률'].get('업종중위수') else "-",
                "timeSeriesScore": pr["자기자본순이익률"].get("시계열점수", "-"),
                "industryScore": pr["자기자본순이익률"].get("업종점수", "-")
                },
                "children": [
                {
                    "name": "당기순이익",
                    "values": {
                    "year2024": safe_get(pr, "자기자본순이익률", "데이터분자값", default="-"),
                    "timeSeriesAverage": safe_get(pr, "자기자본순이익률", "시계열평균분자", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "자본총계",
                    "values": {
                    "year2024": safe_get(pr, "자기자본순이익률", "데이터분모값", default="-"),
                    "timeSeriesAverage": safe_get(pr, "자기자본순이익률", "시계열평균분모", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                }
                ]
            }
            ]

            },
            {
            "title": "4.2. 판매마진 분석",
            "tableHeaders": [
                { "key": "indicator", "label": "" },
                { "key": "year2024", "label": "2024" },
                { "key": "timeSeriesAverage", "label": "시계열평균" },
                { "key": "industryMedian", "label": "업종중위수" },
                { "key": "timeSeriesScore", "label": "시계열점수" },
                { "key": "industryScore", "label": "업종점수" }
            ],
            "items":
            [
            {
                "name": "매출액세전순이익률",
                "values": {
                "year2024": safe_get(mg, "매출액세전순이익률", "데이터", default="-"),
                "timeSeriesAverage": f'{safe_divide(safe_get(mg, "매출액세전순이익률", "시계열평균분자", default="-"), safe_get(mg, "매출액세전순이익률", "시계열평균분모", default="-"), default=0)}%' if safe_get(mg, "매출액세전순이익률", "시계열평균분자", default="-") != "-" and safe_get(mg, "매출액세전순이익률", "시계열평균분모", default="-") != "-" else "-",
                "industryMedian": f"{mg['매출액세전순이익률'].get('업종중위수', '-')}%" if mg['매출액세전순이익률'].get('업종중위수') else "-",
                "timeSeriesScore": mg["매출액세전순이익률"].get("시계열점수", "-"),
                "industryScore": mg["매출액세전순이익률"].get("업종점수", "-")
                },
                "children": [
                {
                    "name": "법인세비용차감전순이익",
                    "values": {
                    "year2024": safe_get(mg, "매출액세전순이익률", "데이터분자값", default="-"),
                    "avg5Years": safe_get(mg, "매출액세전순이익률", "시계열평균분자", default="-"),
                    "sectorMedian": "-",
                    "scoreA": "-",
                    "scoreB": "-"
                    },
                    "children": []
                },
                {
                    "name": "매출액",
                    "values": {
                    "year2024": safe_get(mg, "매출액세전순이익률", "데이터분모값", default="-"),
                    "avg5Years": safe_get(mg, "매출액세전순이익률", "시계열평균분모", default="-"),
                    "sectorMedian": "-",
                    "scoreA": "-",
                    "scoreB": "-"
                    },
                    "children": []
                }
                ]
            },

            {
                "name": "매출액순이익률",
                "values": {
                "year2024": safe_get(mg, "매출액순이익률", "데이터", default="-"),
                "timeSeriesAverage": f'{safe_divide(safe_get(mg, "매출액순이익률", "시계열평균분자", default="-"), safe_get(mg, "매출액순이익률", "시계열평균분모", default="-"), default=0)}%' if safe_get(mg, "매출액순이익률", "시계열평균분자", default="-") != "-" and safe_get(mg, "매출액순이익률", "시계열평균분모", default="-") != "-" else "-",
                "industryMedian": f"{mg['매출액순이익률'].get('업종중위수', '-')}%" if mg['매출액순이익률'].get('업종중위수') else "-",
                "timeSeriesScore": mg["매출액순이익률"].get("시계열점수", "-"),
                "industryScore": mg["매출액순이익률"].get("업종점수", "-")
                },
                "children": [
                {
                    "name": "당기순이익",
                    "values": {
                    "year2024": safe_get(mg, "매출액순이익률", "데이터분자값", default="-"),
                    "avg5Years": safe_get(mg, "매출액순이익률", "시계열평균분자", default="-"),
                    "sectorMedian": "-",
                    "scoreA": "-",
                    "scoreB": "-"
                    },
                    "children": []
                },
                {
                    "name": "매출액",
                    "values": {
                    "year2024": safe_get(mg, "매출액순이익률", "데이터분모값", default="-"),
                    "avg5Years": safe_get(mg, "매출액순이익률", "시계열평균분모", default="-"),
                    "sectorMedian": "-",
                    "scoreA": "-",
                    "scoreB": "-"
                    },
                    "children": []
                }
                ]
            },

            {
                "name": "매출액영업이익률",
                "values": {
                "year2024": safe_get(mg, "매출액영업이익률", "데이터", default="-"),
                "timeSeriesAverage": f'{safe_divide(safe_get(mg, "매출액영업이익률", "시계열평균분자", default="-"), safe_get(mg, "매출액영업이익률", "시계열평균분모", default="-"), default=0)}%' if safe_get(mg, "매출액영업이익률", "시계열평균분자", default="-") != "-" and safe_get(mg, "매출액영업이익률", "시계열평균분모", default="-") != "-" else "-",
                "industryMedian": f"{mg['매출액영업이익률'].get('업종중위수', '-')}%" if mg['매출액영업이익률'].get('업종중위수') else "-",
                "timeSeriesScore": mg["매출액영업이익률"].get("시계열점수", "-"),
                "industryScore": mg["매출액영업이익률"].get("업종점수", "-")
                },
                "children": [
                {
                    "name": "영업이익",
                    "values": {
                    "year2024": safe_get(mg, "매출액영업이익률", "데이터분자값", default="-"),
                    "avg5Years": safe_get(mg, "매출액영업이익률", "시계열평균분자", default="-"),
                    "sectorMedian": "-",
                    "scoreA": "-",
                    "scoreB": "-"
                    },
                    "children": []
                },
                {
                    "name": "매출액",
                    "values": {
                    "year2024": safe_get(mg, "매출액영업이익률", "데이터분모값", default="-"),
                    "avg5Years": safe_get(mg, "매출액영업이익률", "시계열평균분모", default="-"),
                    "sectorMedian": "-",
                    "scoreA": "-",
                    "scoreB": "-"
                    },
                    "children": []
                }
                ]
            },

            {
                "name": "EBIT대매출액",
                "values": {
                "year2024": safe_get(mg, "EBIT대매출액", "데이터", default="-"),
                "timeSeriesAverage": f'{safe_divide(safe_get(mg, "EBIT대매출액", "시계열평균분자", default="-"), safe_get(mg, "EBIT대매출액", "시계열평균분모", default="-"), default=0)}%' if safe_get(mg, "EBIT대매출액", "시계열평균분자", default="-") != "-" and safe_get(mg, "EBIT대매출액", "시계열평균분모", default="-") != "-" else "-",
                "industryMedian": f"{mg['EBIT대매출액'].get('업종중위수', '-')}%" if mg['EBIT대매출액'].get('업종중위수') else "-",
                "timeSeriesScore": mg["EBIT대매출액"].get("시계열점수", "-"),
                "industryScore": mg["EBIT대매출액"].get("업종점수", "-")
                },
                "children": [
                {
                    "name": "법인세비용차감전순이익+이자비용",
                    "values": {
                    "year2024": safe_get(mg, "EBIT대매출액", "데이터분자값", default="-"),
                    "avg5Years": safe_get(mg, "EBIT대매출액", "시계열평균분자", default="-"),
                    "sectorMedian": "-",
                    "scoreA": "-",
                    "scoreB": "-"
                    },
                    "children": []
                },
                {
                    "name": "매출액",
                    "values": {
                    "year2024": safe_get(mg, "EBIT대매출액", "데이터분모값", default="-"),
                    "avg5Years": safe_get(mg, "EBIT대매출액", "시계열평균분모", default="-"),
                    "sectorMedian": "-",
                    "scoreA": "-",
                    "scoreB": "-"
                    },
                    "children": []
                }
                ]
            },

            {
                "name": "EBITDA대매출액",
                "values": {
                "year2024": safe_get(mg, "EBITDA대매출액", "데이터", default="-"),
                "timeSeriesAverage": f'{safe_divide(safe_get(mg, "EBITDA대매출액", "시계열평균분자", default="-"), safe_get(mg, "EBITDA대매출액", "시계열평균분모", default="-"), default=0)}%' if safe_get(mg, "EBITDA대매출액", "시계열평균분자", default="-") != "-" and safe_get(mg, "EBITDA대매출액", "시계열평균분모", default="-") != "-" else "-",
                "industryMedian": f"{mg['EBITDA대매출액'].get('업종중위수', '-')}%" if mg['EBITDA대매출액'].get('업종중위수') else "-",
                "timeSeriesScore": mg["EBITDA대매출액"].get("시계열점수", "-"),
                "industryScore": mg["EBITDA대매출액"].get("업종점수", "-")
                },
                "children": [
                {
                    "name": "법인세비용차감전순이익+이자비용+감가상각비+무형자산상각비",
                    "values": {
                    "year2024": safe_get(mg, "EBITDA대매출액", "데이터분자값", default="-"),
                    "avg5Years": safe_get(mg, "EBITDA대매출액", "시계열평균분자", default="-"),
                    "sectorMedian": "-",
                    "scoreA": "-",
                    "scoreB": "-"
                    },
                    "children": []
                },
                {
                    "name": "매출액",
                    "values": {
                    "year2024": safe_get(mg, "EBITDA대매출액", "데이터분모값", default="-"),
                    "avg5Years": safe_get(mg, "EBITDA대매출액", "시계열평균분모", default="-"),
                    "sectorMedian": "-",
                    "scoreA": "-",
                    "scoreB": "-"
                    },
                    "children": []
                }
                ]
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
                { "key": "year2024", "label": "2024" },
                { "key": "timeSeriesAverage", "label": "시계열평균" },
                { "key": "industryMedian", "label": "업종중위수" },
                { "key": "timeSeriesScore", "label": "시계열점수" },
                { "key": "industryScore", "label": "업종점수" }
            ],
            "items":
            [
            {
                "name": "총자산증가율",
                "values": {
                "year2024": safe_get(gr, "총자산증가율", "데이터", default="-"),
                "timeSeriesAverage": f'{safe_divide(safe_get(gr, "총자산증가율", "시계열평균분자", default="-"), safe_get(gr, "총자산증가율", "시계열평균분모", default="-"), default=0)}%' if safe_get(gr, "총자산증가율", "시계열평균분자", default="-") != "-" and safe_get(gr, "총자산증가율", "시계열평균분모", default="-") != "-" else "-",
                "industryMedian": f"{gr['총자산증가율'].get('업종중위수', '-')}%" if gr['총자산증가율'].get('업종중위수') else "-",
                "timeSeriesScore": gr["총자산증가율"].get("시계열점수", "-"),
                "industryScore": gr["총자산증가율"].get("업종점수", "-")
                },
                "children": [
                {
                    "name": "당기자산총계-전기자산총계",
                    "values": {
                    "year2024": safe_get(gr, "총자산증가율", "데이터분자값", default="-"),
                    "timeSeriesAverage": safe_get(gr, "총자산증가율", "시계열평균분자", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "전기자산총계",
                    "values": {
                    "year2024": safe_get(gr, "총자산증가율", "데이터분모값", default="-"),
                    "timeSeriesAverage": safe_get(gr, "총자산증가율", "시계열평균분모", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                }
                ]
            },

            {
                "name": "유형자산증가율",
                "values": {
                "year2024": safe_get(gr, "유형자산증가율", "데이터", default="-"),
                "timeSeriesAverage": f'{safe_divide(safe_get(gr, "유형자산증가율", "시계열평균분자", default="-"), safe_get(gr, "유형자산증가율", "시계열평균분모", default="-"), default=0)}%' if safe_get(gr, "유형자산증가율", "시계열평균분자", default="-") != "-" and safe_get(gr, "유형자산증가율", "시계열평균분모", default="-") != "-" else "-",
                "industryMedian": f"{gr['유형자산증가율'].get('업종중위수', '-')}%" if gr['유형자산증가율'].get('업종중위수') else "-",
                "timeSeriesScore": gr["유형자산증가율"].get("시계열점수", "-"),
                "industryScore": gr["유형자산증가율"].get("업종점수", "-")
                },
                "children": [
                {
                    "name": "당기유형자산-전기유형자산",
                    "values": {
                    "year2024": safe_get(gr, "유형자산증가율", "데이터분자값", default="-"),
                    "timeSeriesAverage": safe_get(gr, "유형자산증가율", "시계열평균분자", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "전기유형자산",
                    "values": {
                    "year2024": safe_get(gr, "유형자산증가율", "데이터분모값", default="-"),
                    "timeSeriesAverage": safe_get(gr, "유형자산증가율", "시계열평균분모", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                }
                ]
            },

            {
                "name": "유동자산증가율",
                "values": {
                "year2024": safe_get(gr, "유동자산증가율", "데이터", default="-"),
                "timeSeriesAverage": f'{safe_divide(safe_get(gr, "유동자산증가율", "시계열평균분자", default="-"), safe_get(gr, "유동자산증가율", "시계열평균분모", default="-"), default=0)}%' if safe_get(gr, "유동자산증가율", "시계열평균분자", default="-") != "-" and safe_get(gr, "유동자산증가율", "시계열평균분모", default="-") != "-" else "-",
                "industryMedian": f"{gr['유동자산증가율'].get('업종중위수', '-')}%" if gr['유동자산증가율'].get('업종중위수') else "-",
                "timeSeriesScore": gr["유동자산증가율"].get("시계열점수", "-"),
                "industryScore": gr["유동자산증가율"].get("업종점수", "-")
                },
                "children": [
                {
                    "name": "당기유동자산-전기유동자산",
                    "values": {
                    "year2024": safe_get(gr, "유동자산증가율", "데이터분자값", default="-"),
                    "timeSeriesAverage": safe_get(gr, "유동자산증가율", "시계열평균분자", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "전기유동자산",
                    "values": {
                    "year2024": safe_get(gr, "유동자산증가율", "데이터분모값", default="-"),
                    "timeSeriesAverage": safe_get(gr, "유동자산증가율", "시계열평균분모", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                }
                ]
            },

            {
                "name": "자기자본증가율",
                "values": {
                "year2024": safe_get(gr, "자기자본증가율", "데이터", default="-"),
                "timeSeriesAverage": f'{safe_divide(safe_get(gr, "자기자본증가율", "시계열평균분자", default="-"), safe_get(gr, "자기자본증가율", "시계열평균분모", default="-"), default=0)}%' if safe_get(gr, "자기자본증가율", "시계열평균분자", default="-") != "-" and safe_get(gr, "자기자본증가율", "시계열평균분모", default="-") != "-" else "-",
                "industryMedian": f"{gr['자기자본증가율'].get('업종중위수', '-')}%" if gr['자기자본증가율'].get('업종중위수') else "-",
                "timeSeriesScore": gr["자기자본증가율"].get("시계열점수", "-"),
                "industryScore": gr["자기자본증가율"].get("업종점수", "-")
                },
                "children": [
                {
                    "name": "당기자본총계-전기자본총계",
                    "values": {
                    "year2024": safe_get(gr, "자기자본증가율", "데이터분자값", default="-"),
                    "timeSeriesAverage": safe_get(gr, "자기자본증가율", "시계열평균분자", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "전기자본총계",
                    "values": {
                    "year2024": safe_get(gr, "자기자본증가율", "데이터분모값", default="-"),
                    "timeSeriesAverage": safe_get(gr, "자기자본증가율", "시계열평균분모", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                }
                ]
            },

            {
                "name": "매출액증가율",
                "values": {
                "year2024": safe_get(gr, "매출액증가율", "데이터", default="-"),
                "timeSeriesAverage": f'{safe_divide(safe_get(gr, "매출액증가율", "시계열평균분자", default="-"), safe_get(gr, "매출액증가율", "시계열평균분모", default="-"), default=0)}%' if safe_get(gr, "매출액증가율", "시계열평균분자", default="-") != "-" and safe_get(gr, "매출액증가율", "시계열평균분모", default="-") != "-" else "-",
                "industryMedian": f"{gr['매출액증가율'].get('업종중위수', '-')}%" if gr['매출액증가율'].get('업종중위수') else "-",
                "timeSeriesScore": gr["매출액증가율"].get("시계열점수", "-"),
                "industryScore": gr["매출액증가율"].get("업종점수", "-")
                },
                "children": [
                {
                    "name": "당기매출액-전기매출액",
                    "values": {
                    "year2024": safe_get(gr, "매출액증가율", "데이터분자값", default="-"),
                    "timeSeriesAverage": safe_get(gr, "매출액증가율", "시계열평균분자", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "전기매출액",
                    "values": {
                    "year2024": safe_get(gr, "매출액증가율", "데이터분모값", default="-"),
                    "timeSeriesAverage": safe_get(gr, "매출액증가율", "시계열평균분모", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                }
                ]
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
                { "key": "year2024", "label": "2024" },
                { "key": "timeSeriesAverage", "label": "시계열평균" },
                { "key": "industryMedian", "label": "업종중위수" },
                { "key": "timeSeriesScore", "label": "시계열점수" },
                { "key": "industryScore", "label": "업종점수" }
            ],
            "items":
            [
            {
                "name": "총자산회전율",
                "values": {
                "year2024": safe_get(at, "총자산회전율", "데이터", default="-"),
                "timeSeriesAverage": f'{safe_divide(safe_get(at, "총자산회전율", "시계열평균분자", default="-"), safe_get(at, "총자산회전율", "시계열평균분모", default="-"), default=0)}%' if safe_get(at, "총자산회전율", "시계열평균분자", default="-") != "-" and safe_get(at, "총자산회전율", "시계열평균분모", default="-") != "-" else "-",
                "industryMedian": f"{at['총자산회전율'].get('업종중위수', '-')}%" if at['총자산회전율'].get('업종중위수') else "-",
                "timeSeriesScore": at["총자산회전율"].get("시계열점수", "-"),
                "industryScore": at["총자산회전율"].get("업종점수", "-")
                },
                "children": [
                {
                    "name": "매출액",
                    "values": {
                    "year2024": safe_get(at, "총자산회전율", "데이터분자값", default="-"),
                    "timeSeriesAverage": safe_get(at, "총자산회전율", "시계열평균분자", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "자산총계",
                    "values": {
                    "year2024": safe_get(at, "총자산회전율", "데이터분모값", default="-"),
                    "timeSeriesAverage": safe_get(at, "총자산회전율", "시계열평균분모", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                }
                ]
            },

            {
                "name": "자기자본회전율",
                "values": {
                "year2024": safe_get(at, "자기자본회전율", "데이터", default="-"),
                "timeSeriesAverage": f'{safe_divide(safe_get(at, "자기자본회전율", "시계열평균분자", default="-"), safe_get(at, "자기자본회전율", "시계열평균분모", default="-"), default=0)}%' if safe_get(at, "자기자본회전율", "시계열평균분자", default="-") != "-" and safe_get(at, "자기자본회전율", "시계열평균분모", default="-") != "-" else "-",
                "industryMedian": f"{at['자기자본회전율'].get('업종중위수', '-')}%" if at['자기자본회전율'].get('업종중위수') else "-",
                "timeSeriesScore": at["자기자본회전율"].get("시계열점수", "-"),
                "industryScore": at["자기자본회전율"].get("업종점수", "-")
                },
                "children": [
                {
                    "name": "매출액",
                    "values": {
                    "year2024": safe_get(at, "자기자본회전율", "데이터분자값", default="-"),
                    "timeSeriesAverage": safe_get(at, "자기자본회전율", "시계열평균분자", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "자본총계",
                    "values": {
                    "year2024": safe_get(at, "자기자본회전율", "데이터분모값", default="-"),
                    "timeSeriesAverage": safe_get(at, "자기자본회전율", "시계열평균분모", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                }
                ]
            },

            {
                "name": "자본금회전율",
                "values": {
                "year2024": safe_get(at, "자본금회전율", "데이터", default="-"),
                "timeSeriesAverage": f'{safe_divide(safe_get(at, "자본금회전율", "시계열평균분자", default="-"), safe_get(at, "자본금회전율", "시계열평균분모", default="-"), default=0)}%' if safe_get(at, "자본금회전율", "시계열평균분자", default="-") != "-" and safe_get(at, "자본금회전율", "시계열평균분모", default="-") != "-" else "-",
                "industryMedian": f"{at['자본금회전율'].get('업종중위수', '-')}%" if at['자본금회전율'].get('업종중위수') else "-",
                "timeSeriesScore": at["자본금회전율"].get("시계열점수", "-"),
                "industryScore": at["자본금회전율"].get("업종점수", "-")
                },
                "children": [
                {
                    "name": "매출액",
                    "values": {
                    "year2024": safe_get(at, "자본금회전율", "데이터분자값", default="-"),
                    "timeSeriesAverage": safe_get(at, "자본금회전율", "시계열평균분자", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "자본금",
                    "values": {
                    "year2024": safe_get(at, "자본금회전율", "데이터분모값", default="-"),
                    "timeSeriesAverage": safe_get(at, "자본금회전율", "시계열평균분모", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                }
                ]
            },

            {
                "name": "경영자산회전율",
                "values": {
                "year2024": safe_get(at, "경영자산회전율", "데이터", default="-"),
                "timeSeriesAverage": f'{safe_divide(safe_get(at, "경영자산회전율", "시계열평균분자", default="-"), safe_get(at, "경영자산회전율", "시계열평균분모", default="-"), default=0)}%' if safe_get(at, "경영자산회전율", "시계열평균분자", default="-") != "-" and safe_get(at, "경영자산회전율", "시계열평균분모", default="-") != "-" else "-",
                "industryMedian": f"{at['경영자산회전율'].get('업종중위수', '-')}%" if at['경영자산회전율'].get('업종중위수') else "-",
                "timeSeriesScore": at["경영자산회전율"].get("시계열점수", "-"),
                "industryScore": at["경영자산회전율"].get("업종점수", "-")
                },
                "children": [
                {
                    "name": "매출액",
                    "values": {
                    "year2024": safe_get(at, "경영자산회전율", "데이터분자값", default="-"),
                    "timeSeriesAverage": safe_get(at, "경영자산회전율", "시계열평균분자", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "경영자산",
                    "values": {
                    "year2024": safe_get(at, "경영자산회전율", "데이터분모값", default="-"),
                    "timeSeriesAverage": safe_get(at, "경영자산회전율", "시계열평균분모", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                }
                ]
            },

            {
                "name": "비유동자산회전율",
                "values": {
                "year2024": safe_get(at, "비유동자산회전율", "데이터", default="-"),
                "timeSeriesAverage": f'{safe_divide(safe_get(at, "비유동자산회전율", "시계열평균분자", default="-"), safe_get(at, "비유동자산회전율", "시계열평균분모", default="-"), default=0)}%' if safe_get(at, "비유동자산회전율", "시계열평균분자", default="-") != "-" and safe_get(at, "비유동자산회전율", "시계열평균분모", default="-") != "-" else "-",
                "industryMedian": f"{at['비유동자산회전율'].get('업종중위수', '-')}%" if at['비유동자산회전율'].get('업종중위수') else "-",
                "timeSeriesScore": at["비유동자산회전율"].get("시계열점수", "-"),
                "industryScore": at["비유동자산회전율"].get("업종점수", "-")
                },
                "children": [
                {
                    "name": "매출액",
                    "values": {
                    "year2024": safe_get(at, "비유동자산회전율", "데이터분자값", default="-"),
                    "timeSeriesAverage": safe_get(at, "비유동자산회전율", "시계열평균분자", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "비유동자산",
                    "values": {
                    "year2024": safe_get(at, "비유동자산회전율", "데이터분모값", default="-"),
                    "timeSeriesAverage": safe_get(at, "비유동자산회전율", "시계열평균분모", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                }
                ]
            },

            {
                "name": "유형자산회전율",
                "values": {
                "year2024": safe_get(at, "유형자산회전율", "데이터", default="-"),
                "timeSeriesAverage": f'{safe_divide(safe_get(at, "유형자산회전율", "시계열평균분자", default="-"), safe_get(at, "유형자산회전율", "시계열평균분모", default="-"), default=0)}%' if safe_get(at, "유형자산회전율", "시계열평균분자", default="-") != "-" and safe_get(at, "유형자산회전율", "시계열평균분모", default="-") != "-" else "-",
                "industryMedian": f"{at['유형자산회전율'].get('업종중위수', '-')}%" if at['유형자산회전율'].get('업종중위수') else "-",
                "timeSeriesScore": at["유형자산회전율"].get("시계열점수", "-"),
                "industryScore": at["유형자산회전율"].get("업종점수", "-")
                },
                "children": [
                {
                    "name": "매출액",
                    "values": {
                    "year2024": safe_get(at, "유형자산회전율", "데이터분자값", default="-"),
                    "timeSeriesAverage": safe_get(at, "유형자산회전율", "시계열평균분자", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "유형자산",
                    "values": {
                    "year2024": safe_get(at, "유형자산회전율", "데이터분모값", default="-"),
                    "timeSeriesAverage": safe_get(at, "유형자산회전율", "시계열평균분모", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                }
                ]
            },

            {
                "name": "재고자산회전율",
                "values": {
                "year2024": safe_get(at, "재고자산회전율", "데이터", default="-"),
                "timeSeriesAverage": f'{safe_divide(safe_get(at, "재고자산회전율", "시계열평균분자", default="-"), safe_get(at, "재고자산회전율", "시계열평균분모", default="-"), default=0)}%' if safe_get(at, "재고자산회전율", "시계열평균분자", default="-") != "-" and safe_get(at, "재고자산회전율", "시계열평균분모", default="-") != "-" else "-",
                "industryMedian": f"{at['재고자산회전율'].get('업종중위수', '-')}%" if at['재고자산회전율'].get('업종중위수') else "-",
                "timeSeriesScore": at["재고자산회전율"].get("시계열점수", "-"),
                "industryScore": at["재고자산회전율"].get("업종점수", "-")
                },
                "children": [
                {
                    "name": "매출액",
                    "values": {
                    "year2024": safe_get(at, "재고자산회전율", "데이터분자값", default="-"),
                    "timeSeriesAverage": safe_get(at, "재고자산회전율", "시계열평균분자", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "재고자산",
                    "values": {
                    "year2024": safe_get(at, "재고자산회전율", "데이터분모값", default="-"),
                    "timeSeriesAverage": safe_get(at, "재고자산회전율", "시계열평균분모", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                }
                ]
            },

            {
                "name": "상(제)품회전율",
                "values": {
                "year2024": safe_get(at, "상(제)품회전율", "데이터", default="-"),
                "timeSeriesAverage": f'{(float(safe_get(at, "상(제)품회전율", "시계열평균분자", default="-"))/float(safe_get(at, "상(제)품회전율", "시계열평균분모", default="-")))*100}%',
                "industryMedian": f"{at['상(제)품회전율'].get('업종중위수', '-')}%" if at['상(제)품회전율'].get('업종중위수') else "-",
                "timeSeriesScore": at["상(제)품회전율"].get("시계열점수", "-"),
                "industryScore": at["상(제)품회전율"].get("업종점수", "-")
                },
                "children": [
                {
                    "name": "매출액",
                    "values": {
                    "year2024": safe_get(at, "상(제)품회전율", "데이터분자값", default="-"),
                    "timeSeriesAverage": safe_get(at, "상(제)품회전율", "시계열평균분자", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "상품+제품",
                    "values": {
                    "year2024": safe_get(at, "상(제)품회전율", "데이터분모값", default="-"),
                    "timeSeriesAverage": safe_get(at, "상(제)품회전율", "시계열평균분모", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                }
                ]
            },

            {
                "name": "매출채권회전율",
                "values": {
                "year2024": safe_get(at, "매출채권회전율", "데이터", default="-"),
                "timeSeriesAverage": f'{safe_divide(safe_get(at, "매출채권회전율", "시계열평균분자", default="-"), safe_get(at, "매출채권회전율", "시계열평균분모", default="-"), default=0)}%' if safe_get(at, "매출채권회전율", "시계열평균분자", default="-") != "-" and safe_get(at, "매출채권회전율", "시계열평균분모", default="-") != "-" else "-",
                "industryMedian": f"{at['매출채권회전율'].get('업종중위수', '-')}%" if at['매출채권회전율'].get('업종중위수') else "-",
                "timeSeriesScore": at["매출채권회전율"].get("시계열점수", "-"),
                "industryScore": at["매출채권회전율"].get("업종점수", "-")
                },
                "children": [
                {
                    "name": "매출액",
                    "values": {
                    "year2024": safe_get(at, "매출채권회전율", "데이터분자값", default="-"),
                    "timeSeriesAverage": safe_get(at, "매출채권회전율", "시계열평균분자", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "매출채권",
                    "values": {
                    "year2024": safe_get(at, "매출채권회전율", "데이터분모값", default="-"),
                    "timeSeriesAverage": safe_get(at, "매출채권회전율", "시계열평균분모", default="-"),
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                }
                ]
            }
            ]

            }
        ]
        }
    ]
    }


    return response
