import re

from django.conf import settings
from django.db import models


class Book(models.Model):
    """알라딘 Open API에서 가져와 저장한 도서.

    페이지를 그릴 때는 알라딘을 호출하지 않고 이 테이블만 읽는다.
    (빠르고, API 키가 만료돼도 그대로 동작)
    """

    isbn13 = models.CharField('ISBN13', max_length=13, unique=True)
    title = models.CharField('제목', max_length=255)
    subtitle = models.CharField('부제', max_length=255, blank=True)
    author = models.CharField('저자', max_length=255)  # 예: "한강 (지은이)"
    publisher = models.CharField('출판사', max_length=100, blank=True)
    pub_date = models.DateField('출간일', null=True, blank=True)
    description = models.TextField('소개', blank=True)
    cover_url = models.URLField('표지 URL', max_length=500)
    category_name = models.CharField('카테고리', max_length=255, blank=True)
    price_sales = models.PositiveIntegerField('판매가', null=True, blank=True)
    page_count = models.PositiveIntegerField('쪽수', null=True, blank=True)
    rating_score = models.DecimalField('평점', max_digits=3, decimal_places=1, null=True, blank=True)
    rating_count = models.PositiveIntegerField('평점 참여 수', null=True, blank=True)
    aladin_link = models.URLField('알라딘 상품 링크', max_length=500, blank=True)
    bestseller_rank = models.PositiveIntegerField('베스트셀러 순위', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['bestseller_rank', 'title']

    def __str__(self):
        return self.title

    ROLE_SUFFIX = {'지은이': '지음', '옮긴이': '옮김', '엮은이': '엮음', '그림': '그림'}

    def _people(self):
        """"하루키 (지은이), 양억관 (옮긴이)" → [("하루키", "지은이"), ("양억관", "옮긴이")]."""
        people = []
        for part in self.author.split(','):
            part = part.strip()
            if not part:
                continue
            match = re.match(r'^(.*?)\s*\(([^)]*)\)$', part)
            people.append((match.group(1), match.group(2)) if match else (part, ''))
        return people

    @property
    def main_author(self):
        """카드용 짧은 저자: "한강", "김난도 외 12명"."""
        writers = [name for name, role in self._people() if role in ('지은이', '')]
        if not writers:
            return self.author
        return writers[0] + (f' 외 {len(writers) - 1}명' if len(writers) > 1 else '')

    @property
    def author_display(self):
        """상세용 저자: "한강 지음", "무라카미 하루키 지음 · 양억관 옮김"."""
        people = self._people()
        writers = [name for name, role in people if role in ('지은이', '')]
        result = []
        if writers:
            names = writers[0] + (f' 외 {len(writers) - 1}명' if len(writers) > 1 else '')
            result.append(f'{names} 지음')
        for name, role in people:
            if role and role != '지은이':
                result.append(f"{name} {self.ROLE_SUFFIX.get(role, role)}")
        return ' · '.join(result)

    @property
    def category_short(self):
        """"국내도서>소설/시/희곡>한국소설>2000년대 이후 한국소설" → "한국소설"."""
        parts = [p for p in self.category_name.split('>') if p]
        if len(parts) >= 3:
            return parts[2]
        return parts[-1] if parts else ''


class Archive(models.Model):
    """사용자가 '담기'한 책. 담은 날짜가 있어야 마이페이지에서 최근 담은 순으로 보여줄 수 있다."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='archives', verbose_name='사용자')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='archives', verbose_name='도서')
    created_at = models.DateTimeField('담은 날짜', auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'book'], name='unique_archive'),  # 같은 책은 한 번만
        ]

    def __str__(self):
        return f'{self.user} → {self.book}'
