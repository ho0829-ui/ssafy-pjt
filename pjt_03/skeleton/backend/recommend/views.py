import logging

from django.core.cache import cache
from django.http import JsonResponse
from django.urls import reverse
from django.utils.http import urlencode
from django.views.decorators.http import require_POST

from . import ai, services

logger = logging.getLogger(__name__)

RATE_LIMIT = 3  # 새로 만드는(Claude를 부르는) 추천은 사용자당 1분에 3번까지
RATE_WINDOW = 60


def _rate_limited(user):
    key = f'recommend:rate:{user.pk}'
    cache.add(key, 0, RATE_WINDOW)  # 없을 때만 0으로 만들고 60초 뒤 사라짐
    return cache.incr(key) > RATE_LIMIT


@require_POST
def recommend(request):
    """POST /recommend/ (q=검색어) → JSON. 메인 페이지 AI 추천 섹션에서 fetch로 호출한다."""
    if not request.user.is_authenticated:
        login_url = f"{reverse('accounts:login')}?{urlencode({'next': reverse('books:index') + '#ai-recommendation'})}"
        return JsonResponse({'error': '로그인하면 AI 추천을 받을 수 있어요.', 'login_url': login_url}, status=401)

    query = request.POST.get('q', '')
    if not services.is_valid_query(query):
        return JsonResponse({'error': f'검색어는 {services.MIN_QUERY}~{services.MAX_QUERY}자로 입력해 주세요.'}, status=400)

    cached = services.cached_result(query)
    if cached:
        return JsonResponse({**cached, 'cached': True})

    if _rate_limited(request.user):
        return JsonResponse({'error': 'AI 추천은 1분에 3번까지 받을 수 있어요. 잠시 후 다시 시도해 주세요.'}, status=429)

    try:
        return JsonResponse({**services.recommend(query), 'cached': False})
    except ai.AIError as error:
        logger.warning('AI 추천 실패, 일반 검색으로 대체: %s', error)
        return JsonResponse({**services.fallback(query), 'cached': False})
