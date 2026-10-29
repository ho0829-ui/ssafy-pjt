from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()
PASSWORD = 'read-books-2026!'


class SignUpTests(TestCase):
    url = reverse('accounts:signup')

    def post(self, **overrides):
        data = {'username': 'reader1', 'nickname': '책먼지', 'password1': PASSWORD, 'password2': PASSWORD}
        data.update(overrides)
        return self.client.post(self.url, data)

    def test_signup_creates_user_and_logs_in(self):
        response = self.post()
        self.assertRedirects(response, reverse('books:index'))
        user = User.objects.get(username='reader1')
        self.assertEqual(user.nickname, '책먼지')
        self.assertNotEqual(user.password, PASSWORD)  # 해시로 저장
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_duplicate_nickname_rejected(self):
        User.objects.create_user('other', password=PASSWORD, nickname='책먼지')
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '이미 사용 중인 닉네임이에요.')
        self.assertFalse(User.objects.filter(username='reader1').exists())

    def test_invalid_nickname_rejected(self):
        for nickname in ['a', '책 먼지', '<b>x</b>']:
            response = self.post(nickname=nickname)
            self.assertEqual(response.status_code, 200, nickname)
        self.assertFalse(User.objects.exists())

    def test_password_mismatch_marks_field_invalid(self):
        response = self.post(password2='different-pass-9!')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'is-invalid')

    def test_next_redirect_and_external_next_blocked(self):
        response = self.client.post(self.url + '?next=/search/', {
            'username': 'r2', 'nickname': '독자2', 'password1': PASSWORD, 'password2': PASSWORD,
            'next': '/search/?q=x'})
        self.assertRedirects(response, '/search/?q=x', fetch_redirect_response=False)
        self.client.logout()
        response = self.client.post(self.url, {
            'username': 'r3', 'nickname': '독자3', 'password1': PASSWORD, 'password2': PASSWORD,
            'next': 'https://evil.example.com/'})
        self.assertRedirects(response, reverse('books:index'))


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('reader1', password=PASSWORD, nickname='책먼지')

    def test_login_success_with_next(self):
        response = self.client.post(reverse('accounts:login'),
                                    {'username': 'reader1', 'password': PASSWORD, 'remember_me': 'on',
                                     'next': '/search/'})
        self.assertRedirects(response, '/search/', fetch_redirect_response=False)
        self.assertFalse(self.client.session.get_expire_at_browser_close())

    def test_login_without_remember_me_expires_on_browser_close(self):
        self.client.post(reverse('accounts:login'), {'username': 'reader1', 'password': PASSWORD})
        self.assertTrue(self.client.session.get_expire_at_browser_close())

    def test_wrong_password_shows_message(self):
        response = self.client.post(reverse('accounts:login'), {'username': 'reader1', 'password': 'nope'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '아이디 또는 비밀번호가 맞지 않아요.')

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('accounts:logout')).status_code, 405)
        response = self.client.post(reverse('accounts:logout'))
        self.assertRedirects(response, reverse('books:index'), fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logged_in_user_is_redirected_away_from_auth_pages(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get(reverse('accounts:login')), reverse('books:index'),
                             fetch_redirect_response=False)
        self.assertRedirects(self.client.get(reverse('accounts:signup')), reverse('books:index'),
                             fetch_redirect_response=False)


class NavbarTests(TestCase):
    def test_logged_out_navbar(self):
        response = self.client.get(reverse('books:index'))
        self.assertContains(response, reverse('accounts:login'))
        self.assertNotContains(response, 'id="logoutModal"')

    def test_logged_in_navbar_shows_nickname_and_logout_form(self):
        user = User.objects.create_user('reader1', password=PASSWORD, nickname='책먼지')
        self.client.force_login(user)
        response = self.client.get(reverse('books:index'))
        self.assertContains(response, '책먼지 님')
        self.assertContains(response, f'action="{reverse("accounts:logout")}"')
        self.assertContains(response, 'csrfmiddlewaretoken')


# ---------------------------------------------------------------------------
# 6단계: 담기 · 마이페이지
# ---------------------------------------------------------------------------
import shutil  # noqa: E402
import tempfile  # noqa: E402

from django.test import override_settings  # noqa: E402

from books.models import Archive, Book  # noqa: E402
from threads.models import Thread  # noqa: E402
from threads.tests import make_image  # noqa: E402

TEMP_MEDIA = tempfile.mkdtemp()


class ArchiveTests(TestCase):
    fixtures = ['books']

    def setUp(self):
        self.user = User.objects.create_user('reader1', password=PASSWORD, nickname='책먼지')
        self.book = Book.objects.get(isbn13='9788936434595')
        self.url = reverse('books:archive', args=[self.book.isbn13])

    def test_anonymous_gets_401_with_login_url(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 401)
        self.assertIn('next=%2Fbooks%2F9788936434595%2F', response.json()['login_url'])

    def test_toggle(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(self.url).json(), {'archived': True})
        self.assertEqual(Archive.objects.filter(user=self.user, book=self.book).count(), 1)
        self.assertEqual(self.client.post(self.url).json(), {'archived': False})
        self.assertFalse(Archive.objects.exists())

    def test_detail_shows_archived_state(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse('books:detail', args=[self.book.isbn13])), '>담기<')
        Archive.objects.create(user=self.user, book=self.book)
        self.assertContains(self.client.get(reverse('books:detail', args=[self.book.isbn13])), '>담았어요<')

    def test_unique_per_user_and_book(self):
        from django.db import IntegrityError, transaction
        Archive.objects.create(user=self.user, book=self.book)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Archive.objects.create(user=self.user, book=self.book)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class MyPageTests(TestCase):
    fixtures = ['books']

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user('reader1', password=PASSWORD, nickname='책먼지')
        self.other = User.objects.create_user('reader2', password=PASSWORD, nickname='남궁')
        self.book = Book.objects.get(isbn13='9788936434595')
        self.client.force_login(self.user)

    def test_login_required(self):
        self.client.logout()
        response = self.client.get(reverse('mypage:index'))
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('mypage:index')}",
                             fetch_redirect_response=False)

    def test_books_tab_shows_only_my_archives(self):
        Archive.objects.create(user=self.user, book=self.book)
        Archive.objects.create(user=self.other, book=Book.objects.get(isbn13='9788936434120'))
        page = self.client.get(reverse('mypage:index')).context['page']
        self.assertEqual([a.book for a in page.object_list], [self.book])

    def test_threads_likes_tabs_and_stats(self):
        mine = Thread.objects.create(author=self.user, book=self.book, title='내 글', content='열 글자가 넘는 내용입니다.')
        theirs = Thread.objects.create(author=self.other, book=self.book, title='남의 글', content='열 글자가 넘는 내용입니다.')
        mine.likes.add(self.other)
        theirs.likes.add(self.user)
        threads = self.client.get(reverse('mypage:index'), {'tab': 'threads'})
        self.assertEqual([t.title for t in threads.context['page'].object_list], ['내 글'])
        self.assertEqual(threads.context['stats'], {'archives': 0, 'threads': 1, 'likes_received': 1})
        likes = self.client.get(reverse('mypage:index'), {'tab': 'likes'})
        self.assertEqual([t.title for t in likes.context['page'].object_list], ['남의 글'])

    def test_unknown_tab_falls_back_to_books(self):
        self.assertEqual(self.client.get(reverse('mypage:index'), {'tab': 'x'}).context['tab'], 'books')

    def test_nickname_change_and_duplicate(self):
        response = self.client.post(reverse('mypage:nickname'), {'nickname': '남궁'})
        self.assertContains(response, '이미 사용 중인 닉네임이에요.')
        self.assertContains(response, '책먼지 님')  # 실패해도 Navbar 닉네임은 그대로
        self.client.post(reverse('mypage:nickname'), {'nickname': '새이름'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.nickname, '새이름')

    def test_password_change_keeps_login(self):
        new = 'another-pass-2026!'
        response = self.client.post(reverse('mypage:password'),
                                    {'old_password': PASSWORD, 'new_password1': new, 'new_password2': new})
        self.assertRedirects(response, f"{reverse('mypage:index')}?tab=settings", fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new))
        self.assertEqual(self.client.get(reverse('mypage:index')).status_code, 200)  # 여전히 로그인

    def test_delete_requires_correct_password(self):
        response = self.client.post(reverse('mypage:delete'), {'password': 'wrong'})
        self.assertContains(response, '비밀번호가 맞지 않아요.')
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_delete_account_removes_data_and_files(self):
        thread = Thread.objects.create(author=self.user, book=self.book, title='내 글',
                                       content='열 글자가 넘는 내용입니다.', image=make_image())
        storage, name = thread.image.storage, thread.image.name
        Archive.objects.create(user=self.user, book=self.book)
        response = self.client.post(reverse('mypage:delete'), {'password': PASSWORD})
        self.assertRedirects(response, reverse('books:index'), fetch_redirect_response=False)
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        self.assertFalse(Thread.objects.exists() or Archive.objects.exists())
        self.assertFalse(storage.exists(name))
        self.assertNotIn('_auth_user_id', self.client.session)
