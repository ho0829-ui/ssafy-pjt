from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.ThreadLoginView.as_view(), name='login'),
    path('logout/', views.ThreadLogoutView.as_view(), name='logout'),
]
