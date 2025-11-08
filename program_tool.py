import os
import datetime
import time
from functools import wraps

# decorator
def singleton(cls):
    instances = {}
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return get_instance

#decorator
def logging(func):
    def wrapper(*args, **kwargs):
        print(f"{func.__name__} called")
        print(f"{func.__name__} finished")
    return wrapper

@singleton
class DateTimeManager():

    def __init__(self):
        self.set_time()

    def set_time(self):
        self.now = datetime.datetime.now()
        #format
        #ex 20201231
        self.formatted_today = self.now.strftime("%Y%m%d")
        self.formatted_year = self.now.strftime("%Y")
        self.formatted_month = self.now.strftime("%m")
        self.year = int(self.formatted_year)
        
    #return formatted_today - date 
    def get_past_time(self,date:int) -> str:
        past_time = self.now - datetime.timedelta(days=date)
        formatted_past_time = past_time.strftime("%Y%m%d")
        return formatted_past_time


#debuger
class Debuger():
    @staticmethod
    def printd(msg):
        print(f"[DBG] {msg}",flush=True)
    @staticmethod
    def printc(msg):
        os.system("cls")
        print(f"[DBG] {msg}",flush = True)

class LoadingDebugger(Debuger):
    def __init__(self,name,total):
        os.system("cls")
        super().printd(f"{name} 시작")
        self.name = name
        self.total = total
        self.progress = 0.0
    def print_progress(self,cnt,flush = False):
        if cnt / self.total >= self.progress:
            if flush:
                os.system("cls")
            super().printd(f"{self.name} 진행률 : {cnt}/{self.total}   ||  {cnt/self.total * 100}%")
            self.progress += 0.1
    def __del__(self):
            super().printd(f"{self.name} 완료")

@singleton
class Timer():

    def __init__(self):
        self.log = {}

    def measure(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            end = time.time()
            self.log[func.__name__] = end - start
            return result
        return wrapper



def test():

    @Timer().measure
    def waittime():
        time.sleep(1)
    
    waittime()
    print(Timer().log)

if __name__ == "__main__":
    test()