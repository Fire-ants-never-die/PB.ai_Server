from program_tool import *
import json, sys,os,pandas as pd
from openai import OpenAI
from chunking import Chunking

@singleton
class Embedding:

    CHUNK_LENGTH = 1000

    #key.json 파일에서 api key를 불러오고, OpenAI 객체를 인스턴스 변수로 선언합니다.
    def __init__(self,test = False):
        
        with open("key.json") as f:
            self.key_dict = json.load(f)

        if test:
            keycode = "api_key_test"
        else:
            keycode = "api_key"       

        __api_key= self.key_dict[keycode]

        self.client = OpenAI(api_key=__api_key)
    


    #임베딩
    #db에서 불러온 데이터프레임을 리스트화 하고, 각 데이터프레임에 맞는 [회사이름,테이블이름] 리스트를
    #df_list 와 company_table_list로 집어넣습니다.
    #한 번에 너무 많은 양을 df_list로 넣으면, 메모리 사용량이 커질 것 같습니다. 500개의 회사 단위로 넣는게 좋아보입니다.
    def get_embedding(self,df_list:pd.DataFrame,company_table_list:list,model : str = "small"):
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
            emb = self.client.embeddings.create(
                model = model_name,
                input = chunk
            )
            embeddings.append(emb.data[0].embedding)
        
        return embeddings