import json  # JSON 파일을 처리하기 위한 라이브러리
from pathlib import Path  # 파일 경로를 처리하기 위한 라이브러리
from collections import defaultdict

# 1. 파일 경로 설정 (books_500.json 사용)
file_path = Path('./data/books_500.json')  # 파일 경로 설정 부분

# 파일 존재 여부 확인
if file_path.exists():  # 파일이 존재할 경우
    # 2. 파일 열기
    with file_path.open('r', encoding='utf-8') as file:  # 파일을 열고 JSON 데이터를 읽는 코드 (파일 열기, json.load 사용)
        books = json.load(file)

    # 3. 카테고리별 통계 집계
    category_stats = {}  # 카테고리별 통계를 저장할 딕셔너리
    category_stats = defaultdict(lambda: {'count': 0, 'sum': 0})

    for book in books:
        category = book['categoryName']
        price = book['priceSales']

        category_stats[category]['count'] += 1  # 카테고리별로 도서 수와 가격을 집계하는 코드
        category_stats[category]['sum'] += price
        

    # 4. 결과 출력
    print("카테고리별 도서 통계:")
    for category, stats in category_stats.items():  # 각 카테고리별 통계 출력
        avg = stats['sum'] / stats['count']  
        print(f'{category}: {stats["count"]}권, 평균가격 {avg:,.2f}원')  # 도서 수와 평균 가격을 출력하는 코드
else:
    print(f"파일이 존재하지 않습니다: {file_path}")
