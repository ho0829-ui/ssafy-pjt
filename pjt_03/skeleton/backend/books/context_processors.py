from .genres import GENRES


def genres(request):
    """모든 페이지의 검색 오버레이에서 장르 바로가기를 쓰기 위해 장르 목록을 넘긴다."""
    return {'all_genres': GENRES}
