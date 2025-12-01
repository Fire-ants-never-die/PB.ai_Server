import pandas as pd
import OpenDartReader
from tqdm import tqdm
from krx_crawler import KrxCrawler
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from program_tool import *
from controller.data_controller import DataController

#싱글톤
@singleton
class ReportCrawler():
    #초기화:api key, data_controller 객체, 추출항목, dart(재무제표크롤링) 객체, krx(국내시장크롤링)객체
    #      datetime (날짜관리) 객체, timer (api과호출 방지) 객체
    #   위 내용을 초기화 합니다. 추후에 embedding api, gpt api 등의 모듈이 다른 파일에서 작성되면, 여기서 객체로
    #   초기화 될 수 있습니다. vscode vim 한글 에러 거지같네 개발자 누구야 이거
    def __init__(self):
        #api key등이 담긴 data/meta.json
        self.data_controller = DataController()
        meta_data = self.data_controller.get_meta_data()

        #api key 호출
        self.api_key = meta_data["api_key"]

        #크롤링한 재무제표/연결제무제표 +@ 에서 추출할 항목들
        self.balance_name = meta_data["balance_name"] #이름으로 추출
        self.income_name = meta_data["income_name"]
        self.balance_id = meta_data["balance_id"] #개정과목체계에 따른 id로 추출
        self.income_id = meta_data["income_id"]

        #OpenDartReader class
        self.dart = OpenDartReader(self.api_key) # type: ignore

        #KRX Cralwer class
        self.krx = KrxCrawler()

        #날짜/연도 관리
        self.datetime = DateTimeManager()

        #분기별 보고서 reprt_code
        self.reprt_code = [0,'11013','11012','11014', '11011']

        #dart api 호출량 통제 (1000회/분, 20000회/일)를 위한 변수
        #보수적으로 1초에 15번 이상 호출 안되게끔 해야 함함
        self.dart_api_call_volume = 0
        self.timer = Timer()

    ##====일괄 다운로드 재무제표 파싱 ====
    def parse_all_downloads_items(self):
        pass       

    #private입니다. 
    #재무제표를 크롤링하는 함수입니다. 결과는 raw.db에 저장됩니다. 성공하면 True 반환
    #ticker는 string 형식으로, year은 int, 분기는 int 형으로 입력되어야 합니다.
    #ex) crawl_finstate("005930",2024,2)  : 삼성전자 2024년도 2분기 재무제표
    def __crawl_finstate(self,tickermeta):
        #과호출 방지
        if self.dart_api_call_volume >= 19999 :
            Debuger.printc("api 과호출")
            return False
        elif self.timer.crawl_timer(self.dart_api_call_volume) == False:
            Debuger.printc("api 과호출")
            return False
        #크롤링
        year = int(tickermeta[0:4])
        ticker = tickermeta[4:10]
        quarter = int(tickermeta[-1])
        try:
            self.dart_api_call_volume += 1
            fdata = self.dart.finstate_all(ticker,year)
        except:
            Debuger.printc(f"dart 크롤링 실패: {tickermeta}")
            return False
        #비어있으면 크롤실패로 간주
        if fdata.empty:
            Debuger.printc(f"크롤된 데이터 비어있음 : {ticker} / {year}")
            return False
        #데이터 저장
        table_name = tickermeta
        try:
            self.data_controller.create_table(fdata,"raw",table_name,False)
        except:
            Debuger.printc("데이터 저장과정에서 에러")
            return False
        
        return True
    
    #티커리스트의 모든 회사들의 재무제표를 크롤링한 후, 저장사항을 meta/crawled_set.pkl에 기록합니다.
    #크롤 안된 티커meta 반환합니다.
    def crawl_finstate_by_tickermetalist(self,tickermetalist)->list:
        sucess_list = []
        fail_list = []
        to_crawl_list = self.check_crawled(tickermetalist)
        for tickermeta in progress(to_crawl_list,"kospi 재무제표 사업보고서 크롤링"):
            is_sucess = self.__crawl_finstate(tickermeta)
            if is_sucess:
                sucess_list.append(tickermeta)
            else:
                fail_list.append(tickermeta)
        #저장사항 기록
        self.data_controller.set_crawled_set(sucess_list)
        return fail_list

    #중복 크롤링을 방지하기 위해 특정 회사들을 크롤링했는지 체크하는 메서드입니다. 
    #일반적인 상황에서는 쓰이지 않을 것으로 예상하지만 혹시나 해서 만들어두었습니다. 
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
   
    #크롤링한 재무제표로부터 meta.json의 회계항목들 파싱하는 메서드입니다. parse_5_year_data()메서드에서 호출됩니다.
    #파싱된 항목들은 재무상태표와 손익계산서로 분리되어, 2차원 리스트 [재무상태표리스트,손익계산서리스트]로 반환됩니다.
    def parse_items(self,df:pd.DataFrame) -> list:
        #재무상태표
        balance_data = []
        #손익계산서
        income_data = []
        #재무상태표 파싱
        for i in range(len(self.balance_name)):
            name = self.balance_name[i]
            id = self.balance_id[i]
            #당기 파싱 (thstrm_amount) (이름으로 => account_nm)
            amount_balance = df.loc[(df['sj_div']=="BS")&(df['account_nm'].str.contains(name,case=False,na=False)),'thstrm_amount'].to_list() # type: ignore
            amount_balance_id = df.loc[(df['sj_div']=="BS")&(df['account_id']==id),'thstrm_amount'].to_list() # type: ignore
            data = None
            #dataframe null 확인
            if len(amount_balance) >= 1:
                data = int(amount_balance[0])
            #id로 존재하면 id 쓰기
            else:
                if len(amount_balance_id) >= 1:
                    data = int(amount_balance_id[0])
            balance_data.append(data) # type: ignore

        #손익계산서 (포괄,일반)
        for i in range(len(self.income_name)):
            name = self.income_name[i]
            id = self.income_id[i]
            amount_income = df.loc[(df['sj_div']=="CIS")&(df['account_nm'].str.contains(name,case=False,na=False)),'thstrm_amount'].to_list() # type: ignore
            amount_income_id = df.loc[(df['sj_div']=="CIS")&(df['account_id']==id),'thstrm_amount'].to_list() # type: ignore
            amount_income_IS = df.loc[(df['sj_div']=="IS")&(df['account_nm'].str.contains(name,case=False,na=False)),'thstrm_amount'].to_list() # type: ignore
            amount_income_IS_id = df.loc[(df['sj_div']=="IS")&(df['account_id']==id),'thstrm_amount'].to_list() # type: ignore
            data = None
            for amount_list in [amount_income,amount_income_id,amount_income_IS,amount_income_IS_id]:
                if len(amount_list) >= 1:
                    data = int(amount_list[0])
                    break
            income_data.append(data) 
        #=====후처리======
        #당좌자산 = 유동자산 - 재고자산
        data1 = balance_data[0]
        data2 = balance_data[3]
        if (data1 != None) & (data2 != None):
            balance_data[20] = data1 - data2
        #차입금(이자지급부채) = 단기차입금+유동성장기부채+사채+장기차입금+금융리스부채
        def check_None(idx):
            balance_data[idx] = balance_data[idx] if balance_data[idx] != None else 0
        check_list = [10,11,13,14,15]
        for i in check_list:
            check_None(i)
        balance_data[21] = 0
        for i in check_list:
            balance_data[21] += balance_data[i]
        # 매출원가 = 매출액 - 매출총이익
        data1 = income_data[0]; data2 = income_data[1]
        if (data1 != None) & (data2 != None):
            income_data[9] = data1 - data2
        # 판매비와관리비 = 매출총이익 - 영업이익
        data1 = income_data[1]; data2 = income_data[2]
        if (data1 != None) & (data2 != None):
            income_data[10] = data1 - data2
        #======후처리 끝 =====
        res = [balance_data,income_data]
        return res
    
    #5개년도 재무데이터를 파싱하는 메서드입니다. 가급적 크롤링이 선행되면 좋지만, 안되어있을 경우 크롤링도 합니다.
    #파싱 성공한 티커리스트 반환
    def parse_5year_data(self,tickerlist:list,quarter:int) -> list:
        current_year = self.datetime.year
        if quarter == 4:
            current_year -= 1
        month = int(self.datetime.formatted_month)
        #성공적으로 파싱한 항목은 meta/parsed_set.pkl 에 저장
        parsed_list = []
        #3월달까지는 사업보고서(Q4)가 발행이 안되어 있을 가능성이 있습니다.
        if month <= 3:
            current_year -= 1
        
        #티커메타 구성후 크롤 시작 (티커메타 = {year}{ticker}Q{quarter})
        tickermetalist = []
        for ticker in tickerlist:
            for dy in range(0,5):
                year = current_year - dy
                tickermetalist.append(str(year)+ticker+f"Q{quarter}")

        fail_list = self.crawl_finstate_by_tickermetalist(tickermetalist)       

        #티커리스트가 비어있다면 pickle로 저장되어있는 크롤된 재무제표 메타데이터 가져오기
        if len(tickerlist) == 0:
            crawled = self.data_controller.get_crawled_set()
            tickermetalist = list(crawled)
        #파싱 코드 (추후 멀티 프로세스로 변경)
        parse_fail = 0
        sucess_ticker = []
        for tickermeta in progress(tickermetalist,"파싱 중"):
            if tickermeta in fail_list:
                continue
            try:
                year = tickermeta[0:4]; quarter = tickermeta[-1]; tickername = tickermeta[4:10]
                df = self.data_controller.read_table("raw",tickermeta)
                datalist = self.parse_items(df)
                #bdata == balance (재무상태표) / idata == income (손익계산서)
                bdata = datalist[0]; idata = datalist[1]
                bdataframe = pd.DataFrame([bdata],columns= self.balance_name); bdataframe["year"] = year + "Q" + f"{quarter}" 
                idataframe = pd.DataFrame([idata],columns= self.income_name); idataframe["year"] = year + "Q" + f"{quarter}"
                #db 저장 코드
                self.data_controller.create_table_set_key(bdataframe,"extracted",f"{tickername}B","year")
                self.data_controller.create_table_set_key(idataframe,"extracted",f"{tickername}I","year")

                parsed_list.append(tickermeta)
                sucess_ticker.append(tickermeta[4:10])
            except:
                parse_fail += 1
                Debuger.printc(f"파싱실패 : f{parse_fail}")
                pass
        self.data_controller.set_parsed_set(parsed_list)
        return sucess_ticker
        
    #DB에 저장된 파싱항목을 토대로 3년 시계열평균 (이동평균) 값을 구합니다. CY-1, CY-2, CY-3
    # 반환값은 실패한 티커리스트.
    def calculate_MA(self,current_year)->list:
        #실패리스트
        fail_ticker_list = []

        #파싱된 집합에서 계산. 만약 CY-1, CY-2, CY-3 3개년치에서 하나도도라도 존재하지 않으면 continue
        pset = self.data_controller.get_parsed_set()
        parsed_tickermeta_list = sorted(list(pset),reverse= True) #내림차순으로 정리하여 연도를 하나씩 내릴겁니다
        to_list = []
        prev_ticker = ""
        exist_year = 0
        for tickermeta in progress(parsed_tickermeta_list,"시계열평균을 구할 종목을 구성중입니다"):
            ticker = tickermeta[4:10]
            year = int(tickermeta[0:4])
            if ticker != prev_ticker:
                if exist_year >= 3:
                    to_list.append(prev_ticker)
                    exist_year = 0
                if year == current_year - 1:
                    exist_year = 1
                    prev_ticker = ticker
            else:
                exist_year += 1
        if exist_year >= 3:
            to_list.append(prev_ticker)

        #파싱안된 항목 제외하고 계산해서 저장
        for ticker in progress(to_list,"시계열평균 계산중입니다"):
            
            #파싱 데이터 가져오기

            bdataframe = self.data_controller.read_table("extracted",ticker+"B")
            idataframe = self.data_controller.read_table("extracted",ticker+"I")

            row_name = f"{current_year}M"
            if bdataframe["year"].isin([row_name]).any() == True:
                continue

            sum_bdict = {"year":row_name}; sum_idict = {"year":row_name}
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
    
    # 5개년 시장의 보고서를 크롤만 합니다. market은 "ALL", "KOSPI", "KOSDAQ", "KONEX" 입니다.
    # parse_5_year_data 가 호출되기 전에 이 메서드로 한 번에 미리 크롤링하는 것이 좋습니다.
    def crawl_market_5_year_report(self,market :str = "ALL",quarter :int = 4):
        today = self.datetime.formatted_today
        year = int(self.datetime.formatted_year) - 1
        tickerlist = self.krx.get_market_list(today,market)
        
        if int(self.datetime.formatted_month) <= 3:
            year -= 1
        tickermetalist = []
        for ticker in tickerlist:
            for dy in range(5):
                tickermeta = f"{year - dy}{ticker}Q{quarter}"
                tickermetalist.append(tickermeta)
        self.crawl_finstate_by_tickermetalist(tickermetalist)

    #디버깅용 시험 메서드
    def test(self):
        #self.data_controller.remove_data_for_debug()

        #ceo_nm, est_dt(설립일자), 
        #self.crawl_market_5_year_report("KOSPI")

        #-------------------
        # test_ticker_list = ["005930", "000660", "373220", "207940"]
        # crawled_set = self.data_controller.get_crawled_set()

        # sucess_ticker_list = self.parse_5year_data([],4)
        self.calculate_MA(2025)
        #df = self.dart.finstate_all("삼성전자",2023)
        # df2 = self.dart.finstate('삼성전자', 2021, reprt_code='11013')
        # df3 = self.dart.finstate('005930, 000660, 005380', 2021)
        #self.data_controller.to_excel_test(df,"samsung2023")
        


            
        # self.crawl_market_report("KOSPI",4)
        
        


#인터넷을 사용해서 긁어올 기업정보가 있을때 사용하는 클래스입니다. deprecated
def debug():
    reportCrawler =ReportCrawler()
    reportCrawler.test()
    #krx= KRXCrawler()
    #krx.crawl_stock_list()

    test_list = ["005930","000660","373220","207940"]

    #msg = reportCrawler.test()



if __name__ == "__main__":
    debug()

