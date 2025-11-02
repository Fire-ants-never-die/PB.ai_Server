import os
import json
import pandas as pd
from program_tool import *


@singleton
class DataController:

    save_dir = "data/"   
    test_dir = "testdata/"

    @staticmethod
    def get_meta_data() ->dict:
        current_dir = os.path.dirname(__file__)
        meta_path = os.path.join(current_dir,'data','meta.json')
        with open(meta_path,'r',encoding='utf-8') as f:
            meta_data = json.load(f)
        return meta_data
    
    @staticmethod
    def save_df_excel(df:pd.DataFrame, name : str,istest:bool = False):
        if istest == True:
            #for test
            df.to_excel(excel_writer = DataController().test_dir +f'{name}.xlsx')
        else:
            df.to_excel(excel_writer = DataController().save_dir +f'{name}.xlsx')
    
    @staticmethod
    def save_df_feather(df:pd.DataFrame, name : str, istest:bool = False):
        if istest == True:
            #for test
            df.to_feather(DataController().test_dir +f'{name}.feather')
        else:
            df.to_excel(DataController().save_dir +f'{name}.feather')
 
    @staticmethod
    def read_feather(name : str, istest:bool = False) ->pd.DataFrame:
        if istest == True:
            return pd.read_feather(DataController().test_dir +f'{name}.feather')
        else:
            return pd.read_feather(DataController().save_dir +f'{name}.feather')
