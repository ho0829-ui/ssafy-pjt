from django.contrib import admin

from .models import Archive, Book


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'publisher', 'bestseller_rank', 'isbn13')
    list_filter = ('publisher',)
    search_fields = ('title', 'author', 'isbn13')


@admin.register(Archive)
class ArchiveAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'created_at')
    raw_id_fields = ('book',)
