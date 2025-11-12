import pandas as pd
from program_tool import *
from data_controller import DataController
import OpenDartReader
from pykrx import stock,bond

@singleton
class ReportCrawler():

    def __init__(self):
        #api key등이 담긴 data/meta.json
        self.data_controller = DataController()
        meta_data = self.data_controller.get_meta_data()

        #api ke출출
        self.api_key = meta_data["api_key"]

        #크롤링한 재무제표/연결제무제표 +@ 에서 추출할 항목들
        self.balance_name = meta_data["balance_name"] #이름으로 추출
        self.income_name = meta_data["income_name"]
        self.balance_id = meta_data["balance_id"] #개정과목체계에 따른 id로 추출

        #OpenDartReader class
        self.dart = OpenDartReader(self.api_key) # type: ignore

        #날짜/연도 관리
        self.datetime = DateTimeManager()

        #분기별 보고서 reprt_code
        self.reprt_code = [0,'11013','11012','11014', '11011']

        #dart api 호출량 통제 (1000회/분, 20000회/일)를 위한 변수
        #보수적으로 1초에 15번 이상 호출 안되게끔 해야 함함
        self.dart_api_call_volume = 0
        self.timer = Timer()

    # "stock_list" items must be uniform as either ticker or name => only ticker
    #  ticker
    def crawl_finstate(self,ticker: str, year : int, quarter:int):
        #과호출 방지
        if self.dart_api_call_volume >= 19999 :
            return False
        elif self.timer.crawl_timer(self.dart_api_call_volume) == False:
            return False
        #fdata = self.dart.finstate(ticker,year,reprt_code = self.reprt_code[quarter])
        fdata = self.dart.finstate_all(ticker,year)
        self.dart_api_call_volume += 1
        self.data_controller.create_table(fdata,"raw",f"{year}{ticker}Q{quarter}",False)

        #feather (deprecated)
        #self.data_controller.save_df_feather(fdata,year,f"Y{year}T{ticker}PQ4",True)
    
    # (연도+티커+분기)리스트에서 크롤링 안한 항목들만 모아서 리스트로 넘겨줍니다.
    def check_crawled(self,tickermeta_list:list) -> list:
        res = []
        cset = self.data_controller.get_crawled_set()
        for tickermeta in tickermeta_list:
            if tickermeta in cset:
                continue
            else:
                res.append(tickermeta)
        return res
    
   
    #크롤링한 재무제표로부터 meta.json의 회계항목들 파싱 -> data/year/005930Y.feather
    #feather파일 이름명 규칙 :분기는 Q1,Q2...이런식으로 
    #Y(year)T(ticker)P(property).feather
    #ftype : Q1 / Q2 / Q3 /Q4
    #[재무상태표리스트,손익계산서리스트] 반환
    def extract_items(self,df:pd.DataFrame) -> list:
        #재무상태표
        balance_data = []
        #손익계산서
        income_data = []
        #재무상태표 파싱
        for i in range(len(self.balance_name)):
            name = self.balance_name[i]
            #당기 파싱 (thstrm_amount)
            amount_balance = df.loc[(df['sj_nm']=="재무상태표")&(df['account_nm']==name),'thstrm_amount'].to_list() # type: ignore
            data = None
            if len(amount_balance) == 1:
                data = int(amount_balance[0])
            balance_data.append(data) # type: ignore
        #손익계산서
        for i in range(len(self.income_name)):
            name = self.income_name[i]
            amount_income = df.loc[(df['sj_nm']=="손익계산서")&(df['account_nm']==name),'thstrm_amount'].to_list() # type: ignore
            data = None
            if len(amount_income) == 1:
                data = int(amount_income[0])
            income_data.append(data) 
        #후처리
        #당좌자산 = 유동자산 - 재고자산
        data1 = balance_data[0]
        data2 = balance_data[3]
        if (data1 != None) & (data2 != None):
            balance_data[19] = data1 - data2
        #차입금(이자지급부채) = 단기차입금+유동성장기부채+사채+장기차입금+금융리스부채
        def check_None(idx):
            balance_data[idx] = balance_data[idx] if balance_data[idx] != None else 0
        check_list = [10,11,13,14,15]
        for i in check_list:
            check_None(i)
        balance_data[20] = 0
        for i in check_list:
            balance_data[20] += balance_data[i]
        res = [balance_data,income_data]
        return res
    
    def parse_5year_data(self,tickerlist:list,quarter:int) -> bool:
        current_year = self.datetime.year
        if quarter == 4:
            current_year -= 1
        month = int(self.datetime.formatted_month)
        #성공적으로 파싱한 항목은 meta/parsed_set.pkl 에 저장
        parsed_list = []
        #3월달까지는 사업보고서(Q4)가 발행이 안되어 있을 가능성이 있습니다.
        if month <= 3:
            current_year -= 1
        
        #크롤 안한 재무제표 확인 후 크롤 시작
        tickermeta_list = []
        for ticker in tickerlist:
            for dy in range(0,5):
                year = current_year - dy
                tickermeta_list.append(str(year)+ticker+f"Q{quarter}")
        
        to_crawl_list = self.check_crawled(tickermeta_list)

        #크롤 코드 (추후 멀티 스레드로 변경)

        for tickermeta in to_crawl_list:
            year = int(tickermeta[0:4])
            ticker = tickermeta[4:10]
            quarter = int(tickermeta[-1])

            is_success = self.crawl_finstate(ticker,year,quarter)
            #크롤 한도 초과 예외처리
            if is_success == False:
                return False

        #크롤 한 후, 메타SET 피클 업데이트 코드
        self.data_controller.set_crawled_set(new_list=to_crawl_list)


        #파싱 코드 (추후 멀티 프로세스로 변경)
        for tickermeta in tickermeta_list:
            year = tickermeta[0:4]; quarter = tickermeta[-1]; tickername = tickermeta[4:10]
            df = self.data_controller.read_table("raw",tickermeta)
            datalist = self.extract_items(df)
            #bdata == balance (재무상태표) / idata == income (손익계산서)
            bdata = datalist[0]; idata = datalist[1]
            bdataframe = pd.DataFrame([bdata],columns= self.balance_name); bdataframe["year"] = year + "Q" + f"{quarter}" 
            idataframe = pd.DataFrame([idata],columns= self.income_name); idataframe["year"] = year + "Q" + f"{quarter}"
            #db 저장 코드
            self.data_controller.create_table_set_key(bdataframe,"extracted",f"{tickername}B","year")
            self.data_controller.create_table_set_key(idataframe,"extracted",f"{tickername}I","year")

            parsed_list.append(tickermeta)

        self.data_controller.set_parsed_set(parsed_list)
        return True
        
#--------------------
    #DB에 저장된 파싱항목을 토대로 3년 시계열평균 (이동평균) 값을 구합니다. CY-1, CY-2, CY-3. 반환값은 실패한 티커리스트
    def calculate_MA(self,tickerlist,current_year)->list:
        #실패리스트
        fail_ticker_list = []
        #파싱안된 항목 제외하고 계산해서 저장
        for ticker in tickerlist:
            #파싱검증
            pset = self.data_controller.get_parsed_set()
            flag = True
            for dy in range(1,4):
                year = current_year - dy
                tickermeta = str(year) + ticker + "Q4"
                if tickermeta not in pset:
                    flag = False
                    break
            if not flag:
                fail_ticker_list.append(ticker)
                continue
            
            #파싱 데이터 가져오기

            bdataframe = self.data_controller.read_table("extracted",ticker+"B")
            idataframe = self.data_controller.read_table("extracted",ticker+"I")

            sum_bdict = {"year":f"{current_year}M"}; sum_idict = {"year":f"{current_year}M"}
            # calculate
            for dy in range(1,4):
                year = current_year - dy
                weight = 4 - dy
                bdict = bdataframe[bdataframe['year'] == str(year) + "Q4"].to_dict('records')[0]
                idict = idataframe[idataframe['year'] == str(year) + "Q4"].to_dict('records')[0]

                for key,value in bdict.items():
                    if key == 'year':
                        continue
                    elif value == None:
                        sum_bdict[key] = None # type: ignore
                    else:
                        if key not in sum_bdict:
                            sum_bdict[key] = int(value) * weight # type: ignore

                        elif sum_bdict[key] == None: # type: ignore
                            continue
                        else:
                            sum_bdict[key] += int(value) * weight # type: ignore
                            if dy == 3:
                                sum_bdict[key] /= 3 # type: ignore
                for key,value in idict.items():
                    if key == 'year':
                        continue
                    elif value == None:
                        sum_idict[key] = None # type: ignore
                    else:
                        if key not in sum_idict:
                            sum_idict[key] = int(value) * weight # type: ignore
                        elif sum_idict[key] == None: # type: ignore
                            continue
                        else:
                            sum_idict[key] += int(value) * weight # type: ignore
                            if dy == 3:
                                sum_idict[key] /= 3 # type: ignore
                
                bmdataframe = pd.DataFrame([sum_bdict])
                imdataframe = pd.DataFrame([sum_idict])
                self.data_controller.create_table(bmdataframe,"extracted",f"{ticker}B")
                self.data_controller.create_table(imdataframe,"extracted",f"{ticker}I")

        return fail_ticker_list
                 

            
        """
        for ticker in tickerlist:

            #check whether crawled or not
            #self.data_controller.read_table("raw",f"{ticker}")

            fail_count = 0 #크롤 실패한 횟수. 5번이 최대
            datalist = []
            for dy in range(1,6):
                target_year = current_year - dy
                #크롤링
                is_success = self.crawl_finstate(ticker,target_year,4)
                #크롤 한도 초과 예외처리
                if is_success == False:
                    return False
                #파싱
                raw_df = self.data_controller.get_raw_finstate_data(ticker,target_year,'Q4')
                #크롤 성공여부 평가
                if raw_df.empty:
                    fail_count += 1
                    continue
                extracted_data = self.extract_items(raw_df)
                datalist.append(extracted_data)
            
            avg_balance = [0 for _ in range(len(self.balance_name))]
            avg_income = [0 for _ in range(len(self.income_name))]
            for i in range(len(datalist)):
                bdata = datalist[i][0]
                idata = datalist[i][1]
                #시계열 평균 계산
                if i <= 2:
                    weight = 3 - i
                    for idx in range(len(avg_balance)):
                        if bdata[idx] != None:
                            avg_balance[idx] += weight * bdata[idx]
                    for idx in range(len(avg_income)):
                        if idata[idx] != None:
                            avg_income[idx] += weight * idata[idx]
                #dataframe으로 만들기
                bdataframe = pd.DataFrame([bdata],columns= self.balance_name); bdataframe["year"] = str(current_year - i - 1) + "Q4" 
                idataframe = pd.DataFrame([idata],columns= self.income_name); idataframe["year"] = str(current_year - i - 1) + "Q4"

                #bdataframe.set_index("year"); idataframe.set_index("year")
                #db에 저장
                self.data_controller.create_table_set_key(bdataframe,"extracted",f"{ticker}B","year")
                self.data_controller.create_table_set_key(idataframe,"extracted",f"{ticker}I","year")
                #self.data_controller.create_table(bdata,"extracted",f"{ticker}B")
           
            #시계열 평균 dataframe으로 만들고 db에 저장
            bmdataframe = pd.DataFrame([avg_balance],columns=self.balance_name); bmdataframe["year"] = str(current_year) + "M"
            imdataframe = pd.DataFrame([avg_income],columns=self.income_name); imdataframe["year"] = str(current_year) + "M"
            #bmdataframe.set_index("year"); imdataframe.set_index("year")
            
            self.data_controller.create_table_set_key(bmdataframe,"extracted",f"{ticker}B","year")
            self.data_controller.create_table_set_key(imdataframe,"extracted",f"{ticker}I","year")
        return True
        """
    def test(self):
        self.data_controller.remove_data_for_debug()
        ticker_list = ["005930","000660"]
        self.parse_5year_data(ticker_list,4)
        self.calculate_MA(ticker_list,2025)
        
        


#인터넷을 사용해서 긁어올 기업정보가 있을때 사용하는 클래스입니다.
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

def debug():
    reportCrawler =ReportCrawler()
    reportCrawler.test()
    #krx= KRXCrawler()
    #krx.crawl_stock_list()

    test_list = ["005930","000660","373220","207940"]

    #msg = reportCrawler.test()



if __name__ == "__main__":
    debug()

