from program_tool import *
from data_controller import DataController
import OpenDartReader

@singleton
class ReportCrawler():

    def __init__(self,data_controller : DataController):

        #get api key
        self.data_controller = data_controller
        self.meta_data = data_controller.get_meta_data()
        self.api_key = self.meta_data["api_key"]

        #create Object : OpenDataReader

        #ignore 'module callable error'
        self.dart = OpenDartReader(self.api_key) # type: ignore



    #stock code might be a code (ex 005930), but also could be a stock name (ex 삼성전자)
    def crawl_finstate_all(self,stock_code : str, year : int):
        file_name = ""
        if stock_code.isdigit() == True:
            file_name = stock_code + self.dart.find_corp_code(stock_code)
        else:
            file_name = self.dart.find_corp_code(stock_code) + stock_code
        file_name += str(year)
        statement = self.dart.finstate_all(stock_code, year)
        statement.to_excel(excel_writer = f'data/statement/{file_name}.xlsx')


def debug():
    dataController = DataController()
    reportCrawler = ReportCrawler(dataController)
    reportCrawler.crawl_finstate_all("005930",2024)
    
if __name__ == "__main__":
    debug()


