from datetime import datetime  # 날짜와 시간을 처리하기 위한 라이브러리
import json  # JSON 파일을 처리하기 위한 라이브러리
from pathlib import Path  # 파일 경로를 처리하기 위한 라이브러리

# 월별 책 정보 모아보고 평균 가격 계산하기
# 아래에 전체 코드 작성
file_path = Path('./data/books_2000.json')

def calculate_monthly_average_price():
    if not file_path.exists():
        print(f"오류: '{file_path}' 파일을 찾을 수 없습니다.")
        return

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    items = data.get('item', data) if isinstance(data, dict) else data
    monthly_stats = {}

    for book in items:
        pub_date_str = book.get('pubDate') or book.get('publication_date')
        price = book.get('priceSales') or book.get('price')

        if not pub_date_str or price is None:
            continue

        try:
            clean_date_str = str(pub_date_str).strip()
            if len(clean_date_str) == 8 and clean_date_str.isdigit():
                dt = datetime.strptime(clean_date_str, '%Y%m%d')
            else:
                dt = datetime.strptime(clean_date_str[:10], '%Y-%m-%d')
            
            month_key = dt.strftime('%Y-%m')
            price_val = float(price)

            if month_key not in monthly_stats:
                monthly_stats[month_key] = {'total_price': 0.0, 'count': 0}
            
            monthly_stats[month_key]['total_price'] += price_val
            monthly_stats[month_key]['count'] += 1

        except (ValueError, TypeError):
            continue

    print("=== 월별 도서 평균 가격 결과 ===")
    for month in sorted(monthly_stats.keys()):
        stats = monthly_stats[month]
        avg_price = stats['total_price'] / stats['count'] if stats['count'] > 0 else 0
        print(f"[{month}] 도서 수: {stats['count']}권 / 평균 가격: {avg_price:,.2f}원")

except Exception as e:
    print(f"파일을 처리하는 도중 오류가 발생했습니다: {e}")

if __name__ == '__main__':
    calculate_monthly_average_price() 
