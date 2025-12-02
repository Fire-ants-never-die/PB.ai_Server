from openai import OpenAI
from program_tool import *
import json ,os


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

#chat session이 각 세션별로 대화를 기억을 하는지 테스트 해야 합니다!!!!
class ChatSession:
    
    def __init__(self,model : str = "gpt-4o-mini"):
        self.model  = model
        self.gpt = GPT()
        self.client = self.gpt.client
        if self.client == None:
            Debuger.printc("openAI 이 없습니다.")
            return

        #대화 기록용 리스트. 첫 dict는 사전 프롬프트 (meta.json 의 system-content)
        self.msg_list = [{"role":'system',"content":self.gpt.system_content}]

        #질문 개수 카운팅
        self.ask_cnt = 0

    #질답 모두 string
    def ask(self,question:str) -> str:

        self.ask_cnt += 1       

        self.msg_list.append({'role':'user',"content":question})

        response = self.client.chat.completions.create(model = self.model, messages=self.msg_list) # type: ignore

        answer = response.choices[0].message.content

        self.msg_list.append({'role':'user',"content":answer})
    
        return answer # type: ignore


def __debug():
    session1 = ChatSession()

    for i in range(5):
        q = input("질문을 입력하시오 >>")
        ans = session1.ask(q)
        print(ans)

if __name__ == "__main__":
    __debug()