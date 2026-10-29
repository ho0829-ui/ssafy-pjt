from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import urlencode
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from books.models import Book

from .forms import ThreadForm
from .models import Thread

PER_PAGE = 12
SORT_LABELS = {'latest': '최신순', 'popular': '인기순'}


def with_like_count(queryset):
    return queryset.select_related('author', 'book').annotate(like_count=Count('likes', distinct=True))


def popular_threads(limit=6):
    """메인 "지금 이 쓰레드": 최근 30일 좋아요 많은 순. 부족하면 기간 상관없이 채운다."""
    base = with_like_count(Thread.objects.all()).order_by('-like_count', '-created_at')
    recent = list(base.filter(created_at__gte=timezone.now() - timedelta(days=30))[:limit])
    if len(recent) < limit:
        seen = {thread.pk for thread in recent}
        recent += [t for t in base.exclude(pk__in=seen)[:limit - len(recent)]]
    return recent


def thread_list(request):
    sort = request.GET.get('sort', 'latest')
    if sort not in SORT_LABELS:
        sort = 'latest'
    threads = with_like_count(Thread.objects.all())
    book = None
    if isbn13 := request.GET.get('book'):
        book = get_object_or_404(Book, isbn13=isbn13)
        threads = threads.filter(book=book)
    threads = threads.order_by('-like_count', '-created_at') if sort == 'popular' else threads.order_by('-created_at')
    page = Paginator(threads, PER_PAGE).get_page(request.GET.get('page'))
    return render(request, 'threads/list.html', {
        'page': page, 'sort': sort, 'sorts': SORT_LABELS, 'book': book,
    })


@ensure_csrf_cookie  # 로그아웃 상태에도 좋아요 fetch가 CSRF 토큰을 쓸 수 있도록 쿠키를 심는다
def thread_detail(request, pk):
    thread = get_object_or_404(with_like_count(Thread.objects.all()), pk=pk)
    liked = request.user.is_authenticated and thread.likes.filter(pk=request.user.pk).exists()
    more = with_like_count(thread.book.threads.exclude(pk=thread.pk))[:3]
    return render(request, 'threads/detail.html', {'thread': thread, 'liked': liked, 'more_threads': more})


@login_required
def thread_create(request):
    # 쓰레드는 항상 책 한 권에 대해 쓴다: ?book=<isbn13> 이 없으면 책부터 고르게 한다
    book = Book.objects.filter(isbn13=request.GET.get('book') or request.POST.get('book')).first()
    if book is None:
        messages.info(request, '어떤 책에 대한 쓰레드인지 먼저 골라 주세요.')
        return redirect('books:search')

    form = ThreadForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        thread = form.save(commit=False)
        thread.author = request.user
        thread.book = book
        thread.save()
        messages.success(request, '쓰레드를 올렸어요.')
        return redirect(thread)
    return render(request, 'threads/form.html', {'form': form, 'book': book, 'is_edit': False})


def _own_thread(request, pk):
    """작성자 본인의 쓰레드만 돌려준다. 버튼을 숨기는 것과 별개로 서버에서 다시 확인한다."""
    thread = get_object_or_404(Thread.objects.select_related('book'), pk=pk)
    if thread.author_id != request.user.pk:
        raise PermissionDenied('작성자만 수정·삭제할 수 있어요.')
    return thread


@login_required
def thread_update(request, pk):
    thread = _own_thread(request, pk)
    form = ThreadForm(request.POST or None, request.FILES or None, instance=thread)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, '쓰레드를 수정했어요.')
        return redirect(thread)
    return render(request, 'threads/form.html', {'form': form, 'book': thread.book, 'is_edit': True, 'thread': thread})


@login_required
@require_POST
def thread_delete(request, pk):
    thread = _own_thread(request, pk)
    book = thread.book
    thread.delete()
    messages.info(request, '쓰레드를 삭제했어요.')
    return redirect('books:detail', isbn13=book.isbn13)


@require_POST
def thread_like(request, pk):
    """좋아요 토글 (fetch로 호출, JSON 응답). 로그인하지 않았으면 401과 로그인 주소를 돌려준다."""
    if not request.user.is_authenticated:
        login_url = f"{reverse('accounts:login')}?{urlencode({'next': reverse('threads:detail', args=[pk])})}"
        return JsonResponse({'login_url': login_url}, status=401)
    thread = get_object_or_404(Thread, pk=pk)
    if thread.likes.filter(pk=request.user.pk).exists():
        thread.likes.remove(request.user)
        liked = False
    else:
        thread.likes.add(request.user)
        liked = True
    return JsonResponse({'liked': liked, 'count': thread.likes.count()})
