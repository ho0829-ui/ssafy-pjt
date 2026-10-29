import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    """닉네임 필드 추가.

    필수(unique) 필드라 기본값이 필요하지만, 추가 시점에 사용자가 0명이라
    임시 기본값('')은 실제로 쓰이지 않는다. (preserve_default=False)
    """

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='nickname',
            field=models.CharField(
                default='',
                error_messages={'unique': '이미 사용 중인 닉네임이에요.'},
                help_text='2~12자. 한글, 영문, 숫자, 밑줄(_)',
                max_length=12,
                unique=True,
                validators=[
                    django.core.validators.MinLengthValidator(2, '닉네임은 2자 이상이어야 해요.'),
                    django.core.validators.RegexValidator('^[가-힣a-zA-Z0-9_]+$', '한글, 영문, 숫자, 밑줄(_)만 쓸 수 있어요.'),
                ],
                verbose_name='닉네임',
            ),
            preserve_default=False,
        ),
    ]
