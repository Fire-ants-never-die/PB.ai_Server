import pandas as pd
import json
from program_tool import *
from data_controller import DataController
from tqdm import tqdm
import OpenDartReader
import openpyxl
import pyarrow

from pykrx import stock,bond

@singleton
class ReportCrawler():

    def __init__(self):
        #api key등이 담긴 data/meta.json 
        meta_data = DataController().get_meta_data()

        #api key
        self.api_key = meta_data["api_key"]

        #크롤링한 재무제표/연결제무제표 +@ 에서 추출할 항목들
        self.balance_name = meta_data["balance_name"] #이름으로 추출
        self.income_name = meta_data["income_name"]
        self.balance_id = meta_data["balance_id"] #개정과목체계에 따른 id로 추출

        #OpenDartReader class
        self.dart = OpenDartReader(self.api_key) # type: ignore

        #날짜/연도 관리
        self.datetime = DateTimeManager()

    # "stock_list" items must be uniform as either ticker or name
    #  ticker
    def crawl_finstate_year(self,stock_list: list, year : int):
        for stock in stock_list:
            fdata = self.dart.finstate_all(stock,year)
            DataController().save_df_feather(fdata,year,f"{stock}Y",True)

            #정리해서 다시 엑셀파일에 저장. 추후에 기능분리할 것
            #fdata.to_excel(excel_writer = f'testdata/{stock}.xlsx')
    
    #크롤링한 재무제표로부터 meta.json의 회계항목들 파싱 -> data/year/005930Y.feather
    #feather파일 이름명 규칙 : 사업보고서(1년)은 ticker뒤에 Y 붙이고, 반기는 H, 분기는 Q1,Q2...이런식으로 
    #ftype : Y / H / Q1 / Q2 / Q3 /Q4
    def extract_items(self,df:pd.DataFrame,ticker:str,year:int,ftype:str):
        #추출 성공 항목
        data = []
        #추출실패 항목
        failed_items = []
        #값이 여러개 있는 경우 (검수 필요)
        strange_items = []
        #name으로 먼저 추출 시도
        for i in range(len(self.balance_name)):
            item = {}
            item["종류"] = "재무상태표"
            name = self.balance_name[i]
            #당기 파싱 (thstrm_amount)
            amount_balance = df.loc[(df['sj_nm']=="재무상태표")&(df['account_nm']==name),'thstrm_amount'].to_list() # type: ignore
            if len(amount_balance) == 1:
                item[name] = amount_balance[0]
            elif len(amount_balance) > 2 :
                strange_items.append(name)
                item[name] = None
            else:
                failed_items.append(name)
                item[name] = None
            data.append(item)
        for i in range(len(self.income_name)):
            item = {}
            item["종류"] = "손익계산서"
            name = self.income_name[i]
            amount_income = df.loc[(df['sj_nm']=="손익계산서")&(df['account_nm']==name),'thstrm_amount'].to_list() # type: ignore
            if len(amount_income) == 1:
                item[name] = amount_income[0]
            elif len(amount_income) > 2 :
                strange_items.append(name)
                item[name] = None
            else:
                failed_items.append(name)
                item[name] = None
            data.append(item)


        res_df = pd.DataFrame(data)
        #for debug
        res_df.to_excel(excel_writer="testdata/testresult.xlsx")
        DataController().save_df_feather(res_df,year,f"{ticker}{ftype}",False)
    
    #DB001, DB002  O(n^2)
    #balance 와 income은 각각 재무상태표,손익계산서를 파싱할지 안할지를 체크하는 bool 변수입니다.
    def parse_5year_data(self,tickerlist:list,balance= True,income = True):
        current_year = self.datetime.year
        for dy in range(1,6):
            target_year = current_year - dy
            #크롤링
            self.crawl_finstate_year(tickerlist,target_year)
            #파싱
            for ticker in tickerlist:
                raw_df = DataController().get_raw_finstate_data(ticker,target_year,'Y')
                if raw_df.empty:
                    continue
                self.extract_items(raw_df,ticker,target_year,'Y')
        
    def test(self):
        self.parse_5year_data(["005930"])
        """
        self.crawl_finstate_year(["005930"],2024)
        raw_df = DataController().get_raw_finstate_data("005930",2024,'Y')
        self.extract_items(raw_df,"005930",2024,'Y')
        df = DataController().get_finstate_data("005930",2024,'Y')
        df.to_excel("testdata/test.xlsx")
        print(df)
        """
        return
        


#인터넷을 사용해서 긁어올 기업정보가 있을때 사용하는 클래스입니다.
@singleton
class KRXCrawler():
    #상장법인리스트 url
    #url = "http://kind.krx.co.kr/corpgeneral/corpList.do?method=download"

    def __init__(self) -> None:
        self.date_time_manager = DateTimeManager()

    def crawl_stock_list(self,date : str = ""):
        if date == "":
            date = self.date_time_manager.formatted_today
        #kospi(유가)
        tickers_kospi = stock.get_market_ticker_list(date,market="KOSPI")
        tickers_kosdaq = stock.get_market_ticker_list(date,market="KOSDAQ")
        tickers_konex = stock.get_market_ticker_list(date,market="KONEX")
        
        kospi_list_dict = {"ticker":[],"name":[]}
        kosdaq_list_dict = {"ticker":[],"name":[]}
        konex_list_dict = {"ticker":[],"name":[]}

        for ticker in tickers_kospi:
            name = stock.get_market_ticker_name(ticker)
            kospi_list_dict["ticker"].append(ticker)
            kospi_list_dict["name"].append(name)

        for ticker in tickers_kosdaq:
            name = stock.get_market_ticker_name(ticker)
            kosdaq_list_dict["ticker"].append(ticker)
            kosdaq_list_dict["name"].append(name)

        for ticker in tickers_konex:
            name = stock.get_market_ticker_name(ticker)
            konex_list_dict["ticker"].append(ticker)
            konex_list_dict["name"].append(name)
        
        self.kospi_df = pd.DataFrame(kospi_list_dict)
        self.kosdaq_df = pd.DataFrame(kosdaq_list_dict)
        self.konex_df = pd.DataFrame(konex_list_dict)

        self.kospi_df.set_index("name")

def debug():
    reportCrawler =ReportCrawler()

    test_list = ["005930","000660","373220","207940"]

    reportCrawler.test()




if __name__ == "__main__":
    debug()

