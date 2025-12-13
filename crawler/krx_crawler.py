from pykrx import stock
import FinanceDataReader as fdr
import pandas as pd
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from program_tool import *
from controller.data_controller import DataController

@singleton
class KrxCrawler:

    def __init__(self):
        self.time_manager = DateTimeManager()
        self.data_controller = DataController()
        self.date = DateTimeManager()

        #오늘 시장 크롤링 (런타임 메모리에 저장하는데, db에도 저장은 함..)
        self.market_df = self.update_market_info()

    #시장의 티커들을 리스트로 반환합니다.
    #date : YYmmdd, market : KOSPI KOSDAQ KONEX
    def get_market_list(self,date:str ="",market = "ALL") -> list:
        try:
            if date == "":
                tickers = stock.get_market_ticker_list(market=market)
            else:
                tickers = stock.get_market_ticker_list(date=date,market=market)
            return tickers
        except:
            return []

    #티커로 회사이름을 알려줍니다. 못찾으면 str 타입으로 "Null" 반환
    def get_market_ticker_name(self,ticker) -> str:
        res = ""

        return res
    
    
    #시장의 펀더멘털 (bps,per,pbr,eps,div,dps)데이터 조회 date: YYmmdd, market : KOSPI KOSDAQ KONEX ALL
    def get_market_fundamental(self,date : str = "",market:str= "") -> pd.DataFrame:
        try:
            if market == "":
                market = "ALL"
            df = stock.get_market_fundamental(date=date,market=market)
            return df
        except:
            return pd.DataFrame()
#------------------------------------------------------------------------------------
#       개 별 회 사 정 보     크 롤 링
#-------------------------------------------------------------------------------------
    #start날짜부터, end날짜까지의 해당ticker의 ohlcv를 데이터프레임으로 반환합니다.
    #수정주가 반영합니다.
    def get_ohlcv(self,start,end,ticker) -> pd.DataFrame:
        res = pd.DataFrame()
        try:
            res = stock.get_market_ohlcv(start,end,ticker)
        except:
            pass
        return res
    
    # 특정 티커의 기간 펀더멘털 데이터 (freq는 수집 주기. d는 일, m은 월(월말 종가), y는 연)
    def get_fundamental(self,start:str,end:str,ticker:str,freq:str = "d") -> pd.DataFrame:
        try:
            df = stock.get_market_fundamental(fromdate = start, todate = end,ticker=ticker,freq=freq,name_display = True)
            return df
        except:
            return pd.DataFrame()

    # 특정 티커의 [시가총액,발행주식수] 데이터
    def get_market_cap(self,ticker) -> list:
        try:
            df = stock.get_market_cap(fromdate = self.time_manager.get_past_time(2),todate = self.time_manager.formatted_today,ticker=ticker)
            last_data = df.iloc[-1]
            return [int(last_data["시가총액"]),int(last_data["상장주식수"])]
        except:
            return [0,0]


#--------------------------------------------------
#             DB 로 저장
#--------------------------------------------------
    #오늘자 모든 기업의
    #  이름/티커/ohlcv/fundametal data를 크롤링 하여 data/market.db에 저장합니다.
    def update_market_info(self) -> pd.DataFrame:
        df = pd.DataFrame()
        try:
            df = fdr.StockListing('KRX')
        except:
            pass
        company_df = df[['Code','Name','Market','Dept','Open','High','Low','Close','Volume','Marcap','Stocks']]
        
        #db 저장코드. 런타임 메모리가 부족하지 않다면 나중에 지워도 될듯.
        self.data_controller.create_table_set_key(df = company_df,dbtype="market",table_name=self.date.formatted_today,key_name='Code') # type: ignore

        return company_df # type: ignore


def debug():
    krx = KrxCrawler()
    res = krx.get_market_cap("005930")
    print(res)
if __name__ == "__main__":
    df = fdr.StockListing('KRX')   # 전체 상장종목
    print(df.columns.tolist())
