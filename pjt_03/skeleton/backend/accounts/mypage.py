"""마이페이지: 담은 책 · 내 쓰레드 · 좋아요한 쓰레드 · 설정 (탭은 ?tab= 주소로 나눈다)."""

from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from books.models import Archive
from threads.models import Thread
from threads.views import with_like_count

from .forms import DeleteAccountForm, NicknameForm, StyledPasswordChangeForm
from .models import User

TABS = {'books': '담은 책', 'threads': '내 쓰레드', 'likes': '좋아요한 쓰레드', 'settings': '설정'}


def _stats(user):
    return {
        'archives': user.archives.count(),
        'threads': user.threads.count(),
        # 내가 쓴 쓰레드들이 받은 좋아요 합계
        'likes_received': Thread.likes.through.objects.filter(thread__author=user).count(),
    }


def _render(request, tab, **forms):
    user = request.user
    context = {'tab': tab, 'tabs': TABS, 'stats': _stats(user)}
    page_number = request.GET.get('page')
    if tab == 'books':
        archives = Archive.objects.filter(user=user).select_related('book')
        context['page'] = Paginator(archives, 24).get_page(page_number)
    elif tab == 'threads':
        context['page'] = Paginator(with_like_count(user.threads.all()), 12).get_page(page_number)
    elif tab == 'likes':
        liked = with_like_count(user.liked_threads.all()).order_by('-created_at')
        context['page'] = Paginator(liked, 12).get_page(page_number)
    else:
        # 폼 인스턴스에는 request.user 대신 복사본을 넘긴다.
        # (잘못된 닉네임으로 검증이 실패해도 화면의 Navbar 닉네임이 바뀌지 않도록)
        context.update(
            nickname_form=forms.get('nickname_form') or NicknameForm(instance=User.objects.get(pk=user.pk)),
            password_form=forms.get('password_form') or StyledPasswordChangeForm(user),
            delete_form=forms.get('delete_form') or DeleteAccountForm(user),
        )
    return render(request, 'accounts/mypage.html', context)


@login_required
def mypage(request):
    tab = request.GET.get('tab', 'books')
    return _render(request, tab if tab in TABS else 'books')


@login_required
@require_POST
def update_nickname(request):
    form = NicknameForm(request.POST, instance=User.objects.get(pk=request.user.pk))
    if form.is_valid():
        form.save()
        messages.success(request, f'닉네임을 바꿨어요: {form.instance.nickname}')
        return redirect(f"{reverse('mypage:index')}?tab=settings")
    return _render(request, 'settings', nickname_form=form)


@login_required
@require_POST
def update_password(request):
    form = StyledPasswordChangeForm(request.user, request.POST)
    if form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)  # 비밀번호를 바꿔도 로그인 유지
        messages.success(request, '비밀번호를 바꿨어요.')
        return redirect(f"{reverse('mypage:index')}?tab=settings")
    return _render(request, 'settings', password_form=form)


@login_required
@require_POST
def delete_account(request):
    form = DeleteAccountForm(request.user, request.POST)
    if form.is_valid():
        user = request.user
        logout(request)
        user.delete()  # 쓰레드·좋아요·담은 책도 함께 삭제 (쓰레드 이미지 파일은 post_delete 신호가 정리)
        messages.info(request, '탈퇴했어요. 그동안 함께해 주셔서 고마워요.')
        return redirect('books:index')
    return _render(request, 'settings', delete_form=form)
