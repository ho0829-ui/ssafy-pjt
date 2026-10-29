from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.http import urlencode
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from threads.views import popular_threads, with_like_count

from . import aladin
from .genres import GENRES, GENRES_BY_SLUG
from .models import Archive, Book
from .services import ensure_details, genre_books, is_valid_isbn13, save_book, search_books

MAX_QUERY_LENGTH = 100
QUERY_TYPE_LABELS = {'all': '전체', 'title': '제목', 'author': '저자', 'publisher': '출판사'}
SORT_LABELS = {'accuracy': '정확도', 'sales': '판매량', 'latest': '최신순'}

def index(request):
    bestsellers = list(
        Book.objects.filter(bestseller_rank__isnull=False).order_by('bestseller_rank')[:12]
    )
    # 캐러셀: 4권씩 한 슬라이드
    slides = [bestsellers[i:i + 4] for i in range(0, len(bestsellers), 4)]

    threads = popular_threads(6)

    ai_examples = ['AI 입문', '번아웃 왔을 때', '여행 가기 전에', '주식 공부 시작']
    return render(request, 'books/index.html', {
        'slides': slides, 'threads': threads, 'genres': GENRES, 'ai_examples': ai_examples,
    })


@ensure_csrf_cookie  # 로그아웃 상태에서도 담기 fetch가 CSRF 토큰을 쓸 수 있도록
def detail(request, isbn13):
    book = Book.objects.filter(isbn13=isbn13).first()
    if book is None:
        # DB에 없는 책이면 (키가 살아 있을 때만) 알라딘에서 찾아 저장한다
        if not is_valid_isbn13(isbn13):
            raise Http404('잘못된 ISBN입니다.')
        try:
            item = aladin.lookup(isbn13)
        except aladin.AladinError:
            item = None
        book = item and save_book(item)
        if book is None:
            raise Http404('도서를 찾을 수 없습니다.')
    else:
        book = ensure_details(book)
    threads = with_like_count(book.threads.all()).order_by('-created_at')
    archived = request.user.is_authenticated and Archive.objects.filter(user=request.user, book=book).exists()
    return render(request, 'books/detail.html', {
        'book': book, 'threads': threads[:5], 'thread_count': threads.count(), 'archived': archived,
    })


@require_POST
def archive_toggle(request, isbn13):
    """담기 토글 (fetch로 호출, JSON 응답). 로그인하지 않았으면 401과 로그인 주소를 돌려준다."""
    if not request.user.is_authenticated:
        next_url = reverse('books:detail', args=[isbn13])
        return JsonResponse({'login_url': f"{reverse('accounts:login')}?{urlencode({'next': next_url})}"}, status=401)
    book = get_object_or_404(Book, isbn13=isbn13)
    archive, created = Archive.objects.get_or_create(user=request.user, book=book)
    if not created:
        archive.delete()
    return JsonResponse({'archived': created})


def _page_number(request):
    try:
        return max(1, int(request.GET.get('page', 1)))
    except ValueError:
        return 1


def _page_range(result, window=2):
    """현재 페이지 주변 번호만 보여준다. 예: 1 … 4 5 [6] 7 8 … 10"""
    first, last = max(1, result.page - window), min(result.num_pages, result.page + window)
    return range(first, last + 1)


def search(request):
    query = request.GET.get('q', '').strip()[:MAX_QUERY_LENGTH]
    query_type = request.GET.get('type', 'all')
    sort = request.GET.get('sort', 'accuracy')
    if query_type not in QUERY_TYPE_LABELS:
        query_type = 'all'
    if sort not in SORT_LABELS:
        sort = 'accuracy'

    context = {
        'query': query, 'query_type': query_type, 'sort': sort,
        'query_type_label': QUERY_TYPE_LABELS[query_type],
        'query_types': QUERY_TYPE_LABELS, 'sorts': SORT_LABELS,
        # 검색어가 없거나 결과가 없을 때 보여줄 추천 검색어
        'suggestions': Book.objects.filter(bestseller_rank__isnull=False)
                                   .order_by('bestseller_rank').values_list('title', flat=True)[:6],
    }
    if query:
        result = search_books(query, query_type, sort, _page_number(request))
        context.update(result=result, page_range=_page_range(result))
    return render(request, 'books/search.html', context)


def genre(request, slug):
    genre = GENRES_BY_SLUG.get(slug)
    if genre is None:
        raise Http404('없는 장르입니다.')
    result = genre_books(genre, _page_number(request))
    return render(request, 'books/search.html', {
        'genre': genre, 'genres': GENRES, 'result': result, 'page_range': _page_range(result),
        'query': '',  # 템플릿의 |highlight:query 인자는 변수가 없으면 오류가 나므로 빈 값으로 넘긴다
    })
