"""메인 페이지 장르 타일과 알라딘 카테고리의 대응표.

category_id는 알라딘 API로 실제 결과를 확인해 고른 값이다.
철학·로맨스는 상위 분류 ID를 API로 확인할 수 없어, 결과가 가장 많은 하위 분류를 쓴다.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Genre:
    slug: str          # URL: /genres/<slug>/
    name: str          # 화면에 보이는 이름
    image: str         # static 경로
    area: str          # 벤토 그리드 칸 이름 (main.css의 .genre-<area>)
    category_id: int   # 알라딘 CategoryId
    category_label: str  # 알라딘 분류 이름 (결과 화면 안내용)
    db_keyword: str    # 키가 없을 때 DB에서 찾을 category_name 키워드


GENRES = [
    Genre('art', '예술', 'images/genre/art.jpg', 'art', 517, '예술/대중문화', '예술'),
    Genre('science', '자연과학', 'images/genre/natural_science.jpg', 'sci', 987, '과학', '과학'),
    Genre('history', '역사', 'images/genre/history.jpg', 'his', 74, '역사', '역사'),
    Genre('economy', '경제/경영', 'images/genre/economy.jpg', 'eco', 170, '경제경영', '경제경영'),
    Genre('travel', '여행', 'images/genre/travel.jpg', 'tra', 1196, '여행', '여행'),
    Genre('baby', '유아', 'images/genre/baby.jpg', 'bab', 13789, '유아', '유아'),
    Genre('philosophy', '철학', 'images/genre/philosophy.jpg', 'phi', 51440, '인문학 > 교양 철학', '철학'),
    Genre('romance', '로맨스', 'images/genre/romance.jpg', 'rom', 51125, '한국 로맨스소설', '로맨스'),
    Genre('youth', '청소년', 'images/genre/youth.jpg', 'you', 1137, '청소년', '청소년'),
    Genre('health', '건강', 'images/genre/health.jpg', 'hea', 55890, '건강/취미', '건강'),
]

GENRES_BY_SLUG = {genre.slug: genre for genre in GENRES}
