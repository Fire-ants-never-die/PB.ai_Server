from crawler.krx_crawler import KrxCrawler
from crawler.report_crawler import ReportCrawler
from controller.data_controller import DataController
from program_tool import *
from ai.ai_chatting_queue_controller import AIChattingQueueController, ChattingQueueData

# 본 파이썬 main.py 모듈은 피그마 프로토타입을 참고하여,
# 메인 홈 / 기업 오버 뷰/ 리포트_재무현황 분석 등의 페이지에 맞는 기능동작을 묶어서
# 클래스/함수로 정의 해놓은 모듈입니다.
# 반환값은 json으로 쉽게 변경하기 위하여 가급적 dictionay 형으로 반환합니다. (값 하나만 출력하는거면 int,str)
# 미완성 메서드는 주석에 ***를 붙입니다. 

#메인 홈 입니다.
#주식회사 검색시스템인데..회사 로고는 크롤링이 안되어 있으므로, 로고는 제외하고 {key회사명 : value티커} 형태의 dict로 반환합니다. 
class Home():
    def __init__(self) -> None:
        self.data_controller = DataController()
        self.krx = KrxCrawler()

        #krx에서 불러온 오늘 주가데이터로 이름/티커 반환 메서드 작성해야 함!!
        

#report에 들어갈 데이터 객체 한 번에 생성. 리포트 안의 5가지 탭을 오갈 때, 중복 처리 하지 않기 위해서 딱 한번만 불러옵니다.
#프/백 개발자는 이 클래스만 쓰면 됩니다!! + AI 클래스 하나 더.
class Report():
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
        #아래 4가지 탭 클래스...싱글톤으로 해야하나...

        self.report_ov = ReportOverview(self.name,self.ticker,self.company_market_data)
        self.report_fa = ReportFinancialAnalyze(self.name,self.ticker,self.current_year)
        self.report_ii = ReportInvestmentIndex()
        self.report_sv = ReportStockValuation()
    
    

#리포트 기업 오버뷰 (krx 크롤링이 포함됩니다.)
class ReportOverview():
    # company_name은 ticker, 이름 둘 다 가능합니다.
    def __init__(self,name,ticker,market_data):
        self.name = name
        self.ticker = ticker
        self.company_market_data = market_data
        self.data_controller = DataController()
        self.current_year = DateTimeManager().formatted_year

        # ai 넘겨줄 정보 저장
        self.data_for_ai = {}
        self.is_called = [False,False,False,False,False] #아래에 있는 함수들이 호출되면서 data_for_ai가 채워졌는지 확인하는 bool리스트입니다.
    #1 기업 프로필 ***
    #{시가총액 상장일자x 설립일자 종업원수x 대표이사 발행주식수 주요계열사x} 딕셔너리로 반환
    # 현재 위 리스트의 x 항목을 크롤 할 방법을 찾아야 함.
    def get_company_profile(self) -> dict:
        info_dict = {}
        info_dict["시가총액"] = format_number(self.company_market_data['Marcap'],style=True)
        info_dict["발행주식수"] = f"{self.company_market_data['Marcap']}주"

        if self.is_called[0] == False:
            self.is_called[0] = True
            self.data_for_ai["기업 프로필"] = info_dict

        return info_dict

    #2 매출 산업구성 ***
    #매출 산업이 어떻게 구성되는지, 최대 N가지의 구성종목을 key(구성종목) : value 형태로 반환합니다.
    def get_company_industrial_part(self) -> dict:
        info_dict = {}


        if self.is_called[1] == False:
            self.is_called[1] = True
            self.data_for_ai["매출 산업 구성"] = info_dict

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
            b_dict = df_b[df_b['year'] == target_year].to_dict('records') # type: ignore
            i_dict = df_i[df_i['year'] == target_year].to_dict('records') # type: ignore
            for key in item_list:
                if key in b_dict:
                    year_dict[key] = format_number(int(b_dict[key])) # type: ignore
                elif key in i_dict:
                    year_dict[key] = format_number(int(i_dict[key]))  # type: ignore
                else:
                    year_dict[key] = "NULL"
            info_dict[f"{target_year}"] = year_dict

        if self.is_called[2] == False:
            self.is_called[2] = True
            self.data_for_ai["재무현황"] = info_dict

        return info_dict

    #4 재무건전성***
    def get_company_financial_soundness(self) -> int:
        res = 0

        if self.is_called[3] == False:
            self.is_called[3] = True
            self.data_for_ai["재무건전성"] = int
        return res

    #5 산업 설명
    #산업명/평가기준일/산업평가 종합등급 /여신정책
    def get_industrial_explanation(self) -> dict:
        info_dict = {}
        
        if self.is_called[4] == False:
            self.is_called[4] = True
            self.data_for_ai["산업 설명"] = info_dict
        return info_dict


#리포트_재무현황 분석
class ReportFinancialAnalyze():
    def __init__(self,name,ticker,current_year) -> None:
        self.name = name
        self.ticker = ticker
        self.current_year = current_year
        self.data_controller = DataController()

        # ai 넘겨줄 정보 저장
        self.data_for_ai = {}
        self.is_called = [False,False,False,False,False]

    #1 재무 상황. 리포트오버뷰 페이지와 동일한 데이터지만, 실제로 그래프를 그려야 하므로
    #  한글로 포매팅된 str 형식이 아닌, int형 데이터를 반환해야 합니다. 그래프 아래에 보여질
    # 표를 위해 한글로 포매팅된 str값도 반환해야 합니다.
    # {"real": 실제 숫자 형식 (최대)5개년 데이터, "format" : 표에 들어갈 한글형식 (1조3000억)데이터}
    def get_company_status(self) -> dict:
        info_dict = {}
        real_number_dict = {}
        format_number_dict = {}
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
            year_format_dict = {}
            year_real_dict = {}
            target_year = int(self.current_year) - i
            b_dict = df_b[df_b['year'] == target_year].to_dict('records') # type: ignore
            i_dict = df_i[df_i['year'] == target_year].to_dict('records') # type: ignore
            for key in item_list:
                if key in b_dict:
                    year_format_dict[key] = format_number(int(b_dict[key])) # type: ignore
                    year_real_dict[key] = format_number(int(b_dict[key])) # type: ignore
                elif key in i_dict:
                    year_format_dict[key] = format_number(int(i_dict[key]))  # type: ignore
                    year_real_dict[key] = format_number(int(i_dict[key]))  # type: ignore
                else:
                    year_format_dict[key] = "NULL"
                    year_real_dict[key] = "NULL"
            format_number_dict[f"{target_year}"] = year_format_dict
            real_number_dict[f"{target_year}"] = year_real_dict
        
        info_dict["real":real_number_dict, "format":format_number_dict]

        return info_dict

    #2 재무 비율 판정.
    def get_evaluation_financial_ratio(self):
        pass

    #3 안정성 분석
    #3.1 유동성 분석   유동비율 : {"2023": data, "시계열평균": data, "업종중위수" : data, "시계열점수" : data, "업종점수" : data}
    #                당좌비율...
    #                현금비율, 순운전자본대총자본, 비유동비율, 비유동장기적합율 등등이 key로 존재합니다.
    def get_analyze_stability_liquidity(self):
        pass

    #3.2 레버리지 분석
    # 열 값은 3.1과 같으며, {부채비율, 자기자본비율, 유동부채비율, 비유동부채비율,차입금의존도, 차입금대매출액} 이 있습니다.
    def get_analyze_stability_leverage(self):
        pass
    
    #4 수익성 분석
    #4.1 투자수익성 분석
    #열 값은 3.1과 같으며, {총자산세전수익률, 총자산순이익률,기업세전순이익률,기업순이익률,자기자본세전순이익률,자본금세전순이익률,자본금순이익률,자기자본순이익률}
    def get_analyze_profitability_investment(self):
        pass
    #4.2 판매 마진 분석
    #열 값은 3.1과 같으며, {매출액세전순이익률,매출액순이익률,매출액영업이익률,EBIT대매출액,EBITDA대매출액}
    def get_analyze_profitability_margin(self):
        pass
    
    #5 성장성 분석
    #열 값은 3.1과 같으며, {총자산증가율,유형자산증가율,유동자산증가율,자기자본증가율,매출액 증가율}
    def get_analyze_growth(self):
        pass

    #6 활동성 분석
    #열 값은 3.1과 같으며, {총자산회전율,자기자본회전율,자본금회전율,경영자산회전,비유동자산회전율,유형자산회전율,재고자산회전율,제품회전율,매출채권회전율}
    def get_analyze_activity(self):
        pass


#리포트_투자지표
class ReportInvestmentIndex():
    def __init__(self):


    # ai 넘겨줄 정보 저장
        self.data_for_ai = {}
        self.is_called = [False,False,False,False,False]

#리포트_주식가치평가
class ReportStockValuation():
    def __init__(self):


    # ai 넘겨줄 정보 저장
        self.data_for_ai = {}
        self.is_called = [False,False,False,False,False]

#채팅
#채팅 세션은 우선순위큐에 저장되고, 우선순위가 높은순(유료회원)으로 응답이 완료되어 반환됩니다
#user_id는 유저를 구분하는 고유 id 입니다. 프/백에서 유저의 아이디, 혹은 구별할 수 있는 고유의 string이면 됩니다
#tab class 는 상단의 탭 객체입니다. rag를 위해 필요합니다.(주식가치평가, overview등의 정보를 담은 객체. main.py에 있는 Report로 시작하는 모든 class가 여기에 해당)
#company_name은 회사의 한글이름
#tab_name은 상단의 탭 이름입니다. (주식가치 평가 등.)
#user_level은 int형으로서, 숫자가 높을 수록 우선적으로 처리됩니다. (유료 버전 사용자)
import asyncio

@singleton
class AIChat:
    def __init__(self,worker_num,queue_size) -> None:
        self.queue_controller = AIChattingQueueController(worker_num = worker_num,max_size = queue_size)
    

    #이 메서드를 실행해야 대기열이 생성됩니다.
    async def run_queue(self):
        await self.queue_controller.run()
    
    async def ask(self,user_id:str,question:str,tab_class,company_name:str,tab_name:str,user_level:int):
        queue_data = ChattingQueueData(
            user_id = user_id,
            question = question,
            tab_class = tab_class,
            company_name = company_name,
            tab_name = tab_name,
            user_level = user_level
        )
        answer = await self.queue_controller.put_task(queue_data)
        return answer


async def main():
    #작업스레드2개, 큐 크기 최대 1000개
    ai_chat = AIChat(2,1000)

    await ai_chat.run_queue()

    tab_class = ReportStockValuation()
    tab_class.data_for_ai = {
        "내 이름":"진우",
        "친구 이름" :{"재원":"고등학교 친구","금주":"여자친구"},
        "친구가 좋아하는 과일":"사과",
        "사과":"독사과를 조심해야 함",
        "비오는 날":"판초우의",
        "진우":{"컴퓨터":"노트북만 씀","취미":"헬스"},
        "질병":{
            "어지러움" :"메니에르병",
            "복통" : "장염. 야채죽도 먹으면 안됨",
            "안구건조" : "물담긴 세숫대야에 얼굴을 넣고 1분동안 눈을 뜨고 있어야 함"
        }
        }
    q_list = [
        "진우의 취미를 알려줘",
        "요즘 배가 아파. 복통인거 같아. 왜지?",
        "눈이 건조하면 어떻게 해야 해?",
        "진우의 여자친구는 누구야?",
        "사과먹을 때 조심해야 할 점 말해줄래?"
    ]
    ans_list = []
    # ans_list.append(await ai_chat.ask("jinu","나 지금까지 몇 번 질문 했어??",tab_class,"samsung","주식가치평가",0))
    for i in range(len(q_list)):
        q = q_list[i]
        level = len(q_list) - i
        ans_list.append(await ai_chat.ask("apple",q,tab_class,"samsung","주식가치평가",level))
    
    for ans in ans_list:
        res = await ans
        print(res)

    # print(await ai_chat.ask("daf","친구 이름은 뭐야??",tab_class,"samsung","주식가치평가",1))
    # print(await ai_chat.ask("asdf","재원이가 좋아하는 과일은 뭐야?",tab_class,"samsung","주식가치평가",2))
    # print(await ai_chat.ask("jasdf","방금 내가 무슨 질문을 했지?",tab_class,"samsung","주식가치평가",3))
    # print(await ai_chat.ask("jasdfasdf","비오는 날에는 뭘 쓰면 좋아?",tab_class,"samsung","주식가치평가",4))



if __name__ == "__main__":

    asyncio.run(main())