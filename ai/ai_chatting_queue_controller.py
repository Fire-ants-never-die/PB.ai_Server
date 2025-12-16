from program_tool import *
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from ai.embedding import Embedding
from ai.prompt import ChatSession
from main import Tab
import asyncio

#상위폴더 모듈 import
# sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from controller.data_controller import UserDataController

# ======AI 채팅과 큐에 삽입될 정보를 관리하는 모듈입니다.=======

#비동기큐 메서드 오버로딩 (메모리 관리하기 위함입니다)
#어떻게 이렇게 재미난 테크닉을 썼냐구요? 물론 gpt 작품입니다. gpt없던 시절엔 어떻게 코딩했을까 ㅅㅂ
class MemoryTrackingPriorityQueue(asyncio.PriorityQueue):
    def __init__(self, max_size: int = 2) -> None:
        super().__init__(maxsize=max_size)
        self.memory_usage = 0
    
    async def put(self, item):
        """삽입 시 메모리 측정 및 누적."""
        size = self.get_byte(item)
        self.memory_usage += size
        await super().put(item)

    async def get(self):
        """꺼낼 때 메모리 차감."""
        item = await super().get()
        size = self.get_byte(item)
        self.memory_usage -= size
        return item

    def get_memory_usage(self):
        """현재 메모리 상태 반환."""
        return {
            "bytes": self.memory_usage,
            "kb": round(self.memory_usage / 1024, 2),
            "mb": round(self.memory_usage / 1024 / 1024, 4),
        }

    def get_queue_length(self):
        return self.qsize()
    
    def get_byte(self,obj, unit:str = "mb",seen=None) -> int:
        import sys
        from collections import deque
        """객체의 실제 메모리 사용량을 재귀적으로 계산."""
        size = sys.getsizeof(obj)
        if seen is None:
            seen = set()

        obj_id = id(obj)
        if obj_id in seen:
            return 0
        seen.add(obj_id)

        # 컨테이너 타입이면 내부 요소도 모두 더하기
        if isinstance(obj, dict):
            size += sum((self.get_byte(k, unit,seen) + self.get_byte(v,unit,seen)) for k, v in obj.items())
        elif isinstance(obj, (list, tuple, set, frozenset, deque)):
            size += sum(self.get_byte(i, unit,seen) for i in obj)
            
        return size


#채팅 큐에 삽입될 정보
class ChattingQueueData:
    #인스턴스 갯수
    _counter = 0
    #유저 식별 id, 탭(주식가치평가, overview등의 정보를 담은 객체. main.py에 있는 Report로 시작하는 모든 class가 여기에 해당)
    # user_level : int형 변수로서, 높을 수록 우선순위가 높게 답변이 생성됨. (유료 회원 기능)
    def __init__(self,user_id,question,tab_class:Tab,company_name, tab_name,user_level:int):
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

        ChattingQueueData._counter += 1
        if ChattingQueueData._counter > 999:
            ChattingQueueData._counter = 0
        self._instance_id = ChattingQueueData._counter

        #context data 확인용
        self.context = ""
    
    #큐에 인스턴스가 들어가고 우선순위가 같을때 우선권을 비교결정 하기 위한 메서드입니다.
    def __lt__(self,other):
        return self._instance_id < other._instance_id
        
    #질문 세션시작하기
    async def get_answer(self) -> str:
        #RAG
        #컨텍스트 데이터 가져오기
        context_data = await self.embedding.get_context()
        self.question = "다음의 검색된 데이터를 참고하여 질문에 답변해주세요." + context_data + "질문 :" + self.question
        session = ChatSession(self.question,self.user_id,self.company_name,self.tab_name,self.model_name)

        #context data 확인용
        self.context = context_data

        return await session.ask()




#채팅 큐 관리 (일단 대충 크기는 1000)
@singleton
class AIChattingQueueController:
    
    def __init__(self,worker_num:int = 2,max_size:int = 1000):
        #비동기 큐 선언
        #큐 크기는 대충 1000, 작업 스레드는 대충 2개
        self.queue = MemoryTrackingPriorityQueue(max_size=max_size)
        self.workers = []
        self.worker_num = worker_num
        self.running = False

    #대기열 처리 시작
    async def run(self):
        if not self.running:
            self.running = True

            # for worker_idx in range(self.worker_num):
            #     worker = asyncio.create_task(self.execute(worker_idx))
            #     self.workers.append(worker)
            
            #작업자 worker 배치 (기본값은 2. 얼마나 worker 할당가능한지는 잘 모르겠음)
            for i in range(1,self.worker_num + 1):
                new_worker = asyncio.create_task(self.worker(i,self.queue))
                self.workers.append(new_worker)

    #작업함수
    async def worker(self,worker_id:int, queue: MemoryTrackingPriorityQueue):
        # self.loop = asyncio.get_running_loop()
        while True:
            is_sucess = False
            try:
                priority, item = await self.queue.get()
                item:ChattingQueueData
                #for debug
                print(f"[Worker {worker_id}] Got item, priority={priority}, memory_usage = {self.queue.memory_usage}bytes")
                #비동기 실행
                # await self.loop.run_in_executor(None,item.get_answer)
                ans = await item.get_answer()
                is_sucess = True

                response = {
                    "status" : "200",
                    "user_id" : item.user_id,
                    "company_name" : item.company_name,
                    "company_tab_name" : item.company_tab_name,
                    "question" : item.question,
                    "answer" : ans
                }

                Debuger.printc(f"queue controller 인스턴스의 worker 함수 속에서 실행되는 답변입니다\n 질문 : {item.question}\n 검색된 데이터:{item.context}\n답변 :{ans}")

            except Exception as e:
                Debuger.printc(f"worker비동기 에러 : {e}")
                response = {
                    "status" : f"{e}"
                }
            finally:

                #여기에서 response를 백엔드로 보내면 됩니다

                if is_sucess:
                    self.queue.task_done()
    
    #큐에 삽입
    async def put_task(self,item:ChattingQueueData):
        await self.queue.put((-item.user_level,item))



    #대기열 처리 중단
    async def stop(self):
        self.running = False
        for worker in self.workers:
            worker.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)