"""알라딘 Open API 호출만 담당하는 모듈.

응답(JSON)을 그대로 돌려주고, DB 저장·캐시는 services.py가 맡는다.
API 문서: https://blog.aladin.co.kr/openapi
"""

import requests
from django.conf import settings

BASE_URL = 'http://www.aladin.co.kr/ttb/api/'
TIMEOUT = 5  # 초
MAX_RESULTS = 200  # 알라딘 검색·목록 API는 한 조건당 최대 200건까지만 제공
MAX_PAGE_SIZE = 50  # 한 번 호출에 받을 수 있는 최대 건수

# 화면의 선택값 → 알라딘 파라미터
# (2026-10 확인: 알라딘이 QueryType을 무시해서, 범위 검색은 services.py에서 직접 걸러낸다)
QUERY_TYPES = {'all': 'Keyword', 'title': 'Title', 'author': 'Author', 'publisher': 'Publisher'}
SORTS = {'accuracy': 'Accuracy', 'sales': 'SalesPoint', 'latest': 'PublishTime'}


class AladinError(Exception):
    """키가 없거나, 만료됐거나, 네트워크·응답 오류가 난 경우."""


def _request(endpoint, **params):
    if not settings.ALADIN_TTB_KEY:
        raise AladinError('ALADIN_TTB_KEY가 설정되지 않았습니다.')
    params.update({
        'ttbkey': settings.ALADIN_TTB_KEY,
        'output': 'js',
        'Version': '20131101',
        'Cover': 'Big',
    })
    try:
        response = requests.get(BASE_URL + endpoint, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as error:
        raise AladinError(f'알라딘 API 요청 실패: {error}') from error
    if 'errorCode' in data:
        raise AladinError(f"알라딘 API 오류 {data['errorCode']}: {data.get('errorMessage')}")
    return data


def bestsellers(count=12):
    """국내도서 주간 베스트셀러."""
    return _request('ItemList.aspx', QueryType='Bestseller', SearchTarget='Book',
                    MaxResults=count, start=1).get('item', [])


def category_bestsellers(category_id, page=1, count=20):
    """특정 카테고리의 베스트셀러. (item 목록, 전체 건수)를 돌려준다."""
    data = _request('ItemList.aspx', QueryType='Bestseller', SearchTarget='Book',
                    CategoryId=category_id, MaxResults=count, start=page)
    return data.get('item', []), data.get('totalResults', 0)


def search(query, query_type='all', sort='accuracy', page=1, count=20):
    """국내도서 검색. (item 목록, 전체 건수)를 돌려준다."""
    data = _request('ItemSearch.aspx', Query=query, SearchTarget='Book',
                    QueryType=QUERY_TYPES.get(query_type, 'Keyword'),
                    Sort=SORTS.get(sort, 'Accuracy'), MaxResults=count, start=page)
    return data.get('item', []), data.get('totalResults', 0)


def lookup(isbn13):
    """ISBN13으로 상세 조회. 부제·쪽수·평점(subInfo)까지 포함."""
    items = _request('ItemLookUp.aspx', ItemId=isbn13, ItemIdType='ISBN13',
                     OptResult='ratingInfo').get('item', [])
    return items[0] if items else None
