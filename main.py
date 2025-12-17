import asyncio
import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
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
        task_id = task_id,
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
        task_id =task_id,
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
        task_id =task_id,
        user_id=req.user_id,
        user_level= 1))
    response = await scon.put_task(queue_data)

    return response

@app.post('/prevqna/delete')
async def delete_prev_qna_session(req:ClientRequest):
    task_id = str(uuid.uuid4())
    queue_data = ServerQueueData(QueueItem(
        type = "delete_session",
        task_id =task_id,
        user_id=req.user_id,
        company_name=req.company_name,
        tab_name=req.tab_name,
        user_level= 1,
        ))
    response = await scon.put_task(queue_data)

    return response
