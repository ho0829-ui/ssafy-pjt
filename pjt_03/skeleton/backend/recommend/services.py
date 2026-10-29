"""검색어 기반 AI 도서 추천.

    "AI" → Claude: 알라딘 검색어 2~3개 → 알라딘 후보(최대 50권) → Claude: 후보 중 3권 + 이유
         → 후보에 있는 ISBN만 통과 → 하루 동안 저장해 같은 검색어에 재사용
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from books import aladin
from books.models import Book
from books.services import save_book, search_books

from . import ai
from .models import AIRecommendation

PICK_COUNT = 3
MAX_CANDIDATES = 50
PER_KEYWORD = 20
CACHE_FOR = timedelta(days=1)
MIN_QUERY, MAX_QUERY = 2, 50


def normalize(query):
    """앞뒤 공백 제거, 연속 공백 하나로, 영문 소문자. ("  AI   입문 " → "ai 입문")"""
    return ' '.join((query or '').split()).lower()


def is_valid_query(query):
    return MIN_QUERY <= len(normalize(query)) <= MAX_QUERY


def cached_result(query):
    """하루 안에 만든 같은 검색어 결과가 있으면 돌려준다 (Claude를 다시 부르지 않음)."""
    record = AIRecommendation.objects.filter(
        query=normalize(query), created_at__gte=timezone.now() - CACHE_FOR,
    ).first()
    return _to_response(record) if record else None


def _candidates(keywords):
    """검색어별 알라딘 결과를 동시에 받고, DB 저장은 한 스레드에서 한다 (SQLite 동시 쓰기 방지)."""
    def fetch(keyword):
        try:
            return aladin.search(keyword, 'all', 'accuracy', 1, PER_KEYWORD)[0]
        except aladin.AladinError:
            return []

    with ThreadPoolExecutor(max_workers=len(keywords)) as pool:
        results = list(pool.map(fetch, keywords))

    books, seen = [], set()
    # 검색어마다 1위, 2위… 순으로 번갈아 담아 한 검색어 결과에 치우치지 않게 한다
    for rank in range(PER_KEYWORD):
        for items in results:
            if rank < len(items):
                book = save_book(items[rank])
                if book and book.isbn13 not in seen:
                    seen.add(book.isbn13)
                    books.append(book)
    if not books:
        # 알라딘을 쓸 수 없으면 저장된 도서에서라도 후보를 찾는다
        for keyword in keywords:
            for book in search_books(keyword).books:
                if book.isbn13 not in seen:
                    seen.add(book.isbn13)
                    books.append(book)
    return books[:MAX_CANDIDATES]


def recommend(query):
    """AI 추천을 새로 만든다. Claude 호출이 실패하면 ai.AIError가 올라간다."""
    keywords = [k.strip() for k in ai.make_keywords(query) if k.strip()][:3] or [query]
    candidates = _candidates(keywords)
    if not candidates:
        raise ai.AIError('추천할 후보 도서를 찾지 못했습니다.')

    result = ai.pick_books(query, candidates)
    allowed = {book.isbn13 for book in candidates}
    picks, used = [], set()
    for pick in result.picks:
        # 후보 목록에 없는 ISBN(지어낸 책)과 중복은 버린다
        if pick.isbn13 in allowed and pick.isbn13 not in used:
            used.add(pick.isbn13)
            picks.append({'isbn13': pick.isbn13, 'reason': pick.reason.strip()[:200]})
    if not picks:
        raise ai.AIError('후보 목록 안에서 고른 책이 없습니다.')

    record, _ = AIRecommendation.objects.update_or_create(
        query=normalize(query),
        defaults={'keywords': keywords, 'summary': result.summary.strip()[:200], 'picks': picks[:PICK_COUNT]},
    )
    return _to_response(record)


def fallback(query):
    """AI를 쓸 수 없을 때: 일반 도서 검색 상위 3권 (AI 추천이 아니라고 화면에 표시)."""
    books = search_books(query).books[:PICK_COUNT]
    return {'query': query, 'ai': False, 'summary': '', 'keywords': [],
            'books': [_book_dict(book, '') for book in books]}


def _book_dict(book, reason):
    return {
        'isbn13': book.isbn13,
        'title': book.title,
        'author': book.main_author,
        'publisher': book.publisher,
        'year': book.pub_date.year if book.pub_date else None,
        'cover_url': book.cover_url,
        'url': reverse('books:detail', args=[book.isbn13]),
        'reason': reason,
    }


def _to_response(record):
    books_by_isbn = Book.objects.in_bulk([p['isbn13'] for p in record.picks], field_name='isbn13')
    books = [_book_dict(books_by_isbn[p['isbn13']], p['reason']) for p in record.picks if p['isbn13'] in books_by_isbn]
    return {'query': record.query, 'ai': True, 'summary': record.summary,
            'keywords': record.keywords, 'books': books}
