import asyncio
import uuid,json
from fastapi import FastAPI
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
        "http://127.0.0.1:5500",      # 로컬 테스트
        "http://localhost:5173",       # Vite 개발 서버
        "https://pb-ai-web.vercel.app/",    # 프로덕션 프론트엔드
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
        with open(f'data/{ticker}.json', 'r', encoding='utf-8') as f:
            cdict = json.load(f)
        return cdict

@app.get('/companies/{ticker}/profile')
def get_company_profile(ticker:str):
    item_names = {"시가총액":"시가총액","상장일자":"상장일자","설립일자":"설립일","종업원수":"종업원수","대표 이사":"CEO","발행주식수":"발행주식수","주요 계열사/관계사":"주요계열사"}
    data = get_company_data(ticker)
    profile = data["리포트오버뷰"]["기업프로필"]
    profile_list = []
    for k, v in item_names.items():
        temp = {}
        temp["label"] = k
        temp["value"] = profile[v]
        profile_list.append(temp)
    response = {
        "companyCode":profile["티커"],
        "companyName":profile["기업이름"],
        "profile":profile_list
    }
    return response

@app.get('/companies/{ticker}/financial-overview')
def get_company_financial_overview(ticker:str):

    data = get_company_data(ticker)
    dt = data["리포트재무현황분석"]["재무상황"]["num"]
    response = {"revenueChart":[],"netIncomeChar":[],"financialTable":[]}
    for year,values in dt:
        temp = {}
        temp["year"] = year 
        temp["value"] = values["매출액"]
        response["revenueChart"].append(temp)

        operating_income = values["당기순이익"] / values["매출액"]
        temp["netIncome"] = values["당기순이익"]
        temp["netIncomeRate"] = operating_income

        response["netIncomeChar"].append(temp)

        fdict = {
            "year":year,
            "revenue":values["매출액"],
            "totalAssets":values["자산총계"],
            "totalLiabilities": values["부채총계"],
            "totalEquity": values["자본총계"],
            "operatingIncome": operating_income,
            "netIncome": values["당기순이익"]
        }
        response["financialTable"].append(fdict)
    return response

@app.get('/companies/{ticker}/financial-health')
def get_company_financial_health(ticker:str):
    
    data = get_company_data(ticker)
    dt = data["리포트재무현황분석"]["재무상황"]["재무비율판정"]
    judge = dt["지표판정"]
    response = {
        "description": "재무건전성은 필수소비재 섹터 업종 중위수와 시계열 점수로 판정됩니다",
        "scoreValue": float(dt["점수"]),
        "scoreRange": {
            "min": -1,
            "max": 1,
            "thresholds": [-1, -0.5, 0, 0.5, 1]
        },
        "healthCategories": [
            { "label": "유동성", "status": judge["유동성"] },
            { "label": "레버리지", "status": judge["레버리지"] },
            { "label": "투자수익성", "status": judge["투자수익성"] },
            { "label": "판매마진", "status": judge["판매마진"] },
            { "label": "활동성", "status": judge["활동성"] },
            { "label": "성장성", "status": judge["성장성"] }
        ]
    }
    return response

@app.get('/companies/{ticker}/industry-description')
def get_company_industry_description(ticker:str):
    
    data = get_company_data(ticker)
    dt = data["리포트오버뷰"]["산업설명"]
    response = {
        "items": [
            { "label": "산업명", "value": dt["산업명"] },
            { "label": "평가기준일", "value": dt["평가기준일"] },
            { "label": "산업평가 종합등급", "value": dt["산업평가종합등급"] }
        ]
    }
    return response

@app.get('/companies/{ticker}/financial-ratio-judgment')
def get_company_financial_ratio_judgment(ticker:str):
    data = get_company_data(ticker)
    dt = data["리포트재무현황분석"]["재무비율판정"]
    judge = dt["지표판정"]
    point = dt["지표점수"]
    response = {
        "financialHealth": {
            "scoreValue": 0.855,
            "scoreRange": {
            "min": -1,
            "max": 1,
            "thresholds": [-1, -0.5, 0, 0.5, 1]
            },
            "healthCategories": [
            { "label": "유동성", "status": judge["유동성"] },
            { "label": "레버리지", "status": judge["레버리지"] },
            { "label": "투자수익성", "status": judge["투자수익성"] },
            { "label": "판매마진", "status": judge["판매마진"] },
            { "label": "활동성", "status": judge["활동성"] },
            { "label": "성장성", "status": judge["성장성"] }
            ]
        },
        "ratioJudgmentTable": [
            {
            "indicator": "지표 점수",
            "stability": point["유동성"],
            "leverage": point["레버리지"],
            "investmentProfitability": point["투자수익성"],
            "salesMargin": point["판매마진"],
            "activity": point["활동성"],
            "growth": point["성장성"]
            }
        ]
    }
    return response


@app.get('/companies/{ticker}/financial-analysis-details')
def get_company_financial_analysis_details(ticker:str):
    data = get_company_data(ticker)
    st = data["리포트재무현황분석"]["유동성분석"]
    lv = data["리포트재무현황분석"]["레버리지분석"]
    pr = data["리포트재무현황분석"]["투자수익성분석"]
    mg = data["리포트재무현황분석"]["판매마진분석"]
    gr = data["리포트재무현황분석"]["성장성분석"]
    at = data["리포트재무현황분석"]["활동성분석"]

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
                { "key": "year2023", "label": "2023" },
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
                    "year2023": st["유동비율"]["데이터"],
                    "timeSeriesAverage": f'{(float(st["유동비율"]["시계열평균분자"])/float(st["유동비율"]["시계열평균분모"]))/100}%',
                    "industryMedian": f"{st['유동비율']['업종중위수']}%",
                    "timeSeriesScore": st["유동비율"]["시계열점수"],
                    "industryScore": st["유동비율"]["업종점수"]
                    },
                    "children": [
                    {
                        "name": "유동자산",
                        "values": {
                        "year2023": st["유동비율"]["데이터분자값"],
                        "timeSeriesAverage": st["유동비율"]["시계열평균분자"],
                        "industryMedian": "-",
                        "timeSeriesScore": "-",
                        "industryScore": "-"
                        },
                        "children": []
                    },
                    {
                        "name": "유동부채",
                        "values": {
                        "year2023": st["유동비율"]["데이터분모값"],
                        "timeSeriesAverage": st["유동비율"]["시계열평균분모"],
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
                    "year2023": st["당좌비율"]["데이터"],
                    "timeSeriesAverage": f'{(float(st["당좌비율"]["시계열평균분자"])/float(st["당좌비율"]["시계열평균분모"]))/100}%',
                    "industryMedian": f"{st['당좌비율']['업종중위수']}%",
                    "timeSeriesScore": st["당좌비율"]["시계열점수"],
                    "industryScore": st["당좌비율"]["업종점수"]
                    },
                    "children": [
                    {
                        "name": "당좌자산",
                        "values": {
                        "year2023": st["당좌비율"]["데이터분자값"],
                        "timeSeriesAverage": st["당좌비율"]["시계열평균분자"],
                        "industryMedian": "-",
                        "timeSeriesScore": "-",
                        "industryScore": "-"
                        },
                        "children": []
                    },
                    {
                        "name": "유동부채",
                        "values": {
                        "year2023": st["당좌비율"]["데이터분모값"],
                        "timeSeriesAverage": st["당좌비율"]["시계열평균분모"],
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
                    "year2023": st["현금비율"]["데이터"],
                    "timeSeriesAverage": f'{(float(st["현금비율"]["시계열평균분자"])/float(st["현금비율"]["시계열평균분모"]))/100}%',
                    "industryMedian": f"{st['현금비율']['업종중위수']}%",
                    "timeSeriesScore": st["현금비율"]["시계열점수"],
                    "industryScore": st["현금비율"]["업종점수"]
                    },
                    "children": [
                    {
                        "name": "현금및현금성자산",
                        "values": {
                        "year2023": st["현금비율"]["데이터분자값"],
                        "timeSeriesAverage": st["현금비율"]["시계열평균분자"],
                        "industryMedian": "-",
                        "timeSeriesScore": "-",
                        "industryScore": "-"
                        },
                        "children": []
                    },
                    {
                        "name": "유동부채",
                        "values": {
                        "year2023": st["현금비율"]["데이터분모값"],
                        "timeSeriesAverage": st["현금비율"]["시계열평균분모"],
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
                    "year2023": st["순운전자본대총자본"]["데이터"],
                    "timeSeriesAverage": f'{(float(st["순운전자본대총자본"]["시계열평균분자"])/float(st["순운전자본대총자본"]["시계열평균분모"]))/100}%',
                    "industryMedian": f"{st['순운전자본대총자본']['업종중위수']}%",
                    "timeSeriesScore": st["순운전자본대총자본"]["시계열점수"],
                    "industryScore": st["순운전자본대총자본"]["업종점수"]
                    },
                    "children": [
                    {
                        "name": "유동자산+유동부채",
                        "values": {
                        "year2023": st["순운전자본대총자본"]["데이터분자값"],
                        "timeSeriesAverage": st["순운전자본대총자본"]["시계열평균분자"],
                        "industryMedian": "-",
                        "timeSeriesScore": "-",
                        "industryScore": "-"
                        },
                        "children": []
                    },
                    {
                        "name": "자산총계",
                        "values": {
                        "year2023": st["순운전자본대총자본"]["데이터분모값"],
                        "timeSeriesAverage": st["순운전자본대총자본"]["시계열평균분모"],
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
                    "year2023": st["비유동비율"]["데이터"],
                    "timeSeriesAverage": f'{(float(st["비유동비율"]["시계열평균분자"])/float(st["비유동비율"]["시계열평균분모"]))/100}%',
                    "industryMedian": f"{st['비유동비율']['업종중위수']}%",
                    "timeSeriesScore": st["비유동비율"]["시계열점수"],
                    "industryScore": st["비유동비율"]["업종점수"]
                    },
                    "children": [
                    {
                        "name": "비유동자산",
                        "values": {
                        "year2023": st["비유동비율"]["데이터분자값"],
                        "timeSeriesAverage": st["비유동비율"]["시계열평균분자"],
                        "industryMedian": "-",
                        "timeSeriesScore": "-",
                        "industryScore": "-"
                        },
                        "children": []
                    },
                    {
                        "name": "자본총계",
                        "values": {
                        "year2023": st["비유동비율"]["데이터분모값"],
                        "timeSeriesAverage": st["비유동비율"]["시계열평균분모"],
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
                    "year2023": st["비유동장기적합률"]["데이터"],
                    "timeSeriesAverage": f'{(float(st["비유동장기적합률"]["시계열평균분자"])/float(st["비유동장기적합률"]["시계열평균분모"]))/100}%',
                    "industryMedian": f"{st['비유동장기적합률']['업종중위수']}%",
                    "timeSeriesScore": st["비유동장기적합률"]["시계열점수"],
                    "industryScore": st["비유동장기적합률"]["업종점수"]
                    },
                    "children": [
                    {
                        "name": "비유동자산",
                        "values": {
                        "year2023": st["비유동장기적합률"]["데이터분자값"],
                        "timeSeriesAverage": st["비유동장기적합률"]["시계열평균분자"],
                        "industryMedian": "-",
                        "timeSeriesScore": "-",
                        "industryScore": "-"
                        },
                        "children": []
                    },
                    {
                        "name": "자본총계+비유동부채",
                        "values": {
                        "year2023": st["비유동장기적합률"]["데이터분모값"],
                        "timeSeriesAverage": st["비유동장기적합률"]["시계열평균분모"],
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
                { "key": "year2023", "label": "2023" },
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
        "year2023": lv["부채비율"]["데이터"],
        "timeSeriesAverage": f'{(float(lv["부채비율"]["시계열평균분자"])/float(lv["부채비율"]["시계열평균분모"]))/100}%',
        "industryMedian": f"{lv['부채비율']['업종중위수']}%",
        "timeSeriesScore": lv["부채비율"]["시계열점수"],
        "industryScore": lv["부채비율"]["업종점수"]
        },
        "children": [
        {
            "name": "부채총계",
            "values": {
            "year2023": lv["부채비율"]["데이터분자값"],
            "timeSeriesAverage": lv["부채비율"]["시계열평균분자"],
            "industryMedian": "-",
            "timeSeriesScore": "-",
            "industryScore": "-"
            },
            "children": []
        },
        {
            "name": "자본총계",
            "values": {
            "year2023": lv["부채비율"]["데이터분모값"],
            "timeSeriesAverage": lv["부채비율"]["시계열평균분모"],
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
        "year2023": lv["자기자본비율"]["데이터"],
        "timeSeriesAverage": f'{(float(lv["자기자본비율"]["시계열평균분자"])/float(lv["자기자본비율"]["시계열평균분모"]))/100}%',
        "industryMedian": f"{lv['자기자본비율']['업종중위수']}%",
        "timeSeriesScore": lv["자기자본비율"]["시계열점수"],
        "industryScore": lv["자기자본비율"]["업종점수"]
        },
        "children": [
        {
            "name": "자본총계",
            "values": {
            "year2023": lv["자기자본비율"]["데이터분자값"],
            "timeSeriesAverage": lv["자기자본비율"]["시계열평균분자"],
            "industryMedian": "-",
            "timeSeriesScore": "-",
            "industryScore": "-"
            },
            "children": []
        },
        {
            "name": "자산총계",
            "values": {
            "year2023": lv["자기자본비율"]["데이터분모값"],
            "timeSeriesAverage": lv["자기자본비율"]["시계열평균분모"],
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
        "year2023": lv["유동부채비율"]["데이터"],
        "timeSeriesAverage": f'{(float(lv["유동부채비율"]["시계열평균분자"])/float(lv["유동부채비율"]["시계열평균분모"]))/100}%',
        "industryMedian": f"{lv['유동부채비율']['업종중위수']}%",
        "timeSeriesScore": lv["유동부채비율"]["시계열점수"],
        "industryScore": lv["유동부채비율"]["업종점수"]
        },
        "children": [
        {
            "name": "유동부채",
            "values": {
            "year2023": lv["유동부채비율"]["데이터분자값"],
            "timeSeriesAverage": lv["유동부채비율"]["시계열평균분자"],
            "industryMedian": "-",
            "timeSeriesScore": "-",
            "industryScore": "-"
            },
            "children": []
        },
        {
            "name": "자본총계",
            "values": {
            "year2023": lv["유동부채비율"]["데이터분모값"],
            "timeSeriesAverage": lv["유동부채비율"]["시계열평균분모"],
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
        "year2023": lv["비유동부채비율"]["데이터"],
        "timeSeriesAverage": f'{(float(lv["비유동부채비율"]["시계열평균분자"])/float(lv["비유동부채비율"]["시계열평균분모"]))/100}%',
        "industryMedian": f"{lv['비유동부채비율']['업종중위수']}%",
        "timeSeriesScore": lv["비유동부채비율"]["시계열점수"],
        "industryScore": lv["비유동부채비율"]["업종점수"]
        },
        "children": [
        {
            "name": "비유동부채",
            "values": {
            "year2023": lv["비유동부채비율"]["데이터분자값"],
            "timeSeriesAverage": lv["비유동부채비율"]["시계열평균분자"],
            "industryMedian": "-",
            "timeSeriesScore": "-",
            "industryScore": "-"
            },
            "children": []
        },
        {
            "name": "자본총계",
            "values": {
            "year2023": lv["비유동부채비율"]["데이터분모값"],
            "timeSeriesAverage": lv["비유동부채비율"]["시계열평균분모"],
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
        "year2023": lv["차입금의존도"]["데이터"],
        "timeSeriesAverage": f'{(float(lv["차입금의존도"]["시계열평균분자"])/float(lv["차입금의존도"]["시계열평균분모"]))/100}%',
        "industryMedian": f"{lv['차입금의존도']['업종중위수']}%",
        "timeSeriesScore": lv["차입금의존도"]["시계열점수"],
        "industryScore": lv["차입금의존도"]["업종점수"]
        },
        "children": [
        {
            "name": "차입금(이자지급부채)",
            "values": {
            "year2023": lv["차입금의존도"]["데이터분자값"],
            "timeSeriesAverage": lv["차입금의존도"]["시계열평균분자"],
            "industryMedian": "-",
            "timeSeriesScore": "-",
            "industryScore": "-"
            },
            "children": []
        },
        {
            "name": "자산총계",
            "values": {
            "year2023": lv["차입금의존도"]["데이터분모값"],
            "timeSeriesAverage": lv["차입금의존도"]["시계열평균분모"],
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
        "year2023": lv["차입금대매출액"]["데이터"],
        "timeSeriesAverage": f'{(float(lv["차입금대매출액"]["시계열평균분자"])/float(lv["차입금대매출액"]["시계열평균분모"]))/100}%',
        "industryMedian": f"{lv['차입금대매출액']['업종중위수']}%",
        "timeSeriesScore": lv["차입금대매출액"]["시계열점수"],
        "industryScore": lv["차입금대매출액"]["업종점수"]
        },
        "children": [
        {
            "name": "차입금(이자지급부채)",
            "values": {
            "year2023": lv["차입금대매출액"]["데이터분자값"],
            "timeSeriesAverage": lv["차입금대매출액"]["시계열평균분자"],
            "industryMedian": "-",
            "timeSeriesScore": "-",
            "industryScore": "-"
            },
            "children": []
        },
        {
            "name": "매출액",
            "values": {
            "year2023": lv["차입금대매출액"]["데이터분모값"],
            "timeSeriesAverage": lv["차입금대매출액"]["시계열평균분모"],
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
                { "key": "year2023", "label": "2023" },
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
                "year2023": pr["총자산세전수익률"]["데이터"],
                "timeSeriesAverage": f'{(float(pr["총자산세전수익률"]["시계열평균분자"])/float(pr["총자산세전수익률"]["시계열평균분모"]))/100}%',
                "industryMedian": f"{pr['총자산세전수익률']['업종중위수']}%",
                "timeSeriesScore": pr["총자산세전수익률"]["시계열점수"],
                "industryScore": pr["총자산세전수익률"]["업종점수"]
                },
                "children": [
                {
                    "name": "법인세비용차감전순이익",
                    "values": {
                    "year2023": pr["총자산세전수익률"]["데이터분자값"],
                    "timeSeriesAverage": pr["총자산세전수익률"]["시계열평균분자"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "당기순이익",
                    "values": {
                    "year2023": pr["총자산세전수익률"]["데이터분모값"],
                    "timeSeriesAverage": pr["총자산세전수익률"]["시계열평균분모"],
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
                "year2023": pr["총자산순이익률"]["데이터"],
                "timeSeriesAverage": f'{(float(pr["총자산순이익률"]["시계열평균분자"])/float(pr["총자산순이익률"]["시계열평균분모"]))/100}%',
                "industryMedian": f"{pr['총자산순이익률']['업종중위수']}%",
                "timeSeriesScore": pr["총자산순이익률"]["시계열점수"],
                "industryScore": pr["총자산순이익률"]["업종점수"]
                },
                "children": [
                {
                    "name": "당기순이익",
                    "values": {
                    "year2023": pr["총자산순이익률"]["데이터분자값"],
                    "timeSeriesAverage": pr["총자산순이익률"]["시계열평균분자"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "자산총계",
                    "values": {
                    "year2023": pr["총자산순이익률"]["데이터분모값"],
                    "timeSeriesAverage": pr["총자산순이익률"]["시계열평균분모"],
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
                "year2023": pr["기업세전순이익률"]["데이터"],
                "timeSeriesAverage": f'{(float(pr["기업세전순이익률"]["시계열평균분자"])/float(pr["기업세전순이익률"]["시계열평균분모"]))/100}%',
                "industryMedian": f"{pr['기업세전순이익률']['업종중위수']}%",
                "timeSeriesScore": pr["기업세전순이익률"]["시계열점수"],
                "industryScore": pr["기업세전순이익률"]["업종점수"]
                },
                "children": [
                {
                    "name": "법인세비용차감전순이익+이자비용",
                    "values": {
                    "year2023": pr["기업세전순이익률"]["데이터분자값"],
                    "timeSeriesAverage": pr["기업세전순이익률"]["시계열평균분자"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "당기순이익+이자비용",
                    "values": {
                    "year2023": pr["기업세전순이익률"]["데이터분모값"],
                    "timeSeriesAverage": pr["기업세전순이익률"]["시계열평균분모"],
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
                "year2023": pr["기업순이익률"]["데이터"],
                "timeSeriesAverage": f'{(float(pr["기업순이익률"]["시계열평균분자"])/float(pr["기업순이익률"]["시계열평균분모"]))/100}%',
                "industryMedian": f"{pr['기업순이익률']['업종중위수']}%",
                "timeSeriesScore": pr["기업순이익률"]["시계열점수"],
                "industryScore": pr["기업순이익률"]["업종점수"]
                },
                "children": [
                {
                    "name": "당기순이익+이자비용",
                    "values": {
                    "year2023": pr["기업순이익률"]["데이터분자값"],
                    "timeSeriesAverage": pr["기업순이익률"]["시계열평균분자"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "자산총계",
                    "values": {
                    "year2023": pr["기업순이익률"]["데이터분모값"],
                    "timeSeriesAverage": pr["기업순이익률"]["시계열평균분모"],
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
                "year2023": pr["자기자본세전순이익률"]["데이터"],
                "timeSeriesAverage": f'{(float(pr["자기자본세전순이익률"]["시계열평균분자"])/float(pr["자기자본세전순이익률"]["시계열평균분모"]))/100}%',
                "industryMedian": f"{pr['자기자본세전순이익률']['업종중위수']}%",
                "timeSeriesScore": pr["자기자본세전순이익률"]["시계열점수"],
                "industryScore": pr["자기자본세전순이익률"]["업종점수"]
                },
                "children": [
                {
                    "name": "법인세비용차감전순이익",
                    "values": {
                    "year2023": pr["자기자본세전순이익률"]["데이터분자값"],
                    "timeSeriesAverage": pr["자기자본세전순이익률"]["시계열평균분자"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "자본총계",
                    "values": {
                    "year2023": pr["자기자본세전순이익률"]["데이터분모값"],
                    "timeSeriesAverage": pr["자기자본세전순이익률"]["시계열평균분모"],
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
                "year2023": pr["자본금세전순이익률"]["데이터"],
                "timeSeriesAverage": f'{(float(pr["자본금세전순이익률"]["시계열평균분자"])/float(pr["자본금세전순이익률"]["시계열평균분모"]))/100}%',
                "industryMedian": f"{pr['자본금세전순이익률']['업종중위수']}%",
                "timeSeriesScore": pr["자본금세전순이익률"]["시계열점수"],
                "industryScore": pr["자본금세전순이익률"]["업종점수"]
                },
                "children": [
                {
                    "name": "법인세비용차감전순이익",
                    "values": {
                    "year2023": pr["자본금세전순이익률"]["데이터분자값"],
                    "timeSeriesAverage": pr["자본금세전순이익률"]["시계열평균분자"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "자본금",
                    "values": {
                    "year2023": pr["자본금세전순이익률"]["데이터분모값"],
                    "timeSeriesAverage": pr["자본금세전순이익률"]["시계열평균분모"],
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
                "year2023": pr["자본금순이익률"]["데이터"],
                "timeSeriesAverage": f'{(float(pr["자본금순이익률"]["시계열평균분자"])/float(pr["자본금순이익률"]["시계열평균분모"]))/100}%',
                "industryMedian": f"{pr['자본금순이익률']['업종중위수']}%",
                "timeSeriesScore": pr["자본금순이익률"]["시계열점수"],
                "industryScore": pr["자본금순이익률"]["업종점수"]
                },
                "children": [
                {
                    "name": "당기순이익",
                    "values": {
                    "year2023": pr["자본금순이익률"]["데이터분자값"],
                    "timeSeriesAverage": pr["자본금순이익률"]["시계열평균분자"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "자본금",
                    "values": {
                    "year2023": pr["자본금순이익률"]["데이터분모값"],
                    "timeSeriesAverage": pr["자본금순이익률"]["시계열평균분모"],
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
                "year2023": pr["자기자본순이익률"]["데이터"],
                "timeSeriesAverage": f'{(float(pr["자기자본순이익률"]["시계열평균분자"])/float(pr["자기자본순이익률"]["시계열평균분모"]))/100}%',
                "industryMedian": f"{pr['자기자본순이익률']['업종중위수']}%",
                "timeSeriesScore": pr["자기자본순이익률"]["시계열점수"],
                "industryScore": pr["자기자본순이익률"]["업종점수"]
                },
                "children": [
                {
                    "name": "당기순이익",
                    "values": {
                    "year2023": pr["자기자본순이익률"]["데이터분자값"],
                    "timeSeriesAverage": pr["자기자본순이익률"]["시계열평균분자"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "자본총계",
                    "values": {
                    "year2023": pr["자기자본순이익률"]["데이터분모값"],
                    "timeSeriesAverage": pr["자기자본순이익률"]["시계열평균분모"],
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
                { "key": "avg5Years", "label": "5개년 평균" },
                { "key": "sectorMedian", "label": "섹터중위수" },
                { "key": "scoreA", "label": "점수A" },
                { "key": "scoreB", "label": "점수B" }
            ],
            "items":
            [
            {
                "name": "매출액세전순이익률",
                "values": {
                "year2023": mg["매출액세전순이익률"]["데이터"],
                "timeSeriesAverage": f'{(float(mg["매출액세전순이익률"]["시계열평균분자"])/float(mg["매출액세전순이익률"]["시계열평균분모"]))/100}%',
                "industryMedian": f"{mg['매출액세전순이익률']['업종중위수']}%",
                "timeSeriesScore": mg["매출액세전순이익률"]["시계열점수"],
                "industryScore": mg["매출액세전순이익률"]["업종점수"]
                },
                "children": [
                {
                    "name": "법인세비용차감전순이익",
                    "values": {
                    "year2023": mg["매출액세전순이익률"]["데이터분자값"],
                    "timeSeriesAverage": mg["매출액세전순이익률"]["시계열평균분자"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "매출액",
                    "values": {
                    "year2023": mg["매출액세전순이익률"]["데이터분모값"],
                    "timeSeriesAverage": mg["매출액세전순이익률"]["시계열평균분모"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                }
                ]
            },

            {
                "name": "매출액순이익률",
                "values": {
                "year2023": mg["매출액순이익률"]["데이터"],
                "timeSeriesAverage": f'{(float(mg["매출액순이익률"]["시계열평균분자"])/float(mg["매출액순이익률"]["시계열평균분모"]))/100}%',
                "industryMedian": f"{mg['매출액순이익률']['업종중위수']}%",
                "timeSeriesScore": mg["매출액순이익률"]["시계열점수"],
                "industryScore": mg["매출액순이익률"]["업종점수"]
                },
                "children": [
                {
                    "name": "당기순이익",
                    "values": {
                    "year2023": mg["매출액순이익률"]["데이터분자값"],
                    "timeSeriesAverage": mg["매출액순이익률"]["시계열평균분자"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "매출액",
                    "values": {
                    "year2023": mg["매출액순이익률"]["데이터분모값"],
                    "timeSeriesAverage": mg["매출액순이익률"]["시계열평균분모"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                }
                ]
            },

            {
                "name": "매출액영업이익률",
                "values": {
                "year2023": mg["매출액영업이익률"]["데이터"],
                "timeSeriesAverage": f'{(float(mg["매출액영업이익률"]["시계열평균분자"])/float(mg["매출액영업이익률"]["시계열평균분모"]))/100}%',
                "industryMedian": f"{mg['매출액영업이익률']['업종중위수']}%",
                "timeSeriesScore": mg["매출액영업이익률"]["시계열점수"],
                "industryScore": mg["매출액영업이익률"]["업종점수"]
                },
                "children": [
                {
                    "name": "영업이익",
                    "values": {
                    "year2023": mg["매출액영업이익률"]["데이터분자값"],
                    "timeSeriesAverage": mg["매출액영업이익률"]["시계열평균분자"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "매출액",
                    "values": {
                    "year2023": mg["매출액영업이익률"]["데이터분모값"],
                    "timeSeriesAverage": mg["매출액영업이익률"]["시계열평균분모"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                }
                ]
            },

            {
                "name": "EBIT대매출액",
                "values": {
                "year2023": mg["EBIT대매출액"]["데이터"],
                "timeSeriesAverage": f'{(float(mg["EBIT대매출액"]["시계열평균분자"])/float(mg["EBIT대매출액"]["시계열평균분모"]))/100}%',
                "industryMedian": f"{mg['EBIT대매출액']['업종중위수']}%",
                "timeSeriesScore": mg["EBIT대매출액"]["시계열점수"],
                "industryScore": mg["EBIT대매출액"]["업종점수"]
                },
                "children": [
                {
                    "name": "법인세비용차감전순이익+이자비용",
                    "values": {
                    "year2023": mg["EBIT대매출액"]["데이터분자값"],
                    "timeSeriesAverage": mg["EBIT대매출액"]["시계열평균분자"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "매출액",
                    "values": {
                    "year2023": mg["EBIT대매출액"]["데이터분모값"],
                    "timeSeriesAverage": mg["EBIT대매출액"]["시계열평균분모"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                }
                ]
            },

            {
                "name": "EBITDA대매출액",
                "values": {
                "year2023": mg["EBITDA대매출액"]["데이터"],
                "timeSeriesAverage": f'{(float(mg["EBITDA대매출액"]["시계열평균분자"])/float(mg["EBITDA대매출액"]["시계열평균분모"]))/100}%',
                "industryMedian": f"{mg['EBITDA대매출액']['업종중위수']}%",
                "timeSeriesScore": mg["EBITDA대매출액"]["시계열점수"],
                "industryScore": mg["EBITDA대매출액"]["업종점수"]
                },
                "children": [
                {
                    "name": "법인세비용차감전순이익+이자비용+감가상각비+무형자산상각비",
                    "values": {
                    "year2023": mg["EBITDA대매출액"]["데이터분자값"],
                    "timeSeriesAverage": mg["EBITDA대매출액"]["시계열평균분자"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "매출액",
                    "values": {
                    "year2023": mg["EBITDA대매출액"]["데이터분모값"],
                    "timeSeriesAverage": mg["EBITDA대매출액"]["시계열평균분모"],
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
            "items":
            [
            {
                "name": "총자산증가율",
                "values": {
                "year2023": gr["총자산증가율"]["데이터"],
                "timeSeriesAverage": f'{(float(gr["총자산증가율"]["시계열평균분자"])/float(gr["총자산증가율"]["시계열평균분모"]))/100}%',
                "industryMedian": f"{gr['총자산증가율']['업종중위수']}%",
                "timeSeriesScore": gr["총자산증가율"]["시계열점수"],
                "industryScore": gr["총자산증가율"]["업종점수"]
                },
                "children": [
                {
                    "name": "당기자산총계-전기자산총계",
                    "values": {
                    "year2023": gr["총자산증가율"]["데이터분자값"],
                    "timeSeriesAverage": gr["총자산증가율"]["시계열평균분자"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "전기자산총계",
                    "values": {
                    "year2023": gr["총자산증가율"]["데이터분모값"],
                    "timeSeriesAverage": gr["총자산증가율"]["시계열평균분모"],
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
                "year2023": gr["유형자산증가율"]["데이터"],
                "timeSeriesAverage": f'{(float(gr["유형자산증가율"]["시계열평균분자"])/float(gr["유형자산증가율"]["시계열평균분모"]))/100}%',
                "industryMedian": f"{gr['유형자산증가율']['업종중위수']}%",
                "timeSeriesScore": gr["유형자산증가율"]["시계열점수"],
                "industryScore": gr["유형자산증가율"]["업종점수"]
                },
                "children": [
                {
                    "name": "당기유형자산-전기유형자산",
                    "values": {
                    "year2023": gr["유형자산증가율"]["데이터분자값"],
                    "timeSeriesAverage": gr["유형자산증가율"]["시계열평균분자"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "전기유형자산",
                    "values": {
                    "year2023": gr["유형자산증가율"]["데이터분모값"],
                    "timeSeriesAverage": gr["유형자산증가율"]["시계열평균분모"],
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
                "year2023": gr["유동자산증가율"]["데이터"],
                "timeSeriesAverage": f'{(float(gr["유동자산증가율"]["시계열평균분자"])/float(gr["유동자산증가율"]["시계열평균분모"]))/100}%',
                "industryMedian": f"{gr['유동자산증가율']['업종중위수']}%",
                "timeSeriesScore": gr["유동자산증가율"]["시계열점수"],
                "industryScore": gr["유동자산증가율"]["업종점수"]
                },
                "children": [
                {
                    "name": "당기유동자산-전기유동자산",
                    "values": {
                    "year2023": gr["유동자산증가율"]["데이터분자값"],
                    "timeSeriesAverage": gr["유동자산증가율"]["시계열평균분자"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "전기유동자산",
                    "values": {
                    "year2023": gr["유동자산증가율"]["데이터분모값"],
                    "timeSeriesAverage": gr["유동자산증가율"]["시계열평균분모"],
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
                "year2023": gr["자기자본증가율"]["데이터"],
                "timeSeriesAverage": f'{(float(gr["자기자본증가율"]["시계열평균분자"])/float(gr["자기자본증가율"]["시계열평균분모"]))/100}%',
                "industryMedian": f"{gr['자기자본증가율']['업종중위수']}%",
                "timeSeriesScore": gr["자기자본증가율"]["시계열점수"],
                "industryScore": gr["자기자본증가율"]["업종점수"]
                },
                "children": [
                {
                    "name": "당기자본총계-전기자본총계",
                    "values": {
                    "year2023": gr["자기자본증가율"]["데이터분자값"],
                    "timeSeriesAverage": gr["자기자본증가율"]["시계열평균분자"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "전기자본총계",
                    "values": {
                    "year2023": gr["자기자본증가율"]["데이터분모값"],
                    "timeSeriesAverage": gr["자기자본증가율"]["시계열평균분모"],
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
                "year2023": gr["매출액증가율"]["데이터"],
                "timeSeriesAverage": f'{(float(gr["매출액증가율"]["시계열평균분자"])/float(gr["매출액증가율"]["시계열평균분모"]))/100}%',
                "industryMedian": f"{gr['매출액증가율']['업종중위수']}%",
                "timeSeriesScore": gr["매출액증가율"]["시계열점수"],
                "industryScore": gr["매출액증가율"]["업종점수"]
                },
                "children": [
                {
                    "name": "당기매출액-전기매출액",
                    "values": {
                    "year2023": gr["매출액증가율"]["데이터분자값"],
                    "timeSeriesAverage": gr["매출액증가율"]["시계열평균분자"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "전기매출액",
                    "values": {
                    "year2023": gr["매출액증가율"]["데이터분모값"],
                    "timeSeriesAverage": gr["매출액증가율"]["시계열평균분모"],
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
                { "key": "year2023", "label": "2023" },
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
                "year2023": at["총자산회전율"]["데이터"],
                "timeSeriesAverage": f'{(float(at["총자산회전율"]["시계열평균분자"])/float(at["총자산회전율"]["시계열평균분모"]))/100}%',
                "industryMedian": f"{at['총자산회전율']['업종중위수']}%",
                "timeSeriesScore": at["총자산회전율"]["시계열점수"],
                "industryScore": at["총자산회전율"]["업종점수"]
                },
                "children": [
                {
                    "name": "매출액",
                    "values": {
                    "year2023": at["총자산회전율"]["데이터분자값"],
                    "timeSeriesAverage": at["총자산회전율"]["시계열평균분자"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "자산총계",
                    "values": {
                    "year2023": at["총자산회전율"]["데이터분모값"],
                    "timeSeriesAverage": at["총자산회전율"]["시계열평균분모"],
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
                "year2023": at["자기자본회전율"]["데이터"],
                "timeSeriesAverage": f'{(float(at["자기자본회전율"]["시계열평균분자"])/float(at["자기자본회전율"]["시계열평균분모"]))/100}%',
                "industryMedian": f"{at['자기자본회전율']['업종중위수']}%",
                "timeSeriesScore": at["자기자본회전율"]["시계열점수"],
                "industryScore": at["자기자본회전율"]["업종점수"]
                },
                "children": [
                {
                    "name": "매출액",
                    "values": {
                    "year2023": at["자기자본회전율"]["데이터분자값"],
                    "timeSeriesAverage": at["자기자본회전율"]["시계열평균분자"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "자본총계",
                    "values": {
                    "year2023": at["자기자본회전율"]["데이터분모값"],
                    "timeSeriesAverage": at["자기자본회전율"]["시계열평균분모"],
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
                "year2023": at["자본금회전율"]["데이터"],
                "timeSeriesAverage": f'{(float(at["자본금회전율"]["시계열평균분자"])/float(at["자본금회전율"]["시계열평균분모"]))/100}%',
                "industryMedian": f"{at['자본금회전율']['업종중위수']}%",
                "timeSeriesScore": at["자본금회전율"]["시계열점수"],
                "industryScore": at["자본금회전율"]["업종점수"]
                },
                "children": [
                {
                    "name": "매출액",
                    "values": {
                    "year2023": at["자본금회전율"]["데이터분자값"],
                    "timeSeriesAverage": at["자본금회전율"]["시계열평균분자"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "자본금",
                    "values": {
                    "year2023": at["자본금회전율"]["데이터분모값"],
                    "timeSeriesAverage": at["자본금회전율"]["시계열평균분모"],
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
                "year2023": at["경영자산회전율"]["데이터"],
                "timeSeriesAverage": f'{(float(at["경영자산회전율"]["시계열평균분자"])/float(at["경영자산회전율"]["시계열평균분모"]))/100}%',
                "industryMedian": f"{at['경영자산회전율']['업종중위수']}%",
                "timeSeriesScore": at["경영자산회전율"]["시계열점수"],
                "industryScore": at["경영자산회전율"]["업종점수"]
                },
                "children": [
                {
                    "name": "매출액",
                    "values": {
                    "year2023": at["경영자산회전율"]["데이터분자값"],
                    "timeSeriesAverage": at["경영자산회전율"]["시계열평균분자"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "경영자산",
                    "values": {
                    "year2023": at["경영자산회전율"]["데이터분모값"],
                    "timeSeriesAverage": at["경영자산회전율"]["시계열평균분모"],
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
                "year2023": at["비유동자산회전율"]["데이터"],
                "timeSeriesAverage": f'{(float(at["비유동자산회전율"]["시계열평균분자"])/float(at["비유동자산회전율"]["시계열평균분모"]))/100}%',
                "industryMedian": f"{at['비유동자산회전율']['업종중위수']}%",
                "timeSeriesScore": at["비유동자산회전율"]["시계열점수"],
                "industryScore": at["비유동자산회전율"]["업종점수"]
                },
                "children": [
                {
                    "name": "매출액",
                    "values": {
                    "year2023": at["비유동자산회전율"]["데이터분자값"],
                    "timeSeriesAverage": at["비유동자산회전율"]["시계열평균분자"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "비유동자산",
                    "values": {
                    "year2023": at["비유동자산회전율"]["데이터분모값"],
                    "timeSeriesAverage": at["비유동자산회전율"]["시계열평균분모"],
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
                "year2023": at["유형자산회전율"]["데이터"],
                "timeSeriesAverage": f'{(float(at["유형자산회전율"]["시계열평균분자"])/float(at["유형자산회전율"]["시계열평균분모"]))/100}%',
                "industryMedian": f"{at['유형자산회전율']['업종중위수']}%",
                "timeSeriesScore": at["유형자산회전율"]["시계열점수"],
                "industryScore": at["유형자산회전율"]["업종점수"]
                },
                "children": [
                {
                    "name": "매출액",
                    "values": {
                    "year2023": at["유형자산회전율"]["데이터분자값"],
                    "timeSeriesAverage": at["유형자산회전율"]["시계열평균분자"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "유형자산",
                    "values": {
                    "year2023": at["유형자산회전율"]["데이터분모값"],
                    "timeSeriesAverage": at["유형자산회전율"]["시계열평균분모"],
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
                "year2023": at["재고자산회전율"]["데이터"],
                "timeSeriesAverage": f'{(float(at["재고자산회전율"]["시계열평균분자"])/float(at["재고자산회전율"]["시계열평균분모"]))/100}%',
                "industryMedian": f"{at['재고자산회전율']['업종중위수']}%",
                "timeSeriesScore": at["재고자산회전율"]["시계열점수"],
                "industryScore": at["재고자산회전율"]["업종점수"]
                },
                "children": [
                {
                    "name": "매출액",
                    "values": {
                    "year2023": at["재고자산회전율"]["데이터분자값"],
                    "timeSeriesAverage": at["재고자산회전율"]["시계열평균분자"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "재고자산",
                    "values": {
                    "year2023": at["재고자산회전율"]["데이터분모값"],
                    "timeSeriesAverage": at["재고자산회전율"]["시계열평균분모"],
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
                "year2023": at["상(제)품회전율"]["데이터"],
                "timeSeriesAverage": f'{(float(at["상(제)품회전율"]["시계열평균분자"])/float(at["상(제)품회전율"]["시계열평균분모"]))/100}%',
                "industryMedian": f"{at['상(제)품회전율']['업종중위수']}%",
                "timeSeriesScore": at["상(제)품회전율"]["시계열점수"],
                "industryScore": at["상(제)품회전율"]["업종점수"]
                },
                "children": [
                {
                    "name": "매출액",
                    "values": {
                    "year2023": at["상(제)품회전율"]["데이터분자값"],
                    "timeSeriesAverage": at["상(제)품회전율"]["시계열평균분자"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "상품+제품",
                    "values": {
                    "year2023": at["상(제)품회전율"]["데이터분모값"],
                    "timeSeriesAverage": at["상(제)품회전율"]["시계열평균분모"],
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
                "year2023": at["매출채권회전율"]["데이터"],
                "timeSeriesAverage": f'{(float(at["매출채권회전율"]["시계열평균분자"])/float(at["매출채권회전율"]["시계열평균분모"]))/100}%',
                "industryMedian": f"{at['매출채권회전율']['업종중위수']}%",
                "timeSeriesScore": at["매출채권회전율"]["시계열점수"],
                "industryScore": at["매출채권회전율"]["업종점수"]
                },
                "children": [
                {
                    "name": "매출액",
                    "values": {
                    "year2023": at["매출채권회전율"]["데이터분자값"],
                    "timeSeriesAverage": at["매출채권회전율"]["시계열평균분자"],
                    "industryMedian": "-",
                    "timeSeriesScore": "-",
                    "industryScore": "-"
                    },
                    "children": []
                },
                {
                    "name": "매출채권",
                    "values": {
                    "year2023": at["매출채권회전율"]["데이터분모값"],
                    "timeSeriesAverage": at["매출채권회전율"]["시계열평균분모"],
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
    

