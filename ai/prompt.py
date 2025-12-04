from openai import OpenAI
from program_tool import *
import json ,os,sys, datetime
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from controller.data_controller import UserDataController

@singleton
class GPT:
    def __init__(self):
        dir = os.path.dirname(__file__)
        meta_path = os.path.join(dir,"meta.json")
        with open(meta_path,'r',encoding="utf-8") as f:
            self.meta = json.load(f)

        self.system_content = self.meta["system-content"]
        __api_key= self.meta["api_key"]

        try:
            self.client = OpenAI(api_key=__api_key)
        except:
            self.client = None
            Debuger.printc("openAI연결 실패")


class ChatSession:
                            #price per 1M token. standard 기준. (일반 응답속도)
    model_info={    "gpt-4.1-nano" : 1047576, # 0.1 / 0.4    # 일반형
                    "gpt-4o-mini"  : 128000,# 0.15 / 0.6
                    "gpt-4.1-mini" : 1047576, # 0.4 / 1.6    # 유료형
                    "gpt-5-mini"   : 400000,  # 0.25 / 2.0   # 고급형이지만...질문 저장공간이 적음
                    "gpt-5-nano"   : 400000   # 0.05 / 0.4
                }   
    #유저 식별 id, 기업과탭이름 (농심 Overview, 농심 주식가치평가 등), gpt모델 (default는 4.1nano)
    def __init__(self,user_id,company, tab_name,model_name : str = "gpt-4.1-nano"):
        self.model  = model_name
        self.company_tab_name = company + " " + tab_name
        self.gpt = GPT()
        self.client = self.gpt.client
        self.user_id = user_id
        if self.client == None:
            Debuger.printc("openAI 이 없습니다.")
            return
        
        #질답 db 저장을 위한 data controller 싱글톤 객체
        self.log_data = UserDataController()

        #대화 기록용 리스트. 첫 dict는 사전 프롬프트 (meta.json 의 system-content)
        self.gpt.system_content = f"너는 회사 '{company}'의" + self.gpt.system_content
        self.msg_list = [{"role":'system',"content":self.gpt.system_content}]

        #질문 개수 카운팅
        self.ask_cnt = 0

        #토큰 카운팅
        self.token_cnt = 0
        #마지막 토큰 길이
        self.last_token = 0

    #질답 모두 string
    #프롬프트 한도 근접시, "Token Limit Error" 반환
    def ask(self,question:str) -> str:
        
        limit_check = self.__check_token_limit()
        if limit_check == False:
            return "Token Limit Error"

        self.ask_cnt += 1       

        self.msg_list.append({'role':'user',"content":question})
        response = self.client.chat.completions.create(model = self.model, messages=self.msg_list) # type: ignore
        answer = response.choices[0].message.content
        self.msg_list.append({'role':'user',"content":answer})

        self.last_token = response.usage.total_tokens # type: ignore
        self.token_cnt += response.usage.total_tokens # type: ignore

    
        self.log_data.set_qna(self.user_id,question,answer,self.company_tab_name,datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        return answer # type: ignore

    def __check_token_limit(self):
        if (self.token_cnt + self.last_token * 2) >= self.model_info[self.model]:
            return False
        else:
            return True

def __debug():
    """
    session1 = ChatSession()
    session2 = ChatSession()

    for i in range(2):
        one = input("session[1] 질문을 입력하시오 >>")
        ans = session1.ask(one)
        print("session[1] answer : ",ans)
        two = input("session[2] 질문을 입력하시오 >>")
        ans = session2.ask(two)
        print("session[2] answer : ",ans)
    """
    # session = ChatSession()

    # for i in range(3):
    #     print("답변>>",session.ask(input("질문 >>")))
    #     print("토큰사용량:",session.last_token," 총 토큰 사용량:",session.token_cnt)



if __name__ == "__main__":
    __debug()