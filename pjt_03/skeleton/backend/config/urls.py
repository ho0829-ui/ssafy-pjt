from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('mypage/', include('accounts.mypage_urls')),
    path('threads/', include('threads.urls')),
    path('recommend/', include('recommend.urls')),
    path('', include('books.urls')),
]

# 개발 서버에서만 업로드 파일 제공 (배포 시에는 웹 서버가 담당)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
