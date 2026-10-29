// 스크롤 등장 애니메이션: .reveal 요소가 화면에 들어오면 한 번만 나타나게 한다
const revealObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        revealObserver.unobserve(entry.target); // 한 번만 재생
      }
    });
  },
  { threshold: 0.15 }
);
document.querySelectorAll(".reveal").forEach((el) => revealObserver.observe(el));

// 베스트셀러 캐러셀: 슬라이드가 바뀌면 "1 / 3" 표시 갱신
const bestsellerCarousel = document.querySelector("#bestsellerCarousel");
const carouselCounter = document.querySelector(".carousel-counter strong");
if (bestsellerCarousel && carouselCounter) {
  bestsellerCarousel.addEventListener("slid.bs.carousel", (event) => {
    carouselCounter.textContent = event.to + 1;
  });
}

// F309: 베스트셀러 카드 높이의 절반을 --overlap으로 설정 (메인 페이지에만 존재)
const bestsellerGlass = document.querySelector(".bestseller-glass");
if (bestsellerGlass) {
  new ResizeObserver(() => {
    document.documentElement.style.setProperty(
      "--overlap",
      bestsellerGlass.offsetHeight / 2 + "px"
    );
  }).observe(bestsellerGlass);
}

// ===== 도서 검색 =====
// 최근 검색어는 이 브라우저(localStorage)에만 저장한다. 저장소를 쓸 수 없으면 조용히 건너뛴다.
const RECENT_KEY = "thread:recentSearches";
const RECENT_MAX = 5;

function readRecent() {
  try {
    const saved = JSON.parse(localStorage.getItem(RECENT_KEY) || "[]");
    return Array.isArray(saved) ? saved.filter((q) => typeof q === "string") : [];
  } catch {
    return [];
  }
}

function writeRecent(list) {
  try {
    localStorage.setItem(RECENT_KEY, JSON.stringify(list));
  } catch {
    /* 사생활 보호 모드 등: 저장하지 않음 */
  }
}

function renderRecent() {
  const box = document.querySelector("#searchModal .search-recent");
  if (!box) return;
  const searchUrl = document.querySelector("#searchModal form").action;
  const recent = readRecent();
  const list = box.querySelector(".search-recent-list");
  list.replaceChildren(
    ...recent.map((q) => {
      const link = document.createElement("a");
      link.className = "search-chip";
      link.href = `${searchUrl}?q=${encodeURIComponent(q)}`;
      link.textContent = q; // textContent라서 검색어가 HTML로 해석되지 않음
      return link;
    })
  );
  box.hidden = recent.length === 0;
}

document.querySelectorAll(".search-form").forEach((form) => {
  form.addEventListener("submit", () => {
    const q = form.querySelector("input[name='q']").value.trim();
    if (q) writeRecent([q, ...readRecent().filter((item) => item !== q)].slice(0, RECENT_MAX));
  });
  // 결과 페이지: 검색 범위를 바꾸면 같은 검색어로 바로 다시 검색
  form.querySelectorAll("input[name='type']").forEach((radio) => {
    radio.addEventListener("change", () => {
      if (form.querySelector("input[name='q']").value.trim()) form.requestSubmit();
    });
  });
});

const searchModal = document.querySelector("#searchModal");
if (searchModal) {
  searchModal.addEventListener("show.bs.modal", renderRecent);
  searchModal.addEventListener("shown.bs.modal", () => searchModal.querySelector("input[name='q']").focus());
  searchModal.querySelector(".search-recent-clear").addEventListener("click", () => {
    writeRecent([]);
    renderRecent();
  });
}

// ===== 알림 토스트 (Django messages) =====
document.querySelectorAll(".thread-toast").forEach((el) => bootstrap.Toast.getOrCreateInstance(el).show());

// ===== 로그인·회원가입: 비밀번호 보기 토글 =====
document.querySelectorAll(".auth-password-toggle").forEach((button) => {
  button.addEventListener("click", () => {
    const input = button.parentElement.querySelector("input");
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    button.setAttribute("aria-pressed", show);
    button.setAttribute("aria-label", show ? "비밀번호 숨기기" : "비밀번호 보기");
    button.querySelector("i").className = show ? "bi bi-eye-slash" : "bi bi-eye";
  });
});

// ===== 쓰레드 =====
// Django CSRF 토큰 (fetch POST에 필요)
function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : "";
}

// 좋아요: 새로고침 없이 토글. 로그인하지 않았으면 서버가 401과 로그인 주소를 돌려준다
document.querySelectorAll(".thread-like").forEach((button) => {
  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      const response = await fetch(button.dataset.url, {
        method: "POST",
        headers: { "X-CSRFToken": getCookie("csrftoken") },
      });
      if (response.status === 401) {
        window.location.href = (await response.json()).login_url;
        return;
      }
      if (!response.ok) return;
      const { liked, count } = await response.json();
      button.classList.toggle("is-liked", liked);
      button.setAttribute("aria-pressed", liked);
      button.querySelector("i").className = liked ? "bi bi-heart-fill" : "bi bi-heart";
      button.querySelector(".thread-like-count").textContent = count;
      if (liked) {
        button.classList.remove("pop");
        void button.offsetWidth; // 애니메이션 다시 재생
        button.classList.add("pop");
      }
    } finally {
      button.disabled = false;
    }
  });
});

// 작성·수정: 글자 수 표시
document.querySelectorAll(".char-count").forEach((counter) => {
  const field = document.getElementById(counter.dataset.for);
  const update = () => (counter.textContent = field.value.length);
  field.addEventListener("input", update);
  update();
});

// 작성·수정: 이미지 미리보기
document.querySelectorAll(".thread-form input[type='file']").forEach((input) => {
  const preview = input.closest("div").querySelector(".thread-image-preview");
  input.addEventListener("change", () => {
    const [file] = input.files;
    if (preview.src) URL.revokeObjectURL(preview.src);
    preview.hidden = !file;
    if (file) preview.src = URL.createObjectURL(file);
  });
});

// "쓰레드 작성"(책 미선택) → 검색 오버레이 제목을 안내 문구로 바꿔서 연다
document.querySelectorAll("[data-search-hint]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelector("#searchModalLabel").textContent = button.dataset.searchHint;
  });
});
if (searchModal) {
  searchModal.addEventListener("hidden.bs.modal", () => {
    document.querySelector("#searchModalLabel").textContent = "도서 검색";
  });
}

// ===== 담기 (책 상세 버튼, 마이페이지 "빼기") =====
async function toggleArchive(url) {
  const response = await fetch(url, { method: "POST", headers: { "X-CSRFToken": getCookie("csrftoken") } });
  if (response.status === 401) {
    window.location.href = (await response.json()).login_url;
    return null;
  }
  return response.ok ? (await response.json()).archived : null;
}

document.querySelectorAll("[data-archive-url]").forEach((button) => {
  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      const archived = await toggleArchive(button.dataset.archiveUrl);
      if (archived === null) return;
      button.classList.toggle("is-archived", archived);
      button.setAttribute("aria-pressed", archived);
      button.querySelector("i").className = archived ? "bi bi-archive-fill me-1" : "bi bi-archive me-1";
      button.querySelector("span").textContent = archived ? "담았어요" : "담기";
    } finally {
      button.disabled = false;
    }
  });
});

// 마이페이지 담은 책: "빼기"를 누르면 서버에서 지우고 표지 칸을 없앤다
document.querySelectorAll("[data-archive-remove]").forEach((button) => {
  button.addEventListener("click", async () => {
    button.disabled = true;
    const archived = await toggleArchive(button.dataset.archiveRemove);
    if (archived === false) {
      const tile = button.closest(".shelf-item");
      tile.classList.add("is-removing");
      setTimeout(() => tile.remove(), 300);
      const counter = document.querySelector("[data-stat='archives']");
      if (counter) counter.textContent = Math.max(0, Number(counter.textContent) - 1);
    } else {
      button.disabled = false;
    }
  });
});

// ===== AI 추천 (메인) =====
// 결과는 textContent로만 그려서 응답 내용이 HTML로 해석되지 않게 한다
const aiForm = document.querySelector(".ai-form");
if (aiForm) {
  const box = document.querySelector(".ai-result");
  const head = box.querySelector(".ai-result-head");
  const cards = box.querySelector(".ai-cards");
  const note = box.querySelector(".ai-result-note");
  const input = aiForm.querySelector("input[name='q']");
  const button = aiForm.querySelector("button[type='submit']");

  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  };

  const showLoading = (query) => {
    box.hidden = false;
    head.className = "ai-result-head";
    head.textContent = `“${query}”에 맞는 책을 AI가 고르는 중… (10~20초 걸릴 수 있어요)`;
    cards.replaceChildren(...[0, 1, 2].map(() => el("div", "ai-card is-skeleton")));
    note.textContent = "";
  };

  const showError = (message, loginUrl) => {
    head.className = "ai-result-head ai-result-error";
    head.textContent = message;
    cards.replaceChildren();
    note.replaceChildren();
    if (loginUrl) {
      const link = el("a", "", "로그인하러 가기");
      link.href = loginUrl;
      note.append(link);
    }
  };

  const showResult = (data) => {
    head.className = "ai-result-head";
    head.textContent = data.ai ? data.summary || `“${data.query}” 추천 도서` : `“${data.query}” 검색 결과`;
    (data.keywords || []).forEach((keyword) => head.append(el("span", "ai-keyword", `#${keyword}`)));
    cards.replaceChildren(
      ...data.books.map((book) => {
        const card = el("a", "ai-card");
        card.href = book.url;
        const img = el("img");
        img.src = book.cover_url;
        img.alt = "";
        const body = el("div");
        body.append(el("p", "ai-card-title", book.title));
        body.append(el("p", "ai-card-meta", [book.author, book.publisher, book.year].filter(Boolean).join(" · ")));
        if (book.reason) body.append(el("p", "ai-card-reason", book.reason));
        card.append(img, body);
        return card;
      })
    );
    if (!data.books.length) head.textContent = `“${data.query}”에 맞는 책을 찾지 못했어요. 다른 말로 다시 시도해 보세요.`;
    note.textContent = data.ai
      ? "AI(Claude)가 알라딘 도서 중에서 고른 추천이에요. 추천 이유는 AI가 작성했어요."
      : "AI 추천을 불러오지 못해 알라딘 검색 결과를 대신 보여드려요.";
  };

  const run = async (query) => {
    query = query.trim();
    if (query.length < 2) {
      box.hidden = false;
      showError("검색어를 2자 이상 입력해 주세요.");
      return;
    }
    button.disabled = true;
    showLoading(query);
    try {
      const response = await fetch(aiForm.action, { method: "POST", body: new FormData(aiForm) });
      const data = await response.json();
      if (!response.ok) showError(data.error || "추천을 받지 못했어요.", data.login_url);
      else showResult(data);
    } catch {
      showError("네트워크 오류로 추천을 받지 못했어요. 잠시 후 다시 시도해 주세요.");
    } finally {
      button.disabled = false;
    }
  };

  aiForm.addEventListener("submit", (event) => {
    event.preventDefault();
    run(input.value);
  });
  document.querySelectorAll("[data-ai-example]").forEach((chip) => {
    chip.addEventListener("click", () => {
      input.value = chip.dataset.aiExample;
      run(input.value);
    });
  });
}
