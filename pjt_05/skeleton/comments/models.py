from django.db import models


class CrawlResult(models.Model):
    """한 번의 크롤링 요청에 대한 단계별 결과(수집 -> 전처리 -> 증강)를 통합 저장한다."""

    keyword = models.CharField("입력 회사명", max_length=100)
    company_name = models.CharField("실제 종목명", max_length=100)
    raw_comments = models.JSONField("원본 댓글 목록", default=list)
    cleaned_comments = models.JSONField("정제 댓글 목록", default=list)
    augmented_comments = models.JSONField("증강 댓글 목록", default=list)
    # 원본 댓글별 {original, cleaned, augmented, removed_reason} 통합 레코드
    integrated = models.JSONField("통합 데이터", default=list)
    iqr_info = models.JSONField("IQR 임계값 정보", default=dict)
    summary = models.TextField("댓글 요약", blank=True)
    warnings = models.JSONField("처리 경고", default=list)
    created_at = models.DateTimeField("생성 일시", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.company_name} ({self.created_at:%Y-%m-%d %H:%M})"
