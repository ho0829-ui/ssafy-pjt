"""GMS(SSAFY 생성형 AI API)를 이용한 부적절 댓글 필터링, 데이터 증강, 요약."""
import json
import os
import re

from openai import OpenAI

GMS_BASE_URL = os.getenv("GMS_BASE_URL", "https://gms.ssafy.io/gmsapi/api.openai.com/v1")
GMS_MODEL = os.getenv("GMS_MODEL", "gpt-4o-mini")


class LLMUnavailable(Exception):
    """GMS 키가 없거나 호출에 실패한 경우."""


def _client():
    api_key = os.getenv("GMS_KEY")
    if not api_key:
        raise LLMUnavailable("GMS_KEY 환경 변수가 설정되지 않았습니다.")
    return OpenAI(api_key=api_key, base_url=GMS_BASE_URL)


def _chat(system, user):
    try:
        response = _client().chat.completions.create(
            model=GMS_MODEL,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.3,
        )
    except LLMUnavailable:
        raise
    except Exception as e:
        raise LLMUnavailable(f"GMS 호출 실패: {e}")
    return response.choices[0].message.content.strip()


def _parse_json_array(text):
    """응답에서 JSON 배열 부분만 추출해 파싱한다 (```json 코드블록 대응)."""
    match = re.search(r"\[.*\]", text, re.S)
    if not match:
        raise LLMUnavailable(f"JSON 배열 응답을 해석할 수 없습니다: {text[:100]}")
    try:
        return json.loads(match.group())
    except json.JSONDecodeError as e:
        raise LLMUnavailable(f"JSON 파싱 실패: {e}")


def _numbered(comments):
    return "\n".join(f"{i}. {c}" for i, c in enumerate(comments))


def find_inappropriate(comments):
    """부적절한 댓글의 인덱스 집합을 반환한다."""
    if not comments:
        return set()
    answer = _chat(
        "너는 주식 커뮤니티 댓글을 검수하는 모더레이터다. 반드시 JSON 배열만 출력한다.",
        "다음 댓글 목록에서 부적절한 댓글(욕설, 혐오, 비방, 선정성, 과도한 비난 등)의 "
        "번호(0부터 시작)만 JSON 배열로 알려줘. 없으면 []를 출력해.\n\n" + _numbered(comments),
    )
    return {int(i) for i in _parse_json_array(answer) if str(i).isdigit() and int(i) < len(comments)}


def augment(comments):
    """각 댓글의 의미를 유지하면서 표현을 확장한 문장 목록을 반환한다 (입력과 같은 길이)."""
    if not comments:
        return []
    answer = _chat(
        "너는 텍스트 데이터 증강 도우미다. 반드시 JSON 문자열 배열만 출력한다.",
        "다음 주식 커뮤니티 댓글 각각에 대해 원래 의미와 감정(긍정/부정)을 유지하면서 "
        "조금 더 자연스럽고 풍부한 표현으로 바꾼 한 문장을 만들어줘. "
        "원문에 없는 사실이나 감정을 추가하지 말고, 뜻이 모호한 은어는 원문 표현을 최대한 살려. "
        f"입력과 같은 순서로 정확히 {len(comments)}개의 문자열을 JSON 배열로 출력해.\n\n"
        + _numbered(comments),
    )
    augmented = [str(s).strip() for s in _parse_json_array(answer)]
    if len(augmented) != len(comments):
        raise LLMUnavailable(f"증강 결과 개수 불일치 (입력 {len(comments)}개, 출력 {len(augmented)}개)")
    return augmented


def summarize(company_name, comments):
    """전체 댓글의 주요 내용을 요약한다."""
    if not comments:
        return ""
    return _chat(
        "너는 주식 커뮤니티 여론을 분석하는 애널리스트다.",
        f"다음은 '{company_name}' 종목 커뮤니티 댓글이다. 전반적인 투자자 분위기(긍정/부정 비율 느낌), "
        "주로 언급되는 이슈, 핵심 의견을 한국어 3~4문장으로 요약해줘. 욕설은 인용하지 마.\n\n"
        + _numbered(comments),
    )
