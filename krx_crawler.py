from pykrx import stock
from program_tool import *
import pandas as pd

@singleton
class KrxCrawler:

    def __init__(self):
        self.time_manager = DateTimeManager()

    #date : YYmmdd, market : KOSPI KOSDAQ KONEX
    def get_market_list(self,date:str ="",market = "ALL") -> list:
        if date == "":
            tickers = stock.get_market_ticker_list(market=market)
        else:
            tickers = stock.get_market_ticker_list(date=date,market=market)
        return tickers

    #과호출 하면 안될듯
    def get_market_ticker_name(self,ticker) -> str:
        return stock.get_market_ticker_name(ticker)
    
    #수정주가 반영합니다.
    def get_ohlcv(self,start,end,ticker) -> pd.DataFrame:
        res = pd.DataFrame()
        try:
            res = stock.get_market_ohlcv(start,end,ticker)
        except:
            pass
        return res
    
    #시장의 펀더멘털 (bps,per,pbr,eps,div,dps)데이터 조회 date: YYmmdd, market : KOSPI KOSDAQ KONEX ALL
    def get_market_fundamental(self,date : str = "",market:str= "") -> pd.DataFrame:
        if market == "":
            market = "ALL"
        df = stock.get_market_fundamental(date=date,market=market)
        return df
    # 특정 티커의 기간 펀더멘털 데이터 (freq는 수집 주기. d는 일, m은 월(월말 종가), y는 연)
    def get_fundamental(self,start:str,end:str,ticker:str,freq:str = "d") -> pd.DataFrame:
        df = stock.get_market_fundamental(fromdate = start, todate = end,ticker=ticker,freq=freq,name_display = True)
        return df







def debug():
    krx = KrxCrawler()
    res = krx.get_fundamental("20251101","20251111","005930")
    df = res.head(5)
    print(df)
    print("==========================")
    for idx, row in df.iterrows():
        print(idx,end="") # type: ignore
        print(row)
        print("=========================")

if __name__ == "__main__":
    debug()



""" 
@singleton
class KRXCrawler():
    #상장법인리스트 url
    #url = "http://kind.krx.co.kr/corpgeneral/corpList.do?method=download"

    def __init__(self) -> None:
        self.date_time_manager = DateTimeManager()
        self.data_controller = DataController()

    def crawl_stock_list(self,date : str = ""):
        if date == "":
            date = self.date_time_manager.formatted_today
        
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

        self.kospi_df.set_index("ticker")
        self.kosdaq_df.set_index("ticker")
        self.konex_df.set_index("ticker")

        self.data_controller.create_table(self.kospi_df,"market","kospi")
        self.data_controller.create_table(self.kosdaq_df,"market","kosdaq")
        self.data_controller.create_table(self.konex_df,"market","konex") 
"""