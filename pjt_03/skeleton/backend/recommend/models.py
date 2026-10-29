from django.db import models


class AIRecommendation(models.Model):
    """검색어별 AI 추천 결과 (하루 동안 재사용해 GMS 크레딧을 아낀다).

    검색어만으로 만든 결과라 개인정보가 없으므로 모든 사용자가 같은 결과를 공유한다.
    """

    query = models.CharField('검색어(정규화)', max_length=50, unique=True)
    keywords = models.JSONField('알라딘 검색어', default=list)
    summary = models.CharField('한 줄 요약', max_length=200, blank=True)
    picks = models.JSONField('추천 [{isbn13, reason}]', default=list)
    created_at = models.DateTimeField(auto_now=True)  # 다시 만들 때마다 갱신

    class Meta:
        verbose_name = 'AI 추천 결과'

    def __str__(self):
        return self.query
