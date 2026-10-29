from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import LoginForm, SignUpForm


def _safe_next(request, default='books:index'):
    """?next= 값이 우리 사이트 주소일 때만 그곳으로, 아니면 기본 페이지로 (외부 사이트로 튕기기 방지)."""
    target = request.POST.get('next') or request.GET.get('next')
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()},
                                                  require_https=request.is_secure()):
        return target
    return default


def signup(request):
    if request.user.is_authenticated:
        return redirect('books:index')

    form = SignUpForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)  # 가입과 동시에 로그인
        messages.success(request, f'{user.nickname} 님, 가입을 환영해요!')
        return redirect(_safe_next(request))
    return render(request, 'accounts/signup.html', {'form': form, 'next': _safe_next(request, '')})


class ThreadLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        if not form.cleaned_data.get('remember_me'):
            self.request.session.set_expiry(0)  # 브라우저를 닫으면 로그아웃
        messages.success(self.request, f'{self.request.user.nickname} 님, 다시 만나서 반가워요!')
        return response


class ThreadLogoutView(LogoutView):
    """Django 5부터 로그아웃은 POST로만 가능하다 (GET 요청은 405)."""

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        messages.info(request, '로그아웃했어요. 또 만나요!')
        return response
