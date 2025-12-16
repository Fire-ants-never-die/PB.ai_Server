import zipfile
import io,xml.etree.ElementTree as ET
import pandas as pd
import requests, sys, os
from crawler.krx_crawler import KrxCrawler
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from controller.data_controller import DataController
from program_tool import *


class DartCrawler:
    def __init__(self):
        self.data_controller = DataController()
        self.api_key = self.data_controller.get_env("DART_API_KEY")
        # self.api_key = self.data_controller.get_meta_data()["api_key"]


#종목코드과, 기업고유번호, 기업 이름을 크롤링해옵니다. 자주는 아니더라도 가끔씩 아래메서드를 호출하여 업데이트하는 것이 좋겠습니다.
class CodeCrawler(DartCrawler):

    def __init__(self):
        super().__init__()
        self.url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={self.api_key}"

    def crawl_save_code(self):
        response = requests.get(self.url)

        if response.status_code != 200:
            Debuger.printc("Dart api url get 실패")

        # ZIP 파일 메모리 로드 및 압축 해제
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            file_list = z.namelist()
            xml_filename = file_list[0]               
            xml_data = z.read(xml_filename)            

        # XML 파싱
        root = ET.fromstring(xml_data)

        # corp (기업 리스트) 파싱
        records = []
        for corp in root.findall('list'):
            stock_code = corp.findtext('stock_code')   # 종목코드 (없으면 None이 아님 시팔! "   "임. 도나 진짜)
            if stock_code == "" or stock_code == None:
                continue
            if " " in stock_code:
                continue
            corp_name = corp.findtext('corp_name')     # 회사명
            corp_code = corp.findtext('corp_code')     # 고유번호
            records.append([stock_code, corp_code, corp_name])

        df = pd.DataFrame(records, columns=['stock_code', 'corp_code', 'corp_name'])

        self.data_controller.create_table_set_key(df,"market","CodeTable","stock_code",True)
@singleton
class FinstateCralwer(DartCrawler):
    def __init__(self):
        super().__init__()
        self.url = 	"https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
        self.params = {
            "crtfc_key": self.api_key,
            "corp_code": "",
            "bsns_year": "",
            "reprt_code": "",
            "fs_div" : ""
        }
        self.code_df = self.data_controller.read_table("market","CodeTable")
        self.quarter_list = [0,'11013','11012','11014', '11011']

    def crawl_finstate(self,ticker:str,year:str,quarter:int,fs_div:str = "CFS")->pd.DataFrame:
        corp_code = self.code_df.loc[self.code_df['stock_code'] == ticker,'corp_code'].iloc[0]
        self.params["corp_code"] = corp_code
        self.params["bsns_year"] = year
        self.params["reprt_code"] = self.quarter_list[quarter]
        if fs_div != "CFS":
            fs_div = "OFS"
        self.params["fs_div"] = fs_div

        try:
            res = requests.get(self.url,params=self.params)
            res = res.json()
            return pd.DataFrame(res["list"])
        except Exception as e:
            Debuger.printc(f"크롤 실패 : {e}")
            return pd.DataFrame()
    
        

class CompanyCrawler(DartCrawler):
    def __init__(self):
        super().__init__()
        self.url_company = "https://opendart.fss.or.kr/api/company.json"
        self.url_employ = "	https://opendart.fss.or.kr/api/empSttus.json"
        self.krx = KrxCrawler()
        self.params_company ={
                    "crtfc_key": self.api_key,
                    "corp_code": ""
                }
       
        reprt_code = ["11013","11012","11014","11011"]
        date = DateTimeManager()
        year = int(date.formatted_year)
        month = int(date.formatted_month)
        if month >= 6 and month <= 8 :
            idx = 0
        elif month >= 9 and month <= 11 :
            idx = 1
        elif month >= 12 or month <= 3:
            idx = 2
            if month <= 3:
                year -= 1
        else:
            idx = 3
            year -= 1

        self.params_employ ={
                    "crtfc_key": self.api_key,
                    "corp_code": "",
                    "bsns_year": str(year),
                    "reprt_code": reprt_code[idx]
                    }
        self.code_df = self.data_controller.read_table("market","CodeTable")
        
    def _crawl_company(self,ticker):
        try:
            corp_code = self.code_df.loc[self.code_df['stock_code'] == ticker,'corp_code'].iloc[0]
        except:
            Debuger.printc(f"{ticker} 파싱데이터가 없습니다.")
            return
        self.params_company["corp_code"] = corp_code
        self.params_employ["corp_code"] = corp_code

        #개황정보 크롤링
        r1 = requests.get(self.url_company,params=self.params_company)
        rc = r1.json()
        #직원 정보 크롤링
        r2 = requests.get(self.url_employ,params=self.params_employ)
        ec = r2.json()

        if r1.status_code != 200 or r2.status_code != 200:
            Debuger.printc("Dart api url get 실패")
            return

        #개황정보 파싱
        company_dict = {}
        company_key_dict = {
            "stock_code" : "티커", #티커
            "corp_code" : "고유번호", #고유번호
            "corp_name" : "기업이름", #기업 이름
            "corp_name_eng" : "기업영문", #기업 영문 이름
            "stock_name" : "주식이름", #주식 이름 (상장된 이름)
            "ceo_nm" : "CEO",    #ceo 이름
            "corp_cls": "상장구분",   #법인 구분 (코스피,코스닥,코넥스,기타)
            "adres" : "주소",   #주소  (key값이 adres 임에 주의)
            "hm_url" : "홈페이지",  #회사 홈페이지
            "induty_code" : "업종코드",  #업종 코드
            "est_dt" : "설립일", #설립일 
            "acc_mt": "결산월"   #결산월 ex) 12
        }
        market_name_dict = {"Y":"KOSPI","K":"KOSDAQ","N":"KONEX","E": "기타","NULL":"NULL"}
        for k ,v in company_key_dict.items():
            key_name = v
            try:
                value = rc[k]
                if key_name == "상장구분":
                    value = market_name_dict[value]
            except:
                value = "NULL"
            company_dict[key_name] = value
        
        #직원 수 파싱
        # filtered = df[df["fo_bbm"] != "합계" or df["fo_bbm"] != "성별합계" or df["fo_bbm"] != "성별 합계"]
        # member_num = filtered["rgllbr_co"].sum()

        try:
            df = pd.DataFrame(ec["list"])
            member_num = 0
            ms_list = df.loc[~df["fo_bbm"].isin(["합계","성별합계","성별 합계"]),"rgllbr_co"].tolist() # type: ignore
            for ms in ms_list:
                ms = ms.replace(",","")
                if ms.isdigit():
                    member_num += int(ms)
        except:
            member_num = "NULL"

        company_dict["종업원수"] = member_num

        #시가총액 / 발행주식 수
        try:
            cap = self.krx.get_market_cap(ticker)
            company_dict["시가총액"] = cap[0]
            company_dict["발행주식수"] = cap[1]
        except:
            company_dict["시가총액"] = "NULL"
            company_dict["발행주식수"] = "NULL"
        return company_dict
    
    #개황정보/기타정보 시장단위 크롤링 후 db에 저장 ("ALL KOSPI KOSDAQ KONEX")
    def crawl_save_company(self,market_name:str = "ALL"):
        ticker_list = self.krx.get_market_list(market=market_name)
        print(len(ticker_list))
        for ticker in progress(ticker_list,"개황정보/기타정보 크롤링"):
            c_dict = self._crawl_company(ticker)
            if c_dict == None:
                Debuger.printc("조회되지 않음")
            else:
                self.data_controller.create_table_set_key_from_dict(c_dict,"market","company","티커",True)
        

def _test():
    # cc = CompanyCrawler()
    # cc.crawl_save_company("KOSPI")

    fc = FinstateCralwer()
    res = fc.crawl_finstate("005930","2025",2)
    res = pd.DataFrame(res)
    DataController().save_df_excel(res,"samsung2025Q2")
    
_test()


       