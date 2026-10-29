from django.urls import path

from . import views

app_name = 'threads'

urlpatterns = [
    path('', views.thread_list, name='list'),
    path('new/', views.thread_create, name='create'),
    path('<int:pk>/', views.thread_detail, name='detail'),
    path('<int:pk>/edit/', views.thread_update, name='update'),
    path('<int:pk>/delete/', views.thread_delete, name='delete'),
    path('<int:pk>/like/', views.thread_like, name='like'),
]
