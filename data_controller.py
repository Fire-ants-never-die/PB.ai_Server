import os
import json
from program_tool import *


@singleton
class DataController():
    
    @staticmethod
    def get_meta_data() ->dict:
        current_dir = os.path.dirname(__file__)
        meta_path = os.path.join(current_dir,'data','meta.json')
        with open(meta_path,'r',encoding='utf-8') as f:
            meta_data = json.load(f)
        return meta_data