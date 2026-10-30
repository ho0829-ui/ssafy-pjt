"""토스증권 커뮤니티 댓글 크롤러 (Selenium)."""
import time

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE_URL = "https://www.tossinvest.com/"
POST_SELECTOR = '[data-section-name="커뮤니티__게시글"][data-post-anchor-id]'
TEXT_SELECTOR = "span._1xixuox0"  # 게시글 본문 텍스트


class CrawlError(Exception):
    """사용자에게 안내할 수 있는 크롤링 실패."""


def _create_driver(headless=True):
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1400,1000")
    options.add_argument("--lang=ko-KR")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    try:
        # Selenium Manager(내장)로 드라이버를 먼저 시도하고, 실패 시 webdriver-manager 사용
        return webdriver.Chrome(options=options)
    except Exception:
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager

        return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def _search_company(driver, wait, keyword):
    """검색창에 회사명을 입력하고 최상단 결과를 선택한다. 실제 종목명을 반환."""
    driver.get(BASE_URL)
    search_trigger = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//span[contains(text(),'를 눌러 검색하세요')]"))
    )
    search_trigger.click()
    search_input = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="검색어를 입력해주세요"]'))
    )
    search_input.send_keys(keyword)
    time.sleep(2)  # 자동완성 결과 렌더링 대기 (최상단 회사가 자동 포커싱됨)

    start_url = driver.current_url
    search_input.send_keys(Keys.ENTER)
    try:
        WebDriverWait(driver, 8).until(lambda d: "/stocks/" in d.current_url and d.current_url != start_url)
    except TimeoutException:
        raise CrawlError(f"'{keyword}'에 해당하는 회사를 찾을 수 없습니다.")

    # og:title 메타 태그 형식: "삼성전자(005930) 실시간 주가를 확인해보세요"
    def read_og_title(d):
        metas = d.find_elements(By.CSS_SELECTOR, 'meta[property="og:title"]')
        content = metas[0].get_attribute("content") if metas else ""
        return content if "(" in content else False

    try:
        og_title = WebDriverWait(driver, 10).until(read_og_title)
        return og_title.split("(")[0].strip()
    except TimeoutException:
        # 탭 제목 형식: "218,500원 -5.81% | 삼성전자"
        return driver.title.split("|")[-1].strip()


def _open_community_tab(driver, wait):
    tab = wait.until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, '[data-parent-name="StockInfoTabComp"][data-content-value="커뮤니티"]')
        )
    )
    driver.execute_script("arguments[0].click();", tab)


def _collect_posts(driver, wait, limit):
    """가상 스크롤 목록을 내리면서 게시글 텍스트를 중복 없이 수집한다."""
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, POST_SELECTOR)))
    except TimeoutException:
        return []

    # 목록이 스크롤 중 계속 다시 렌더링되므로(StaleElement 방지) 한 번의 JS 실행으로 읽고 스크롤한다
    read_and_scroll = """
        const posts = [...document.querySelectorAll(arguments[0])];
        const rows = posts.map(p => ({
            id: p.getAttribute('data-post-anchor-id'),
            text: [...p.querySelectorAll(arguments[1])].map(s => s.innerText.trim()).join(' ')
                .replace(/\\s*더 보기$/, ''),  // 긴 글의 '더 보기' 버튼 문구 제거
        }));
        if (posts.length) posts[posts.length - 1].scrollIntoView({block: 'start'});
        return rows;
    """
    collected = {}
    stale_rounds = 0
    while len(collected) < limit and stale_rounds < 5:
        before = len(collected)
        for row in driver.execute_script(read_and_scroll, POST_SELECTOR, TEXT_SELECTOR):
            collected.setdefault(row["id"], row["text"])
        time.sleep(1)
        stale_rounds = stale_rounds + 1 if len(collected) == before else 0
    return list(collected.values())[:limit]


def crawl_comments(keyword, limit=20, headless=True):
    """회사명으로 검색해 댓글을 수집하는 제너레이터.

    진행 상황 메시지(str)를 yield 하고, 최종적으로 (실제종목명, 댓글 리스트)를 return 한다.
    """
    yield "크롬 브라우저 실행 중..."
    driver = _create_driver(headless=headless)
    wait = WebDriverWait(driver, 15)
    try:
        yield "토스증권 접속 및 회사 검색 중..."
        company_name = _search_company(driver, wait, keyword)
        yield f"최상단 종목 선택: {company_name}"

        yield "커뮤니티 탭으로 이동 중..."
        _open_community_tab(driver, wait)

        yield f"댓글 {limit}개 수집 중..."
        comments = _collect_posts(driver, wait, limit)
        yield f"댓글 {len(comments)}개 수집 완료"
        return company_name, comments
    except CrawlError:
        raise
    except TimeoutException:
        raise CrawlError("토스증권 페이지 로딩 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.")
    finally:
        driver.quit()
