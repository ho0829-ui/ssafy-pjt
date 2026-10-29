from django.urls import path

from . import views

app_name = 'books'

urlpatterns = [
    path('', views.index, name='index'),
    path('search/', views.search, name='search'),
    path('genres/<slug:slug>/', views.genre, name='genre'),
    path('books/<str:isbn13>/', views.detail, name='detail'),
    path('books/<str:isbn13>/archive/', views.archive_toggle, name='archive'),
]
