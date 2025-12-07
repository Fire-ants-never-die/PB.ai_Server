from program_tool import *
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from ai.embedding import Embedding
from ai.prompt import ChatSession
import asyncio

#상위폴더 모듈 import
# sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from controller.data_controller import UserDataController

# AI 채팅과 큐에 삽입될 정보를 관리하는 모듈입니다.

#채팅 큐에 삽입될 정보
class ChattingQueueData:
    #유저 식별 id, 탭(주식가치평가, overview등의 정보를 담은 객체. main.py에 있는 Report로 시작하는 모든 class가 여기에 해당)
    # user_level : int형 변수로서, 높을 수록 우선순위가 높게 답변이 생성됨. (유료 회원 기능)
    def __init__(self,user_id,question,tab_class,company_name, tab_name,user_level:int):
        self.tab_info = tab_class.data_for_ai #dictionary형의 재무정보/등등입니다.
        
        #데이터 구성
        self.question = question
        self.company_name = company_name; self.tab_name = tab_name
        self.company_tab_name = company_name + tab_name

        #질문 저장/불러오는 컨트롤러 싱글톤 객체
        self.userdata_controller = UserDataController()

        #user별 답변 품질에 영향끼치는 k변수 설정. (참고하는 데이터가 많아집니다. 커지면 느려질 수도 있고 오히려 쓸모없는 데이터를 참고해서 안좋아질 수도 있습니다.)
        k_dict = {}       

        #임베딩 객체 (싱글톤에서 그냥 객체로 바꿨습니다.)
        self.embedding = Embedding(self.question,self.tab_info)
        self.user_id = user_id
        self.user_level = user_level
        self.model_name = "gpt-4.1-mini"
    
    #질문 세션시작하기
    async def get_answer(self) -> str:
        #RAG
        #컨텍스트 데이터 가져오기
        context_data = self.embedding.get_context()
        self.question = "다음의 검색된 데이터를 참고하여 질문에 답변해주세요." + context_data + "질문 :" + self.question
        session = ChatSession(self.question,self.user_id,self.company_name,self.tab_name,self.model_name)

        #RAG가 제대로 작동하는지 확인하는 코드. 참고되는 컨텍스트 데이터가 잘 뽑히는지 확인합니다
        #===
        # res = "\n========검색된 데이터===-=====\n"
        # res += context_data
        # res += await session.ask()
        # return res
        #==

        return await session.ask()




#채팅 큐 관리 (일단 대충 크기는 1000)
@singleton
class AIChattingQueueController:
    
    def __init__(self,worker_num:int = 2,max_size:int = 1000):
        #비동기 큐 선언
        #큐 크기는 대충 1000, 작업 스레드는 대충 2개
        self.queue = asyncio.PriorityQueue(maxsize=max_size)
        self.workers = []
        self.worker_num = worker_num
        self.running = False

    #대기열 처리 시작
    async def run(self):
        if not self.running:
            self.running = True

            #스레드(라고 하는게 맞나??) 배치 (기본값은 2. 얼마나 worker 할당가능한지는 잘 모르겠음)
            for worker_idx in range(self.worker_num):
                worker = asyncio.create_task(self.execute(worker_idx))
                self.workers.append(worker)

    #대기열 처리 중단
    async def stop(self):
        self.running = False
        for worker in self.workers:
            worker.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)

    #대기열 작업자 (worker)가 실행할 함수
    async def execute(self,worker_idx):
        while True:
            priority, task_id,ChattingQueueData,future = await self.queue.get()
            try:
                answer = await ChattingQueueData.get_answer()
                future.set_result(answer)
                #현재 future에 문제가 있음
            except Exception as e:
                Debuger.printc("비동기 에러")
            finally:
                self.queue.task_done()
                
    #대기열에 작업 넣기
    async def put_task(self,chatting:ChattingQueueData):
        future = asyncio.get_running_loop().create_future()
        task_id = id(future)
        await self.queue.put((-chatting.user_level,task_id,chatting,future))
        return future
   
    #현재 대기열 상황 (큐에 몇개 있는지,큐 전체 메모리)
    def get_queue_info(self) -> tuple:
        res = ()
        return res
    
