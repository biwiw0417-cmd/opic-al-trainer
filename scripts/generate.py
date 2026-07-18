# -*- coding: utf-8 -*-
"""매일 OPIc AL 훈련 콘텐츠 생성 스크립트 (Gemini 무료 티어 버전).

1. curriculum.json에서 오늘의 주제 선택 (평일: 미완료 첫 항목)
2. Gemini API로 학습 JSON 생성 (질문/모범답변/단어15/퀴즈/패턴/복습)
3. data/days/YYYY-MM-DD.json 저장 + curriculum/words/patterns 갱신
4. 주말(토/일): 새 진도 대신 그 주 단어 종합 테스트용 JSON 생성 (API 호출 없음)

환경변수: GEMINI_API_KEY (필수), TRAIN_DATE (테스트용, YYYY-MM-DD)
"""
import json
import os
import random
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # Windows 콘솔(cp949) 대응

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
KST = timezone(timedelta(hours=9))

# LLM 설정 — 나중에 Claude 등으로 바꾸려면 call_llm()만 교체하면 됨
# 앞의 모델이 혼잡(503/타임아웃)하면 뒤의 모델로 자동 폴백
GEMINI_MODELS = [
    "gemini-flash-latest",
    "gemini-3-flash-preview",
    "gemini-flash-lite-latest",
]
GEMINI_URL_TMPL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)

SYSTEM_PROMPT = """당신은 OPIc AL(Advanced Low) 등급을 목표로 하는 한국인 학습자를 위한 데일리 스피킹 콘텐츠 작가입니다.
학습자의 최대 약점은 어휘이므로, 단어 학습이 이 콘텐츠의 핵심 축입니다.

## 작성 순서 (반드시 이 순서를 지킬 것)
1. 오늘 주제로 실제 OPIc 6-6 난이도의 Eva 스타일 영어 질문 1개를 만든다 (콤보 3연속 질문 구조 중 한 문항이라고 가정하고, combo_context에 그 흐름을 설명).
2. **core 단어 10개를 먼저 정한다.** 선정 기준:
   - 10개 중 6개는 모범답변 스크립트에 실제로 등장할 단어, 4개는 오늘 주제를 말할 때 필수인 주제어.
   - 어려운 단어 자랑이 아니라 **말할 때 실제로 쓰는 실용 단어** 우선. 학습자 수준을 고려해 중학~수능 수준 단어도 배제하지 말 것.
   - 단독 단어보다 덩어리(collocation)로 제시 (예: "keep" 대신 "keep track of").
3. 그 core 단어 10개가 **자연스럽게 녹아 있는** 모범답변 스크립트를 쓴다.
4. core 중 5개를 골라 extend(대체어) 5개를 붙인다. 유의어·반의어·연관어 1개씩, linked_word에 어떤 core 단어의 대체어인지 명시. (같은 단어 반복을 피해 바꿔 말하는 paraphrasing이 AL 채점 포인트)

## 모범답변(model_answer.script) 기준
- 원어민의 자연스러운 미국식 구어체, 1분 30초~2분 분량 (구어 기준 200~250단어), 외우기 좋게 문장 구조는 명료하게.
- 구조: 서론 – MP(Main Point) – 디테일 확장 – 감정/생각 – 마무리. 문단 사이는 빈 줄로 구분.
- 반드시 포함: 정확한 과거 시제 서사, 과거 vs 현재 비교, 디스코스 마커(you know, actually, the thing is, looking back 등), 구체적 디테일과 감정 묘사.
- structure_note: 답변 뼈대를 한국어로 도식화 (서론→MP→디테일→감정→마무리 각 부분이 스크립트 어디인지).
- al_points: "왜 이 문장이 AL스러운가"를 한국어 존댓말로 3개. 시제 전환 지점, 디테일 확장 기법, 채점자에게 어필하는 포인트를 짚을 것.

## vocab (정확히 15개 = core 10 + extend 5)
- 각 항목: word(덩어리 표현 가능) / pos(품사) / meaning(한국어 뜻) / example(오늘 답변 속 사용 문장, 주제어라 스크립트에 없으면 오늘 주제에 맞는 새 예문) / collocation(자주 붙는 덩어리 표현 1개) / tier("core"|"extend") / linked_word(extend만: 대체하는 core 단어, core는 null)
- 누적 단어 목록에 이미 있는 단어는 다시 선정하지 말 것.

## vocab_quiz (정확히 7문제, 모두 4지선다, answer_index는 0~3)
- matching(뜻 매칭) 3문제: 오늘 단어의 뜻 고르기 (오답 보기도 그럴듯한 한국어 뜻으로)
- blank(빈칸) 2문제: 오늘 답변 속 문장에서 단어를 ____로 비운 뒤 고르기
- synonym(교체어) 2문제: "스크립트의 ___ 대신 쓸 수 있는 말은?" — extend 단어가 정답

## patterns (정확히 2개)
- 모범답변에서 뽑은 재활용 문장 패턴. pattern / meaning(한국어 뜻) / usage_today(오늘 답변에서의 사용 문장) / extra_example(다른 주제 응용 예문 1개)
- 최근 패턴 목록과 중복 금지.

## review_words / review_patterns
- 입력으로 준 복습 대상 단어 각각에 오늘 주제와 어울리는 새 예문(new_example)을 쓴다. 대상이 없으면 빈 배열.
- 복습 패턴에는 new_example과 mini_mission("이 패턴과 오늘 배운 단어 ○○를 함께 써서 한 문장 말해보기" 형식)을 쓴다.

## checklist (정확히 6개, 한국어)
- "오늘 단어를 4개 이상 썼다" / "과거 시제가 흔들리지 않았다" / "MP 후 디테일을 2개 이상 확장했다" / "감정이나 생각을 말했다" / "마무리 문장을 했다" / "필러 없이 침묵 3초 이상이 없었다"

## 출력 규칙 (매우 중요)
- 아래 스키마의 JSON **하나만** 출력합니다. JSON 앞뒤에 설명, 인사, 마크다운 펜스 등 다른 텍스트를 절대 붙이지 마세요.

{
  "date": "YYYY-MM-DD",
  "question": {"english": "", "korean": "", "combo_context": ""},
  "model_answer": {"script": "", "structure_note": "", "al_points": ["", "", ""]},
  "vocab": [{"word": "", "pos": "", "meaning": "", "example": "", "collocation": "", "tier": "core", "linked_word": null}],
  "vocab_quiz": [{"type": "matching", "question": "", "choices": ["", "", "", ""], "answer_index": 0}],
  "patterns": [{"pattern": "", "meaning": "", "usage_today": "", "extra_example": ""}],
  "review_words": [{"word": "", "learned_date": "", "new_example": ""}],
  "review_patterns": [{"pattern": "", "learned_date": "", "new_example": "", "mini_mission": ""}],
  "checklist": ["", "", "", "", "", ""]
}
"""


def today_kst() -> datetime:
    override = os.environ.get("TRAIN_DATE")  # 테스트용: YYYY-MM-DD
    if override:
        return datetime.strptime(override, "%Y-%m-%d").replace(tzinfo=KST)
    return datetime.now(KST)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- 복습 대상 선정

def words_on(words: list, date_str: str) -> list:
    return [w for w in words if w.get("date") == date_str]


def pick_review_words(words: list, today: datetime) -> list:
    """3일 전 4개 + 7일 전 4개, core 우선."""
    targets = []
    for days in (3, 7):
        d = (today - timedelta(days=days)).strftime("%Y-%m-%d")
        day_words = words_on(words, d)
        day_words.sort(key=lambda w: 0 if w.get("tier") == "core" else 1)
        targets.extend(day_words[:4])
    return targets


def pick_review_pattern(patterns: list, today: datetime):
    d = (today - timedelta(days=3)).strftime("%Y-%m-%d")
    for p in patterns:
        if p.get("date") == d:
            return p
    return None


# ---------------------------------------------------------------- 프롬프트 구성

def build_user_prompt(today, item, words, patterns) -> str:
    date_str = today.strftime("%Y-%m-%d")
    weekday_kr = "월화수목금토일"[today.weekday()]
    yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")

    lines = [
        f"오늘 날짜: {date_str} ({weekday_kr}요일)",
        f"오늘의 커리큘럼: Unit {item['unit']}. {item['unit_title']} — 「{item['topic']}」",
        "",
    ]

    review_words = pick_review_words(words, today)
    if review_words:
        lines.append("복습 대상 단어 (review_words에 각각 새 예문을 쓸 것):")
        for w in review_words:
            lines.append(f"- {w['word']} (뜻: {w['meaning']}, 배운 날짜: {w['date']})")
    else:
        lines.append("복습 대상 단어가 아직 없습니다. review_words는 빈 배열 []로 하세요.")

    lines.append("")
    rp = pick_review_pattern(patterns, today)
    if rp:
        lines.append(f"복습 대상 패턴: \"{rp['pattern']}\" (뜻: {rp['meaning']}, 배운 날짜: {rp['date']})")
        lines.append("- review_patterns에 이 패턴의 새 예문과, 오늘 배운 단어 1개를 함께 쓰는 mini_mission을 쓰세요.")
    else:
        lines.append("복습 대상 패턴이 아직 없습니다. review_patterns는 빈 배열 []로 하세요.")

    lines.append("")
    y_words = [w["word"] for w in words_on(words, yesterday)]
    if y_words:
        lines.append("어제 배운 단어 (참고용 — 오늘 vocab에 중복 선정 금지): " + ", ".join(y_words))

    all_words = [w["word"] for w in words]
    if all_words:
        lines.append("지금까지 배운 누적 단어 (오늘 vocab에 중복 선정 금지): " + ", ".join(all_words))
    else:
        lines.append("아직 배운 단어가 없습니다. 자유롭게 선정하세요.")

    recent_patterns = [p["pattern"] for p in patterns[-14:]]
    if recent_patterns:
        lines.append("최근 패턴 (중복 금지): " + " / ".join(recent_patterns))

    lines += ["", "위 조건으로 오늘의 훈련 JSON을 생성하세요."]
    return "\n".join(lines)


# ---------------------------------------------------------------- API 호출/파싱

def call_llm(user_prompt: str) -> str:
    """Gemini API 호출 (JSON 모드). 혼잡/일시 오류는 다음 모델로 폴백 + 재시도."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
        sys.exit(1)

    body = json.dumps({
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "maxOutputTokens": 16384,
        },
    }).encode("utf-8")

    last_err = None
    for attempt in range(3):
        for model in GEMINI_MODELS:
            try:
                req = urllib.request.Request(
                    GEMINI_URL_TMPL.format(model=model),
                    data=body,
                    headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
                )
                with urllib.request.urlopen(req, timeout=180) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                print(f"[generate] 모델 사용: {model}")
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                last_err = e
                print(f"[generate] {model} 호출 실패({e}) → 다음 모델/재시도")
        time.sleep(20 * (attempt + 1))
    raise RuntimeError(f"Gemini API 호출 실패 (모든 모델/재시도 소진): {last_err}")


def extract_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start:end + 1])
        raise


def validate(day: dict) -> None:
    for key in ("question", "model_answer", "vocab", "vocab_quiz", "patterns",
                "review_words", "review_patterns", "checklist"):
        if key not in day:
            raise ValueError(f"'{key}' 키가 없습니다")
    core = [w for w in day["vocab"] if w.get("tier") == "core"]
    extend = [w for w in day["vocab"] if w.get("tier") == "extend"]
    if len(core) != 10 or len(extend) != 5:
        raise ValueError(f"vocab 구성이 어긋납니다 (core {len(core)}, extend {len(extend)})")
    if any(not w.get("linked_word") for w in extend):
        raise ValueError("extend 단어에 linked_word가 없습니다")
    if len(day["vocab_quiz"]) != 7:
        raise ValueError(f"vocab_quiz가 7문제가 아닙니다 ({len(day['vocab_quiz'])})")
    if len(day["patterns"]) != 2:
        raise ValueError(f"patterns가 2개가 아닙니다 ({len(day['patterns'])})")
    wc = len(day["model_answer"]["script"].split())
    if wc < 150:
        raise ValueError(f"모범답변이 너무 짧습니다 ({wc}단어)")


# ---------------------------------------------------------------- 주말 처리

def week_start(today: datetime) -> datetime:
    return today - timedelta(days=today.weekday())  # 월요일


def build_weekend(today: datetime, words: list) -> dict | None:
    """주말: 그 주(월~금) 단어 종합 테스트 + 질문 2개 재녹음. API 호출 없음.
    이번 주 단어가 10개 미만이면 None을 반환해 평일 흐름으로 폴백."""
    monday = week_start(today).strftime("%Y-%m-%d")
    friday = (week_start(today) + timedelta(days=4)).strftime("%Y-%m-%d")
    week_words = [w for w in words if monday <= w.get("date", "") <= friday]
    if len(week_words) < 10:
        return None

    # 그 주 day JSON에서 재녹음할 질문 2개 랜덤 선택
    questions = []
    for f in sorted((DATA / "days").glob("*.json")):
        if monday <= f.stem <= friday:
            d = load_json(f)
            if d.get("type") != "weekend" and "question" in d:
                questions.append({"date": f.stem, "english": d["question"]["english"],
                                  "korean": d["question"].get("korean", "")})
    random.shuffle(questions)

    # 토/일 세트가 겹치지 않게: 요일 기반 시드로 셔플 후 토=전반부, 일=후반부에서 30개
    rnd = random.Random(monday)  # 같은 주엔 같은 순서
    shuffled = week_words[:]
    rnd.shuffle(shuffled)
    half = len(shuffled) // 2
    pool = shuffled[:half] if today.weekday() == 5 else shuffled[half:]
    while len(pool) < 30 and shuffled:
        extra = [w for w in shuffled if w not in pool]
        if not extra:
            break
        pool.extend(extra[:30 - len(pool)])

    return {
        "date": today.strftime("%Y-%m-%d"),
        "type": "weekend",
        "weekly_words": pool[:30],          # 오늘 출제할 30개 (부족하면 있는 만큼)
        "all_week_words": week_words,        # 리스트 복습용
        "requestions": questions[:2],
        "checklist": [
            "주간 단어 테스트 30문제를 완료했다",
            "재녹음 질문 2개를 스크립트 없이 말했다",
            "이번 주 단어 중 헷갈린 단어를 따로 표시했다",
        ],
    }


# ---------------------------------------------------------------- 메인

def main() -> None:
    today = today_kst()
    date_str = today.strftime("%Y-%m-%d")
    words = load_json(DATA / "words.json")
    patterns = load_json(DATA / "patterns.json")
    curriculum = load_json(DATA / "curriculum.json")

    # 주말이면 종합 테스트 JSON (이번 주 단어가 충분할 때만)
    if today.weekday() >= 5:
        weekend = build_weekend(today, words)
        if weekend:
            save_json(DATA / "days" / f"{date_str}.json", weekend)
            print(f"[generate] 주말 종합 테스트 저장: data/days/{date_str}.json "
                  f"(단어 {len(weekend['weekly_words'])}개, 재녹음 질문 {len(weekend['requestions'])}개)")
            return
        print("[generate] 이번 주 학습 데이터가 부족해 평일 흐름으로 진행합니다.")

    item = next((it for it in curriculum if not it["completed"]), None)
    if item is None:
        print("커리큘럼 40개 주제를 모두 완료했습니다. 심화 유닛을 추가해 주세요.")
        sys.exit(1)

    print(f"[generate] {date_str} — Unit {item['unit']} 「{item['topic']}」 생성 시작")
    user_prompt = build_user_prompt(today, item, words, patterns)

    try:
        day = extract_json(call_llm(user_prompt))
        validate(day)
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        print(f"[generate] 1차 파싱/검증 실패({e}) → 재시도")
        day = extract_json(call_llm(user_prompt))
        validate(day)

    day["date"] = date_str
    day["type"] = "daily"
    day["unit"] = item["unit"]
    day["unit_title"] = item["unit_title"]
    day["topic"] = item["topic"]
    save_json(DATA / "days" / f"{date_str}.json", day)
    print(f"[generate] data/days/{date_str}.json 저장 완료")

    # 진도 갱신
    item["completed"] = True
    item["date"] = date_str
    item["briefing_url"] = f"archive/{date_str}/"
    save_json(DATA / "curriculum.json", curriculum)

    # 단어 누적 (같은 날 재실행 시 중복 방지)
    existing = {w["word"] for w in words}
    added = 0
    for w in day["vocab"]:
        if w["word"] not in existing:
            words.append({**w, "date": date_str, "topic": item["topic"]})
            added += 1
    save_json(DATA / "words.json", words)

    # 패턴 누적
    existing_p = {p["pattern"] for p in patterns}
    for p in day["patterns"]:
        if p["pattern"] not in existing_p:
            patterns.append({**p, "date": date_str, "unit": item["unit"],
                             "unit_title": item["unit_title"], "topic": item["topic"]})
    save_json(DATA / "patterns.json", patterns)
    print(f"[generate] 단어 {added}개, 패턴 누적 완료 — 진도: {item['topic']}")


if __name__ == "__main__":
    main()
