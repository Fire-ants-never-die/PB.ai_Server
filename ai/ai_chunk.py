import pandas as pd
import sys,os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from program_tool import *

class Chunking:

    def __init__(self,df:pd.DataFrame):
        self.df = df
    
    
    #private
    def _make_chunk(self):
        pass
