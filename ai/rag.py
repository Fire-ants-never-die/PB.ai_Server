from program_tool import *
import json, sys,os,pandas as pd
from openai import OpenAI
import tiktoken

class ComapanyDataChunking:

    def __init__(self,df:pd.DataFrame,company_name,table_name):
        #청크 토큰 길이
        self.len = 0
        #청크
        self.chunk = ""

        self.df_to_text_chunks(df,company_name,table_name)
        self.len = self.token_counter(self.chunk)

    #api에 들어갈 토큰 길이를 카운팅합니다.
    #임베딩은 입력 토큰 길이가 500~1000로 제한할 것입니다.
    #token 측정은 모델별로 상이합니다.
    def token_counter(self,text) -> int:
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))

    #private
    #아래 형식의 dataframe을 str형의 청크로 바꿔줍니다. token은 
    #year    유동자산, 채권 ...
    #2024Q4   4343   234   이런 형태입니다.
    #회사 이름과, 테이블 이름이 string 인자로 들어갑니다.
    def df_to_text_chunks(self,df:pd.DataFrame,company_name:str,table_name:str):
        _type = "재무상태표"
        if table_name[-1] == "I":
            _type = "손익계산서"
        
        common_text = f"[회사명: {company_name}] {_type}"

        for idx, row in df.iterrows():
            text = common_text
            year = ""; property = ""; 
            property_text = ""; data_text = ""
            for col,val in row.items():
                if col == "year":
                    year = val[0:4]
                    property = val[4:]
                    if property[0] == 'Q':
                        property_text += f"{year} {property[1]}분기"
                    else:
                        property_text += f"{year} 3년 시계열평균"
                else:
                    data_text += f" {col} : {val}"
            text += property_text
            text += data_text
            text += "\n"
            self.chunk += text


@singleton
class RAG:

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
            chunk = ComapanyDataChunking(df_list[idx],company,table)
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