from django.contrib.auth.models import AbstractUser
from django.core.validators import MinLengthValidator, RegexValidator
from django.db import models


class User(AbstractUser):
    """프로젝트 전용 사용자 모델.

    - username(아이디): 로그인에만 쓰고 다른 사람에게 보여주지 않는다.
    - nickname(닉네임): 쓰레드 작성자·마이페이지 등 화면에 보이는 이름.
    """

    nickname = models.CharField(
        '닉네임',
        max_length=12,
        unique=True,
        validators=[
            MinLengthValidator(2, '닉네임은 2자 이상이어야 해요.'),
            RegexValidator(r'^[가-힣a-zA-Z0-9_]+$', '한글, 영문, 숫자, 밑줄(_)만 쓸 수 있어요.'),
        ],
        help_text='2~12자. 한글, 영문, 숫자, 밑줄(_)',
        error_messages={'unique': '이미 사용 중인 닉네임이에요.'},
    )

    # createsuperuser 실행 시 닉네임도 묻는다
    REQUIRED_FIELDS = ['nickname']

    def __str__(self):
        return self.nickname or self.username
