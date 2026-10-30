from django.urls import path

from . import views

app_name = "comments"

urlpatterns = [
    path("", views.index, name="index"),
    path("crawl/", views.crawl_stream, name="crawl"),
    path("results/<int:pk>/", views.result, name="result"),
]
