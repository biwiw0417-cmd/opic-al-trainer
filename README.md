# OPIc AL 데일리 스피킹 트레이너

OPIc **AL(Advanced Low)** 등급을 목표로 매일 자동 생성되는 스피킹 학습 사이트.

- 매일 아침 7:00 KST에 GitHub Actions가 자동 실행
- Gemini API(무료 티어)가 그날의 학습 콘텐츠 생성 (커리큘럼 40일 = 8유닛 × 5일)
- 정적 HTML → GitHub Pages 배포 (모바일 우선)
- 브라우저 기본 기능만으로 TTS(질문 듣기) + 녹음 + 타이머 + 플래시카드 + 단어 테스트
- 하루 단어 15개(핵심 10 + 확장 5) 중심의 어휘 학습이 핵심 축

## 구조

```
data/
  curriculum.json   # 40일 커리큘럼 진도
  words.json        # 누적 단어장
  patterns.json     # 누적 패턴(표현 사전)
  days/             # 일별 생성 JSON
scripts/
  generate.py       # Claude API로 오늘의 콘텐츠 생성
  build_site.py     # 정적 사이트 빌드 → docs/
  build_docx.py     # Word 파일 생성 → docs/files/
docs/               # GitHub Pages 루트
.github/workflows/daily.yml  # 매일 07:00 KST 자동 실행
```

## 로컬 실행

```
set GEMINI_API_KEY=AIza...
python scripts/generate.py
python scripts/build_site.py
python scripts/build_docx.py
```

테스트용 날짜 지정: `set TRAIN_DATE=2026-07-20`
