from program_tool import *
import json, sys,os,pandas as pd
from openai import OpenAI

class ComapanyDataChunking:

    def __init__(self,df:pd.DataFrame,company_name):
        self.df = df
        self.company_name = company_name


    #private
    #아래 형식의 dataframe을 청크로 바꿔줍니다. token은 
    #year    유동자산, 채권 ...
    #2024Q4   4343   234 
    #회사 이름과, 테이블 이름이 string 인자로 들어갑니다.
    def df_to_text_chunks(self,df:pd.DataFrame,company_name:str,table_name:str):
        chunks = []
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
            chunks.append(text)
        return chunks


@singleton
class OpenAi:

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
    def get_embedding(self,df_list:pd.DataFrame,company_table_list:list,model : str = "small"):
        if model != "large" or model != "small":
            return
        model_name = "text-embedding-3-" + model

        embeddings = []

        for idx in range(len(df_list)):
            df = df_list[idx]; company = company_table_list[idx][0]; table = company_table_list[idx][1]
            emb = self.client.embeddings.create(
                model = model_name,
                input = df
            )           

