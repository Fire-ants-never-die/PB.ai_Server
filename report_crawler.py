import pandas as pd
import json
from program_tool import *
from data_controller import DataController
from tqdm import tqdm
import OpenDartReader
import openpyxl
import pyarrow

@singleton
class ReportCrawler():

    def __init__(self):
        #api key등이 담긴 data/meta.json 
        meta_data = DataController().get_meta_data()
        self.api_key = meta_data["api_key"]

        #OpenDartReader class
        self.dart = OpenDartReader(self.api_key) # type: ignore

        #test : dataframe   
        # 당좌자산이랑 차입급이자급부채는 파싱하는 거 아님. 
        # 비율항목 계산할 것 (기능사항 요구 명세서 선택데이터)
        # 재무상태표 < 연결재무상대표, 손익계산서 < 포괄손익계산서(연결손익계산서) (테이블 따로)
        #재무상태표에서 재고자산항목의 하위항목(상품,제품)은 없을 가능성도 있는데 이때 null처리 할 것.
        # 회사 - 1.연도별 필수데이터 / 2.연도별 선택데이터 



        #test = self.dart.finstate_all('농심', 2021)
        # print(test.columns)
        #test.to_excel(excel_writer = 'testdata/sk_test.xlsx')
        #test.to_feather('testdata/test.feather')
    
    # "stock_list" items must be uniform as either ticker or name
    #  ticker
    def crawl_finstate_year(self,stock_list: list, year : int):
        for stock in stock_list:
            finstate = self.dart.finstate_all(stock,year)
            finstate.to_feather(f'data/{year}{stock}.feather')

            #정리해서 다시 엑셀파일저 저장 추후에 기능분리할 것
            finstate.to_excel(excel_writer = f'testdata/{stock}.xlsx')



#인터넷을 사용해서 긁어올 기업정보가 있을때 사용하는 클래스입니다.
@singleton
class CompanyInfoCrawler():
    
    def __init__(self) -> None:
        self.reportCrawler = ReportCrawler()

    def crawl_company_list(self):
        print("hi")
        pass

def debug():
    reportCrawler =ReportCrawler()

    test_list = ["005930","000660","373220","207940"]
    
    company_info_crawler = CompanyInfoCrawler()

    company_info_crawler.crawl_company_list()



if __name__ == "__main__":
    debug()

