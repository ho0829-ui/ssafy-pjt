from django.contrib import admin

from .models import Thread


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'book', 'like_count', 'created_at')
    search_fields = ('title', 'content', 'author__nickname', 'book__title')
    raw_id_fields = ('book',)  # 도서가 많아 선택 상자 대신 ID 입력
    filter_horizontal = ('likes',)

    @admin.display(description='좋아요')
    def like_count(self, obj):
        return obj.likes.count()
