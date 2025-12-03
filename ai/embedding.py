from program_tool import *
import json, sys,os,pandas as pd
from openai import OpenAI
from chunking import Chunking,chunk_dict_data
from prompt import GPT
import chromadb

@singleton
class Embedding:

    CHUNK_LENGTH = 1000

    def __init__(self):
        gpt = GPT()   
        self.client = gpt.client

    #임베딩 & 로컬 메모리 저장 (사용자 질문 임베딩, 리포트 임베딩)
    #인자로 들어가는 정보들은, 불규칙적 일 가능성이 높습니다.
    # 따라서 청킹은 dictionary기반의 key:value형태로 잘라지되, value 또한 dictionay일 가능성이 있으므로
    # chunking.py에서 chunking이 재귀적으로 이루어집니다. 
    def embedding_on_memory(self,data,model_name:str = "text-embedding-3-small"):
        chunk = chunk_dict_data(data)
        embeddings = [self.client.embeddings.create(model=model_name,input=t).data[0].embedding for t in chunk] # type: ignore
        chroma = chromadb.Client()
        

        
    #임베딩 & 주기억장치 저장 (db_folder)
    #db에서 불러온 데이터프레임을 리스트화 하고, 각 데이터프레임에 맞는 [회사이름,테이블이름] 리스트를
    #df_list 와 company_table_list로 집어넣습니다.
    #한 번에 너무 많은 양을 df_list로 넣으면, 메모리 사용량이 커질 것 같습니다. 500개의 회사 단위로 넣는게 좋아보입니다.
    def embedding_from_extractd_db(self,df_list:pd.DataFrame,company_table_list:list,model : str = "small"):
        #embedding 모델 설정 추후에 모델을 large로 바꿀 수도 있습니다.
        if model != "large" or model != "small":
            return
        model_name = "text-embedding-3-" + model

        #임베딩 결과 저장 리스트
        embeddings = []

        #청킹. 청킹 길이를 1000개 전후로 자릅니다.
        chunked = []
        last_chunk_size = 0
        last_chunk = ""
        for idx in range(len(df_list)):
            company = company_table_list[idx][0]; table = company_table_list[idx][1]
            #청킹하고 1200개 미만이면 병합 1200개 넘으면 새로 
            chunk = Chunking(df_list[idx],company,table)
            if last_chunk_size + chunk.len >= RAG.CHUNK_LENGTH * 1.2:
                chunked.append(last_chunk)
                last_chunk = chunk
            else:
                last_chunk += chunk
        #임베딩
        
        for chunk in chunked:
            emb = self.client.embeddings.create( # type: ignore
                model = model_name,
                input = chunk
            )
            embeddings.append(emb.data[0].embedding)
        
        return embeddings