import zipfile
import io,xml.etree.ElementTree as ET
import pandas as pd
import requests, sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from controller.data_controller import DataController



#종목코드과, 기업고유번호, 기업 이름을 크롤링해옵니다. 자주는 아니더라도 가끔씩 아래메서드를 호출하여 업데이트하는 것이 좋겠습니다.

class CodeCrawler:

    def __init__(self):
        self.data_controller = DataController()
        api_key = self.data_controller.get_meta_data()["api_key"]
        self.url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={api_key}"
    
    def crawl_save_code(self):
        response = requests.get(self.url)

        if response.status_code != 200:
            raise Exception("DART API 요청 실패")

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