import io
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from books.models import Book

from .models import Thread

User = get_user_model()
TEMP_MEDIA = tempfile.mkdtemp()  # 테스트 업로드가 실제 media 폴더에 남지 않도록


def make_image(name='photo.png', size=(40, 40)):
    buffer = io.BytesIO()
    Image.new('RGB', size, 'red').save(buffer, format='PNG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class ThreadTestCase(TestCase):
    fixtures = ['books']

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.book = Book.objects.get(isbn13='9788936434595')
        self.writer = User.objects.create_user('writer', password='pw-123456!', nickname='작가')
        self.other = User.objects.create_user('other', password='pw-123456!', nickname='남')

    def make_thread(self, **kwargs):
        defaults = {'author': self.writer, 'book': self.book, 'title': '읽고 나서', 'content': '정말 좋은 책이었어요. 추천합니다.'}
        defaults.update(kwargs)
        return Thread.objects.create(**defaults)


class CreateTests(ThreadTestCase):
    url = reverse('threads:create')

    def test_login_required(self):
        response = self.client.get(self.url, {'book': self.book.isbn13})
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}%3Fbook%3D{self.book.isbn13}",
                             fetch_redirect_response=False)

    def test_book_required(self):
        self.client.force_login(self.writer)
        self.assertRedirects(self.client.get(self.url), reverse('books:search'))

    def test_create_with_image(self):
        self.client.force_login(self.writer)
        response = self.client.post(self.url, {
            'book': self.book.isbn13, 'title': '첫 쓰레드', 'content': '열 글자가 넘는 내용입니다.', 'image': make_image(),
        })
        thread = Thread.objects.get()
        self.assertRedirects(response, thread.get_absolute_url())
        self.assertEqual((thread.author, thread.book), (self.writer, self.book))
        self.assertTrue(thread.image.name.startswith('threads/'))

    def test_invalid_input(self):
        self.client.force_login(self.writer)
        not_image = SimpleUploadedFile('x.png', b'not an image', content_type='image/png')
        response = self.client.post(self.url, {'book': self.book.isbn13, 'title': 'a', 'content': '짧음', 'image': not_image})
        self.assertEqual(response.status_code, 200)
        errors = response.context['form'].errors
        self.assertEqual(set(errors), {'title', 'content', 'image'})
        self.assertFalse(Thread.objects.exists())


class PermissionTests(ThreadTestCase):
    def test_other_user_cannot_edit_or_delete(self):
        thread = self.make_thread()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse('threads:update', args=[thread.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse('threads:delete', args=[thread.pk])).status_code, 403)
        self.assertTrue(Thread.objects.filter(pk=thread.pk).exists())

    def test_author_can_edit_and_delete(self):
        thread = self.make_thread()
        self.client.force_login(self.writer)
        self.client.post(reverse('threads:update', args=[thread.pk]),
                         {'title': '수정한 제목', 'content': '수정한 내용입니다. 열 글자 이상.'})
        thread.refresh_from_db()
        self.assertEqual(thread.title, '수정한 제목')
        self.assertEqual(self.client.get(reverse('threads:delete', args=[thread.pk])).status_code, 405)  # POST만
        response = self.client.post(reverse('threads:delete', args=[thread.pk]))
        self.assertRedirects(response, reverse('books:detail', args=[self.book.isbn13]))
        self.assertFalse(Thread.objects.exists())

    def test_image_file_removed_on_replace_and_delete(self):
        thread = self.make_thread(image=make_image('a.png'))
        storage, first = thread.image.storage, thread.image.name
        thread.image = make_image('b.png')
        thread.save()
        self.assertFalse(storage.exists(first))
        second = thread.image.name
        thread.delete()
        self.assertFalse(storage.exists(second))


class LikeTests(ThreadTestCase):
    def test_anonymous_gets_401_with_login_url(self):
        thread = self.make_thread()
        response = self.client.post(reverse('threads:like', args=[thread.pk]))
        self.assertEqual(response.status_code, 401)
        self.assertIn(reverse('accounts:login'), response.json()['login_url'])

    def test_toggle_and_no_duplicates(self):
        thread = self.make_thread()
        self.client.force_login(self.other)
        url = reverse('threads:like', args=[thread.pk])
        self.assertEqual(self.client.post(url).json(), {'liked': True, 'count': 1})
        self.assertEqual(self.client.post(url).json(), {'liked': False, 'count': 0})
        self.client.post(url)
        thread.likes.add(self.other)  # 같은 사람을 다시 추가해도 1개
        self.assertEqual(thread.likes.count(), 1)

    def test_detail_sets_csrf_cookie_for_anonymous(self):
        thread = self.make_thread()
        response = self.client.get(thread.get_absolute_url())
        self.assertIn('csrftoken', response.cookies)


class DisplayTests(ThreadTestCase):
    def test_content_html_is_escaped(self):
        thread = self.make_thread(content='<script>alert(1)</script>\n둘째 줄입니다')
        response = self.client.get(thread.get_absolute_url())
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;<br>둘째 줄입니다')

    def test_main_page_orders_by_likes(self):
        quiet = self.make_thread(title='조용한 글')
        loved = self.make_thread(title='인기 많은 글')
        loved.likes.add(self.other)
        titles = [t.title for t in self.client.get(reverse('books:index')).context['threads']]
        self.assertEqual(titles[:2], ['인기 많은 글', '조용한 글'])
        self.assertTrue(quiet)

    def test_book_detail_lists_threads(self):
        self.make_thread(title='책 상세에 보일 글')
        response = self.client.get(reverse('books:detail', args=[self.book.isbn13]))
        self.assertContains(response, '책 상세에 보일 글')
        self.assertContains(response, f"{reverse('threads:create')}?book={self.book.isbn13}")

    def test_list_filter_and_sort(self):
        self.make_thread(title='A')
        b = self.make_thread(title='B')
        b.likes.add(self.other)
        response = self.client.get(reverse('threads:list'), {'book': self.book.isbn13, 'sort': 'popular'})
        self.assertEqual([t.title for t in response.context['page'].object_list], ['B', 'A'])
        self.assertEqual(self.client.get(reverse('threads:list'), {'book': '0000000000000'}).status_code, 404)


class CascadeCleanupTests(ThreadTestCase):
    def test_image_removed_when_author_deleted(self):
        thread = self.make_thread(image=make_image('c.png'))
        storage, name = thread.image.storage, thread.image.name
        self.writer.delete()  # CASCADE로 쓰레드도 삭제
        self.assertFalse(Thread.objects.exists())
        self.assertFalse(storage.exists(name))
