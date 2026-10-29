from django.contrib import admin

from .models import AIRecommendation


@admin.register(AIRecommendation)
class AIRecommendationAdmin(admin.ModelAdmin):
    list_display = ('query', 'keywords', 'created_at')
    search_fields = ('query',)
