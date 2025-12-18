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
        with open(f'{ticker}.json', 'r', encoding='utf-8') as f:
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
        profile.append(temp)
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