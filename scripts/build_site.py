# -*- coding: utf-8 -*-
"""정적 사이트 빌드 스크립트.

data/days/*.json → docs/index.html(최신) + docs/archive/YYYY-MM-DD/index.html
외부 라이브러리 없이 인라인 CSS/JS만 사용 (TTS·녹음·타이머·플래시카드·퀴즈 전부 클라이언트).
"""
import html
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"

UNIT_COLORS = {
    1: "#6366f1", 2: "#0ea5e9", 3: "#10b981", 4: "#f59e0b",
    5: "#ef4444", 6: "#ec4899", 7: "#8b5cf6", 8: "#14b8a6",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def esc(s) -> str:
    return html.escape(str(s or ""))


def js_json(obj) -> str:
    """<script> 안에 안전하게 넣을 JSON."""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


# ================================================================ 페이지 템플릿

PAGE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root {
  --bg: #ffffff; --fg: #1a1a1a; --muted: #6b7280; --card: #f8f9fa;
  --line: #e5e7eb; --accent: __ACCENT__; --ok: #16a34a; --bad: #dc2626;
}
@media (prefers-color-scheme: dark) {
  :root { --bg: #111318; --fg: #e8eaed; --muted: #9aa0a6; --card: #1c1f26; --line: #2c313a; }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--fg);
  font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR", sans-serif;
  font-size: 17px; line-height: 1.7;
}
main { max-width: 680px; margin: 0 auto; padding: 20px 18px 96px; }
h1 { font-size: 1.35rem; line-height: 1.4; margin: 8px 0 4px; }
h2 { font-size: 1.05rem; margin: 0 0 12px; display: flex; align-items: center; gap: 8px; }
h2 .num {
  background: var(--accent); color: #fff; border-radius: 8px;
  width: 26px; height: 26px; display: inline-flex; align-items: center; justify-content: center;
  font-size: .85rem; flex: none;
}
.date { color: var(--muted); font-size: .9rem; }
.unit-badge {
  display: inline-block; color: var(--accent); border: 1px solid var(--accent);
  border-radius: 999px; padding: 1px 10px; font-size: .8rem; margin-bottom: 6px;
}
section { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 18px 16px; margin: 18px 0; }
.en { font-family: Georgia, "Times New Roman", serif; }
.q-en { font-size: 1.08rem; line-height: 1.65; }
.btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  min-height: 44px; min-width: 44px; padding: 8px 16px; border-radius: 12px;
  border: 1px solid var(--line); background: var(--bg); color: var(--fg);
  font-size: .95rem; cursor: pointer; touch-action: manipulation;
}
.btn:active { transform: scale(.97); }
.btn.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
.btn.small { min-height: 44px; padding: 6px 12px; font-size: .88rem; }
.btn-row { display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0; }
details { margin: 10px 0; }
summary { cursor: pointer; color: var(--muted); font-size: .92rem; min-height: 44px; display: flex; align-items: center; }
.hint { color: var(--muted); font-size: .88rem; }
.timer { font-variant-numeric: tabular-nums; font-size: 2rem; font-weight: 700; letter-spacing: 1px; }
.timer.warn { color: var(--bad); }
.script p { margin: 0 0 1em; font-size: 1.02rem; }
.al-point { border-left: 3px solid var(--accent); padding: 6px 12px; margin: 10px 0; background: var(--bg); border-radius: 0 10px 10px 0; font-size: .93rem; }
.structure { background: var(--bg); border: 1px dashed var(--line); border-radius: 10px; padding: 10px 14px; font-size: .9rem; color: var(--muted); }
/* 플래시카드 */
.fc-wrap { perspective: 1000px; }
.fc {
  position: relative; width: 100%; min-height: 240px; cursor: pointer;
  transform-style: preserve-3d; transition: transform .45s;
}
.fc.flipped { transform: rotateY(180deg); }
.fc-face {
  position: absolute; inset: 0; backface-visibility: hidden; -webkit-backface-visibility: hidden;
  background: var(--bg); border: 1.5px solid var(--line); border-radius: 16px;
  padding: 20px; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; gap: 8px;
}
.fc-back { transform: rotateY(180deg); }
.fc-word { font-size: 1.5rem; font-weight: 700; }
.fc-pos { color: var(--muted); font-size: .85rem; }
.fc-meaning { font-size: 1.2rem; font-weight: 700; }
.fc-ex { font-size: .92rem; color: var(--muted); }
.tier { font-size: .75rem; border-radius: 999px; padding: 1px 10px; }
.tier.core { background: var(--accent); color: #fff; }
.tier.extend { border: 1px solid var(--accent); color: var(--accent); }
.fc-progress { text-align: center; color: var(--muted); font-size: .88rem; margin-top: 8px; }
/* 퀴즈 */
.quiz-q { background: var(--bg); border: 1px solid var(--line); border-radius: 12px; padding: 14px; margin: 12px 0; }
.quiz-q .qt { font-size: .95rem; margin-bottom: 10px; white-space: pre-line; }
.choice {
  display: block; width: 100%; text-align: left; margin: 6px 0; padding: 10px 14px; min-height: 44px;
  border: 1px solid var(--line); border-radius: 10px; background: var(--card); color: var(--fg);
  font-size: .92rem; cursor: pointer;
}
.choice.correct { border-color: var(--ok); background: color-mix(in srgb, var(--ok) 12%, var(--card)); }
.choice.wrong { border-color: var(--bad); background: color-mix(in srgb, var(--bad) 12%, var(--card)); }
.choice:disabled { cursor: default; opacity: .85; }
.quiz-score { font-weight: 700; text-align: center; padding: 12px; }
/* 패턴 */
.pattern-card { background: var(--bg); border: 1px solid var(--line); border-radius: 12px; padding: 14px; margin: 12px 0; }
.pattern-card .p-en { font-weight: 700; font-size: 1.02rem; }
.pattern-card .p-line { font-size: .9rem; margin-top: 6px; }
.label { display: inline-block; font-size: .75rem; color: var(--accent); border: 1px solid var(--accent); border-radius: 6px; padding: 0 6px; margin-right: 6px; }
/* 체크리스트 */
.check { display: flex; gap: 10px; align-items: flex-start; padding: 8px 0; font-size: .93rem; }
.check input { width: 22px; height: 22px; margin-top: 3px; accent-color: var(--accent); flex: none; }
audio { width: 100%; margin-top: 8px; }
.note { font-size: .85rem; color: var(--muted); }
/* 하단 내비게이션 */
nav.bottom {
  position: fixed; bottom: 0; left: 0; right: 0; background: var(--bg);
  border-top: 1px solid var(--line); display: flex; z-index: 10;
  padding-bottom: env(safe-area-inset-bottom);
}
nav.bottom a {
  flex: 1; text-align: center; padding: 12px 0 10px; min-height: 48px;
  color: var(--muted); text-decoration: none; font-size: .82rem;
}
nav.bottom a.active { color: var(--accent); font-weight: 700; }
nav.bottom a span { display: block; font-size: 1.15rem; }
</style>
</head>
<body>
<main>
__CONTENT__
</main>
<nav class="bottom">
  <a href="__ROOT__index.html" class="__NAV_TODAY__"><span>🎙️</span>오늘</a>
  <a href="__ROOT__vocab/" class="__NAV_VOCAB__"><span>📚</span>단어장</a>
  <a href="__ROOT__archive/" class="__NAV_ARCHIVE__"><span>🗂️</span>아카이브</a>
  <a href="__ROOT__curriculum/" class="__NAV_CURR__"><span>📈</span>진도</a>
</nav>
<script>
__DATA__
/* ============================ TTS (Web Speech API) */
var ttsOK = ('speechSynthesis' in window);
var voices = [];
function refreshVoices(){ voices = speechSynthesis.getVoices(); }
if (ttsOK) { refreshVoices(); speechSynthesis.onvoiceschanged = refreshVoices; }
function enVoice(){
  return voices.find(function(v){ return v.name.indexOf('Google US English') >= 0; })
      || voices.find(function(v){ return v.lang === 'en-US'; })
      || voices.find(function(v){ return v.lang && v.lang.indexOf('en') === 0; })
      || null;
}
function speak(text, rate){
  if (!ttsOK) return;
  speechSynthesis.cancel();
  var u = new SpeechSynthesisUtterance(text);
  u.lang = 'en-US'; u.rate = rate || 1.0;
  var v = enVoice(); if (v) u.voice = v;
  speechSynthesis.speak(u);
}
if (!ttsOK) {
  document.querySelectorAll('.tts').forEach(function(b){ b.style.display = 'none'; });
  document.querySelectorAll('.tts-note').forEach(function(n){ n.textContent = '이 브라우저는 음성 재생(TTS)을 지원하지 않습니다.'; });
}
document.addEventListener('click', function(e){
  var t = e.target.closest('[data-say]');
  if (t) { e.stopPropagation(); speak(t.getAttribute('data-say'), parseFloat(t.getAttribute('data-rate') || '1')); }
});
document.querySelectorAll('[data-tts-stop]').forEach(function(b){
  b.addEventListener('click', function(){ if (ttsOK) speechSynthesis.cancel(); });
});
/* ============================ 타이머 (90초 + 종료 비프) */
function beep(){
  try {
    var ctx = new (window.AudioContext || window.webkitAudioContext)();
    [0, 0.45].forEach(function(dt){
      var o = ctx.createOscillator(), g = ctx.createGain();
      o.connect(g); g.connect(ctx.destination);
      o.frequency.value = 880; g.gain.value = 0.12;
      o.start(ctx.currentTime + dt); o.stop(ctx.currentTime + dt + 0.3);
    });
  } catch (e) {}
}
function makeTimer(root, seconds){
  var left = seconds, iv = null;
  var disp = root.querySelector('.timer');
  var startBtn = root.querySelector('.t-start'), resetBtn = root.querySelector('.t-reset');
  function show(){
    var m = Math.floor(left / 60), s = left % 60;
    disp.textContent = m + ':' + (s < 10 ? '0' : '') + s;
    disp.classList.toggle('warn', left <= 10);
  }
  function stop(){ if (iv) { clearInterval(iv); iv = null; } startBtn.textContent = '▶ 시작'; }
  startBtn.addEventListener('click', function(){
    if (iv) { stop(); return; }
    startBtn.textContent = '⏸ 일시정지';
    iv = setInterval(function(){
      left--;
      if (left <= 0) { left = 0; show(); stop(); beep(); disp.textContent = '⏰ 종료!'; return; }
      show();
    }, 1000);
  });
  resetBtn.addEventListener('click', function(){ stop(); left = seconds; show(); });
  show();
}
document.querySelectorAll('.timer-box').forEach(function(el){ makeTimer(el, parseInt(el.getAttribute('data-sec') || '90', 10)); });
/* ============================ 녹음 (MediaRecorder) */
function makeRecorder(root){
  var btn = root.querySelector('.rec-btn'), status = root.querySelector('.rec-status');
  var player = root.querySelector('.rec-player'), dl = root.querySelector('.rec-dl');
  var mr = null, chunks = [];
  if (!navigator.mediaDevices || !window.MediaRecorder) {
    btn.style.display = 'none'; status.textContent = '이 브라우저는 녹음을 지원하지 않습니다.'; return;
  }
  btn.addEventListener('click', function(){
    if (mr && mr.state === 'recording') { mr.stop(); return; }
    navigator.mediaDevices.getUserMedia({ audio: true }).then(function(stream){
      chunks = [];
      mr = new MediaRecorder(stream);
      mr.ondataavailable = function(e){ chunks.push(e.data); };
      mr.onstop = function(){
        stream.getTracks().forEach(function(t){ t.stop(); });
        var mime = (mr.mimeType && mr.mimeType.split(';')[0]) || 'audio/webm';
        var ext = mime.indexOf('mp4') >= 0 ? 'm4a' : 'webm';   /* iOS Safari는 mp4로 녹음됨 */
        var blob = new Blob(chunks, { type: mime });
        var url = URL.createObjectURL(blob);
        player.src = url; player.style.display = 'block';
        dl.href = url; dl.download = (DAY.date || 'opic') + '_recording.' + ext; dl.style.display = 'inline-flex';
        btn.textContent = '🎙️ 다시 녹음'; btn.classList.remove('primary');
        status.textContent = '녹음 완료 — 아래에서 다시 들어보세요.';
      };
      mr.start();
      btn.textContent = '⏹ 녹음 정지'; btn.classList.add('primary');
      status.textContent = '녹음 중... (파일은 이 기기에만 저장됩니다)';
    }).catch(function(){
      status.textContent = '마이크 권한이 거부되었습니다. 브라우저 설정에서 마이크를 허용해 주세요.';
    });
  });
}
document.querySelectorAll('.rec-box').forEach(makeRecorder);
/* ============================ 퀴즈 엔진 */
function shuffle(a){
  a = a.slice();
  for (var i = a.length - 1; i > 0; i--) {
    var j = Math.floor(Math.random() * (i + 1)), t = a[i]; a[i] = a[j]; a[j] = t;
  }
  return a;
}
function renderQuiz(root, questions, opts){
  opts = opts || {};
  root.innerHTML = '';
  var answered = 0, correct = 0, done = false;
  var timerEl = null, iv = null;
  if (opts.timeLimit) {
    timerEl = document.createElement('div');
    timerEl.className = 'timer'; timerEl.style.textAlign = 'center';
    root.appendChild(timerEl);
    var left = opts.timeLimit;
    var tick = function(){
      var m = Math.floor(left / 60), s = left % 60;
      timerEl.textContent = m + ':' + (s < 10 ? '0' : '') + s;
      timerEl.classList.toggle('warn', left <= 15);
      if (left <= 0) { clearInterval(iv); beep(); finish(true); }
      left--;
    };
    tick(); iv = setInterval(tick, 1000);
  }
  var scoreEl = document.createElement('div');
  function finish(timeout){
    if (done) return; done = true;
    if (iv) clearInterval(iv);
    root.querySelectorAll('.choice').forEach(function(b){ b.disabled = true; });
    scoreEl.className = 'quiz-score';
    scoreEl.textContent = (timeout ? '⏰ 시간 종료! ' : '🎉 ') + questions.length + '문제 중 ' + correct + '개 정답';
    root.appendChild(scoreEl);
  }
  questions.forEach(function(q, qi){
    var box = document.createElement('div'); box.className = 'quiz-q';
    var qt = document.createElement('div'); qt.className = 'qt';
    qt.textContent = 'Q' + (qi + 1) + '. ' + q.question;
    box.appendChild(qt);
    q.choices.forEach(function(c, ci){
      var b = document.createElement('button');
      b.className = 'choice'; b.textContent = c;
      b.addEventListener('click', function(){
        if (b.disabled || done) return;
        box.querySelectorAll('.choice').forEach(function(x){ x.disabled = true; });
        if (ci === q.answer_index) { b.classList.add('correct'); correct++; }
        else {
          b.classList.add('wrong');
          box.querySelectorAll('.choice')[q.answer_index].classList.add('correct');
        }
        answered++;
        if (answered === questions.length) finish(false);
      });
      box.appendChild(b);
    });
    root.appendChild(box);
  });
}
function matchingFrom(words, pool){
  var meanings = (pool || words).map(function(w){ return w.meaning; });
  return shuffle(words).map(function(w){
    var others = shuffle(meanings.filter(function(m){ return m !== w.meaning; })).slice(0, 3);
    var choices = shuffle([w.meaning].concat(others));
    return { question: "'" + w.word + "'의 뜻은?", choices: choices, answer_index: choices.indexOf(w.meaning) };
  });
}
/* ============================ 플래시카드 */
(function(){
  var wrap = document.getElementById('flashcards');
  if (!wrap || !DAY.vocab) return;
  var cards = DAY.vocab, i = 0, memorized = {};
  var fc = wrap.querySelector('.fc'), front = wrap.querySelector('.fc-front'), back = wrap.querySelector('.fc-back');
  var prog = wrap.querySelector('.fc-progress');
  function render(){
    var w = cards[i];
    fc.classList.remove('flipped');
    var tierHtml = w.tier === 'core'
      ? '<span class="tier core">핵심</span>'
      : '<span class="tier extend">확장 · ' + w.linked_word + ' 대신</span>';
    front.innerHTML = tierHtml
      + '<div class="fc-word en">' + w.word + '</div>'
      + '<div class="fc-pos">' + w.pos + '</div>'
      + '<button class="btn small tts" data-say="' + w.word.replace(/"/g, '&quot;') + '">🔊 발음</button>'
      + '<div class="hint">탭하면 뜻이 나옵니다</div>';
    back.innerHTML = '<div class="fc-meaning">' + w.meaning + '</div>'
      + '<div class="fc-ex en">' + w.example + '</div>'
      + '<div class="fc-ex">🧩 ' + w.collocation + '</div>';
    var doneCnt = Object.keys(memorized).length;
    prog.textContent = (i + 1) + ' / ' + cards.length + (doneCnt ? ' · 외운 단어 ' + doneCnt + '개' : '');
    if (!ttsOK) front.querySelectorAll('.tts').forEach(function(b){ b.style.display = 'none'; });
  }
  fc.addEventListener('click', function(e){
    if (e.target.closest('.tts')) return;
    fc.classList.toggle('flipped');
  });
  function move(d){ i = (i + d + cards.length) % cards.length; render(); }
  wrap.querySelector('.fc-prev').addEventListener('click', function(){ move(-1); });
  wrap.querySelector('.fc-next').addEventListener('click', function(){ move(1); });
  wrap.querySelector('.fc-done').addEventListener('click', function(){ memorized[i] = true; move(1); });
  var sx = null;
  fc.addEventListener('touchstart', function(e){ sx = e.touches[0].clientX; }, { passive: true });
  fc.addEventListener('touchend', function(e){
    if (sx === null) return;
    var dx = e.changedTouches[0].clientX - sx;
    if (Math.abs(dx) > 45) move(dx < 0 ? 1 : -1);
    sx = null;
  }, { passive: true });
  render();
})();
/* ============================ 오늘의 미니 테스트 7문제 */
(function(){
  var root = document.getElementById('vocab-quiz');
  if (!root || !DAY.vocab_quiz) return;
  document.getElementById('vocab-quiz-start').addEventListener('click', function(){
    this.style.display = 'none';
    renderQuiz(root, DAY.vocab_quiz);
  });
})();
/* ============================ 어제 단어 초스피드 테스트 (90초) */
(function(){
  var root = document.getElementById('speed-quiz');
  if (!root || !YESTERDAY_WORDS.length) return;
  document.getElementById('speed-quiz-start').addEventListener('click', function(){
    this.style.display = 'none';
    renderQuiz(root, matchingFrom(YESTERDAY_WORDS), { timeLimit: 90 });
  });
})();
/* ============================ 주말 종합 테스트 (30문제) */
(function(){
  var root = document.getElementById('weekly-quiz');
  if (!root || !DAY.weekly_words) return;
  document.getElementById('weekly-quiz-start').addEventListener('click', function(){
    this.style.display = 'none';
    renderQuiz(root, matchingFrom(DAY.weekly_words, DAY.all_week_words));
  });
})();
__EXTRA_JS__
</script>
</body>
</html>
"""


# ================================================================ 섹션 렌더링

def timer_html(sec: int = 90) -> str:
    return f"""
    <div class="timer-box" data-sec="{sec}">
      <div class="timer">1:30</div>
      <div class="btn-row">
        <button class="btn primary t-start">▶ 시작</button>
        <button class="btn t-reset">↺ 리셋</button>
      </div>
    </div>"""


def recorder_html() -> str:
    return """
    <div class="rec-box">
      <div class="btn-row">
        <button class="btn rec-btn">🎙️ 녹음 시작</button>
        <a class="btn rec-dl" style="display:none">⬇ 파일 저장</a>
      </div>
      <div class="rec-status note">녹음은 이 기기에서만 재생·저장됩니다 (서버 업로드 없음).</div>
      <audio class="rec-player" controls style="display:none"></audio>
    </div>"""


def sec_question(day: dict) -> str:
    q = day["question"]
    return f"""
<section>
  <h2><span class="num">1</span>오늘의 질문</h2>
  <p class="en q-en">{esc(q["english"])}</p>
  <div class="btn-row">
    <button class="btn tts" data-say="{esc(q["english"])}">🔊 질문 듣기</button>
    <button class="btn tts" data-tts-stop>⏹ 정지</button>
  </div>
  <p class="note tts-note"></p>
  <details><summary>🇰🇷 한국어 해석 보기</summary>
    <p>{esc(q["korean"])}</p>
    <p class="hint">💡 콤보 맥락: {esc(q.get("combo_context", ""))}</p>
  </details>
  <hr style="border:none;border-top:1px solid var(--line)">
  <p><b>먼저 스스로 답해보세요!</b> <span class="hint">모범답변을 보기 전에 1분 30초 동안 녹음해 보세요.</span></p>
  {timer_html(90)}
  {recorder_html()}
</section>"""


def sec_answer(day: dict) -> str:
    ma = day["model_answer"]
    paragraphs = "".join(f"<p>{esc(p)}</p>" for p in ma["script"].split("\n\n") if p.strip())
    points = "".join(f'<div class="al-point">✨ {esc(p)}</div>' for p in ma["al_points"])
    script_attr = esc(ma["script"].replace("\n", " "))
    return f"""
<section>
  <h2><span class="num">2</span>AL 모범답변 + 전략 해설</h2>
  <details>
    <summary>🔒 스스로 답한 후 열어보세요 — 탭해서 열기</summary>
    <div class="btn-row">
      <button class="btn tts" data-say="{script_attr}" data-rate="0.8">🐢 0.8x 재생</button>
      <button class="btn tts" data-say="{script_attr}" data-rate="1.0">▶ 1.0x 재생</button>
      <button class="btn tts" data-tts-stop>⏹ 정지</button>
    </div>
    <div class="script en">{paragraphs}</div>
    <div class="structure">🧭 <b>답변 뼈대</b><br>{esc(ma["structure_note"])}</div>
    <h3 style="font-size:.98rem">이 답변이 AL인 이유 3가지</h3>
    {points}
  </details>
</section>"""


def sec_vocab() -> str:
    return """
<section>
  <h2><span class="num">3</span>오늘의 단어 15 <span class="hint">(핵심 10 + 확장 5)</span></h2>
  <p class="hint">카드를 탭하면 뜻이 뒤집혀 나옵니다. 확장 카드에는 어떤 핵심 단어의 대체어인지 표시됩니다.</p>
  <div id="flashcards">
    <div class="fc-wrap">
      <div class="fc">
        <div class="fc-face fc-front"></div>
        <div class="fc-face fc-back"></div>
      </div>
    </div>
    <div class="fc-progress"></div>
    <div class="btn-row" style="justify-content:center">
      <button class="btn fc-prev">◀ 이전</button>
      <button class="btn primary fc-done">다 외웠어요 ✓</button>
      <button class="btn fc-next">다음 ▶</button>
    </div>
  </div>
  <hr style="border:none;border-top:1px solid var(--line);margin:18px 0">
  <h3 style="font-size:.98rem">📝 미니 테스트 7문제 <span class="hint">(뜻 매칭 3 · 빈칸 2 · 교체어 2)</span></h3>
  <button class="btn primary" id="vocab-quiz-start">테스트 시작</button>
  <div id="vocab-quiz"></div>
</section>"""


def sec_patterns(day: dict) -> str:
    cards = ""
    for p in day["patterns"]:
        cards += f"""
    <div class="pattern-card">
      <div class="p-en en">{esc(p["pattern"])}</div>
      <div class="p-line">{esc(p["meaning"])}</div>
      <div class="p-line"><span class="label">오늘 답변</span><span class="en">{esc(p["usage_today"])}</span></div>
      <div class="p-line"><span class="label">응용</span><span class="en">{esc(p["extra_example"])}</span></div>
      <div class="btn-row"><button class="btn small tts" data-say="{esc(p["usage_today"])}">🔊 듣기</button></div>
    </div>"""
    return f"""
<section>
  <h2><span class="num">4</span>오늘의 패턴 2</h2>
  {cards}
</section>"""


def sec_review(day: dict, has_yesterday: bool) -> str:
    speed = ""
    if has_yesterday:
        speed = """
  <h3 style="font-size:.98rem">⚡ 어제 단어 15개 초스피드 테스트 <span class="hint">(90초 컷)</span></h3>
  <button class="btn primary" id="speed-quiz-start">90초 테스트 시작</button>
  <div id="speed-quiz"></div>
  <hr style="border:none;border-top:1px solid var(--line);margin:18px 0">"""
    else:
        speed = '<p class="hint">어제 학습 기록이 없어 초스피드 테스트는 내일부터 시작됩니다.</p>'

    rw = ""
    if day.get("review_words"):
        items = ""
        for w in day["review_words"]:
            items += f"""
      <div class="pattern-card">
        <div class="p-en en">{esc(w["word"])} <span class="hint">({esc(w["learned_date"])} 학습)</span></div>
        <div class="p-line"><span class="label">새 예문</span><span class="en">{esc(w["new_example"])}</span></div>
        <div class="btn-row"><button class="btn small tts" data-say="{esc(w["new_example"])}">🔊 듣기</button></div>
      </div>"""
        rw = f'<h3 style="font-size:.98rem">🔁 3일 전 · 7일 전 단어 재노출</h3>{items}'

    rp = ""
    if day.get("review_patterns"):
        items = ""
        for p in day["review_patterns"]:
            items += f"""
      <div class="pattern-card">
        <div class="p-en en">{esc(p["pattern"])} <span class="hint">({esc(p["learned_date"])} 학습)</span></div>
        <div class="p-line"><span class="label">새 예문</span><span class="en">{esc(p["new_example"])}</span></div>
        <div class="p-line"><span class="label">미니 미션</span>{esc(p["mini_mission"])}</div>
      </div>"""
        rp = f'<h3 style="font-size:.98rem">🔁 패턴 복습 + 미니 미션</h3>{items}'

    return f"""
<section>
  <h2><span class="num">5</span>복습 — 단어 중심 간격 반복</h2>
  {speed}
  {rw}
  {rp}
</section>"""


def sec_mission(day: dict) -> str:
    checks = "".join(
        f'<label class="check"><input type="checkbox"><span>{esc(c)}</span></label>'
        for c in day["checklist"]
    )
    return f"""
<section>
  <h2><span class="num">6</span>스피킹 미션 + 셀프 체크</h2>
  <p><b>미션:</b> 스크립트를 덮고 다시 1분 30초 녹음하세요 (2차 녹음).<br>
  <span class="hint">조건: 오늘 배운 단어를 <b>4개 이상</b> 넣어 말하기 — 확장 단어를 쓰면 더 좋습니다!</span></p>
  {timer_html(90)}
  {recorder_html()}
  <h3 style="font-size:.98rem">✅ 셀프 체크리스트</h3>
  {checks}
</section>"""


def render_daily(day: dict) -> str:
    unit = day.get("unit", 1)
    return f"""
<header>
  <div class="date">{esc(day["date"])}</div>
  <div class="unit-badge">Unit {unit} · {esc(day.get("unit_title", ""))}</div>
  <h1>{esc(day.get("topic", ""))}</h1>
  <p class="hint">오늘 훈련 약 30~35분 — 단어 학습이 절반입니다. 순서대로 진행하세요.</p>
</header>
{sec_question(day)}
{sec_answer(day)}
{sec_vocab()}
{sec_patterns(day)}
{sec_review(day, bool(day.get("_yesterday_words")))}
{sec_mission(day)}"""


def render_weekend(day: dict) -> str:
    reqs = ""
    for i, q in enumerate(day.get("requestions", []), 1):
        reqs += f"""
  <div class="pattern-card">
    <div class="p-en en">Q{i}. {esc(q["english"])} <span class="hint">({esc(q["date"])})</span></div>
    <div class="btn-row"><button class="btn small tts" data-say="{esc(q["english"])}">🔊 듣기</button></div>
    {timer_html(90)}
    {recorder_html()}
  </div>"""
    checks = "".join(
        f'<label class="check"><input type="checkbox"><span>{esc(c)}</span></label>'
        for c in day.get("checklist", [])
    )
    n = len(day.get("weekly_words", []))
    return f"""
<header>
  <div class="date">{esc(day["date"])}</div>
  <div class="unit-badge">주말 복습</div>
  <h1>이번 주 단어 종합 테스트</h1>
  <p class="hint">새 진도 대신, 이번 주 배운 단어를 총정리합니다. 토/일 문제가 달라 대부분의 단어가 커버됩니다.</p>
</header>
<section>
  <h2><span class="num">1</span>주간 단어 테스트 {n}문제</h2>
  <button class="btn primary" id="weekly-quiz-start">테스트 시작</button>
  <div id="weekly-quiz"></div>
</section>
<section>
  <h2><span class="num">2</span>이번 주 질문 재녹음</h2>
  <p class="hint">스크립트 없이, 배운 단어를 살려 다시 답해보세요.</p>
  {reqs}
</section>
<section>
  <h2><span class="num">3</span>셀프 체크</h2>
  {checks}
</section>"""


# ================================================================ 페이지 조립

def build_page(day: dict, depth: int, yesterday_words: list, is_today: bool, docx_name: str | None) -> str:
    root = "../" * depth
    unit = day.get("unit", 0)
    accent = UNIT_COLORS.get(unit, "#6366f1")
    content = render_weekend(day) if day.get("type") == "weekend" else render_daily(
        {**day, "_yesterday_words": yesterday_words})

    if docx_name:
        content += f"""
<p style="text-align:center"><a class="btn" href="{root}files/{esc(docx_name)}">📄 Word 파일 다운로드</a></p>"""

    data_js = (
        f"var DAY = {js_json(day)};\n"
        f"var YESTERDAY_WORDS = {js_json(yesterday_words)};"
    )
    title = f"{day['date']} · OPIc AL 트레이너"
    page = (PAGE
            .replace("__TITLE__", esc(title))
            .replace("__ACCENT__", accent)
            .replace("__CONTENT__", content)
            .replace("__DATA__", data_js)
            .replace("__ROOT__", root)
            .replace("__NAV_TODAY__", "active" if is_today else "")
            .replace("__NAV_VOCAB__", "")
            .replace("__NAV_ARCHIVE__", "" if is_today else "active")
            .replace("__NAV_CURR__", "")
            .replace("__EXTRA_JS__", ""))
    return page


def sub_page(title: str, content: str, data_js: str, extra_js: str, nav: str) -> str:
    """단어장/표현사전/진도/아카이브용 페이지 (docs/<name>/index.html, depth 1)."""
    return (PAGE
            .replace("__TITLE__", esc(title))
            .replace("__ACCENT__", "#6366f1")
            .replace("__CONTENT__", content)
            .replace("__DATA__", "var DAY = {date:''}; var YESTERDAY_WORDS = [];\n" + data_js)
            .replace("__ROOT__", "../")
            .replace("__NAV_TODAY__", "active" if nav == "today" else "")
            .replace("__NAV_VOCAB__", "active" if nav == "vocab" else "")
            .replace("__NAV_ARCHIVE__", "active" if nav == "archive" else "")
            .replace("__NAV_CURR__", "active" if nav == "curr" else "")
            .replace("__EXTRA_JS__", extra_js))


def yesterday_words_for(date_str: str, words: list) -> list:
    d = datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=1)
    y = d.strftime("%Y-%m-%d")
    return [w for w in words if w.get("date") == y]


# ================================================================ 단어장 페이지

VOCAB_CONTENT = """
<header>
  <h1>📚 단어장</h1>
  <div class="btn-row">
    <span class="btn primary small" style="cursor:default">단어장</span>
    <a class="btn small" href="../patterns/">표현 사전 →</a>
  </div>
  <p class="hint">누적 단어 <b id="v-count"></b>개 — 시험 직전엔 플래시카드·테스트 모드를 활용하세요.</p>
</header>
<section>
  <div class="btn-row">
    <button class="btn v-mode primary" data-mode="list">📖 리스트</button>
    <button class="btn v-mode" data-mode="fc">🃏 플래시카드</button>
    <button class="btn v-mode" data-mode="test">📝 테스트</button>
  </div>
  <div id="mode-list">
    <input id="v-search" placeholder="단어·뜻 검색" style="width:100%;min-height:44px;padding:8px 14px;border:1px solid var(--line);border-radius:12px;background:var(--bg);color:var(--fg);font-size:1rem">
    <select id="v-topic" style="width:100%;min-height:44px;margin-top:8px;padding:8px 14px;border:1px solid var(--line);border-radius:12px;background:var(--bg);color:var(--fg);font-size:.95rem">
      <option value="">전체 주제</option>
    </select>
    <div id="v-list"></div>
  </div>
  <div id="mode-fc" hidden>
    <div class="btn-row">
      <button class="btn small v-scope primary" data-scope="all">전체</button>
      <button class="btn small v-scope" data-scope="week">최근 7일</button>
      <button class="btn small v-scope" data-scope="rand">랜덤 30개</button>
    </div>
    <div class="fc-wrap">
      <div class="fc" id="v-fc">
        <div class="fc-face fc-front" id="v-front"></div>
        <div class="fc-face fc-back" id="v-back"></div>
      </div>
    </div>
    <div class="fc-progress" id="v-prog"></div>
    <div class="btn-row" style="justify-content:center">
      <button class="btn" id="v-prev">◀ 이전</button>
      <button class="btn" id="v-next">다음 ▶</button>
    </div>
  </div>
  <div id="mode-test" hidden>
    <p class="hint">누적 단어에서 랜덤 20문제 뜻 매칭.</p>
    <button class="btn primary" id="v-test-start">테스트 시작</button>
    <div id="v-test"></div>
  </div>
</section>"""

VOCAB_JS = r"""
(function(){
  if (typeof WORDS === 'undefined') return;
  document.getElementById('v-count').textContent = WORDS.length;
  /* 모드 전환 */
  var panes = { list: document.getElementById('mode-list'), fc: document.getElementById('mode-fc'), test: document.getElementById('mode-test') };
  document.querySelectorAll('.v-mode').forEach(function(b){
    b.addEventListener('click', function(){
      document.querySelectorAll('.v-mode').forEach(function(x){ x.classList.remove('primary'); });
      b.classList.add('primary');
      Object.keys(panes).forEach(function(k){ panes[k].hidden = (k !== b.dataset.mode); });
    });
  });
  /* 리스트 모드: 검색 + 주제 필터 */
  var topics = [];
  WORDS.forEach(function(w){ if (topics.indexOf(w.topic) < 0) topics.push(w.topic); });
  var sel = document.getElementById('v-topic');
  topics.forEach(function(t){ var o = document.createElement('option'); o.value = t; o.textContent = t; sel.appendChild(o); });
  var listEl = document.getElementById('v-list');
  function renderList(){
    var q = document.getElementById('v-search').value.toLowerCase();
    var tp = sel.value;
    listEl.innerHTML = '';
    WORDS.filter(function(w){
      if (tp && w.topic !== tp) return false;
      return !q || w.word.toLowerCase().indexOf(q) >= 0 || w.meaning.indexOf(q) >= 0;
    }).forEach(function(w){
      var d = document.createElement('div'); d.className = 'pattern-card';
      var badge = w.tier === 'core' ? '<span class="tier core">핵심</span>' : '<span class="tier extend">확장 · ' + w.linked_word + ' 대신</span>';
      d.innerHTML = '<div class="p-en en">' + w.word + ' <span class="hint">(' + w.pos + ')</span> ' + badge + '</div>'
        + '<div class="p-line"><b>' + w.meaning + '</b></div>'
        + '<div class="p-line en hint">' + w.example + '</div>'
        + '<div class="p-line hint">🧩 ' + w.collocation + ' · ' + w.date + '</div>'
        + '<div class="btn-row"><button class="btn small tts" data-say="' + w.word.replace(/"/g, '&quot;') + '">🔊 발음</button></div>';
      listEl.appendChild(d);
    });
    if (!listEl.children.length) listEl.innerHTML = '<p class="hint">검색 결과가 없습니다.</p>';
  }
  document.getElementById('v-search').addEventListener('input', renderList);
  sel.addEventListener('change', renderList);
  renderList();
  /* 플래시카드 모드 */
  var deck = WORDS.slice(), vi = 0;
  var fc = document.getElementById('v-fc');
  function cutoff(days){
    var d = new Date(); d.setDate(d.getDate() - days);
    return d.toISOString().slice(0, 10);
  }
  document.querySelectorAll('.v-scope').forEach(function(b){
    b.addEventListener('click', function(){
      document.querySelectorAll('.v-scope').forEach(function(x){ x.classList.remove('primary'); });
      b.classList.add('primary');
      if (b.dataset.scope === 'week') { var c = cutoff(7); deck = WORDS.filter(function(w){ return w.date >= c; }); }
      else if (b.dataset.scope === 'rand') deck = shuffle(WORDS).slice(0, 30);
      else deck = WORDS.slice();
      if (!deck.length) deck = WORDS.slice();
      vi = 0; renderFc();
    });
  });
  function renderFc(){
    var w = deck[vi];
    fc.classList.remove('flipped');
    var badge = w.tier === 'core' ? '<span class="tier core">핵심</span>' : '<span class="tier extend">확장 · ' + w.linked_word + ' 대신</span>';
    document.getElementById('v-front').innerHTML = badge
      + '<div class="fc-word en">' + w.word + '</div><div class="fc-pos">' + w.pos + '</div>'
      + '<button class="btn small tts" data-say="' + w.word.replace(/"/g, '&quot;') + '">🔊 발음</button>'
      + '<div class="hint">탭하면 뜻이 나옵니다</div>';
    document.getElementById('v-back').innerHTML = '<div class="fc-meaning">' + w.meaning + '</div>'
      + '<div class="fc-ex en">' + w.example + '</div><div class="fc-ex">🧩 ' + w.collocation + '</div>';
    document.getElementById('v-prog').textContent = (vi + 1) + ' / ' + deck.length;
  }
  fc.addEventListener('click', function(e){ if (e.target.closest('.tts')) return; fc.classList.toggle('flipped'); });
  function vmove(d){ vi = (vi + d + deck.length) % deck.length; renderFc(); }
  document.getElementById('v-prev').addEventListener('click', function(){ vmove(-1); });
  document.getElementById('v-next').addEventListener('click', function(){ vmove(1); });
  var vsx = null;
  fc.addEventListener('touchstart', function(e){ vsx = e.touches[0].clientX; }, { passive: true });
  fc.addEventListener('touchend', function(e){
    if (vsx === null) return;
    var dx = e.changedTouches[0].clientX - vsx;
    if (Math.abs(dx) > 45) vmove(dx < 0 ? 1 : -1);
    vsx = null;
  }, { passive: true });
  renderFc();
  /* 테스트 모드 */
  document.getElementById('v-test-start').addEventListener('click', function(){
    this.style.display = 'none';
    renderQuiz(document.getElementById('v-test'), matchingFrom(shuffle(WORDS).slice(0, 20), WORDS));
  });
})();
"""


def build_vocab_page(words: list) -> str:
    return sub_page("단어장 · OPIc AL 트레이너", VOCAB_CONTENT,
                    f"var WORDS = {js_json(words)};", VOCAB_JS, "vocab")


# ================================================================ 표현 사전 페이지

PATTERNS_JS = r"""
(function(){
  var search = document.getElementById('p-search');
  if (!search) return;
  function apply(){
    var q = search.value.toLowerCase();
    var u = document.querySelector('.p-unit.primary');
    var unit = u ? u.dataset.unit : '';
    document.querySelectorAll('#p-list .pattern-card').forEach(function(c){
      var okU = !unit || c.dataset.unit === unit;
      var okQ = !q || c.textContent.toLowerCase().indexOf(q) >= 0;
      c.style.display = (okU && okQ) ? '' : 'none';
    });
  }
  search.addEventListener('input', apply);
  document.querySelectorAll('.p-unit').forEach(function(b){
    b.addEventListener('click', function(){
      var was = b.classList.contains('primary');
      document.querySelectorAll('.p-unit').forEach(function(x){ x.classList.remove('primary'); });
      if (!was) b.classList.add('primary');
      apply();
    });
  });
})();
"""


def build_patterns_page(patterns: list) -> str:
    units = sorted({p.get("unit") for p in patterns if p.get("unit")})
    chips = "".join(f'<button class="btn small p-unit" data-unit="{u}">Unit {u}</button>' for u in units)
    cards = ""
    for p in reversed(patterns):
        cards += f"""
    <div class="pattern-card" data-unit="{p.get("unit", "")}">
      <div class="p-en en">{esc(p["pattern"])}</div>
      <div class="p-line">{esc(p["meaning"])}</div>
      <div class="p-line"><span class="label">예문</span><span class="en">{esc(p["usage_today"])}</span></div>
      <div class="p-line"><span class="label">응용</span><span class="en">{esc(p["extra_example"])}</span></div>
      <div class="p-line hint">Unit {p.get("unit", "?")} · {esc(p.get("topic", ""))} · {esc(p.get("date", ""))}</div>
      <div class="btn-row"><button class="btn small tts" data-say="{esc(p["usage_today"])}">🔊 듣기</button></div>
    </div>"""
    if not cards:
        cards = '<p class="hint">아직 누적된 패턴이 없습니다.</p>'
    content = f"""
<header>
  <h1>💬 표현 사전</h1>
  <div class="btn-row">
    <a class="btn small" href="../vocab/">← 단어장</a>
    <span class="btn primary small" style="cursor:default">표현 사전</span>
  </div>
  <p class="hint">매일 2개씩 쌓이는 재활용 문장 패턴 {len(patterns)}개.</p>
</header>
<section>
  <input id="p-search" placeholder="패턴 검색" style="width:100%;min-height:44px;padding:8px 14px;border:1px solid var(--line);border-radius:12px;background:var(--bg);color:var(--fg);font-size:1rem">
  <div class="btn-row" style="margin-top:8px">{chips}</div>
  <div id="p-list">{cards}</div>
</section>"""
    return sub_page("표현 사전 · OPIc AL 트레이너", content, "", PATTERNS_JS, "vocab")


# ================================================================ 진도표 페이지

def build_curriculum_page(curriculum: list) -> str:
    done_total = sum(1 for it in curriculum if it["completed"])
    body = f"""
<header>
  <h1>📈 진도표</h1>
  <p class="hint">전체 진행: <b>{done_total} / {len(curriculum)}</b>일 완료</p>
</header>"""
    units: dict[int, list] = {}
    for it in curriculum:
        units.setdefault(it["unit"], []).append(it)
    for u, items in units.items():
        color = UNIT_COLORS.get(u, "#6366f1")
        done = sum(1 for it in items if it["completed"])
        rows = ""
        for it in items:
            if it["completed"]:
                rows += f"""
      <div class="check"><span style="color:{color}">✅</span>
        <span><a href="../{esc(it["briefing_url"])}" style="color:inherit">{esc(it["topic"])}</a>
        <span class="hint">· {esc(it["date"])}</span></span></div>"""
            else:
                rows += f"""
      <div class="check"><span style="opacity:.35">⬜</span><span style="color:var(--muted)">{esc(it["topic"])}</span></div>"""
        body += f"""
<section>
  <h2><span class="num" style="background:{color}">{u}</span>{esc(items[0]["unit_title"])}
    <span class="hint" style="margin-left:auto">{done}/{len(items)}</span></h2>
  {rows}
</section>"""
    return sub_page("진도표 · OPIc AL 트레이너", body, "", "", "curr")


# ================================================================ 아카이브 페이지

def build_archive_page(day_metas: list) -> str:
    months: dict[str, list] = {}
    for m in sorted(day_metas, key=lambda x: x["date"], reverse=True):
        key = m["date"][:7]
        months.setdefault(key, []).append(m)
    body = """
<header>
  <h1>🗂️ 아카이브</h1>
  <p class="hint">지난 훈련을 날짜별로 다시 볼 수 있습니다.</p>
</header>"""
    for month, items in months.items():
        y, mo = month.split("-")
        rows = ""
        for m in items:
            label = "주간 복습" if m["is_weekend"] else m["topic"]
            badge = "" if m["is_weekend"] else f'<span class="hint">Unit {m["unit"]} · </span>'
            rows += f"""
      <div class="check"><span>📅</span>
        <span><a href="{esc(m["date"])}/" style="color:inherit"><b>{esc(m["date"])}</b> — {badge}{esc(label)}</a></span></div>"""
        body += f"""
<section>
  <h2>{y}년 {int(mo)}월</h2>
  {rows}
</section>"""
    return sub_page("아카이브 · OPIc AL 트레이너", body, "", "", "archive")


def main() -> None:
    words = load_json(DATA / "words.json")
    day_files = sorted((DATA / "days").glob("*.json"))
    if not day_files:
        print("data/days/ 에 생성된 콘텐츠가 없습니다. generate.py를 먼저 실행하세요.")
        sys.exit(1)

    DOCS.mkdir(exist_ok=True)
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")

    latest = day_files[-1]
    day_metas = []
    for f in day_files:
        day = load_json(f)
        y_words = yesterday_words_for(day["date"], words)
        docx_name = f"{day['date']}_OPIc훈련.docx"
        docx_exists = (DOCS / "files" / docx_name).exists()
        day_metas.append({"date": day["date"], "is_weekend": day.get("type") == "weekend",
                          "unit": day.get("unit"), "topic": day.get("topic", "")})

        # 개별 아카이브 페이지
        out_dir = DOCS / "archive" / day["date"]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(
            build_page(day, 2, y_words, False, docx_name if docx_exists else None),
            encoding="utf-8")

        # 최신 날짜 → 루트 index.html
        if f == latest:
            (DOCS / "index.html").write_text(
                build_page(day, 0, y_words, True, docx_name if docx_exists else None),
                encoding="utf-8")

    patterns = load_json(DATA / "patterns.json")
    curriculum = load_json(DATA / "curriculum.json")
    pages = {
        "vocab": build_vocab_page(words),
        "patterns": build_patterns_page(patterns),
        "curriculum": build_curriculum_page(curriculum),
        "archive": build_archive_page(day_metas),
    }
    for name, html_text in pages.items():
        d = DOCS / name
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(html_text, encoding="utf-8")

    print(f"[build_site] {len(day_files)}일치 + 단어장/표현사전/진도/아카이브 빌드 완료 (최신: {load_json(latest)['date']})")


if __name__ == "__main__":
    main()
