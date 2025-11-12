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
