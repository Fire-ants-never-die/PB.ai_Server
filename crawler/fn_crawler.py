import requests
from bs4 import BeautifulSoup
import pandas as pd


class CrawlFromFnGuide():

    def __init__(self,ticker):
        url = f"https://cdn.fnguide.com/SVO2/ASP/SVD_Corp.asp?pGB=1&gicode=A{ticker}&cID=&MenuYn=Y&ReportGB=&NewMenuID=102&stkGb=701"
        try:
            response = requests.get(url)
        except:
            return False
        self.soup = BeautifulSoup(response.text, 'html.parser')
    
    def format(self,txt):
        return txt.replace("\xa0"," ")

    def get_general_items(self) -> dict:
        res = {}
        key_name = ["회사주소","회사링크","영문명",".",".","대표이사","계열명","설립일","상장일",".",".",".",".",".",".","종업원수",".","배당락일"]
        item = []
        tbody = self.soup.find('tbody')
        if tbody:
            rows = tbody.find_all('tr') # type: ignore

            for row in rows:
                cells = row.find_all('td') # type: ignore
                for cell in cells:
                    data = cell.text.replace("\xa0"," ")
                    item.append(data)
        else:
            return {}
        for i in range(len(key_name)):
            if key_name[i] != ".":
                res[key_name[i]] = item[i] 
        return res
    
    def get_part(self) -> dict:
        res = {}
        # table = self.soup.find("table",class_="us_table_ty1 table-hb2 h_fix zigbg_no")
        table = self.soup.select_one("#divProduct > div.ul_col2_l > div > div.um_table.pd_t1 > table")
        df = pd.read_html(str(table))[0]
        latest_column_name = df.columns[-1]
        for idx, row in df.iterrows():
            if idx == (len(df) - 1):
                continue
            else:
                res[self.format(row["제품명"])] = row[self.format(latest_column_name)]
        return res
    
    def get_related_company(self) -> list:
        res = []
        table = self.soup.select_one("#divConnectionComp > div.um_table > table")
        df = pd.read_html(str(table))[0]
        for idx, row in df.head(5).iterrows():
            res.append(self.format(row["연결대상회사"])) # type: ignore
        return res
    
    
def __test():
    fn = CrawlFromFnGuide("005930")
    # print(fn.get_general_items())
    # print(fn.get_part())
    print(fn.get_related_company())

if __name__ == "__main__":
    __test()
