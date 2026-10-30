"""댓글 전처리: 정규식 정제, 길이 필터링, IQR 통계 계산."""
import re
import statistics

MIN_LENGTH = 5
MAX_LENGTH = 76

URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")
# ㅋㅋ, ㅎㅎ, ㅠㅠ, ㅜㅜ 같은 자음/모음 반복 및 단독 자모
JAMO_PATTERN = re.compile(r"[ㄱ-ㅎㅏ-ㅣ]+")
# 한글, 영문, 숫자, 기본 문장부호를 제외한 문자(이모지, 특수기호 등)
SPECIAL_PATTERN = re.compile(r"[^가-힣a-zA-Z0-9\s.,?!%~]")
# 같은 문장부호 반복 (!!!!, ~~~~, ...., ". .")
REPEAT_PUNCT_PATTERN = re.compile(r"([.,?!~])(?:\s*\1)+")
SPACE_PATTERN = re.compile(r"\s+")


def clean_text(text):
    """특수문자, 의미 없는 패턴, 불필요한 공백을 제거한다."""
    if not text:
        return ""
    text = URL_PATTERN.sub(" ", text)
    text = JAMO_PATTERN.sub(" ", text)
    text = SPECIAL_PATTERN.sub(" ", text)
    text = REPEAT_PUNCT_PATTERN.sub(r"\1", text)
    # 문장 앞에 남은 문장부호 제거 (". 다 떨어진거" -> "다 떨어진거")
    return SPACE_PATTERN.sub(" ", text).strip().lstrip(".,?!%~ ")


def compute_iqr(lengths):
    """댓글 길이 분포의 IQR 임계값 정보를 계산한다."""
    if len(lengths) < 2:
        return {}
    q1, _, q3 = statistics.quantiles(lengths, n=4)
    iqr = q3 - q1
    return {
        "q1": round(q1, 2),
        "q3": round(q3, 2),
        "iqr": round(iqr, 2),
        "lower_bound": round(q1 - 1.5 * iqr, 2),
        "upper_bound": round(q3 + 1.5 * iqr, 2),
        "applied_min": MIN_LENGTH,
        "applied_max": MAX_LENGTH,
    }


def preprocess(comments):
    """원본 댓글을 정제하고 길이로 필터링한다.

    반환: (records, iqr_info)
      records: 원본 순서대로 {"original", "cleaned", "removed_reason"} 딕셔너리 목록
               removed_reason 이 None 이면 통과한 댓글
    """
    records = []
    for original in comments:
        cleaned = clean_text(original)
        if not cleaned:
            reason = "결측치/의미 없는 댓글"
        elif not MIN_LENGTH <= len(cleaned) <= MAX_LENGTH:
            reason = f"길이 기준({MIN_LENGTH}~{MAX_LENGTH}자) 벗어남: {len(cleaned)}자"
        else:
            reason = None
        records.append({"original": original, "cleaned": cleaned, "removed_reason": reason})

    lengths = [len(r["cleaned"]) for r in records if r["cleaned"]]
    return records, compute_iqr(lengths)
