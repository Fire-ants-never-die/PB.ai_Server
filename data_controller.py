import os
import json
import pandas as pd
from program_tool import *


@singleton
class DataController:

    @staticmethod
    def get_meta_data() ->dict:
        current_dir = os.path.dirname(__file__)
        meta_path = os.path.join(current_dir,'data','meta.json')
        with open(meta_path,'r',encoding='utf-8') as f:
            meta_data = json.load(f)
        return meta_data
    
    @staticmethod
    def save_df_excel(df:pd.DataFrame, name : str):
        df.to_excel(excel_writer = f'{name}.xlsx')

    
    @staticmethod
    def save_df_feather(df:pd.DataFrame, year:int,name: str,is_raw:bool = True):
        current_dir = os.path.dirname(__file__)
        path = "data/"
        if is_raw:
            path += f"raw/{year}"
        else:
            path += f"{year}"
        path = os.path.join(current_dir,path)
        #path 존재 확인
        os.makedirs(path,exist_ok=True)
        path = os.path.join(path,f'{name}.feather')
        df.to_feather(path)


 
    @staticmethod
    #ftype : Y(사업보고서), H(반기), Q1 (1분기)
    def get_finstate_data(ticker: str, year:int, ftype : str) ->pd.DataFrame:
        path = f"data/{year}/{ticker}{ftype}.feather"

        try:
            res = pd.read_feather(path)
        except FileNotFoundError:
            print(f"{ticker}경로 찾기 에러")

        except Exception as e:
            print(f"{ticker}데이터를 불러오는 중 에러 발생 :",e)
        return res
    
    @staticmethod
    #ftype : Y(사업보고서), H(반기), Q1 (1분기)
    def get_raw_finstate_data(ticker: str, year:int, ftype : str) ->pd.DataFrame:
        path = f"data/raw/finstate/{year}{ticker}{ftype}.feather"

        try:
            res = pd.read_feather(path)
        except FileNotFoundError:
            print(f"{ticker}경로 찾기 에러")

        except Exception as e:
            print(f"{ticker}데이터를 불러오는 중 에러 발생 :",e)
        return res
