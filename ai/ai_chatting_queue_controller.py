from program_tool import *
import sys
from ai.embedding import Embedding
from ai.prompt import ChatSession
import asyncio
import websocket
#상위폴더 모듈 import
# sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from data.data_controller import UserDataController


task_results = {}

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

#type : 처리내용 타입
#question : ai 답변 받아오기 , prev_qna_by_company prev_qna_session, delete_session
class QueueItem:
    def __init__(
            #필수
            self,type:str,user_id:str,user_level:int,
            #선택
            #  - ai 질문 or 질답기록조회 or 기록삭제
            question="",company_name="",tab_name="",preserve_num:int=0) -> None:
        self.type = type
        self.user_id = user_id
        self.user_level = user_level
        #여기는 선택
        self.question = question
        self.company_name = company_name
        self.tab_name = tab_name
        self.preserve_num = preserve_num
        

#큐에 삽입될 정보
class ServerQueueData:
    #인스턴스 갯수
    _counter = 0
    #유저 식별 id, 탭(주식가치평가, overview등의 정보를 담은 객체. main.py에 있는 Report로 시작하는 모든 class가 여기에 해당)
    # user_level : int형 변수로서, 높을 수록 우선순위가 높게 답변이 생성됨. (유료 회원 기능)
    #def __init__(self,task_id,user_id,question,company_name, tab_name,user_level:int):
    def __init__(self,item:QueueItem):

        ServerQueueData._counter += 1
        if ServerQueueData._counter > 999:
            ServerQueueData._counter = 0
        self._instance_id = ServerQueueData._counter
        self.type = item.type
        self.user_id = item.user_id
        self.user_level = item.user_level
        self.userdata_controller = UserDataController()
        self.company_tab_name = f"{item.company_name} {item.tab_name}"
        if self.type == "question":
            #데이터 구성
            self.tab_info = self._get_tab_info(item.company_name,item.tab_name) #dictionary형의 재무정보/등등입니다.
            self.question:str= item.question # type: ignore
            self.company_name = item.company_name; self.tab_name = item.tab_name

            #질문 저장/불러오는 컨트롤러 싱글톤 객체
            self.userdata_controller = UserDataController()

            #user별 답변 품질에 영향끼치는 k변수 설정. (참고하는 데이터가 많아집니다. 커지면 느려질 수도 있고 오히려 쓸모없는 데이터를 참고해서 안좋아질 수도 있습니다.)
            k_dict = {}       

            #임베딩 객체 (싱글톤에서 그냥 객체로 바꿨습니다.)
            self.embedding = Embedding(self.question,self.tab_info)
            self.user_id = item.user_id
            self.user_level = item.user_level
            self.model_name = "gpt-4.1-mini"

            #context data 확인용
            self.context = ""
        self.name_to_ticker = {"농심":"004370","CJ제일제당":"097950"}
    
    #큐에 인스턴스가 들어가고 우선순위가 같을때 우선권을 비교결정 하기 위한 메서드입니다.
    def __lt__(self,other):
        return self._instance_id < other._instance_id
        
    #뽑히면 계산될 내용
    async def process_queue(self) -> dict:
        if self.type == "question":
            #RAG
            #컨텍스트 데이터 가져오기
            context_data = await self.embedding.get_context(self.name_to_ticker[self.company_name])
            self.processed_question = "다음의 검색된 데이터를 참고하여 질문에 답변해주세요." + context_data + "질문 :" + self.question
            session = ChatSession(self.processed_question,self.user_id,self.company_name,self.tab_name,self.model_name)

            #context data 확인용
            self.context = context_data
            try:
                ans = await session.ask()
                res = {
                "status" : "200",
                "user_id" : self.user_id,
                "company_name" : self.company_name,
                "company_tab_name" : self.company_tab_name,
                "question" : self.question,
                "answer" : ans
                }
            except:
                ans = "GPT 답변이 없습니다."
                res ={
                    "status" : f"500 : {ans}"
                }
            
            return res

        elif self.type == "prev_qna_by_company" or self.type == "prev_qna_session":
            qna_list = []
            if self.type == "prev_qna_by_company":
                qna_list =self.userdata_controller.get_qna(self.user_id,self.company_tab_name)
            elif self.type == "prev_qna_session":
                qna_list =self.userdata_controller.get_sessions(self.user_id)

            size = len(qna_list)
            qna_dict_list = []
            key_name = ["user_id", "question","answer", "company_tab_name","created_time"]
            for tp in qna_list:
                qna_dict = {}
                for i in range(len(tp)):
                    qna_dict[key_name[i]] = tp[i]
                qna_dict_list.append(qna_dict)
            return {
                "status" : "200",
                "size":size,
                "list":qna_dict_list
                }
        elif self.type == "delete_session":
            response = {}
            try:
                self.userdata_controller.delete_session(self.user_id,self.company_tab_name,0)
                response["status"] = "Sucess"
            except Exception as e:
                Debuger.printc(f"Delete fail : {e}")
                response["status"] = f"Delete fail : {e}"
            finally:
                return response
        else:
            return {"status":"200"}

    #생성자에서 쓰입니다.
    def _get_tab_info(self,company_name,tab_name) -> dict:
        company_name_decoder = {
            "농심":"004370",
            "CJ제일제당":"097950"
        }
        info = self.userdata_controller.get_mvp_company_data(company_name_decoder[company_name])
        return info



#채팅 큐 관리 (일단 대충 크기는 1000)
@singleton
class ServerQueueController:
    
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
            
            #작업자 worker 배치 (기본값은 2. 얼마나 worker 할당가능한지는 잘 모르겠음)
            for i in range(1,self.worker_num + 1):
                new_worker = asyncio.create_task(self.worker(i,self.queue))
                self.workers.append(new_worker)

    #작업함수
    async def worker(self,worker_id:int, queue: MemoryTrackingPriorityQueue):

        while True:
            is_sucess = False
            try:
                priority, item, future = await self.queue.get()
                item:ServerQueueData
                future:asyncio.Future
                #for debug
                print(f"[Worker {worker_id}] Got item, priority={priority}, memory_usage = {self.queue.memory_usage}bytes")
                #비동기 실행
                # await self.loop.run_in_executor(None,item.get_answer)
                ans_dict = await item.process_queue()
                is_sucess = True

                # Debuger.printc(f"queue controller 인스턴스의 worker 함수 속에서 실행되는 답변입니다\n 질문 : {item.question}\n 검색된 데이터:{item.context}\n답변 :{ans}")
                response = ans_dict
            except Exception as e:
                Debuger.printc(f"worker비동기 에러 : {e}")
                response = {
                    "status" : f"500: {e}"
                }
            finally:
                #여기에서 response를 백엔드로 보내면 됩니다
                future.set_result(response)
                if is_sucess:
                    self.queue.task_done()
    
    #큐에 삽입
    async def put_task(self,item:ServerQueueData):

        loop = asyncio.get_running_loop()       
        future = loop.create_future()

        await self.queue.put((-item.user_level,item,future))
        res = await future
        return res



    #대기열 처리 중단
    async def stop(self):
        self.running = False
        for worker in self.workers:
            worker.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)