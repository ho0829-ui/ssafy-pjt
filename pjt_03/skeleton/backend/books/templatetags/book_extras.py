import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def highlight(text, query):
    """text 안의 query(대소문자 무시)를 <mark>로 감싼다.

    원문을 검색어 기준으로 먼저 나눈 뒤 조각마다 이스케이프하므로,
    HTML이 섞인 제목이나 "amp" 같은 검색어에도 엔티티가 깨지지 않는다.
    """
    text = str(text or '')
    query = (query or '').strip()
    if not query:
        return escape(text)
    pieces = re.split(f'({re.escape(query)})', text, flags=re.IGNORECASE)
    return mark_safe(''.join(
        f'<mark>{escape(piece)}</mark>' if i % 2 else escape(piece)
        for i, piece in enumerate(pieces)
    ))
