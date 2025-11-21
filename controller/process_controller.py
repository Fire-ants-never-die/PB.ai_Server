from concurrent.futures import ThreadPoolExecutor, as_completed
from program_tool import *
import time



# 멀티 스레드를 위한 클래스 입니다.

class ParallelExecutorThread:
    def __init__(self, workers=4):
        self.workers = workers

    def run(self, func, tasks):
        """
        func : 실행할 함수
        tasks : 함수에 들어갈 인수(list 형태). 
                예: [url1, url2, url3]
        """
        results = []
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = [executor.submit(func, task) for task in tasks]
            for f in as_completed(futures):
                results.append(f.result())
        return results




def debug():


    def do_task(msg):
        time.sleep(1)
        print(msg)
    
    @Timer().measure
    def do_five():
        for _ in range(1,5):
            do_task(_)
    do_five()
    
    print(Timer().log)

    start = time.time()
    executor = ParallelExecutorThread(workers=4)
    res = executor.run(do_task,[1,2,3,4])
    end = time.time()
    print(end - start)
        

if __name__ == "__main__":
    debug()