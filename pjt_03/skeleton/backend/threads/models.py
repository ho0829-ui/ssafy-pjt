from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.urls import reverse

from books.models import Book


class Thread(models.Model):
    """책 한 권에 대해 남기는 글."""

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='threads', verbose_name='작성자')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='threads', verbose_name='도서')
    title = models.CharField('제목', max_length=60)
    content = models.TextField('내용', max_length=2000)
    image = models.ImageField('이미지', upload_to='threads/%Y/%m/', blank=True)
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='liked_threads',
                                   blank=True, verbose_name='좋아요')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('threads:detail', args=[self.pk])

    def save(self, *args, **kwargs):
        # 이미지를 바꾸거나 지웠으면 예전 파일을 저장소에서 지운다 (media 폴더에 고아 파일이 쌓이지 않도록)
        old_image = None
        if self.pk:
            old_image = Thread.objects.filter(pk=self.pk).values_list('image', flat=True).first()
        super().save(*args, **kwargs)
        if old_image and old_image != self.image.name:
            self.image.storage.delete(old_image)


@receiver(post_delete, sender=Thread)
def delete_thread_image(sender, instance, **kwargs):
    """쓰레드가 지워지면 이미지 파일도 지운다.

    model.delete()를 덮어쓰면 사용자·도서 삭제로 함께 지워지는 경우(CASCADE)나
    QuerySet.delete()에서는 호출되지 않아서, 모든 삭제에서 실행되는 신호를 쓴다.
    """
    if instance.image:
        instance.image.storage.delete(instance.image.name)
