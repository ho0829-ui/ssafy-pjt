from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm

from .models import User


class BootstrapFormMixin:
    """모든 입력칸에 Bootstrap 클래스를 붙이고, 오류가 있는 칸은 빨갛게 표시한다."""

    def apply_bootstrap(self):
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault('class', 'form-check-input')
                continue
            css = 'form-control'
            if self.is_bound and name in self.errors:
                css += ' is-invalid'
            field.widget.attrs['class'] = css
            field.widget.attrs.setdefault('placeholder', field.label)


class SignUpForm(BootstrapFormMixin, UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'nickname')
        labels = {'username': '아이디', 'nickname': '닉네임'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].label = '비밀번호'
        self.fields['password2'].label = '비밀번호 확인'
        self.fields['password2'].help_text = ''
        self.fields['username'].widget.attrs.update(autocomplete='username', autofocus=True)
        self.fields['nickname'].widget.attrs.update(autocomplete='nickname')
        self.apply_bootstrap()

    def full_clean(self):
        super().full_clean()
        self.apply_bootstrap()  # 검증 후 오류 칸에 is-invalid 반영


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    remember_me = forms.BooleanField(label='로그인 상태 유지', required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = '아이디'
        self.fields['password'].label = '비밀번호'
        self.apply_bootstrap()

    def full_clean(self):
        super().full_clean()
        self.apply_bootstrap()


# ---------------------------------------------------------------------------
# 마이페이지 설정
# ---------------------------------------------------------------------------

class NicknameForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ('nickname',)
        labels = {'nickname': '닉네임'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()

    def full_clean(self):
        super().full_clean()
        self.apply_bootstrap()


class StyledPasswordChangeForm(BootstrapFormMixin, PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].label = '현재 비밀번호'
        self.fields['new_password1'].label = '새 비밀번호'
        self.fields['new_password2'].label = '새 비밀번호 확인'
        self.fields['old_password'].widget.attrs.pop('autofocus', None)  # 설정 탭의 다른 폼과 포커스 경쟁 방지
        self.apply_bootstrap()

    def full_clean(self):
        super().full_clean()
        self.apply_bootstrap()


class DeleteAccountForm(BootstrapFormMixin, forms.Form):
    password = forms.CharField(label='현재 비밀번호', widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}))

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()

    def clean_password(self):
        password = self.cleaned_data['password']
        if not self.user.check_password(password):
            raise forms.ValidationError('비밀번호가 맞지 않아요.')
        return password

    def full_clean(self):
        super().full_clean()
        self.apply_bootstrap()
