from program_tool import *
import json, sys,os,pandas as pd
import tiktoken


#api에 들어갈 토큰 길이를 카운팅합니다.
#임베딩은 입력 토큰 길이가 500~1000로 제한할 것입니다.
#token 측정은 모델별로 상이합니다.
def token_counter(text) -> int:
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))

#정해지지 않은 형식의 dictionary data 청킹 함수
# def chunk_dict_data2(data:dict) -> list:
#     res = [] 

#     #재귀 탐색 함수
#     def rescursive_search(dict_data,keys):
#         for key,value in dict_data.items():
#             current_key = keys + [key]
#             if type(value) == dict:
#                 rescursive_search(value,current_key)
#             #value가 dictionary가 아니라면, list거나 ㄹㅇvalue 일 것이므로 [key1,key2...] : value 형식으로 텍스트 저장
#             else:
#                 adress = ""
#                 for i in range(len(current_key)):
#                     adress += str(current_key[i])
#                     if i != len(current_key) - 1:
#                         adress += ","
#                     else:
#                         adress += ": "
#                 if type(value) == list:
#                     adress += "["
#                     for i in range(len(value)):
#                         adress += f"{str(i+1)}.{value[i]} "
#                         if i != len(value) - 1:
#                             adress += ","
#                         else:
#                             adress += "]"
#                 else:
#                     adress += str(value)
#                 res.append(adress)
#     rescursive_search(data,[])
#     return res

def stringify(value):
    if isinstance(value, dict):
        return " | ".join(
            f"{k}={stringify(v)}" for k, v in value.items()
        )
    elif isinstance(value, list):
        return ", ".join(stringify(v) for v in value)
    else:
        return str(value)

def chunk_dict_by_depth(
    data: dict,
    max_depth: int = 2,
    sep: str = "."
) -> list[str]:
    chunks = []

    def dfs(current, path, depth):
        # depth가 max_depth에 도달하면 청킹
        if depth == max_depth:
            key_path = sep.join(path)
            value_str = stringify(current)
            chunks.append(f"{key_path}: {value_str}")
            return

        # dict이면 계속 순회
        if isinstance(current, dict):
            for k, v in current.items():
                dfs(v, path + [str(k)], depth + 1)
        else:
            # depth 이전에 leaf 값이 나오면 그대로 처리
            key_path = sep.join(path)
            chunks.append(f"{key_path}: {stringify(current)}")

    dfs(data, [], 0)
    return chunks

def chunk_dict_data(dt:dict)->list:
    return chunk_dict_by_depth(dt)

class Chunking:

    def __init__(self,df:pd.DataFrame,company_name,table_name):
        #청크 토큰 길이
        self.len = 0
        #청크
        self.chunk = ""

        self.df_to_text_chunks(df,company_name,table_name)
        self.len = token_counter(self.chunk)

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


def _test():
    data = {"jinu" : {"age" : 24, "height" : 175, "hobby": {"bad" : "game", "good" : "coding" }}, "today":"1203"}

if __name__ == "__main__":
    _test()

