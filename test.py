import FinanceDataReader as fdr

# KRX 상장종목 전체 정보 가져오기
df = fdr.StockListing('KRX')

# 데이터 확인
print(df.head())

# 특정 기업 예: 삼성전자
company_name = '삼성전자'
company_info = df[df['Name'] == company_name]

if not company_info.empty:
    listing_date = company_info.iloc[0]['ListingDate']
    print(f"{company_name} 상장일: {listing_date}")
else:
    print(f"{company_name} 정보가 없습니다.")