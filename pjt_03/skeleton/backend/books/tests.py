from unittest import mock

from django.test import TestCase
from django.urls import reverse

from .models import Book
from .services import is_valid_isbn13, save_book


class IsbnTests(TestCase):
    def test_valid_isbn13(self):
        self.assertTrue(is_valid_isbn13('9788936434595'))

    def test_invalid_isbn13(self):
        for value in ['9788936434596', '0000000000000', 'abc', '', None]:
            self.assertFalse(is_valid_isbn13(value), value)


class AuthorDisplayTests(TestCase):
    def make(self, author):
        return Book(isbn13='9788936434595', title='t', author=author, cover_url='https://x/y.jpg')

    def test_single_author(self):
        book = self.make('한강 (지은이)')
        self.assertEqual(book.main_author, '한강')
        self.assertEqual(book.author_display, '한강 지음')

    def test_author_and_translator(self):
        book = self.make('무라카미 하루키 (지은이), 양억관 (옮긴이)')
        self.assertEqual(book.main_author, '무라카미 하루키')
        self.assertEqual(book.author_display, '무라카미 하루키 지음 · 양억관 옮김')

    def test_many_authors(self):
        book = self.make('김난도, 전미영, 최지혜')
        self.assertEqual(book.main_author, '김난도 외 2명')


class SaveBookTests(TestCase):
    def test_skips_used_and_invalid_items(self):
        self.assertIsNone(save_book({'isbn13': '0000000000000', 'title': '중고책'}))
        self.assertIsNone(save_book({'isbn13': '9788936434595', 'title': 'x', 'mallType': 'USED'}))
        self.assertIsNone(save_book({'isbn13': '', 'title': '[세트]'}))

    def test_list_item_does_not_erase_detail_fields(self):
        save_book({'isbn13': '9788936434595', 'title': '채식주의자', 'author': '한강 (지은이)',
                   'cover': 'https://x/y.jpg', 'subInfo': {'itemPage': 276}})
        # 목록 API 응답에는 subInfo가 없다
        book = save_book({'isbn13': '9788936434595', 'title': '채식주의자', 'author': '한강 (지은이)',
                          'cover': 'https://x/y.jpg'})
        self.assertEqual(book.page_count, 276)


class PageTests(TestCase):
    fixtures = ['books']

    def test_index_shows_bestseller_slides(self):
        response = self.client.get(reverse('books:index'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['slides']), 3)
        self.assertTrue(all(len(slide) == 4 for slide in response.context['slides']))

    def test_index_without_threads_shows_empty_state(self):
        # 인기 쓰레드는 threads/tests.py에서 확인. 쓰레드가 없으면 안내 문구와 목록 링크를 보여준다
        response = self.client.get(reverse('books:index'))
        self.assertContains(response, '아직 쓰레드가 없어요.')
        self.assertContains(response, reverse('threads:list'))

    def test_detail_from_db(self):
        response = self.client.get(reverse('books:detail', args=['9788936434595']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '한강 지음')

    @mock.patch('books.views.aladin.lookup')
    def test_detail_invalid_isbn_does_not_call_api(self, lookup):
        response = self.client.get('/books/0000000000000/')
        self.assertEqual(response.status_code, 404)
        lookup.assert_not_called()


# ---------------------------------------------------------------------------
# 3단계: 검색 · 장르 (알라딘은 mock으로 대체해 네트워크 없이 실행)
# ---------------------------------------------------------------------------
from django.core.cache import cache

from . import aladin as aladin_module
from .genres import GENRES_BY_SLUG
from .services import genre_books, search_books
from .templatetags.book_extras import highlight

ALADIN_ITEM = {'isbn13': '9788936434120', 'title': '소년이 온다', 'author': '한강 (지은이)',
               'publisher': '창비', 'cover': 'https://x/y.jpg', 'mallType': 'BOOK'}


class HighlightTests(TestCase):
    def test_marks_query_case_insensitive(self):
        self.assertEqual(highlight('Harry Potter', 'potter'), 'Harry <mark>Potter</mark>')

    def test_escapes_html_and_entities(self):
        self.assertEqual(highlight('A & B <i>', 'amp'), 'A &amp; B &lt;i&gt;')
        self.assertEqual(highlight('<b>채식</b>', '채식'), '&lt;b&gt;<mark>채식</mark>&lt;/b&gt;')


class SearchServiceTests(TestCase):
    fixtures = ['books']

    def setUp(self):
        cache.clear()

    @mock.patch('books.services.aladin.search', return_value=([ALADIN_ITEM], 1))
    def test_aladin_result_is_saved_and_cached(self, search):
        first = search_books('소년')
        second = search_books('소년')
        self.assertEqual([b.isbn13 for b in first.books], ['9788936434120'])
        self.assertFalse(first.from_db)
        self.assertEqual([b.isbn13 for b in second.books], ['9788936434120'])
        search.assert_called_once()  # 두 번째는 캐시

    @mock.patch('books.services.aladin.search', side_effect=aladin_module.AladinError('만료'))
    def test_falls_back_to_db_when_aladin_fails(self, search):
        result = search_books('한강', query_type='author')
        self.assertTrue(result.from_db)
        self.assertTrue(result.books)
        self.assertTrue(all('한강' in b.author for b in result.books))

    def test_page_count_capped_at_200_results(self):
        with mock.patch('books.services.aladin.search', return_value=([ALADIN_ITEM], 5000)):
            self.assertEqual(search_books('책').num_pages, 10)

    @mock.patch('books.services.aladin.category_bestsellers', side_effect=aladin_module.AladinError('만료'))
    def test_genre_falls_back_to_db(self, _):
        result = genre_books(GENRES_BY_SLUG['history'])
        self.assertTrue(result.from_db)


class SearchViewTests(TestCase):
    fixtures = ['books']

    def setUp(self):
        cache.clear()

    def test_empty_query_shows_landing(self):
        response = self.client.get(reverse('books:search'))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('result', response.context)

    @mock.patch('books.services.aladin.search', return_value=([ALADIN_ITEM], 1))
    def test_invalid_options_fall_back_to_defaults(self, search):
        response = self.client.get(reverse('books:search'),
                                   {'q': '  소년  ', 'type': 'x', 'sort': 'y', 'page': 'abc'})
        self.assertEqual(response.status_code, 200)
        search.assert_called_once_with('소년', 'all', 'accuracy', 1, 20)
        self.assertContains(response, '<mark>소년</mark>')

    @mock.patch('books.services.aladin.search', return_value=([ALADIN_ITEM], 1))
    def test_query_is_trimmed_to_100_chars(self, search):
        self.client.get(reverse('books:search'), {'q': '가' * 300})
        self.assertEqual(len(search.call_args.args[0]), 100)

    @mock.patch('books.services.aladin.category_bestsellers', return_value=([ALADIN_ITEM], 1))
    def test_genre_page(self, _):
        response = self.client.get(reverse('books:genre', args=['history']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '소년이 온다')

    def test_unknown_genre_404(self):
        self.assertEqual(self.client.get('/genres/nope/').status_code, 404)

    def test_index_genre_tiles_link_to_genre_pages(self):
        response = self.client.get(reverse('books:index'))
        for slug in GENRES_BY_SLUG:
            self.assertContains(response, reverse('books:genre', args=[slug]))


class ScopedSearchTests(TestCase):
    """알라딘이 QueryType을 무시하므로, 상위 200권을 받아 직접 걸러내는지 확인."""

    def setUp(self):
        cache.clear()

    @staticmethod
    def fake_search(query, query_type, sort, page, count):
        items = {
            1: [{'isbn13': '9788936434120', 'title': '소년이 온다', 'author': '한강 (지은이)', 'publisher': '창비',
                 'cover': 'https://x/1.jpg'},
                {'isbn13': '9788937473401', 'title': '한강 따라 걷기', 'author': '정대건 (지은이)', 'publisher': '민음사',
                 'cover': 'https://x/2.jpg'}],
            2: [{'isbn13': '9788936439651', 'title': '대온실 수리 보고서', 'author': '김금희 (지은이)', 'publisher': '창비',
                 'cover': 'https://x/3.jpg'}],
        }.get(page, [])
        return items, 3

    def test_author_scope_filters_and_calls_four_pages(self):
        with mock.patch('books.services.aladin.search', side_effect=self.fake_search) as search:
            result = search_books('한강', query_type='author')
        self.assertEqual([b.isbn13 for b in result.books], ['9788936434120'])
        self.assertEqual(result.scanned, 3)
        self.assertEqual(search.call_count, 4)  # 50권 × 4번
        self.assertEqual({c.args[3] for c in search.call_args_list}, {1, 2, 3, 4})

    def test_title_scope_ignores_spaces(self):
        with mock.patch('books.services.aladin.search', side_effect=self.fake_search):
            result = search_books('한강따라', query_type='title')
        self.assertEqual([b.title for b in result.books], ['한강 따라 걷기'])

    def test_publisher_scope_is_cached(self):
        with mock.patch('books.services.aladin.search', side_effect=self.fake_search) as search:
            first = search_books('창비', query_type='publisher')
            second = search_books('창비', query_type='publisher', page=1)
        self.assertEqual(len(first.books), 2)
        self.assertEqual([b.isbn13 for b in first.books], [b.isbn13 for b in second.books])
        self.assertEqual(search.call_count, 4)  # 두 번째는 캐시

    def test_scoped_view_summary(self):
        with mock.patch('books.services.aladin.search', side_effect=self.fake_search):
            response = self.client.get(reverse('books:search'), {'q': '한강', 'type': 'author'})
        self.assertContains(response, '저자 검색 결과')
        self.assertContains(response, '상위 3권 중 저자 일치')

    def test_title_scope_ignores_aladin_subtitle(self):
        item = {'isbn13': '9788954682152', 'title': '작별하지 않는다 - 2024 노벨문학상 수상작가 한강 장편소설',
                'author': '한강 (지은이)', 'publisher': '문학동네', 'cover': 'https://x/4.jpg'}
        with mock.patch('books.services.aladin.search', return_value=([item], 1)):
            result = search_books('한강', query_type='title')
        self.assertEqual(result.books, [])
