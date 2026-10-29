"""예시 쓰레드를 넣는다. (처음 실행했을 때 메인 "지금 이 쓰레드"가 비어 보이지 않도록)

    python manage.py loaddata books     # 먼저 도서 데이터가 있어야 함
    python manage.py seed_threads

- 예시 사용자 6명은 비밀번호가 없는(로그인할 수 없는) 계정이다.
- 여러 번 실행해도 같은 쓰레드가 중복으로 생기지 않는다.
"""

from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from books.models import Book
from threads.models import Thread

IMAGE_DIR = Path(settings.BASE_DIR) / 'static' / 'images' / 'threads'

# (닉네임, 이미지 파일, ISBN13, 제목, 내용, 좋아요 수)
SAMPLES = [
    ('책먼지', 'img1.jpg', '9788936434120', '마지막 장을 덮고 남긴 메모',
     '책을 다 읽고 한참 동안 아무것도 할 수 없었어요. 떠오르는 문장들을 작은 종이에 적어 책갈피 대신 '
     '끼워 두었습니다. 다시 펼칠 용기가 날 때 이 메모부터 읽어보려고 해요.', 5),
    ('밤독서', 'img2.jpg', '9788936434595', '한 문장씩 필사하며 다시 읽기',
     '빠르게 읽을 때는 놓쳤던 문장들이 손으로 옮겨 적으니 비로소 보이더라고요. 하루 한 페이지씩 '
     '필사 중인데 벌써 노트 한 권을 채웠습니다.', 4),
    ('새벽서재', 'img3.jpg', '9788936439651', 'AI 추천으로 만난 올해의 책',
     '평소라면 고르지 않았을 책인데 AI 추천 목록에 있길래 읽어봤어요. 내 독서 기록을 보고 골라줬다는 '
     '게 신기할 만큼 취향에 딱 맞았습니다.', 3),
    ('종이비행기', 'img4.jpg', '9788937473401', '다 포기하고 싶던 날 읽은 책',
     '계획했던 일이 모두 엎어진 날, 우연히 집어 든 책이었어요. 거센 물살 같은 이야기 속에서 이상하게 '
     '위로를 받았습니다.', 2),
    ('산책하는독자', 'img5.jpg', '9788937434488', '공원 벤치에서 쓴 독서 노트',
     '날씨가 좋아서 책과 노트를 들고 공원에 나갔어요. 등장인물들의 관계도를 그려가며 읽으니 훨씬 '
     '몰입이 잘 되더라고요.', 1),
    ('아침책상', 'img6.jpg', '9791130662596', '주말 아침 30분 독서 루틴',
     '주말마다 아침을 먹으며 30분씩 책을 읽고 있어요. 짧은 시간이지만 한 달이 지나니 두 권을 '
     '끝냈습니다. 같이 루틴 만들어요!', 0),
]


class Command(BaseCommand):
    help = '예시 사용자와 쓰레드(이미지 포함)를 만듭니다.'

    def handle(self, *args, **options):
        User = get_user_model()
        users = []
        for index, (nickname, *_rest) in enumerate(SAMPLES, start=1):
            user, created = User.objects.get_or_create(username=f'sample_{index}', defaults={'nickname': nickname})
            if created:
                user.set_unusable_password()  # 로그인할 수 없는 예시 계정
                user.save()
            users.append(user)

        created_count = 0
        for user, (nickname, image, isbn13, title, content, like_count) in zip(users, SAMPLES):
            book = Book.objects.filter(isbn13=isbn13).first()
            if book is None:
                raise CommandError(f'도서 {isbn13}이(가) 없습니다. 먼저 "python manage.py loaddata books"를 실행하세요.')
            thread, created = Thread.objects.get_or_create(
                author=user, title=title, defaults={'book': book, 'content': content},
            )
            if created:
                with open(IMAGE_DIR / image, 'rb') as file:
                    thread.image.save(image, File(file), save=True)  # media/threads/년/월/ 에 복사
                created_count += 1
            # 다른 예시 사용자들이 좋아요를 눌러 인기순 정렬이 보이게 한다
            thread.likes.set([other for other in users if other != user][:like_count])

        self.stdout.write(self.style.SUCCESS(
            f'예시 쓰레드 {created_count}개 생성 (전체 쓰레드 {Thread.objects.count()}개)'
        ))
