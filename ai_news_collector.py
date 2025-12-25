"""
AI 뉴스 자동 수집 및 Notion 데이터베이스 업로드 스크립트

이 스크립트는 다음 기능을 수행합니다:
1. 웹에서 최신 AI 뉴스를 수집 (RSS 피드 또는 웹 스크래핑)
2. Claude API를 사용하여 뉴스 분석 및 분류
3. Notion 데이터베이스에 자동 업로드

사용 전 설정:
1. .env 파일에 API 키 설정
2. 크론잡 또는 스케줄러로 정기 실행 설정
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Optional
import feedparser
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# =============================================================================
# 설정
# =============================================================================

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Notion 데이터베이스 ID (생성된 데이터베이스)
DATABASE_ID = "3e6b5982ea584534afa6618150f29d21"

# AI 뉴스 RSS 피드 목록
RSS_FEEDS = [
    {
        "name": "AI타임스",
        "url": "https://www.aitimes.com/rss/allArticle.xml",
        "language": "ko",
    },
    {
        "name": "인공지능신문",
        "url": "https://www.aitimes.kr/rss/allArticle.xml",
        "language": "ko",
    },
    {
        "name": "MIT Tech Review AI",
        "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed",
        "language": "en",
    },
    {
        "name": "VentureBeat AI",
        "url": "https://venturebeat.com/category/ai/feed/",
        "language": "en",
    },
    {
        "name": "The Verge AI",
        "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "language": "en",
    },
]

# 관련 기술 키워드 매핑
TECH_KEYWORDS = {
    "LLM": [
        "llm",
        "large language model",
        "gpt",
        "claude",
        "gemini",
        "대형언어모델",
        "대규모 언어 모델",
        "chatgpt",
    ],
    "이미지 생성": [
        "image generation",
        "dall-e",
        "midjourney",
        "stable diffusion",
        "이미지 생성",
        "그림 생성",
        "text-to-image",
    ],
    "추론 AI": [
        "reasoning",
        "o1",
        "o3",
        "chain of thought",
        "추론",
        "사고",
        "thinking",
    ],
    "에이전트": ["agent", "agentic", "에이전트", "자율 에이전트", "autonomous"],
    "멀티모달": ["multimodal", "vision", "audio", "멀티모달", "다중모달", "비전"],
    "오픈소스": ["open source", "오픈소스", "opensource", "hugging face", "허깅페이스"],
    "강화학습": ["reinforcement learning", "rl", "rlhf", "강화학습", "보상 모델"],
    "로보틱스": ["robot", "robotics", "로봇", "로보틱스", "embodied ai"],
    "음성/오디오": [
        "voice",
        "audio",
        "speech",
        "tts",
        "stt",
        "음성",
        "오디오",
        "whisper",
    ],
}

# 기업/기관 키워드 매핑
ORG_KEYWORDS = {
    "OpenAI": [
        "openai",
        "chatgpt",
        "gpt-4",
        "gpt-5",
        "dall-e",
        "sam altman",
        "샘 올트먼",
    ],
    "Google": ["google", "구글", "deepmind", "딥마인드", "gemini", "제미나이", "bard"],
    "Anthropic": ["anthropic", "앤스로픽", "claude", "클로드"],
    "Meta": ["meta", "메타", "facebook", "llama", "라마"],
    "Microsoft": ["microsoft", "마이크로소프트", "copilot", "코파일럿", "azure"],
    "NVIDIA": ["nvidia", "엔비디아", "cuda", "gpu", "h100", "blackwell"],
    "국내 연구기관": [
        "kaist",
        "카이스트",
        "서울대",
        "postech",
        "포스텍",
        "unist",
        "etri",
        "한국전자통신연구원",
    ],
}


# =============================================================================
# Notion API 클라이언트
# =============================================================================


class NotionClient:
    """Notion API 클라이언트"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

    def create_page(
        self, database_id: str, properties: dict, news_data: dict = None
    ) -> dict:
        """데이터베이스에 새 페이지 생성 (원문 보존)"""
        url = f"{self.base_url}/pages"

        data = {"parent": {"database_id": database_id}, "properties": properties}

        # 뉴스 데이터가 있으면 페이지 내용 구성
        if news_data:
            children = []

            # 1. 요약 섹션 (AI 분석 결과)
            children.append(
                {
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": news_data.get("summary", "요약 없음")
                                },
                            }
                        ],
                        "icon": {"emoji": "💡"},
                        "color": "blue_background",
                    },
                }
            )

            # 2. 핵심 포인트 (있는 경우)
            key_points = news_data.get("key_points", [])
            if key_points:
                children.append(
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [
                                {"type": "text", "text": {"content": "📌 핵심 포인트"}}
                            ]
                        },
                    }
                )
                for point in key_points[:5]:
                    children.append(
                        {
                            "object": "block",
                            "type": "bulleted_list_item",
                            "bulleted_list_item": {
                                "rich_text": [
                                    {"type": "text", "text": {"content": point}}
                                ]
                            },
                        }
                    )

            # 구분선
            children.append({"object": "block", "type": "divider", "divider": {}})

            # 3. 원문 내용 (수정 없이 그대로)
            children.append(
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [
                            {"type": "text", "text": {"content": "📰 원문 내용"}}
                        ]
                    },
                }
            )

            # 원문 내용을 단락별로 분리 (가독성 향상)
            original_content = news_data.get("content", "")

            # 문장 단위로 단락 구분 (마침표+공백 또는 다 기준)
            paragraphs = self._split_into_paragraphs(original_content)

            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                children.append(
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {"type": "text", "text": {"content": para[:2000]}}
                            ]
                        },
                    }
                )

            # 구분선
            children.append({"object": "block", "type": "divider", "divider": {}})

            # 4. 출처 정보
            children.append(
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "🔗 출처"}}]
                    },
                }
            )

            if news_data.get("link"):
                children.append(
                    {
                        "object": "block",
                        "type": "bookmark",
                        "bookmark": {"url": news_data.get("link", "")},
                    }
                )

            # 5. 메타 정보
            children.append(
                {
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"📅 발행일: {news_data.get('date', 'N/A')} | 📰 출처: {news_data.get('source', 'N/A')}"
                                },
                            }
                        ],
                        "icon": {"emoji": "ℹ️"},
                        "color": "gray_background",
                    },
                }
            )

            data["children"] = children

        response = requests.post(url, headers=self.headers, json=data)
        return response.json()

    def _split_into_paragraphs(self, text: str, sentences_per_para: int = 3) -> list:
        """원문을 단락으로 분리 (내용 수정 없이 가독성만 향상)"""
        import re

        if not text:
            return []

        # 이미 단락 구분이 있으면 그대로 사용
        if "\n\n" in text:
            return [p.strip() for p in text.split("\n\n") if p.strip()]

        if "\n" in text:
            return [p.strip() for p in text.split("\n") if p.strip()]

        # 문장 단위로 분리 (한국어/영어 문장 부호 고려)
        sentences = re.split(r"(?<=[.!?。])\s+", text)

        # N개 문장씩 묶어서 단락 생성
        paragraphs = []
        current_para = []

        for sentence in sentences:
            current_para.append(sentence)
            if len(current_para) >= sentences_per_para:
                paragraphs.append(" ".join(current_para))
                current_para = []

        # 남은 문장 처리
        if current_para:
            paragraphs.append(" ".join(current_para))

        return paragraphs

    def query_database(self, database_id: str, filter_obj: dict = None) -> dict:
        """데이터베이스 쿼리"""
        url = f"{self.base_url}/databases/{database_id}/query"
        data = {}
        if filter_obj:
            data["filter"] = filter_obj

        response = requests.post(url, headers=self.headers, json=data)
        return response.json()

    def check_duplicate(self, database_id: str, title: str) -> bool:
        """중복 기사 체크"""
        filter_obj = {
            "property": "제목",
            "title": {"contains": title[:50]},  # 제목 일부로 검색
        }
        result = self.query_database(database_id, filter_obj)
        return len(result.get("results", [])) > 0


# =============================================================================
# 뉴스 분석기 (Claude API 사용)
# =============================================================================


class NewsAnalyzer:
    """Claude API를 사용한 뉴스 분석"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1/messages"

    def analyze_news(self, title: str, content: str) -> dict:
        """뉴스 분석 및 분류 (원문 보존)"""

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        prompt = f"""다음 AI 관련 뉴스를 분석해주세요.

제목: {title}
내용: {content[:3000]}

중요: 원문의 내용을 절대 수정, 삭제, 추가하지 마세요. 분석만 해주세요.

다음 JSON 형식으로 응답해주세요:
{{
    "summary": "원문 내용을 바탕으로 2-3문장 요약 (한국어)",
    "key_points": ["기사에서 직접 추출한 핵심 포인트 1", "핵심 포인트 2", "핵심 포인트 3"],
    "technologies": ["관련 기술 목록 - LLM, 이미지 생성, 추론 AI, 에이전트, 멀티모달, 오픈소스, 강화학습, 로보틱스, 음성/오디오 중 선택"],
    "organization": "주요 기업/기관 - OpenAI, Google, Anthropic, Meta, Microsoft, NVIDIA, 국내 연구기관, 기타 중 선택",
    "importance": "중요도 - 🔥 주요, 📌 일반, 📝 참고 중 선택"
}}

JSON만 출력하세요."""

        data = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            response = requests.post(self.base_url, headers=headers, json=data)

            # API 오류 확인
            if response.status_code != 200:
                print(f"API 오류 ({response.status_code}): {response.text[:200]}")
                return self._fallback_analysis(title, content)

            result = response.json()

            if "content" in result and len(result["content"]) > 0:
                text = result["content"][0]["text"]

                # JSON 추출 시도 (여러 방법)
                import re

                # 1. 직접 파싱 시도
                try:
                    return json.loads(text)
                except:
                    pass

                # 2. JSON 블록 추출 (```json ... ``` 형식)
                json_match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
                if json_match:
                    try:
                        return json.loads(json_match.group(1))
                    except:
                        pass

                # 3. 중괄호로 시작하는 JSON 찾기
                json_match = re.search(r"\{[\s\S]*\}", text)
                if json_match:
                    try:
                        return json.loads(json_match.group(0))
                    except:
                        pass

                print(f"JSON 추출 실패. 응답: {text[:200]}...")
            else:
                print(f"API 응답 형식 오류: {result}")
        except Exception as e:
            print(f"분석 오류: {e}")

        # 폴백: 키워드 기반 분류
        return self._fallback_analysis(title, content)

    def _fallback_analysis(self, title: str, content: str) -> dict:
        """키워드 기반 폴백 분석"""
        text = (title + " " + content).lower()

        # 기술 분류
        technologies = []
        for tech, keywords in TECH_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                technologies.append(tech)

        # 기관 분류
        organization = "기타"
        for org, keywords in ORG_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                organization = org
                break

        return {
            "summary": title,
            "technologies": technologies[:3] if technologies else ["LLM"],
            "organization": organization,
            "importance": "📌 일반",
        }


# =============================================================================
# 뉴스 수집기
# =============================================================================


class NewsCollector:
    """RSS 피드에서 뉴스 수집"""

    def __init__(self, feeds: list):
        self.feeds = feeds

    def collect_news(self, days: int = 1) -> list:
        """최근 N일 이내의 뉴스 수집"""
        from datetime import timezone

        cutoff_date = datetime.now(timezone.utc).replace(
            tzinfo=None
        )  # UTC 기준, naive로 변환
        cutoff_date = cutoff_date - timedelta(days=days)
        all_news = []

        for feed_info in self.feeds:
            try:
                # User-Agent 헤더 추가 (일부 사이트에서 필요)
                feed = feedparser.parse(
                    feed_info["url"],
                    agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                )

                for entry in feed.entries[:10]:  # 각 피드에서 최대 10개
                    # 날짜 파싱 (다양한 필드 시도)
                    pub_date = self._parse_date(entry)

                    # 타임존 정보 제거 (naive datetime으로 통일)
                    if pub_date.tzinfo is not None:
                        pub_date = pub_date.replace(tzinfo=None)

                    # 기간 필터
                    if pub_date < cutoff_date:
                        continue

                    news_item = {
                        "title": entry.get("title", ""),
                        "link": entry.get("link", ""),
                        "content": self._get_content(entry),
                        "date": pub_date.strftime("%Y-%m-%d"),
                        "source": feed_info["name"],
                    }
                    all_news.append(news_item)

                    # 디버그 출력
                    print(f"📅 {news_item['title'][:50]}... -> {news_item['date']}")

            except Exception as e:
                print(f"피드 수집 오류 ({feed_info['name']}): {e}")

        return all_news

    def _parse_date(self, entry) -> datetime:
        """다양한 날짜 형식 파싱"""
        from email.utils import parsedate_to_datetime
        import re

        # 1. published 문자열 먼저 시도 (한국 RSS 피드는 대부분 이 형식)
        if hasattr(entry, "published") and entry.published:
            parsed = self._parse_date_string(entry.published)
            if parsed:
                return parsed

        # 2. published_parsed 시도
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                return datetime(*entry.published_parsed[:6])
            except:
                pass

        # 3. updated 문자열 파싱 시도
        if hasattr(entry, "updated") and entry.updated:
            parsed = self._parse_date_string(entry.updated)
            if parsed:
                return parsed

        # 4. updated_parsed 시도
        if hasattr(entry, "updated_parsed") and entry.updated_parsed:
            try:
                return datetime(*entry.updated_parsed[:6])
            except:
                pass

        # 5. dc:date 시도 (Dublin Core)
        if hasattr(entry, "dc_date") and entry.dc_date:
            parsed = self._parse_date_string(entry.dc_date)
            if parsed:
                return parsed

        # 폴백: 현재 시간
        return datetime.now()

    def _parse_date_string(self, date_str: str) -> Optional[datetime]:
        """문자열 날짜 파싱"""
        from email.utils import parsedate_to_datetime
        import re

        if not date_str:
            return None

        date_str = date_str.strip()

        # 다양한 날짜 형식 시도 (한국 형식 우선)
        date_formats = [
            "%Y-%m-%d %H:%M:%S",  # 한국 RSS 형식: 2025-12-25 19:09:25
            "%Y-%m-%d %H:%M",  # 2025-12-25 19:09
            "%Y-%m-%d",  # 2025-12-25
            "%Y.%m.%d %H:%M:%S",  # 한국 형식: 2025.12.25 19:09:25
            "%Y.%m.%d %H:%M",  # 2025.12.25 19:09
            "%Y.%m.%d",  # 2025.12.25
            "%Y/%m/%d %H:%M:%S",  # 2025/12/25 19:09:25
            "%Y/%m/%d",  # 2025/12/25
            "%Y-%m-%dT%H:%M:%S%z",  # ISO 8601
            "%Y-%m-%dT%H:%M:%SZ",  # ISO 8601 UTC
            "%Y-%m-%dT%H:%M:%S",  # ISO 8601 no tz
            "%d %b %Y %H:%M:%S",  # 25 Dec 2025 19:09:25
            "%a, %d %b %Y %H:%M:%S",  # Wed, 25 Dec 2025 19:09:25
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # +0900 같은 타임존 제거 후 재시도
        clean_date = re.sub(r"[+-]\d{4}$", "", date_str)
        clean_date = re.sub(r"\s+\w{3,4}$", "", clean_date)  # KST, GMT 등 제거
        clean_date = clean_date.strip()

        for fmt in date_formats:
            try:
                return datetime.strptime(clean_date, fmt)
            except ValueError:
                continue

        # RFC 2822 형식 시도 (예: "Wed, 25 Dec 2024 10:30:00 +0900")
        try:
            return parsedate_to_datetime(date_str)
        except:
            pass

        return None

    def _get_content(self, entry) -> str:
        """기사 본문 추출 - RSS 내용 + 웹 스크래핑"""
        # 먼저 RSS에서 기본 내용 가져오기
        rss_content = ""

        if hasattr(entry, "content") and entry.content:
            if isinstance(entry.content, list) and len(entry.content) > 0:
                rss_content = entry.content[0].get("value", "")

        if not rss_content and hasattr(entry, "summary") and entry.summary:
            rss_content = entry.summary

        if not rss_content and hasattr(entry, "description") and entry.description:
            rss_content = entry.description

        # 기사 링크에서 전체 내용 스크래핑 시도
        link = entry.get("link", "")
        if link:
            full_content = self._scrape_article(link)
            if full_content and len(full_content) > len(rss_content):
                return full_content

        return rss_content

    def _scrape_article(self, url: str) -> str:
        """기사 페이지에서 본문 스크래핑"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            # HTML 파싱
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(response.text, "html.parser")

            # 일반적인 기사 본문 선택자들 시도
            content = None

            # AI타임스, 인공지능신문 등 한국 뉴스 사이트
            selectors = [
                "article#article-view-content-div",  # AI타임스
                "div#article-view-content-div",  # AI타임스
                "div.article-body",  # 일반
                "div.article_body",  # 일반
                "div.article-content",  # 일반
                "div.news-content",  # 일반
                "div.view_cont",  # 일부 한국 사이트
                "div#articleBody",  # 일부 사이트
                "div.entry-content",  # WordPress
                "article.post-content",  # 블로그
                'div[itemprop="articleBody"]',  # Schema.org
                "article",  # 일반 article 태그
            ]

            for selector in selectors:
                element = soup.select_one(selector)
                if element:
                    # 불필요한 요소 제거
                    for tag in element.select(
                        "script, style, nav, footer, aside, .ad, .advertisement, .social-share"
                    ):
                        tag.decompose()

                    content = element.get_text(separator="\n", strip=True)
                    if content and len(content) > 200:
                        break

            if content:
                # 너무 길면 자르기
                return content[:5000]

        except ImportError:
            print("⚠️ BeautifulSoup 미설치. pip install beautifulsoup4 실행 필요")
        except Exception as e:
            # 스크래핑 실패 시 조용히 넘어감
            pass

        return ""


# =============================================================================
# 메인 실행
# =============================================================================


class AINewsBot:
    """AI 뉴스 자동화 봇"""

    def __init__(self):
        self.notion = NotionClient(NOTION_API_KEY)
        self.analyzer = NewsAnalyzer(ANTHROPIC_API_KEY)
        self.collector = NewsCollector(RSS_FEEDS)

    def run(self, days: int = 1, use_claude: bool = True):
        """뉴스 수집 및 업로드 실행"""
        print(f"🔍 최근 {days}일 AI 뉴스 수집 중...")

        # 뉴스 수집
        news_list = self.collector.collect_news(days=days)
        print(f"📰 {len(news_list)}개 뉴스 발견")

        uploaded = 0
        skipped = 0

        for news in news_list:
            # 중복 체크
            if self.notion.check_duplicate(DATABASE_ID, news["title"]):
                print(f"⏭️ 중복 건너뛰기: {news['title'][:30]}...")
                skipped += 1
                continue

            # 뉴스 분석
            if use_claude and ANTHROPIC_API_KEY:
                analysis = self.analyzer.analyze_news(news["title"], news["content"])
            else:
                analysis = self.analyzer._fallback_analysis(
                    news["title"], news["content"]
                )

            # Notion 속성 구성
            properties = {
                "제목": {"title": [{"text": {"content": news["title"][:100]}}]},
                "날짜": {"date": {"start": news["date"]}},
                "출처": {"url": news["link"]},
                "요약": {
                    "rich_text": [
                        {"text": {"content": analysis.get("summary", "")[:200]}}
                    ]
                },
                "관련 기술": {
                    "multi_select": [
                        {"name": tech} for tech in analysis.get("technologies", [])[:5]
                    ]
                },
                "기업/기관": {"select": {"name": analysis.get("organization", "기타")}},
                "중요도": {"select": {"name": analysis.get("importance", "📌 일반")}},
            }

            # Notion에 업로드
            try:
                # 페이지 내용에 사용할 데이터 (원문 보존)
                page_content = {
                    "summary": analysis.get("summary", ""),
                    "key_points": analysis.get("key_points", []),
                    "content": news["content"],  # 원문 그대로 사용
                    "link": news["link"],
                    "date": news["date"],
                    "source": news["source"],
                }

                result = self.notion.create_page(DATABASE_ID, properties, page_content)
                if "id" in result:
                    print(f"✅ 업로드 완료: {news['title'][:40]}...")
                    uploaded += 1
                else:
                    print(f"❌ 업로드 실패: {result.get('message', 'Unknown error')}")
            except Exception as e:
                print(f"❌ 오류: {e}")

        print(f"\n📊 완료! 업로드: {uploaded}개, 중복 건너뛰기: {skipped}개")
        return uploaded


# =============================================================================
# 실행
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI 뉴스 자동 수집기")
    parser.add_argument("--days", type=int, default=1, help="수집할 기간 (일)")
    parser.add_argument(
        "--no-claude", action="store_true", help="Claude API 사용하지 않음"
    )

    args = parser.parse_args()

    # API 키 확인
    if not NOTION_API_KEY:
        print("❌ NOTION_API_KEY 환경 변수를 설정해주세요.")
        exit(1)

    bot = AINewsBot()
    bot.run(days=args.days, use_claude=not args.no_claude)
