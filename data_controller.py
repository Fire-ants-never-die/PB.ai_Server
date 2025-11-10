import os
import json
import pandas as pd
from program_tool import *
import sqlite3


@singleton
class DataController:

    def __init__(self) -> None:
        #DB path
        self.pathtype = {"extracted":"data/extracted.db","raw":"data/raw.db","market":"data/market.db"}
    
    def create_table(self,df:pd.DataFrame,dbtype:str,table_name:str,append:bool = True): #dbtype : "extracted", "raw", "market"
        con = sqlite3.connect(self.pathtype[dbtype])
        property = "append" if append == True else "replace"
        df.to_sql(table_name,con,if_exists=property,index=False)
        con.close()

    def create_table_set_key(self,df:pd.DataFrame,dbtype:str,table_name:str,key_name:str):
        con = sqlite3.connect(self.pathtype[dbtype])   
        name_property = f"'{key_name}' TEXT PRIMARY KEY, "
        for col in df.columns:
            if col == key_name:
                continue
            name_property += f"'{col}' TEXT, "
        name_property = name_property[:-2]

        sql_order = f"CREATE TABLE IF NOT EXISTS '{table_name}' ({name_property})"
        cursor = con.cursor()
        cursor.execute(sql_order)
        try:
            df.to_sql(table_name,con,if_exists="append",index=False)
        except sqlite3.IntegrityError:
            # 이미 존재하는 값일 가능성 큼.
            pass
        con.close()

    def read_table(self,dbtype:str,table_name:str)->pd.DataFrame:
        con = sqlite3.connect(self.pathtype[dbtype])
        res = pd.read_sql(f"SELECT * FROM '{table_name}'",con)
        con.close()
        return res
    
    def check_table(self):
        pass


    def get_meta_data(self) ->dict:
        current_dir = os.path.dirname(__file__)
        meta_path = os.path.join(current_dir,'data','meta.json')
        with open(meta_path,'r',encoding='utf-8') as f:
            meta_data = json.load(f)
        return meta_data
    
    def save_df_excel(self,df:pd.DataFrame, name : str):
        df.to_excel(excel_writer = f'{name}.xlsx')

    #Deprecated
    def save_df_feather(self,df:pd.DataFrame, year:int,name: str,is_raw:bool = True):
        current_dir = os.path.dirname(__file__)
        path = "data/"
        if is_raw:
            path += f"raw/{year}"
        else:
            path += f"extracted/{year}"
        path = os.path.join(current_dir,path)
        #path 존재 확인
        os.makedirs(path,exist_ok=True)
        path = os.path.join(path,f'{name}.feather')
        df.to_feather(path)
    



 
    @staticmethod
    #ftype : Y(사업보고서), H(반기), Q1 (1분기)
    def get_finstate_data(ticker: str, year:int, property : str) ->pd.DataFrame:
        path = f"data/{year}/{year}{ticker}{property}.feather"

        try:
            res = pd.read_feather(path)
        except FileNotFoundError:
            print(f"{ticker}경로 찾기 에러")

        except Exception as e:
            print(f"{ticker}데이터를 불러오는 중 에러 발생 :",e)
        return res
    
    @staticmethod
    #ftype : Y(사업보고서), H(반기), Q1 (1분기)
    def get_raw_finstate_data(ticker: str, year:int, ftype : str)->pd.DataFrame:
        path = f"data/raw/{year}/Y{year}T{ticker}P{ftype}.feather"
        res = pd.DataFrame()
        try:
            res =  pd.read_feather(path)
        except FileNotFoundError:
            print(f"{ticker}경로 찾기 에러")
            print(path)
        except Exception as e:
            print(f"{ticker}데이터를 불러오는 중 에러 발생 :",e)

        return res