"""알라딘 응답을 Book 모델로 저장하고, 검색·장르 결과를 만드는 로직."""

import hashlib
import html
import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date

from django.core.cache import cache
from django.db.models import F, Q

from . import aladin
from .models import Book

PER_PAGE = 20
CACHE_SECONDS = 60 * 60 * 24  # 같은 검색은 하루 동안 알라딘을 다시 부르지 않는다


def _parse_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def is_valid_isbn13(value):
    """978/979로 시작하고 체크 숫자가 맞는 13자리 ISBN인지 확인."""
    if not (value and len(value) == 13 and value.isdigit() and value[:3] in ('978', '979')):
        return False
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(value[:12]))
    return (10 - total % 10) % 10 == int(value[12])


def save_book(item, **extra):
    """알라딘 item(dict) 하나를 ISBN13 기준으로 저장(있으면 갱신)하고 Book을 돌려준다.

    세트 상품(ISBN 없음), 중고 매물처럼 정식 도서가 아닌 항목은 저장하지 않고 None을 돌려준다.
    """
    isbn13 = item.get('isbn13')
    if not is_valid_isbn13(isbn13) or item.get('mallType') == 'USED':
        return None

    sub = item.get('subInfo') or {}
    rating = sub.get('ratingInfo') or {}
    fields = {
        # 알라딘 응답에는 &amp; 같은 HTML 엔티티가 섞여 있어 원래 문자로 되돌린다
        'title': _main_title(item.get('title')),
        'subtitle': html.unescape(sub.get('subTitle') or ''),
        'author': html.unescape(item.get('author', '')),
        'publisher': html.unescape(item.get('publisher', '')),
        'pub_date': _parse_date(item.get('pubDate')),
        'description': html.unescape(item.get('description', '')),
        'cover_url': item.get('cover', ''),
        'category_name': item.get('categoryName', ''),
        'price_sales': item.get('priceSales') or None,
        'page_count': sub.get('itemPage') or None,
        'rating_score': rating.get('ratingScore') or None,
        'rating_count': rating.get('ratingCount') or None,
        'aladin_link': html.unescape(item.get('link', '')),
    }
    # 목록 API에는 subInfo가 없으므로, 빈 값으로 기존 상세 정보를 덮어쓰지 않는다
    fields = {k: v for k, v in fields.items() if v not in ('', None)}
    fields.update(extra)
    book, _ = Book.objects.update_or_create(isbn13=isbn13, defaults=fields)
    return book


# ---------------------------------------------------------------------------
# 검색 · 장르 목록
# ---------------------------------------------------------------------------

@dataclass
class BookPage:
    """검색·장르 결과 한 페이지."""
    books: list = field(default_factory=list)
    total: int = 0
    page: int = 1
    num_pages: int = 1
    from_db: bool = False  # True면 알라딘 대신 저장된 도서에서 찾은 결과
    scanned: int = 0  # 범위 검색일 때 걸러내기 전에 훑어본 알라딘 결과 수 (0이면 범위 검색 아님)


def _num_pages(total):
    return max(1, math.ceil(min(total, aladin.MAX_RESULTS) / PER_PAGE))


def _cached_aladin_page(cache_key, fetch):
    """알라딘 결과(ISBN 순서 + 전체 건수)를 캐시하고, 책은 DB에서 그 순서대로 꺼낸다.

    캐시에는 모델 대신 ISBN 목록만 넣는다. (책 정보는 DB가 원본)
    """
    cached = cache.get(cache_key)
    if cached is None:
        items, total = fetch()  # 실패하면 AladinError가 그대로 올라간다
        isbns = [book.isbn13 for book in (save_book(item) for item in items) if book]
        cached = {'isbns': isbns, 'total': total}
        cache.set(cache_key, cached, CACHE_SECONDS)
    books_by_isbn = Book.objects.in_bulk(cached['isbns'], field_name='isbn13')
    books = [books_by_isbn[isbn] for isbn in cached['isbns'] if isbn in books_by_isbn]
    return books, cached['total']


def _db_page(queryset, page):
    total = queryset.count()
    page = min(page, _num_pages(total))
    start = (page - 1) * PER_PAGE
    return BookPage(list(queryset[start:start + PER_PAGE]), total, page, _num_pages(total), from_db=True)


SCOPE_FIELDS = {'title': ['title'], 'author': ['author'], 'publisher': ['publisher']}


def _main_title(raw_title):
    """알라딘 title "작별하지 않는다 - 2024 노벨문학상 수상작가 한강 장편소설" → "작별하지 않는다".

    save_book이 화면에 보여주는 제목과 같은 기준이다.
    """
    return html.unescape(raw_title or '').split(' - ')[0]


def _compact(text):
    """비교용: 대소문자·띄어쓰기 무시 ("노르웨이의숲" == "노르웨이의 숲")."""
    return ''.join(html.unescape(text or '').split()).lower()


def _scoped_search(query, query_type, sort, page):
    """제목·저자·출판사 범위 검색.

    알라딘은 범위(QueryType)를 무시하므로, 관련도 상위 200권(50권 × 4번, 동시에 호출)을 받아
    해당 필드에 검색어가 들어간 책만 직접 걸러낸다. 걸러낸 ISBN 목록은 하루 동안 캐시한다.
    """
    digest = hashlib.md5(f'{query}|{query_type}|{sort}'.encode()).hexdigest()
    cache_key = f'aladin:scoped:{digest}'
    cached = cache.get(cache_key)
    if cached is None:
        calls = aladin.MAX_RESULTS // aladin.MAX_PAGE_SIZE
        with ThreadPoolExecutor(max_workers=calls) as pool:
            pages = list(pool.map(
                lambda n: aladin.search(query, 'all', sort, n, aladin.MAX_PAGE_SIZE), range(1, calls + 1)
            ))  # 하나라도 실패하면 AladinError가 올라가 DB 검색으로 넘어간다
        items = [item for page_items, _ in pages for item in page_items]
        needle = _compact(query)
        fields = SCOPE_FIELDS[query_type]
        def field_text(item, name):
            return _main_title(item.get(name)) if name == 'title' else item.get(name)

        matched = [item for item in items if any(needle in _compact(field_text(item, f)) for f in fields)]
        isbns = list(dict.fromkeys(  # 순서 유지 중복 제거
            book.isbn13 for book in (save_book(item) for item in matched) if book
        ))
        cached = {'isbns': isbns, 'scanned': len(items)}
        cache.set(cache_key, cached, CACHE_SECONDS)

    total = len(cached['isbns'])
    num_pages = max(1, math.ceil(total / PER_PAGE))
    page = min(page, num_pages)
    page_isbns = cached['isbns'][(page - 1) * PER_PAGE:page * PER_PAGE]
    books_by_isbn = Book.objects.in_bulk(page_isbns, field_name='isbn13')
    books = [books_by_isbn[isbn] for isbn in page_isbns if isbn in books_by_isbn]
    return BookPage(books, total, page, num_pages, scanned=cached['scanned'])


def search_books(query, query_type='all', sort='accuracy', page=1):
    """도서 검색: 캐시 → 알라딘 → DB 저장. 알라딘을 쓸 수 없으면 DB에서 검색한다."""
    page = max(1, min(page, _num_pages(aladin.MAX_RESULTS)))
    digest = hashlib.md5(f'{query}|{query_type}|{sort}|{page}'.encode()).hexdigest()
    try:
        if query_type in SCOPE_FIELDS:
            return _scoped_search(query, query_type, sort, page)
        books, total = _cached_aladin_page(
            f'aladin:search:{digest}',
            lambda: aladin.search(query, query_type, sort, page, PER_PAGE),
        )
        return BookPage(books, total, page, _num_pages(total))
    except aladin.AladinError:
        fields = {'title': ['title', 'subtitle'], 'author': ['author'], 'publisher': ['publisher']}
        condition = Q()
        for name in fields.get(query_type, ['title', 'subtitle', 'author', 'publisher']):
            condition |= Q(**{f'{name}__icontains': query})
        order = {
            'sales': [F('bestseller_rank').asc(nulls_last=True), 'title'],
            'latest': [F('pub_date').desc(nulls_last=True)],
        }.get(sort, ['title'])
        return _db_page(Book.objects.filter(condition).order_by(*order), page)


def genre_books(genre, page=1):
    """장르(알라딘 카테고리) 베스트셀러. 알라딘을 쓸 수 없으면 DB에서 카테고리 이름으로 찾는다."""
    page = max(1, min(page, _num_pages(aladin.MAX_RESULTS)))
    try:
        books, total = _cached_aladin_page(
            f'aladin:genre:{genre.category_id}:{page}',
            lambda: aladin.category_bestsellers(genre.category_id, page, PER_PAGE),
        )
        return BookPage(books, total, page, _num_pages(total))
    except aladin.AladinError:
        queryset = Book.objects.filter(category_name__icontains=genre.db_keyword).order_by('title')
        return _db_page(queryset, page)


def ensure_details(book):
    """검색 목록으로만 저장돼 쪽수·평점이 빈 책은, 상세 페이지를 처음 열 때 한 번 상세 조회한다.

    알라딘에 정보가 없거나 실패해도 하루에 한 번만 다시 시도한다.
    """
    if book.page_count is not None or book.rating_score is not None:
        return book
    if not cache.add(f'aladin:lookup-tried:{book.isbn13}', True, CACHE_SECONDS):
        return book
    try:
        item = aladin.lookup(book.isbn13)
    except aladin.AladinError:
        return book
    return (item and save_book(item)) or book
