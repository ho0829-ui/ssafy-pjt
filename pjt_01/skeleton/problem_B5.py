import json  # JSON 파일을 처리하기 위한 라이브러리
from pathlib import Path  # 파일 경로를 처리하기 위한 라이브러리
from pprint import pprint as print

# 1. 파일 경로 설정 (books_500.json 사용)
file_path = Path('./data/books_500.json')  # 파일 경로 설정 부분

# 파일 존재 여부 확인
if file_path.exists():  # 파일이 존재할 경우
    # 2. 파일 열기
    with file_path.open('r', encoding='utf-8') as file:  # 파일을 열고 JSON 데이터를 읽는 코드 (파일 열기, json.load 사용)
        books = json.load(file)

    # 3. 할인율 계산 함수 정의
    def calculate_discount_rate(book):
        """할인율을 계산하는 함수"""
        discount = float(((book['priceStandard'] - book['priceSales']) / book['priceStandard']) * 100) # 할인율 계산 (book['priceStandard']와 book['priceSales'] 사용)
        return discount

    for book in books:
        book['discount_rate'] = calculate_discount_rate(book)

    # 4. 할인율을 기준으로 도서 정렬 (hint: sorted 함수 key 속성)
    discounted_books =  sorted(books, key=lambda book: book['discount_rate'], reverse=True)

    # 5. 상위 5개 도서 선택
    top_discounted = discounted_books[:5]

    # 6. 결과 출력
    print("할인율 상위 5개 도서:")
    for book in top_discounted:
        print(f"{book['title']} - 할인율: {book['discount_rate']:.2f}%")  # 도서 제목과 할인율 출력 (print(f"{book['title']} - 할인율: {discount_rate:.2f}%"))

else:
    print(f"파일이 존재하지 않습니다: {file_path}")
