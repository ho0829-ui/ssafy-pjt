"""알라딘에서 도서를 가져와 DB에 저장한다.

    python manage.py import_books            # 베스트셀러 12권 + 쓰레드에 나오는 책
    python manage.py import_books --count 20 # 베스트셀러 20권

가져온 뒤 fixture로 남겨 두면 키 없이도 같은 데이터를 쓸 수 있다.
    python manage.py dumpdata books.Book --indent 2 -o books/fixtures/books.json
"""

from django.core.management.base import BaseCommand, CommandError

from books import aladin
from books.models import Book
from books.services import save_book

# 메인 페이지 인기 쓰레드 카드에 등장하는 책 (5단계에서 Thread 모델로 대체)
FEATURED_ISBNS = [
    '9788936434120',  # 소년이 온다
    '9788936434595',  # 채식주의자 (리마스터판)
    '9788936439651',  # 대온실 수리 보고서
    '9788937473401',  # 급류
    '9788937434488',  # 노르웨이의 숲
    '9791130662596',  # 시간의 계곡
]


class Command(BaseCommand):
    help = '알라딘 베스트셀러와 지정한 도서를 상세 정보까지 가져와 저장합니다.'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=12, help='가져올 베스트셀러 수 (기본 12)')

    def handle(self, *args, count, **options):
        try:
            ranked = aladin.bestsellers(count)
        except aladin.AladinError as error:
            raise CommandError(error)

        # 순위는 매번 새로 매긴다 (지난번 베스트셀러였던 책은 순위만 지워지고 데이터는 남음)
        Book.objects.update(bestseller_rank=None)

        targets = [(item.get('isbn13'), rank) for rank, item in enumerate(ranked, start=1)]
        targets += [(isbn, None) for isbn in FEATURED_ISBNS]

        saved = 0
        for isbn13, rank in targets:
            if not isbn13:
                continue
            try:
                # 목록 API에는 부제·쪽수·평점이 없어서 ISBN으로 한 번 더 상세 조회한다
                item = aladin.lookup(isbn13)
            except aladin.AladinError as error:
                self.stderr.write(f'  건너뜀 {isbn13}: {error}')
                continue
            extra = {'bestseller_rank': rank} if rank else {}
            book = item and save_book(item, **extra)
            if book:
                saved += 1
                label = f'{rank:>2}위' if rank else ' 추가'
                self.stdout.write(f'  {label}  {book.title} ({book.author_display})')

        self.stdout.write(self.style.SUCCESS(f'{saved}권 저장 완료 (전체 {Book.objects.count()}권)'))
