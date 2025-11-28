from program_tool import *
import json, sys,os,pandas as pd
import tiktoken

class Chunking:

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

