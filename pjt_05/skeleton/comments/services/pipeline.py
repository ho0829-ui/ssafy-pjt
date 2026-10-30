"""입력 -> 크롤링 -> 전처리 -> 증강 -> 통합/저장 파이프라인.

각 단계는 진행 메시지를 yield 하는 제너레이터로 구성해 스트리밍 응답에서 그대로 사용한다.
"""
from selenium.common.exceptions import WebDriverException

from ..models import CrawlResult
from . import llm
from .crawler import CrawlError, crawl_comments
from .preprocess import preprocess


def progress(message):
    return {"type": "progress", "message": message}


def run_pipeline(keyword, limit=20):
    crawler = crawl_comments(keyword, limit=limit)
    try:
        while True:
            yield progress(next(crawler))
    except StopIteration as stop:
        company_name, raw_comments = stop.value
    except CrawlError as e:
        yield {"type": "error", "message": str(e)}
        return
    except WebDriverException as e:
        yield {"type": "error", "message": f"크롤링 중 브라우저 오류가 발생했습니다: {e.msg}"}
        return

    if not raw_comments:
        yield {"type": "error", "message": f"'{company_name}' 종목의 커뮤니티 댓글이 존재하지 않습니다."}
        return

    # 1) 정규식 정제 + 길이 필터링
    yield progress("댓글 전처리 중 (특수문자/반복 패턴 제거, 길이 5~76자 필터)...")
    records, iqr_info = preprocess(raw_comments)
    passed = [r for r in records if r["removed_reason"] is None]

    warnings = []

    # 2) LLM 부적절 댓글 필터링
    yield progress("LLM으로 부적절한 댓글 검사 중...")
    try:
        bad_indexes = llm.find_inappropriate([r["cleaned"] for r in passed])
        for i in bad_indexes:
            passed[i]["removed_reason"] = "부적절한 댓글(LLM 판정)"
        passed = [r for r in passed if r["removed_reason"] is None]
    except llm.LLMUnavailable as e:
        warnings.append(f"부적절 댓글 필터링 생략: {e}")

    # 3) LLM 데이터 증강
    yield progress(f"LLM으로 댓글 {len(passed)}개 데이터 증강 중...")
    try:
        for record, text in zip(passed, llm.augment([r["cleaned"] for r in passed])):
            record["augmented"] = text
    except llm.LLMUnavailable as e:
        warnings.append(f"데이터 증강 생략: {e}")

    # 4) 전체 댓글 요약 (심화)
    yield progress("전체 댓글 요약 생성 중...")
    try:
        summary = llm.summarize(company_name, [r["cleaned"] for r in records if r["cleaned"]])
    except llm.LLMUnavailable as e:
        summary = ""
        warnings.append(f"요약 생략: {e}")

    # 5) 통합 및 저장
    for record in records:
        record.setdefault("augmented", None)
    result = CrawlResult.objects.create(
        keyword=keyword,
        company_name=company_name,
        raw_comments=raw_comments,
        cleaned_comments=[r["cleaned"] for r in passed],
        augmented_comments=[r["augmented"] for r in passed if r["augmented"]],
        integrated=records,
        iqr_info=iqr_info,
        summary=summary,
        warnings=warnings,
    )
    yield progress("결과 저장 완료")
    yield {"type": "done", "id": result.pk}
