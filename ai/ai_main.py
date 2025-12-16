import asyncio
from ai_chatting_queue_controller import ChattingQueueData, AIChattingQueueController
import sys,os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from main import Tab
from program_tool import *



#채팅
#채팅 세션은 비동기우선순위큐에 저장되고, 우선순위가 높은순(유료회원)으로 응답이 완료되어 반환됩니다
#user_id는 유저를 구분하는 고유 id 입니다. 프/백에서 유저의 아이디, 혹은 구별할 수 있는 고유의 string이면 됩니다
#tab class 는 상단의 탭 객체입니다. rag를 위해 필요합니다.(주식가치평가, overview등의 정보를 담은 객체. main.py에 있는 Report로 시작하는 모든 class가 여기에 해당)
#company_name은 회사의 한글이름
#tab_name은 상단의 탭 이름입니다. (주식가치 평가 등.)
#user_level은 int형으로서, 숫자가 높을 수록 우선적으로 처리됩니다. (유료 버전 사용자)

@singleton
class AIChat:
    def __init__(self,worker_num,queue_size) -> None:
        self.queue_controller = AIChattingQueueController(worker_num = worker_num,max_size = queue_size)
    

    #이 메서드를 실행해야 대기열이 생성됩니다.
    async def run_queue(self):
        await self.queue_controller.run()
    
    async def ask(self,user_id:str,question:str,tab_class:Tab,company_name:str,tab_name:str,user_level:int):
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


#==========ai main =============

async def ai_main():
    ai = AIChat(worker_num=3,queue_size=1000)

    await ai.run_queue()

    #디버깅용 임시 Tab객체
    tab_class = Tab()
    tab_class.data_for_ai = {
        "내 이름":"진우",
        "친구 이름" :{"재원":"고등학교 친구","준수":"돈안갚니?"},
        "친구가 좋아하는 과일":"사과",
        "사과":"독사과를 조심해야 함",
        "비오는 날":"판초우의",
        "진우":{"컴퓨터":"노트북만 씀","취미":"헬스"},
        "질병":{
            "어지러움" :"마구니가 끼어서 그런것임",
            "복통" : "장염. 치킨을 먹어야 함",
            "안구건조" : "물담긴 세숫대야에 얼굴을 넣고 1분동안 눈을 뜨고 있어야 함"
        }
        }
    q_list = [
        "진우의 취미를 알려줘",
        "요즘 배가 아파. 복통인거 같아. 왜지?",
        "눈이 건조하면 어떻게 해야 해?",
        "사과먹을 때 조심해야 할 점 말해줄래?"
    ]
    tab_class.data_for_ai={
        "고양소방서":{
            "화재예방과":["조사팀","민원팀","생안팀","대책팀"],
            "행정과" : ["장비팀"],
            "재난대응과":[]
        },
        "고양소방서일정": {
            "11월" : ["공사시작","안전강사대회준비"],
            "12월" : ["부서이동","교보재 불용처리","안전체험관공사"]
        },
        "카드" :["신용카드","체크카드","교통카드","보안카드"]
    }
    q_list = [
        "고양소방서에는 팀이 몇 개가 있어?",
        "고양소방서 12월 일정좀 알려줘",
        "안전강사대회는 언제열릴까?",
        "카드 종류 4가지좀 알려줄래?"
    ]

    ans_list = []
    # ans_list.append(await ai_chat.ask("jinu","나 지금까지 몇 번 질문 했어??",tab_class,"samsung","주식가치평가",0))
    # for i in range(len(q_list)):
    #     q = q_list[i]
    #     level = len(q_list) - i
    #     ans_list.append(await ai.ask("apple",q,tab_class,"samsung","주식가치평가",level))
    
    for q in q_list:
        await ai.ask("apple",q,tab_class,"samsung","주식가치평가",1)
    
    for num in range(1,1):
        q = f"{num} + 10 은 뭐야?"
        await ai.ask("apple",q,tab_class,"samsung","주식가치평가",1)
        #몇초 대기
        cnt = 0
        for _ in range(20000000):
            cnt += 1

    await asyncio.gather(*ai.queue_controller.workers,return_exceptions=True)
    await ai.queue_controller.queue.join()

if __name__ == "__main__":
    asyncio.run(ai_main())

    #AIChattingQueueController 의 worker함수 맨 밑에서 response를 백엔드 혹은 클라이언트로 보내기만 하면 됨
    #최근 질답 불러오기 갯수 설정은 prompt.py의 Chatsesion 클래스의 self.qna_call_cnt 를 참고 (기본 3개)
    #Embedding.py의 Embdding 클래스의 self.k 변수로 RAG 구성에 필요한 데이터 갯수 조정 (기본 10개)