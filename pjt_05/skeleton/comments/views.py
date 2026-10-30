import json

from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .models import CrawlResult
from .services.pipeline import run_pipeline


def index(request):
    recent = CrawlResult.objects.all()[:10]
    return render(request, "comments/index.html", {"recent": recent})


def crawl_stream(request):
    """회사명을 받아 파이프라인을 실행하고 진행 상황을 NDJSON 으로 스트리밍한다."""
    keyword = request.GET.get("company", "").strip()
    if not keyword:
        # 입력값이 없으면 아무 동작도 하지 않는다 (F601)
        return redirect("comments:index")

    print(f"[입력 회사명] {keyword}")

    def stream():
        for event in run_pipeline(keyword):
            if event["type"] == "progress":
                print(f"  - {event['message']}")
            yield json.dumps(event, ensure_ascii=False) + "\n"

    response = StreamingHttpResponse(stream(), content_type="application/x-ndjson; charset=utf-8")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


def result(request, pk):
    item = get_object_or_404(CrawlResult, pk=pk)
    recent = CrawlResult.objects.all()[:10]
    return render(request, "comments/result.html", {"item": item, "recent": recent})
