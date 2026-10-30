// 회사명 제출 -> 크롤링 진행 상황 스트리밍 표시 -> 완료 시 결과 페이지로 이동
const form = document.getElementById('crawl-form');
const input = document.getElementById('company');
const progressBox = document.getElementById('progress');
const progressLog = document.getElementById('progress-log');
const errorBox = document.getElementById('error');
const submitButton = form.querySelector('button');

function addLog(message) {
  const li = document.createElement('li');
  li.textContent = message;
  progressLog.appendChild(li);
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
}

let finished = false;

function handleEvent(event) {
  if (event.type === 'progress') addLog(event.message);
  else if (event.type === 'error') { finished = true; showError(event.message); }
  else if (event.type === 'done') { finished = true; window.location.href = `/results/${event.id}/`; }
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const company = input.value.trim();
  if (!company) {  // 입력값이 없으면 아무 동작도 하지 않는다
    input.focus();
    return;
  }

  finished = false;
  errorBox.hidden = true;
  progressLog.innerHTML = '';
  progressBox.hidden = false;
  submitButton.disabled = true;

  try {
    const response = await fetch(`${form.action}?company=${encodeURIComponent(company)}`);
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();
      lines.filter(Boolean).forEach((line) => handleEvent(JSON.parse(line)));
    }
    if (buffer.trim()) handleEvent(JSON.parse(buffer));
    if (!finished) showError('서버 처리 중 예기치 못한 오류로 요청이 중단되었습니다.');
  } catch (err) {
    showError(`요청 처리 중 오류가 발생했습니다: ${err.message}`);
  } finally {
    progressBox.hidden = true;
    submitButton.disabled = false;
  }
});
