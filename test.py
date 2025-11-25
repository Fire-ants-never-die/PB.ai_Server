import pandas as pd

data = {
    "year" : ["2024Q4","2023Q3","2024m"],
    "자산": [100, 20, 15],
    "채권": [30, 25, 18],
    "mola": [44, 30, 22]
}
df = pd.DataFrame(data)
print(df)

def df_to_text_chunks(df,company_name,table_name):
    chunks = []
    _type = "재무상태표"
    if table_name[-1] == "I":
        _type = "손익계산서"
    
    common_text = f"[회사명: {company_name}] {_type}"

    for idx, row in df.iterrows():
        text = common_text
        year = ""; property = ""; 
        property_text = ""; data_text = ""
        for col,val in row.items():
            if col == "year":
                year = val[0:4]
                property = val[4:]
                if property[0] == 'Q':
                    property_text += f"{year} {property[1]}분기"
                else:
                    property_text += f"{year} 3년 시계열평균"
            else:
                data_text += f" {col} : {val}"
        text += property_text
        text += data_text
        chunks.append(text)
    return chunks

list = df_to_text_chunks(df,"samsung","005930Q4I")
print("size : ",len(list))

for i in list:
    print(i)     