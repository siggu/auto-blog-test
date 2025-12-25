# 🤖 AI 뉴스 자동 수집기

AI 관련 뉴스를 자동으로 수집하여 Notion 데이터베이스에 저장하는 Python 스크립트입니다.

## ✨ 주요 기능

- **자동 뉴스 수집**: 여러 AI 뉴스 RSS 피드에서 최신 뉴스 수집
- **AI 기반 분석**: Claude API를 사용하여 뉴스 요약 및 분류
- **Notion 연동**: 데이터베이스에 자동 업로드
- **중복 방지**: 이미 저장된 기사는 건너뛰기
- **스케줄링 지원**: 크론잡으로 정기 실행 가능

## 📋 데이터베이스 구조

| 속성      | 타입         | 설명                                   |
| --------- | ------------ | -------------------------------------- |
| 제목      | Title        | 뉴스 제목                              |
| 날짜      | Date         | 발행일                                 |
| 관련 기술 | Multi-select | LLM, 이미지 생성, 추론 AI, 에이전트 등 |
| 기업/기관 | Select       | OpenAI, Google, Anthropic 등           |
| 출처      | URL          | 원본 기사 링크                         |
| 중요도    | Select       | 🔥 주요, 📌 일반, 📝 참고              |
| 요약      | Text         | AI가 생성한 요약                       |

## 🚀 설치 방법

### 1. 필요 패키지 설치

```bash
pip install requests feedparser python-dotenv
```

### 2. 환경 변수 설정

```bash
# .env.example을 .env로 복사
cp .env.example .env

# .env 파일 편집하여 API 키 입력
nano .env
```

### 3. Notion Integration 설정

1. https://www.notion.so/my-integrations 접속
2. "새 통합" 버튼 클릭
3. 이름 입력 (예: "AI 뉴스 봇")
4. 워크스페이스 선택 후 생성
5. "시크릿" 복사하여 `.env`의 `NOTION_API_KEY`에 붙여넣기

### 4. 데이터베이스에 Integration 연결

1. Notion에서 "AI 뉴스 아카이브" 데이터베이스 열기
2. 우측 상단 "..." 메뉴 클릭
3. "연결 추가" → 생성한 Integration 선택

## 💻 사용 방법

### 기본 실행 (최근 1일 뉴스)

```bash
python ai_news_collector.py
```

### 최근 7일 뉴스 수집

```bash
python ai_news_collector.py --days 7
```

### Claude API 없이 실행 (키워드 기반 분류)

```bash
python ai_news_collector.py --no-claude
```

## ⏰ 자동 실행 설정 (Cron)

매일 오전 9시에 자동 실행하려면:

```bash
# crontab 편집
crontab -e

# 다음 줄 추가
0 9 * * * cd /path/to/script && python ai_news_collector.py >> /var/log/ai_news.log 2>&1
```

## 📡 지원 뉴스 소스

| 소스            | 언어   | URL                  |
| --------------- | ------ | -------------------- |
| AI타임스        | 한국어 | aitimes.com          |
| 인공지능신문    | 한국어 | aitimes.kr           |
| MIT Tech Review | 영어   | technologyreview.com |
| VentureBeat AI  | 영어   | venturebeat.com      |
| The Verge AI    | 영어   | theverge.com         |

### 새 RSS 피드 추가

`ai_news_collector.py`의 `RSS_FEEDS` 리스트에 추가:

```python
RSS_FEEDS = [
    # ... 기존 피드들 ...
    {
        "name": "새 뉴스 소스",
        "url": "https://example.com/rss/ai.xml",
        "language": "ko"  # 또는 "en"
    }
]
```

## 🔧 커스터마이징

### 기술 키워드 추가

`TECH_KEYWORDS` 딕셔너리에 새 키워드 추가:

```python
TECH_KEYWORDS = {
    "LLM": ["llm", "gpt", "새키워드"],
    # ...
}
```

### 기업/기관 추가

`ORG_KEYWORDS` 딕셔너리에 추가:

```python
ORG_KEYWORDS = {
    "새기업": ["newcompany", "새기업"],
    # ...
}
```

## 🐛 문제 해결

### "API key is invalid" 오류

- `.env` 파일의 API 키가 올바른지 확인
- Notion Integration이 데이터베이스에 연결되었는지 확인

### "Database not found" 오류

- `DATABASE_ID`가 올바른지 확인
- Integration이 해당 데이터베이스에 접근 권한이 있는지 확인

### RSS 피드 수집 오류

- 해당 사이트가 RSS를 제공하는지 확인
- 피드 URL이 올바른지 확인

## 📝 라이선스

MIT License

## 🤝 기여

이슈와 PR 환영합니다!
