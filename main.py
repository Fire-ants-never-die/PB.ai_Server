from crawler.krx_crawler import KrxCrawler
from crawler.report_crawler import ReportCrawler
from controller.data_controller import DataController
from program_tool import *

# 본 파이썬 main.py 모듈은 피그마 프로토타입을 참고하여,
# 메인 홈 / 기업 오버 뷰/ 리포트_재무현황 분석 등의 페이지에 맞는 기능동작을 묶어서
# 클래스/함수로 정의 해놓은 모듈입니다.
# 반환값은 json으로 쉽게 변경하기 위하여 가급적 dictionay 형으로 반환합니다. (값 하나만 출력하는거면 int,str)
# 미완성 메서드는 주석에 ***를 붙입니다. 

#report에 들어갈 데이터 객체 한 번에 생성. 리포트 안의 5가지 탭을 오갈 때, 중복 처리 하지 않기 위해서 딱 한번만 불러옵니다.
#프/백 개발자는 이 클래스만 쓰면 됩니다!! + AI 클래스 하나 더.
class report():
    def __init__(self,company_name) -> None:
        #전부 싱글톤 객체입니다.
        self.krx = KrxCrawler()
        self.data_controller = DataController()
        self.report_crawler = ReportCrawler()
        #회사의 기본 시장상황 정보를 krx로부터 불러옵니다. 'Code','Name','Market','Dept','Open','High','Low','Close','Volume','Marcap','Stocks'
        try:
            self.company_market_data = self.krx.market_df.loc[self.krx.market_df['Name'] == company_name].iloc[0].to_dict()
            self.ticker = self.company_market_data['Code']
            self.name = self.company_market_data['Name']
        except:
            try:
                self.company_market_data = self.krx.market_df.loc[self.krx.market_df['Code'] == company_name].iloc[0].to_dict()
                self.name = self.company_market_data['Name']
                self.ticker = self.company_market_data['Code']
            except:
                Debuger.printc(f"{company_name} 을 찾을 수 없습니다.")
        #기타
        self.current_year = DateTimeManager().formatted_year

        #4가지 탭 클래스 인스턴스 선언. 기업 overview, 재무현황 분석, 투자지표, 주식가치평가. (채팅은 ai이므로 일단 따로 빼두겠습니다.)
        
        self.report_ov = ReportOverview(self.name,self.ticker,self.company_market_data)
        self.report_fa = ReportFinancialAnalyze()
        self.report_ii = ReportInvestmentIndex()
        self.report_sv = ReportStockValuation()
    
    

#리포트 기업 오버뷰 (krx 크롤링이 포함됩니다.)
class ReportOverview(report):
    # company_name은 ticker, 이름 둘 다 가능합니다.
    def __init__(self,name,ticker,market_data):
        self.name = name
        self.ticker = ticker
        self.company_market_data = market_data
    #1 기업 프로필 ***
    #[시가총액 상장일자x 설립일자 종업원수x 대표이사 발행주식수 주요계열사x] 딕셔너리로 반환
    # 현재 위 리스트의 x 항목을 크롤 할 방법을 찾아야 함.
    def get_company_profile(self) -> dict:
        info_dict = {}
        info_dict["시가총액"] = format_number(self.company_market_data['Marcap'],style=True)
        info_dict["발행주식수"] = f"{self.company_market_data['Marcap']}주"

        return info_dict

    #2 매출 산업구성 ***
    #매출 산업이 어떻게 구성되는지, 최대 N가지의 구성종목을 key(구성종목) : value 형태로 반환합니다.
    def get_company_industrial_part(self) -> dict:
        info_dict = {}
        return info_dict
    
    #3 재무현황
    # 최대 5개년의 재무현황 데이터를 표시합니다. (일단 사업보고서만)
    # {key(년도): value({ key(매출액):값, key(자산총계): 값...}, key(년도): {매출액:값, 자산총계 :값...} ...}
    def get_company_financial_status(self) -> dict:
        info_dict = {}
        table_balance = f"{self.ticker}B"
        table_income = f"{self.ticker}I"
        item_list = ["매출액","자산총계","부채총계","자본총계","당기순이익"]
        try:
            df_b = self.data_controller.read_table("extracted",table_balance)
            df_i = self.data_controller.read_table("extracted",table_income)
        except:
            Debuger.printc(f"{self.name}({self.ticker})가 DB에 저장되어있지 않습니다.")
            return info_dict
        for i in range(5):
            year_dict = {}
            target_year = int(self.current_year) - i
            b_dict = df_b[df_b['year'] == target_year].to_dict('records')
            i_dict = df_i[df_i['year'] == target_year].to_dict('records')
            for key in item_list:
                if key in b_dict:
                    year_dict[key] = format_number(int(b_dict[key])) # type: ignore
                elif key in i_dict:
                    year_dict[key] = format_number(int(i_dict[key]))  # type: ignore
                else:
                    year_dict[key] = "NULL"
            info_dict[f"{target_year}"] = year_dict
        return info_dict

    #4 재무건전성***
    def get_company_financial_soundness(self) -> int:
        res = 0
        return res

    #5 산업 설명
    #산업명/평가기준일/산업평가 종합등급 /여신정책
    def get_industrial_explanation(self) -> dict:
        info_dict = {}

        return info_dict


#리포트_재무현황 분석
class ReportFinancialAnalyze():

    pass

#리포트_투자지표
class ReportInvestmentIndex():
    pass

#리포트_주식가치평가
class ReportStockValuation():
    pass









def main():
    pass


if __name__ == "__main__":
    main()