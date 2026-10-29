from django.urls import path

from . import mypage

app_name = 'mypage'

urlpatterns = [
    path('', mypage.mypage, name='index'),
    path('nickname/', mypage.update_nickname, name='nickname'),
    path('password/', mypage.update_password, name='password'),
    path('delete/', mypage.delete_account, name='delete'),
]
