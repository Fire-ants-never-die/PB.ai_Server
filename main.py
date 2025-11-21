from crawler.krx_crawler import KrxCrawler
from crawler.report_crawler import ReportCrawler
from controller.data_controller import DataController
from program_tool import *

# 본 파이썬 main.py 모듈은 피그마 프로토타입을 참고하여,
# 메인 홈 / 기업 오버 뷰/ 리포트_재무현황 분석 등의 페이지에 맞는 기능동작을 묶어서
# 클래스/함수로 정의 해놓은 모듈입니다.

#싱글톤 객체들 초기화 (크롤링 관련 객체 초기화 오래걸리므로 미리 선언하라고 묶어둠)
def create_objects():
    #전부 싱글톤 객체입니다.
    krx = KrxCrawler()
    data_controller = DataController()
    report_crawler = ReportCrawler()

#메인 홈
def main_home():
    #이거는...없을 듯??
    pass


#리포트 기업 오버뷰
class report_overview():
    # company_name은 ticker, 이름 둘 다 가능합니다.
    def __init__(self,company_name) -> None:
        self.krx = KrxCrawler()
        self.data_controller = DataController()
        try:
            self.market_data = self.krx.market_df.loc[self.krx.market_df['Name'] == company_name].iloc[0].to_dict()
        except:
            try:
                self.market_data = self.krx.market_df.loc[self.krx.market_df['Code'] == company_name].iloc[0].to_dict()
            except:
                Debuger.printc(f"{company_name} 을 찾을 수 없습니다.")
        
    #1 기업 프로필
    #[시가총액 상장일자x 설립일자 종업원수x 대표이사 발행주식수 주요계열사x] 딕셔너리로 반환
    def get_company_profile(self) -> dict:
        info_dict = {}
        info_dict["시가총액"] = self.market_data["Marcap"]
        info_dict["발행주식수"] = self.market_data["Marcap"]

        return info_dict



#리포트_재무현황 분석
def report_finance_analyze():
    pass


#리포트_투자지표
def report_investment_index():
    pass

#리포트_주식가치평가
def report_stock_valuation():
    pass








def main():
    pass


if __name__ == "__main__":
    main()