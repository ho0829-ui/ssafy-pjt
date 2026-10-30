from django.contrib import admin

from .models import CrawlResult


@admin.register(CrawlResult)
class CrawlResultAdmin(admin.ModelAdmin):
    list_display = ("id", "keyword", "company_name", "created_at")
    search_fields = ("keyword", "company_name")
