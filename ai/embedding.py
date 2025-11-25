from program_tool import *
import json, sys,os,pandas as pd
from openai import OpenAI

class ComapanyDataChunking:

    def __init__(self,df:pd.DataFrame,company_name):
        self.df = df
        self.company_name = company_name


    #private
    #아래 형식의 dataframe을 청크로 바꿔줍니다.
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

    def __init__(self,test = False):
        
        with open("key.json") as f:
            self.key_dict = json.load(f)

        if test:
            keycode = "api_key_test"
        else:
            keycode = "api_key"       

        __api_key= self.key_dict[keycode]

        self.client = OpenAI(api_key=__api_key)
    
    def get_embedding(self,chunks):
