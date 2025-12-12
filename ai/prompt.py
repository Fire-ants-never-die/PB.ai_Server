from openai import AsyncOpenAI
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
            self.client = AsyncOpenAI(api_key=__api_key)
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
    def __init__(self,question:str,user_id,company, tab_name,model_name : str = "gpt-4.1-nano"):
        self.model  = model_name; self.company = company; self.question = question
        self.company_tab_name = company + " " + tab_name
        self.gpt = GPT()
        self.client = self.gpt.client
        self.user_id = user_id
        if self.client == None:
            Debuger.printc("openAI 가 연결이 안되어 있습니다.")
            return

    #지난 채팅 추가해서 질답기억하게 하기 (비어있어도 상관없음)
    # key : "XXXX년 X월 X일" , value : {key ("question") : value(질문데이터) , key ("answer") : value (답변 데이터) } 
    def append_chatting_library(self):

        chat_list = self.log_data.get_qna(self.user_id,self.company_tab_name)
        if len(chat_list) == 0:
            return

        #최근 질답 3개만 불러오기
        cnt = 3
        for chat in chat_list:
            #chat : (user_id, question, answer, datetime(str))
            #최신순으로 불러와집니다.
            cnt -= 1
            
            self.msg_list.append({"role":'user', "content" :chat[1]})
            self.msg_list.append({"role":'assistant', "content" :chat[2]})

            if cnt == 0:
                break

    #질답 모두 string
    async def ask(self) -> str:
        #질답 db 저장을 위한 data controller 싱글톤 객체
        self.log_data = UserDataController()

        #대화 기록용 리스트. 첫 dict는 사전 프롬프트 (meta.json 의 system-content)
        self.gpt.system_content = f"너는 회사 '{self.company}'의" + self.gpt.system_content
        self.msg_list = [{"role":'system',"content":self.gpt.system_content}]
        #지난 질답 추가
        self.append_chatting_library()

        self.msg_list.append({'role':'user',"content":self.question})
        response = await self.client.chat.completions.create(model = self.model, messages=self.msg_list) # type: ignore
        answer = response.choices[0].message.content
        self.msg_list.append({'role':'user',"content":answer})

        self.log_data.set_qna(self.user_id,self.question,answer,self.company_tab_name,datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        return answer # type: ignore

       


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