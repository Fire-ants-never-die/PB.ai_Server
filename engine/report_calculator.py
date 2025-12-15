import os, sys, json
import pandas as pd
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from program_tool import *
from controller.data_controller import DataController



class ReportCalculator:

    def __init__(self) -> None:
        self.data_controller = DataController()
        self.datetime = DateTimeManager()
        self.current_year = self.datetime.formatted_year
        self.month = self.datetime.formatted_month
    
    def format(self,data)->str:
        return format(data,".2f")
    #특정 연도 비율 게산 (분자,분모) tuple return
    def _calculate_ratio(self,year,bdf:pd.DataFrame,idf:pd.DataFrame,numerator_list,denominator_list)->tuple:
        #분자 계산
            numerator = 0
            nstr = ""
            for ndata in numerator_list:
                col = ndata[0]; sign = 1 if ndata[1] == "+" else -1
                nstr += ndata[0]
                nstr += ndata[1]
                if col in bdf.columns:
                    # dict = bdf[col].to_dict()
                    dt = dict(zip(bdf['year'], bdf[col]))
                else:
                    dt = dict(zip(idf['year'], idf[col]))
                    # dict = idf[col].to_dict()   
                key = ""
                for quarter in range(4,0,-1):
                    _key = f"{year}Q" + str(quarter)
                    if _key in dt:
                        key = _key 
                if key == "":
                    return ()
                if dt[key] == "None" or dt[key] == None or dt[key] == "":
                    return ()
                numerator += (sign * int(dt[key]))
            nstr = nstr[0:-1]
            #분모 계산
            denominator = 0
            dstr = ""
            for ddata in denominator_list:
                col = ddata[0]; sign = 1 if ddata[1] == "+" else -1
                dstr += ddata[0]
                dstr += ddata[1]
                if col in bdf.columns:
                    dt = dict(zip(bdf['year'], bdf[col]))
                    # dict = bdf[col].to_dict()
                else:
                    dt = dict(zip(idf['year'], idf[col]))
                    # dict = idf[col].to_dict()   
                key = ""
                for quarter in range(4,0,-1):
                    _key = f"{year}Q" + str(quarter)
                    if _key in dt:
                        key = _key 
                if key == "":
                    return ()
                if dt[key] == "None" or dt[key] == None or dt[key] == "":
                    return ()
                denominator += (sign * int(dt[key]))
            dstr = dstr[0:-1]


            return ((nstr,numerator),(dstr,denominator))

    #시계열데이터 분석 private 메서드. 데이터 부족으로 계산 실패하면 빈 튜플 반환
    #numerator_list : (분자로 올 list[["칼럼명","부호"],["칼럼명","부호"]...], denominator: 분모..
    #ex  ["유동자산","+"]
    def _calculate_ma(self, bdf:pd.DataFrame,idf:pd.DataFrame,numerator_list,denominator_list)->tuple:
        year = int(self.current_year)
        if int(self.month) <= 3:
            year -= 1
        n = 0; d = 0
        try:
            for dy in range(1,4):
                target_year = year - dy
                nd = self._calculate_ratio(target_year,bdf,idf, numerator_list,denominator_list)
                n += nd[0] * (4 - dy)
                d += nd[1] * (4 - dy)
                if len(nd) == 0 or nd[1] == 0:
                    return ()
            n /= 6 ; d /= 6
            return (n,d)

        except:
            return ()
            
    
    def _calculate_fomula2(self,bdf:pd.DataFrame,idf:pd.DataFrame,fomula : dict) -> dict:
        #{key = "부채비율", value = {"분자":("부채총계",실제값),"분모":("자본총계",실제값),"data":"계산값","시계열평균분자":값...}}
        #ex) "총자산증가율" : {"분자":("당기자산총계",실제값), "분모":("전기자산총계")분모값, "data":계산값,"시계열평균분자":값..}
        res = {}

        flag = {}
        for k in fomula.keys():
            flag[k] = True

        for dy in range(0,4):
            ty = int(self.current_year) - dy
            _rowcurr = f"{ty}Q"
            _rowprev = f"{ty-1}Q"
            currQ = 0
            prevQ = 0
            for i in range(4,0,-1):
                rowname = _rowcurr + str(i)   
                if (bdf['year'] == rowname).any() and (idf['year'] == rowname).any():
                    currQ = i
                    break
            for i in range(4,0,-1):
                rowname = _rowprev + str(i)   
                if (bdf['year'] == rowname).any() and (idf['year'] == rowname).any():
                    prevQ = i
                    break
            if currQ == 0 or prevQ == 0:
                break
            
            factor = [0,4,2,1.33,1]
            rc = _rowcurr + str(currQ)
            rp = _rowprev + str(prevQ)
            cb = bdf[bdf['year'] == rc].iloc[0].to_dict() #당기 재무분배표 딕셔너리
            ci = idf[idf['year'] == rc].iloc[0].to_dict() #손익계산서
            pb = bdf[bdf['year'] == rp].iloc[0].to_dict() #전기 재무분배표 딕셔너리
            pi = idf[idf['year'] == rp].iloc[0].to_dict() #손익계산서

            ci["매출액"] *= factor[currQ]
            pi["매출액"] *= factor[currQ]
            
            numerator = 0; denominator = 0
            for key, value in fomula.items():
                if value in cb.keys():
                    numerator = int(cb[value])
                elif value in ci.keys():
                    numerator = int(ci[value]) 
                if value in pb.keys():
                    denominator = int(pb[value]) 
                elif value in pi.keys():
                    denominator = int(pi[value]) 
                if numerator != None and numerator != 0 and denominator != None and denominator != 0:
                    numerator = numerator - denominator
                else:
                    continue
                #올해
                if dy == 0:
                    res[key] = {}
                    res[key]["분자"] = (f"당기{value}-전기{value}",numerator)
                    res[key]["분모"] = (f"전기{value}",denominator)
                    try:
                        res[key]["data"] = self.format(numerator/denominator * 100)
                    except:
                        res[key]["data"] = "Null"
                    res[key]["시계열평균분자"] = 0
                else:
                    if numerator != 0 and denominator != 0:
                        res[key]["시계열평균분자"] += (numerator / denominator) * 100 * (4 - dy)
                    else:
                        flag[key] = False
        
        for k in fomula.keys():
            if flag[k] == False:
                res[k]["시계열평균분자"] = "NULL"
                res[k]["시계열평균분모"] = "NULL"
            
            else:
                res[k]["시계열평균분자"] = self.format(res[k]["시계열평균분자"] / 6)
                res[k]["시계열평균분모"] = str(1)
            

                
            


        return res

    #재무현황분석 -> 안정성 분석
    #{key = "부채비율", value = {"분자":("부채총계",실제값),"분모":("자본총계",실제값),"data":"계산값","시계열평균분자":값...}}
    #모두 string형
    def _calculate_stability(self,bdf:pd.DataFrame,idf:pd.DataFrame):

        fomula ={
            #유동성
            #                        분자 (numerator)     /      분모(denominator)
            "유동비율" :        (  [("유동자산","+")],          [("유동부채","+")]   ),
            "당좌비율":         (   [("당좌자산","+")],         [("유동부채","+")]    ),
            "현금비율":         (   [("현금및현금성자산","+")],         [("유동부채","+")]    ),
            "순운전자본대총자본":(   [("유동자산","+"),("유동부채","-")],         [("자산총계","+")]    ),
            "비유동비율":       (   [("비유동자산","+")],         [("자본총계","+")]    ),
            "비유동장기적합률":  (   [("비유동자산","+")],         [("자본총계","+"),("비유동부채","+")]    ),
           
            #레버리지
            "부채비율" :        (  [("부채총계","+")],          [("자본총계","+")]   ),
            "자기자본비율":         (   [("자본총계","+")],         [("자산총계","+")]    ),
            "유동부채비율":         (   [("유동부채","+")],         [("자본총계","+")]    ),
            "비유동부채비율":(   [("비유동부채","+")],         [("자본총계","+")]    ),
            "차입금의존도":       (   [("차입금(이자지급부채)","+")],         [("자산총계","+")]    ),
            "차입금대매출액":  (   [("차입금(이자지급부채)","+")],         [("매출액","+")]    ),

            #투자수익성
            "총자산세전수익률" :        (  [("법인세비용차감전순이익","+")],          [("자산총계","+")]   ),
            "총자산순이익률":         (   [("당기순이익","+")],         [("자산총계","+")]    ),
            "기업세전순이익률":         (   [("법인세비용차감전순이익","+"),("이자비용","+")], [("자산총계","+")]    ),
            "기업순이익률":              (   [("당기순이익","+"),("이자비용","+")],         [("자산총계","+")]    ),
            "자기자본세전순이익률":       (   [("법인세비용차감전순이익","+")],   [("자본총계","+")]    ),
            "자본금세전순이익률":  (   [("법인세비용차감전순이익","+")],    [("자본금","+")]    ),
            "자본금순이익률":  (   [("당기순이익","+")],         [("자본금","+")]    ),
            "자기자본순이익률":  (   [("당기순이익","+")],         [("자본총계","+")]    ),
            
            #판매마진
            "매출액세전순이익률" :        (  [("법인세비용차감전순이익","+")],   [("매출액","+")]   ),
            "매출액순이익률":         (   [("당기순이익","+")],  [("매출액","+")]    ),
            "매출액영업이익률":         (   [("영업이익","+")],         [("매출액","+")]    ),
            "EBIT대매출액":(   [("법인용비용차감전순이익","+"),("이자비용","+")],  [("매출액","+")] ),
            "EBITDA대매출액": ([("법인세비용차감전순이익","+"),("이자비용","+"),("감가상각비","+"),("무형자산상각비","+"),], [("매출액","+")]),
            #성장성은 따로

            #활동성
            "총자산회전율":        (  [("매출액","+")],   [("자산총계","+")]  ),
            "자기자본회전율":        (  [("매출액","+")],   [("자본총계","+")]  ),
            "자본금회전율":        (  [("매출액","+")],   [("자본금","+")]  ),
            "경영자산회전율":        (  [("매출액","+")],   [("경영자산","+")]  ),
            "비유동자산회전율":        (  [("매출액","+")],   [("비유동자산","+")]  ),
            "유형자산회전율":        (  [("매출액","+")],   [("유형자산","+")]  ),
            "재고자산회전율":        (  [("매출액","+")],   [("재고자산","+")]  ),
            "상(제)품회전율":        (  [("매출액","+")],   [("상품","+"),("제품","+")]  ),
            "매출채권회전":        (  [("매출액","+")],   [("매출채권","+")]  ),
        }
        fomula2 = {
            #성장성
            "총자산증가율": "자산총계",
            "유형자산증가율":  "유형자산",
            "유동자산증가율":   "유동자산",
            "자기자본증가율":  "자본총계",
            "매출액증가율": "매출액"
        }
        
        
        info_dict = {}

        year = int(self.current_year)
        if int(self.month) <= 3:
            year -= 1
        
 
        value_f2 = self._calculate_fomula2(bdf,idf,fomula2)
        info_dict.update(value_f2)
 

        for key,val in fomula.items():
            to_key = key
            to_val = {}
            
            #분자/분모 리스트
            numerator = val[0] ; nv = ""
            denominator = val[1]; dv = ""
            if len(numerator) > 1:
                for v in numerator:
                    nv += f"{v[0]}{v[1]}"
            if len(denominator) > 1:
                for v in denominator:
                    dv += f"{v[0]}{v[1]}"
            
            #실제값 계산
            #data
            try:
                real_value = self._calculate_ratio(year,bdf,idf,val[0],val[1])
                if len(real_value) != 0:
                    to_val["분자"] = real_value[0]
                    to_val["분모"] = real_value[1]
                else:
                    to_val["분자"] = ("Null","Null")
                    to_val["분모"] = ("Null","Null")

                if to_val["분모"][1] == "Null" or to_val["분자"][1] == "Null":
                    data = "NULL"
                else:
                    data = self.format(int(to_val["분자"][1]) / int(to_val["분모"][1]) * 100)
                to_val["data"] = data
                


            except Exception as e:
                # Debuger.printc(f"실제값계산-data : {e}{key}")
                to_val["분자"] = ("Null","Null")
                to_val["분모"] = ("Null","Null")
                to_val["data"] = "Null"
                pass

            #시계열평균
            try:
                real_value = self._calculate_ma(bdf,idf,val[0],val[1])
                if len(real_value) == 0:
                    to_val["시계열평균분자"] = "NULL"
                    to_val["시계열평균분모"] = "NULL"
                else:
                    to_val["시계열평균분자"] = self.format(real_value[0])
                    to_val["시계열평균분모"] = self.format(real_value[1])
            except Exception as e:
                Debuger.printc(f"시계열평균-data : {e}")

            info_dict[to_key] = to_val
            
        return info_dict

    #계산하고 db에 넣기

    def save_stability(self,market = "KOSPI"):
        marketdf = self.data_controller.read_table("market","company")
        ticker_list  = marketdf["티커"].tolist()

        # ticker_list = ["005930"]
        for ticker in progress(ticker_list,"계산중"):
            try:
                tickerb = ticker + "B"
                tickeri = ticker + "I"
                bdf = self.data_controller.read_table("extracted",tickerb)
                idf = self.data_controller.read_table("extracted",tickeri)
                _res = self._calculate_stability(bdf,idf)
                res = {}
                # for k,v in _res.items():
                #     print(k,v)
                for key,val in _res.items():
                    res["항목"] = key
                    res["데이터분자"] = val["분자"][0]
                    res["데이터분자값"] = str(val["분자"][1])
                    res["데이터분모"] = val["분모"][0]
                    res["데이터분모값"] = str(val["분모"][1])
                    res["데이터"] = str(val["data"])
                    res["시계열평균분자"] = str(val["시계열평균분자"])
                    res["시계열평균분모"] = str(val["시계열평균분모"])
                    df = pd.DataFrame(res,index=[0])
                    self.data_controller.create_table_set_key(df,"calculation",ticker,"항목")

            except Exception as e:
                Debuger.printc(f"실패 : {e} {key}")

def _test():
    cal = ReportCalculator()
    cal.save_stability()

if __name__ == "__main__":
    _test()