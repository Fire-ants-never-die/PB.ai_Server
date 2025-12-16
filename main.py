import asyncio
import uuid
from fastapi import FastAPI
from pydantic import BaseModel
from program_tool import *
from ai.ai_chatting_queue_controller import *
from data.data_controller import DataController
from contextlib import asynccontextmanager

class ClientRequest(BaseModel):
    user_id:str
    question:str
    tab_name:str
    company_name:str



@app.post('/ask')
async def client_ask(self,req:ClientRequest):
    task_id = str(uuid.uuid4())
    queue_data = ChattingQueueData(
        user_id=req.user_id,
        question= req.question,
        tab_name= req.tab_name,
        company_name=req.company_name,
        user_level= 1
        )

    await qcon.put_task(queue_data)

    return {
        "task_id" : task_id,
        "status" : "queued ok"
    }



#==========[execute server]========

qcon = AIChattingQueueController(2,1000)
dcon = DataController()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("server start")
    await qcon.run()
    yield

    print("server shut down")
    await qcon.stop()
    await asyncio.gather(*qcon.workers,return_exceptions=True)


app = FastAPI(lifespan=lifespan)