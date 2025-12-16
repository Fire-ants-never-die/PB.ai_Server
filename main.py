import asyncio
import uuid
from fastapi import FastAPI
from pydantic import BaseModel
from program_tool import *

class ClientRequest(BaseModel):
    user_id:str
    question:str
    tab_name:str
    company_name:str

@singleton
class Server:
    def __init__(self) -> None:
        self.app = FastAPI()
        self.app.add_api_route("/data",self.get_data,methods=["POST"])
    
    async def get_data(self, req:ClientRequest):
        return {"msg":"hello world!"}




def main():
    server = Server()

if __name__ == "__main__":
    main()