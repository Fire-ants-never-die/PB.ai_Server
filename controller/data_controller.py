import os , sys, json ,pickle, sqlite3
import pandas as pd
from dotenv import load_dotenv
#상위폴더 모듈 import
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from program_tool import *


#ai agent의 질답을 보관하는 user data controller 입니다.
#data/user_ai_qna.db   qa_logs 테이블에 질답이 저장됩니다.
# 클라이언트 식별 id, 질문 ,답변, 회사와 탭이름, 생성일자가 저장됩니다. 생성일자는 "%Y-%m-%d %H:%M:%S" 형식으로 저장됩니다.
# ex) 식별id, "유동자산이뭔가요" ,"유동자산은 ~입니다", "농심 Overview", "2025-10-31-13:33:21"
@singleton
class UserDataController:
    
    def __init__(self) -> None:
        dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
        path = os.path.join(dir,"data\\user_ai_qna.db")
        print(path)
        self.con = sqlite3.connect(path)
        self.cursor = self.con.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS qa_logs (
            user_id TEXT,
            question TEXT,
            answer TEXT,
            company_tab_name TEXT,
            created_time TEXT
            )
            """)
        self.con.commit()
    
    def set_question(self,user_id,question,company_tab_name,created_time):
        try:
            self.cursor.execute("""
                                INSERT INTO questions (user_id, question, company_tab_name, created_time)
                                VALUES (?, ?, ?, ?)
                                """,(user_id, question, company_tab_name,created_time))
            self.con.commit()
        except:
            Debuger.printc("질문 데이터 저장 실패. 질답 처리가 완료되기 전에 여러번 질문을 입력해서 primary key인 id가 중복되었을 가능성")

    def pop_question(self,user_id) -> tuple:
        try:
            self.cursor.execute("SELECT * FROM questions WEHRE user_id = ?",(user_id,))
            res = self.cursor.fetchone()
            self.con.commit()

            return res
        except:
            Debuger.printc("질문 데이터 로딩 실패")
        
            return ()
    
    
    def set_qna(self,user_id, question, answer, company_tab_name,created_time):
        try:
            self.cursor.execute("""
                                INSERT INTO qa_logs (user_id, question, answer, company_tab_name, created_time)
                                VALUES (?, ?, ?, ?, ?)
                                """,(user_id, question, answer, company_tab_name,created_time))
            self.con.commit()
        except:
            Debuger.printc("데이터 저장 실패")
    
    def get_qna(self,user_id, company_tab_name) -> list[tuple]:
        res = []
        try:
            self.cursor.execute("""
                SELECT user_id, question, answer, company_tab_name,created_time
                FROM qa_logs
                WHERE user_id = ? AND company_tab_name = ?
                ORDER BY created_time DESC
                """, (user_id,company_tab_name))
            res = self.cursor.fetchall() 
        except Exception as e:
            Debuger.printc(f"데이터 조회 실패 : {e}")
        
        return res

    #채팅라이브러리 탭에서 쓰이는 메서드입니다.
    #한 유저의 모든 채팅 세션을 불러옵니다. (세션은 각 탭별로 하나씩 존재)
    def get_sessions(self,user_id) -> list[tuple]:
        res = []
        try:
            param = [user_id]
            self.cursor.execute("""
                SELECT user_id, question, answer, company_tab_name,created_time
                FROM qa_logs
                WHERE user_id = ?
                ORDER BY created_time DESC
                """, param)
            res = self.cursor.fetchall()
            
        except Exception as e:
            Debuger.printc(f"데이터 조회 실패 : {e}")
        finally:
            return res

    #채팅 라이브러리가 과도하게 쌓이는걸 대비하여 한 세션에서 remain개 빼고 모두 삭제할 수 있는 기능을 담은 메서드입니다   
    #혹은 탭 세션 초기화할때도 사용 가능



    # 작동ㅇ안함..ㅠㅠ 해결해야댐
    def delete_session(self,user_id,company_tab_name,remain):
        try:
            param = [user_id,company_tab_name,remain,user_id,company_tab_name]
            self.cursor.execute(f"""
                DELETE FROM qa_logs 
                WHERE ROWID NOT IN(
                    SELECT ROWID FROM qa_logs
                    WHERE user_id = ?
                    AND company_tab_name = ?
                    ORDER BY created_time DESC
                    LIMIT ?
                    )
                AND user_id = ?
                AND company_tab_name = ?
                """,param)
            self.con.commit()
        except Exception as e:
            Debuger.printc(f"세션 삭제 실패 : {e}")
    
    #테이블 행 크기 반환
    def get_table_size(self):
        try:
            self.cursor.execute("SELECT COUNT(*) FROM qa_logs")
            res = self.cursor.fetchone()[0]
            return res
        except Exception as e:
            Debuger.printc(f"테이블 크기 조회 실패 {e}")
            pass
        


@singleton
class DataController:

    def __init__(self) -> None:
        #DB path
        dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
        path_name = ["extracted","raw","market","calculation"]
        self.pathtype = {}
        for name in path_name:
            self.pathtype[name] = os.path.join(dir,f"data/{name}.db")

        self.meta_path = os.path.join(dir,"data/meta/")
        
        #.env파일 load
        load_dotenv()
    
    def get_env(self,name:str):
        return os.environ.get(name)
    
    def create_table(self,df:pd.DataFrame,dbtype:str,table_name:str,append:bool = True): #dbtype : "extracted", "raw", "market"
        con = sqlite3.connect(self.pathtype[dbtype])
        property = "append" if append == True else "replace"
        try:
            df.to_sql(table_name,con,if_exists=property,index=False)
        except sqlite3.IntegrityError:
            pass
        con.close()

    #테이블화하면서 특정 열을 primary key화 합니다.
    def create_table_set_key(self,df:pd.DataFrame,dbtype:str,table_name:str,key_name:str,replace:bool = False):
        con = sqlite3.connect(self.pathtype[dbtype])   
        name_property = f"'{key_name}' TEXT PRIMARY KEY, "
        for col in df.columns:
            if col == key_name:
                continue
            name_property += f"'{col}' TEXT, "
        name_property = name_property[:-2]

        sql_order = f"CREATE TABLE IF NOT EXISTS '{table_name}' ({name_property})"
        cursor = con.cursor()
        cursor.execute(sql_order)
        try:
            append_type = "append" if replace == False else "replace"
            df.to_sql(table_name,con,if_exists=append_type,index=False)
        except sqlite3.IntegrityError:
            # 이미 존재하는 값일 가능성 큼.
            pass
        con.commit()
        con.close()
    
    def create_table_set_key_from_dict(self,dt:dict,dbtype:str,table_name:str,key_name:str,replace:bool = False):
        con = sqlite3.connect(self.pathtype[dbtype])   
        name_property = f"'{key_name}' TEXT PRIMARY KEY, "
        for key in dt.keys():
            if key == key_name:
                continue
            name_property += f"'{key}' TEXT, "
        name_property = name_property[:-2] #맨 마지막 쉼표 제거하는 코드입니다.

        sql_order = f"CREATE TABLE IF NOT EXISTS '{table_name}' ({name_property})"
        cursor = con.cursor()
        cursor.execute(sql_order)

        keys = "("
        values = ""
        rv = []
        for k, v in dt.items():
            keys += f"{k},"
            rv.append(v)
            values += "?,"
        rt = tuple(rv)
        keys = keys[:-1]
        values = values[:-1]
        keys += ")"
    
    
        sql_order = f"INSERT OR REPLACE INTO {table_name} {keys} VALUES ({values})"
        cursor.execute(sql_order,rt)
        con.commit()       
        con.close()
    
    def create_table_for_calculation(self,dt:dict,table_name):
        con = sqlite3.connect(self.pathtype["calculation"])
        cursor = con.cursor()
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            항목 TEXT PRIMARY KEY,
            데이터분자 TEXT,
            데이터분자값 TEXT,
            데이터분모 TEXT,
            데이터분모값 TEXT,
            데이터 TEXT,
            시계열평균분자 TEXT,
            시계열평균분모 TEXT
        )
        """)
        cursor.executemany(f"INSERT INTO {table_name} (key, value) VALUES (?, ?)",dt.items())
        con.commit()
        con.close()

    def create_columns(self,dbtype:str,table_name:str,col_list:list):
        con = sqlite3.connect(self.pathtype[dbtype])
        cursor = con.cursor()

        cursor.execute(f'PRAGMA table_info("{table_name}")')
        cols = [row[1] for row in cursor.fetchall()]
        for col in col_list:
            if col not in cols:
                cursor.execute(f"ALTER TABLE '{table_name}' ADD COLUMN {col} TEXT")
        con.commit()
        con.close()

    def read_table(self,dbtype:str,table_name:str)->pd.DataFrame:
        con = sqlite3.connect(self.pathtype[dbtype])
        res = pd.read_sql(f"SELECT * FROM '{table_name}'",con)
        con.close()
        return res
    
    #row_name에 헤당하는 열에서 data_dict의 key값을 찾아, 그 행의 col_name에 해당하는 열에 value를 집어넣습니다.
    def update_column_by_dict(self,dbtype:str,table_name:str,data_dict:dict,row_name:str,col_name:str):
        con = sqlite3.connect(self.pathtype[dbtype])
        cursor = con.cursor()
        params = [(value,key) for key,value in data_dict.items()]
        cursor.executemany(f"""
            UPDATE '{table_name}'
            SET {col_name} = ?
            WHERE {row_name} = ?
            """, params)
        con.commit()
        con.close()
    

    def get_meta_data(self) ->dict:
        #current_dir = os.path.dirname(__file__)
        #meta_path = os.path.join(current_dir,'data','meta.json')
        path = self.meta_path + "meta.json"
        with open(path,'r',encoding='utf-8') as f:
            meta_data = json.load(f)
        return meta_data
    
    def save_df_excel(self,df:pd.DataFrame, name : str):
        df.to_excel(excel_writer = f'{name}.xlsx')


    def set_crawled_set(self,new_list:list):
        path = self.meta_path + "crawled_set.pkl"
        if os.path.exists(path):
            with open(path,'rb') as f:
                cset = pickle.load(f)
        else:
            cset = set()
        cset.update(new_list)
        
        with open(path,'wb') as f:
            pickle.dump(cset,f)

    def set_parsed_set(self,new_list:list):
        path = self.meta_path + "parsed_set.pkl"
        if os.path.exists(path):
            with open(path,'rb') as f:
                pset = pickle.load(f)
        else:
            pset = set()
        pset.update(new_list)
        
        with open(path,'wb') as f:
            pickle.dump(pset,f)
        

    def get_crawled_set(self) -> set:
        path = self.meta_path + "crawled_set.pkl"
        if os.path.exists(path):
            with open(path,'rb') as f:
                res = pickle.load(f)
                return res
        else:
            empty_set = set()
            return empty_set

    def get_parsed_set(self) -> set:
        path = self.meta_path + "parsed_set.pkl"
        if os.path.exists(path):
            with open(path,'rb') as f:
                res = pickle.load(f)
                return res
        else:
            empty_set = set()
            return empty_set



    def remove_data_for_debug(self):
        Debuger.printc("데이터 삭제")
        path1 = "data/extracted.db"
        path2 = "data/raw.db"
        path3 = "data/meta/crawled_set.pkl"
        path4 = "data/meta/parsed_set.pkl"
        path5 = "data/market.db"

        parent_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
        Debuger.printc(parent_dir)

        path_list = [path1,path2,path3,path4,path5]
        for i in path_list:
            path = os.path.join(parent_dir,i)
            if os.path.exists(path):
                os.remove(path)



#------------- for test

    def to_excel_test(self,df:pd.DataFrame,name:str):
        parent_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
        path = parent_dir + f"/testdata/{name}.xlsx"
        df.to_excel(excel_writer = path)

#-------------------------------------------------------------------------------------------------

    #Deprecated
    def save_df_feather(self,df:pd.DataFrame, year:int,name: str,is_raw:bool = True):
        current_dir = os.path.dirname(__file__)
        path = "data/"
        if is_raw:
            path += f"raw/{year}"
        else:
            path += f"extracted/{year}"
        path = os.path.join(current_dir,path)
        #path 존재 확인
        os.makedirs(path,exist_ok=True)
        path = os.path.join(path,f'{name}.feather')
        df.to_feather(path)
    #Deprecated
    @staticmethod
    #ftype : Y(사업보고서), H(반기), Q1 (1분기)
    def get_finstate_data(ticker: str, year:int, property : str) ->pd.DataFrame:
        path = f"data/{year}/{year}{ticker}{property}.feather"

        try:
            res = pd.read_feather(path)
        except FileNotFoundError:
            print(f"{ticker}경로 찾기 에러")

        except Exception as e:
            print(f"{ticker}데이터를 불러오는 중 에러 발생 :",e)
        return res
    #Deprecated
    @staticmethod
    #ftype : Y(사업보고서), H(반기), Q1 (1분기)
    def get_raw_finstate_data(ticker: str, year:int, ftype : str)->pd.DataFrame:

        path = f"data/raw/{year}/Y{year}T{ticker}P{ftype}.feather"
        res = pd.DataFrame()
        try:
            res =  pd.read_feather(path)
        except FileNotFoundError:
            print(f"{ticker}경로 찾기 에러")
            print(path)
        except Exception as e:
            print(f"{ticker}데이터를 불러오는 중 에러 발생 :",e)

        return res
    

def _debug():
    udc = UserDataController()
    # print(udc.get_table_size())

    udc.delete_session("jinu","samsung 주식가치평가",4)

    # fl = udc.get_sessions("apple")

    print(udc.get_table_size())


if __name__ == "__main__":
    _debug()