from program_tool import *
import sys
from prompt import ChatSession, AIChatting
from queue import PriorityQueue
#상위폴더 모듈 import
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from controller.data_controller import UserDataController

# AI 채팅과 채팅스레드를 관리하는 모듈입니다.

#채팅 큐 관리
@singleton
class AIChattingQueueController:
    
    def __init__(self):
        self.queue = PriorityQueue()
    
    def put(self,chat:AIChatting):
        self.queue.put((-chat.user_level,chat))
    
    #비어있으면 False 반환
    #있으면 AIChatting 객체 반환
    def get(self):
        if self.queue.empty():
            return False
        else:
            return self.queue.get()[1]

