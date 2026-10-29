<div align="center">

# 📚 02-pjt

### 알라딘 API로 도서 데이터 수집하고 🎧 음성으로 듣기

API 요청을 통해 데이터를 직접 수집하고, 필요한 형태로 가공·저장한 뒤 <br>
gTTS로 오디오 파일까지 만들어보는 프로젝트

<br>

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![Requests](https://img.shields.io/badge/requests-2C2C2C?style=flat-square)
![gTTS](https://img.shields.io/badge/gTTS-4285F4?style=flat-square&logo=googletranslate&logoColor=white)
![dotenv](https://img.shields.io/badge/python--dotenv-ECD53F?style=flat-square)
![VSCode](https://img.shields.io/badge/VS%20Code-007ACC?style=flat-square&logo=visualstudiocode&logoColor=white)

`2026.09.04` · 페어 프로그래밍

</div>

<br>

## 🗂️ 진행 범위

| 그룹 | 문제 | 상태 |
| :---: | --- | :---: |
| **A** | A1 · A2 · A3 | ✅ 완료 |
| **B** | B1 · B2 · B3 | ✅ 완료 |
| **C** | C1 · C2 · C3 | ⬜ 미진행 |

<br>

## 🧰 사용 기술

| 구분 | 내용 |
| --- | --- |
| 🐍 언어 | Python 3.11+ |
| 🌐 외부 API | 알라딘 상품 검색 API (`ItemSearch`) |
| 📦 라이브러리 | `requests` · `python-dotenv` · `gTTS` |
| 🔧 내장 모듈 | `os` · `json` · `pathlib` |

<br>

## 📁 프로젝트 구조

```
02-pjt/
├── 📄 problem_A1.py                 # 도서 검색 및 제목 출력
├── 📄 problem_A2.py                 # 도서 정보 가공 후 txt 저장
├── 📄 problem_A3.py                 # 도서 제목 TTS 변환
├── 📄 problem_B1.py                 # 주제별 데이터 수집 및 통계
├── 📄 problem_B2.py                 # 할인 여부 기준 분류 후 JSON 저장
├── 📄 problem_B3.py                 # 데이터 요약 TTS 생성
├── 📂 output/                       # 실행 시 자동 생성
│   ├── 📝 computer_books.txt
│   ├── 🔊 book_title.mp3
│   ├── 🗃️ discounted_books.json
│   ├── 🗃️ regular_priced_books.json
│   ├── 🗃️ korean_literature_books.json
│   └── 🔊 book_1.mp3 ~ book_5.mp3
├── 🔐 .env                          # API 키 (git 관리 제외)
└── 📋 requirements.txt
```

<br>

## 🚀 실행 방법

**1️⃣ 가상환경 생성 및 패키지 설치**

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**2️⃣ `.env` 파일 작성**

프로젝트 루트에 `.env` 파일을 만들고 알라딘에서 발급받은 TTB 키를 넣습니다.

```env
MY_TTBKEY=발급받은_API_키
```

**3️⃣ 실행**

```bash
python problem_A1.py
```

<br>

---

<br>

# 🅰️ 그룹 A

<br>

## 1️⃣ A1 · API 요청 함수 작성하기

> 🎯 `F201` `F202` `F203` `F204`

`requests`로 알라딘 API에 GET 요청을 보내고, 응답을 `.json()`으로 파싱해 반환하는 `fetch_books` 함수를 구현했습니다. 검색 키워드는 **"펭귄"**, 결과 10건에 번호를 붙여 출력합니다.

```python
params = {
    'TTBKey': MY_TTBKEY,
    'Query': keyword,
    'output': 'js',
    'Version': '20131101',
}
response = requests.get(ALADIN_SEARCH_URL, params=params, timeout=5)
data = response.json()
```

<img src="skeleton/output_img/A1.png" width="600">

<br><br>

## 2️⃣ A2 · 도서 데이터 가공 및 저장

> 🎯 `F205`

**"컴퓨터"** 키워드로 검색한 결과에서 제목 · 저자 · 출판사 · 정가(`priceStandard`)만 추출해 마크다운 형식으로 가공하고, `output/computer_books.txt`로 저장했습니다.

- 📌 `mkdir(parents=True, exist_ok=True)`로 폴더가 이미 있어도 에러가 나지 않도록 처리
- 📌 응답 데이터의 도서 목록은 최상위가 아니라 **`item` 키 아래**에 들어 있음

<img src="skeleton/output_img/A2.png" width="600">

<br><br>

## 3️⃣ A3 · TTS 파일 생성하기

> 🎯 `F206`

`fetch_book_title`로 검색 결과의 첫 번째 도서 제목을 가져오고, `create_tts_file`에서 gTTS로 음성 변환해 `output/book_title.mp3`로 저장했습니다.

검색 결과가 0건일 때 `IndexError`가 나지 않도록 리스트를 먼저 확인하고, `title`이 없으면 실패 메시지를 출력하도록 분기했습니다.

```python
items = data.get('item', [])
title = items[0].get('title') if items else None
```

<img src="skeleton/output_img/A3.png" width="600">

<br>

---

<br>

# 🅱️ 그룹 B

<br>

## 4️⃣ B1 · 다양한 주제 데이터 수집 및 통합하기

> 🎯 `F207` `F208`

🌿 **자연** · 🎨 **예술** · ⚙️ **기술** 세 주제로 각각 30건씩, 총 **90건**을 수집해 주제별 평균 가격과 평균 출판 연도를 계산했습니다.

- 📌 출판 연도는 `pubDate`(`"2023-05-01"` 형태)에서 앞 4자리를 잘라 `int()`로 변환
- 📌 전체 평균은 주제별 평균을 다시 평균 내지 않고, **전체 도서의 합계를 총 권수로** 나누어 계산

<img src="skeleton/output_img/B1.png" width="600">

<br><br>

## 5️⃣ B2 · 데이터 분류 및 저장하기

> 🎯 `F209`

**"경제"** 관련 도서 50건을 수집하고 `priceSales < priceStandard` 조건으로 할인 도서와 정가 도서를 분류해 각각 JSON으로 저장했습니다.

| 분류 | 저장 경로 |
| --- | --- |
| 🏷️ 할인 중 | `output/discounted_books.json` |
| 💰 정가 | `output/regular_priced_books.json` |

> ⚠️ `json.dump()`에 `ensure_ascii=False`를 지정하지 않으면 한글이 `\uXXXX` 형태로 저장되어 파일을 열어도 읽을 수 없습니다. `indent=2`로 들여쓰기를 넣어 확인하기 쉽게 만들었습니다.

<img src="skeleton/output_img/B2.png" width="600">

**📄 생성된 JSON 일부**

<img src="skeleton/output_img/B2-json.png" width="800">

<br><br>

## 6️⃣ B3 · TTS를 활용하여 데이터 요약 오디오 만들기

> 🎯 `F210`

**"한국문학"** 주제 검색 결과 중 `description`이 있는 도서만 최대 5건 골라 제목과 요약을 JSON으로 정리하고, 각 도서의 제목 + 요약을 합쳐 `output/book_1.mp3` ~ `book_5.mp3`로 저장했습니다.

- 📌 `book.get('description')`은 키가 없을 때뿐 아니라 **빈 문자열일 때도 `False`** → 요약이 비어 있는 도서가 자연스럽게 걸러짐
- 📌 5건을 채우면 `break`로 반복을 중단해 불필요한 순회를 하지 않음
- 📌 `enumerate(books, 1)`로 파일명의 번호를 붙임

<img src="skeleton/output_img/B3.png" width="600">

**📄 생성된 JSON 일부**

<img src="skeleton/output_img/B3-json.png" width="800">

<br>

---

<br>

## 💡 배운 점

<br>

### 🌐 API 호출 흐름을 직접 다뤄본 것

이번 프로젝트를 통해 **API를 호출해서 사용하는 방법**을 자세히 알 수 있었습니다. 엔드포인트 URL에 파라미터를 붙여 요청을 보내고, 돌아온 응답을 JSON으로 변환해 필요한 필드를 꺼내 쓰는 과정을 여섯 개 문제에 걸쳐 반복하면서 흐름이 몸에 익었습니다.

API 문서를 처음부터 끝까지 직접 탐색하면서 코드를 만든 것은 아니었지만, `요청 → 응답 → 파싱 → 가공`이라는 구조 자체는 API가 달라져도 크게 다르지 않다는 점을 확인했습니다. 나중에 새로운 API를 만나도 문서에서 필요한 파라미터만 찾아 적용할 수 있을 것 같습니다.

<br>

### 🔒 `with` 문을 쓰는 이유

파일은 열면 알아서 닫히는 것이 아니라 **반드시 닫아야 한다**는 것, 그리고 `with`가 여는 것과 닫는 것을 한 번에 처리해준다는 것을 이해했습니다. 그동안 관습적으로 써 왔던 문법이었는데, 이번에 파일 입출력을 여러 번 다루면서 왜 필요한지를 알게 됐습니다.

```python
with path.open('w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
```

<br>

### 📂 코드 안에서 파일과 디렉토리 다루기

이전에도 해본 적이 있지만, 코드 안에서 폴더를 만들고 경로를 조합해 파일로 저장하는 방법을 다시 한번 익혔습니다. `pathlib`의 `/` 연산자로 경로를 조합하는 방식과 `mkdir(parents=True, exist_ok=True)`로 중복 생성 에러를 막는 방법이 특히 유용했습니다.

<br>

---

<br>

## 👥 페어 프로그래밍 회고

이번 프로젝트는 **페어 프로그래밍**으로 진행했습니다. 한 명이 어떤 식으로 코드를 작성할지 알려주고, 다른 한 명이 그 방향대로 구현하는 방식이었습니다.

실제로 해보니 처음 정한 역할대로 딱 나뉘지는 않았습니다. 구현하다 보면 자연스럽게 서로 대화하면서 함께 만들어가는 형태로 바뀌었습니다. 다만 그 과정에서 코드에 대해 계속 토론을 해야 했기 때문에, **혼자 작성할 때보다 코드를 훨씬 깊게 들여다보게 됐습니다.** "왜 여기서 이 값을 써야 하는지", "이 경우에는 어떻게 되는지"를 말로 설명해야 하니 대충 넘어갈 수가 없었습니다.

어려우면서도 도움이 되는 방식이라고 느꼈습니다. 🤝

<br>

---

<br>

## ⚠️ 실행 시 참고사항

- 🔄 알라딘 API는 **실시간 데이터**를 반환하므로 실행 시점에 따라 결과가 달라집니다.
- 🔢 `ItemSearch`의 `MaxResults` 최대값은 **50**이므로, 그 이상은 `start` 파라미터를 이용한 페이지네이션이 필요합니다.
- 🔐 `.env` 파일은 API 키가 들어가므로 **`.gitignore`에 반드시 추가**해야 합니다.

<br>
