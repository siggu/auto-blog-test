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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

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
            summary = news_data.get("summary", "요약 없음")
            if summary:
                children.append(
                    {
                        "object": "block",
                        "type": "callout",
                        "callout": {
                            "rich_text": [
                                {"type": "text", "text": {"content": summary}}
                            ],
                            "icon": {"emoji": "💡"},
                            "color": "blue_background",
                        },
                    }
                )

            # 구분선
            children.append({"object": "block", "type": "divider", "divider": {}})

            # 2. 이미지 표시 (최대 3개)
            all_images = news_data.get("all_images", [])
            if not all_images and news_data.get("image_url"):
                all_images = [news_data.get("image_url")]

            for img_url in all_images[:3]:  # 최대 3개
                if img_url:
                    children.append(
                        {
                            "object": "block",
                            "type": "image",
                            "image": {"type": "external", "external": {"url": img_url}},
                        }
                    )

            # 3. 핵심 내용 (원문에서 추출한 문장들)
            key_sentences = news_data.get("key_sentences", [])
            if key_sentences:
                children.append(
                    {
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {
                            "rich_text": [
                                {"type": "text", "text": {"content": "핵심 내용"}}
                            ]
                        },
                    }
                )

                # 각 핵심 문장을 인용 블록으로 표시
                for sentence in key_sentences[:5]:  # 최대 5문장
                    if sentence and sentence.strip():
                        children.append(
                            {
                                "object": "block",
                                "type": "quote",
                                "quote": {
                                    "rich_text": [
                                        {
                                            "type": "text",
                                            "text": {
                                                "content": sentence.strip()[:2000]
                                            },
                                        }
                                    ],
                                    "color": "default",
                                },
                            }
                        )

            # 구분선
            children.append({"object": "block", "type": "divider", "divider": {}})

            # 4. 원문 링크
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
                                    "content": f"발행일: {news_data.get('date', 'N/A')}  |  출처: {news_data.get('source', 'N/A')}"
                                },
                            }
                        ],
                        "icon": {"emoji": "📄"},
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
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            # 너무 짧은 단락은 합치기
            merged = []
            current = ""
            for p in paragraphs:
                if len(p) < 50 and current:
                    current += " " + p
                else:
                    if current:
                        merged.append(current)
                    current = p
            if current:
                merged.append(current)
            return merged

        if "\n" in text:
            lines = [p.strip() for p in text.split("\n") if p.strip()]
            # 한 줄씩 있으면 2-3줄씩 합치기
            merged = []
            current = ""
            for line in lines:
                if len(current) + len(line) < 300:
                    current = (current + " " + line).strip() if current else line
                else:
                    if current:
                        merged.append(current)
                    current = line
            if current:
                merged.append(current)
            return merged

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
# 뉴스 분석기 (OpenAI / Claude API 선택 가능)
# =============================================================================


class NewsAnalyzer:
    """AI API를 사용한 뉴스 분석 (OpenAI 또는 Claude)"""

    def __init__(self, api_key: str, provider: str = "openai"):
        """
        Args:
            api_key: API 키
            provider: "openai" (기본) 또는 "claude"
        """
        self.api_key = api_key
        self.provider = provider.lower()

        if self.provider == "claude":
            self.base_url = "https://api.anthropic.com/v1/messages"
            self.model = "claude-sonnet-4-20250514"
        else:
            self.base_url = "https://api.openai.com/v1/chat/completions"
            self.model = "gpt-5-nano"  # 가장 저렴한 모델 ($0.05/$0.40 per 1M tokens)

    def analyze_news(self, title: str, content: str) -> dict:
        """뉴스 분석 및 분류 (원문 보존)"""

        prompt = f"""다음 뉴스가 AI/인공지능 **기술** 관련 뉴스인지 분석해주세요.

제목: {title}
내용: {content[:4000]}

다음 JSON 형식으로 응답해주세요:
{{
    "is_ai_related": true 또는 false,
    "rejection_reason": "AI 관련 없는 경우 이유",
    "summary": "2-3문장 요약 (한국어)",
    "key_sentences": ["원문에서 핵심 문장 1", "원문에서 핵심 문장 2", ...],
    "technologies": ["LLM", "이미지 생성", "추론 AI", "에이전트", "멀티모달", "오픈소스", "강화학습", "로보틱스", "음성/오디오" 중 선택],
    "organization": "OpenAI, Google, Anthropic, Meta, Microsoft, NVIDIA, 국내 연구기관, 기타 중 선택",
    "importance": "🔥 주요, 📌 일반, 📝 참고 중 선택"
}}

**key_sentences 규칙 (매우 중요):**
- 원문에서 가장 중요한 문장을 **그대로 복사**
- 최소 1문장, 최대 5문장
- 절대 수정하거나 요약하지 말고, 원문 그대로 사용
- 기사의 핵심 정보를 담은 문장 선택

**key_sentences 제외 대상:**
- 이미지 캡션/설명 (예: "사진=...", "(사진:...)", "이미지:...", "출처=...")
- 기자 정보, 저작권 문구
- 날짜/장소만 있는 문장

**AI 관련성 판단:**
✅ AI 관련: AI 기술/연구, AI 기업 동향, AI 정책/규제, AI 제품/서비스
❌ AI 비관련: AI웹툰/만화 (AI 생성 콘텐츠), 연예/스포츠

JSON만 출력하세요."""

        try:
            if self.provider == "openai":
                response = self._call_openai(prompt)
            else:
                response = self._call_claude(prompt)

            if response:
                # key_sentences에서 이미지 캡션 필터링
                if "key_sentences" in response:
                    response["key_sentences"] = self._filter_image_captions(
                        response["key_sentences"]
                    )
                return response
        except Exception as e:
            print(f"분석 오류: {e}")

        # 폴백: 키워드 기반 분류
        return self._fallback_analysis(title, content)

    def _filter_image_captions(self, sentences: list) -> list:
        """이미지 캡션/설명 문장 필터링"""
        import re

        if not sentences:
            return []

        # 이미지 캡션 패턴
        caption_patterns = [
            r"^사진[=:]",
            r"^\(사진[=:]",
            r"^이미지[=:]",
            r"^\(이미지[=:]",
            r"^출처[=:]",
            r"^\(출처[=:]",
            r"^사진 제공",
            r"본지\s*DB",
            r"제공\s*사진",
            r"캡처\s*화면",
            r"스크린샷",
            r"^▲",
            r"^\[사진\]",
            r"AI\s*생성.*이미지",
            r"이미지.*AI\s*생성",
        ]

        filtered = []
        for sentence in sentences:
            if not sentence or not sentence.strip():
                continue

            sentence = sentence.strip()

            # 패턴 매칭으로 이미지 캡션 제외
            is_caption = False
            for pattern in caption_patterns:
                if re.search(pattern, sentence, re.IGNORECASE):
                    is_caption = True
                    break

            # 너무 짧은 문장 제외 (20자 미만)
            if len(sentence) < 20:
                is_caption = True

            if not is_caption:
                filtered.append(sentence)

        return filtered[:5]  # 최대 5문장

    def _call_openai(self, prompt: str) -> dict:
        """OpenAI API 호출"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_completion_tokens": 1000,  # GPT-5 모델은 max_completion_tokens 사용, temperature 미지원
        }

        response = requests.post(self.base_url, headers=headers, json=data)

        if response.status_code != 200:
            print(f"OpenAI API 오류 ({response.status_code}): {response.text[:200]}")
            return None

        result = response.json()

        if "choices" in result and len(result["choices"]) > 0:
            text = result["choices"][0]["message"]["content"]
            return self._parse_json_response(text)

        return None

    def _call_claude(self, prompt: str) -> dict:
        """Claude API 호출"""
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        data = {
            "model": self.model,
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}],
        }

        response = requests.post(self.base_url, headers=headers, json=data)

        if response.status_code != 200:
            print(f"Claude API 오류 ({response.status_code}): {response.text[:200]}")
            return None

        result = response.json()

        if "content" in result and len(result["content"]) > 0:
            text = result["content"][0]["text"]
            return self._parse_json_response(text)

        return None

    def _parse_json_response(self, text: str) -> dict:
        """JSON 응답 파싱"""
        import re

        if not text:
            return None

        # 디버깅: 응답 앞부분 출력
        # print(f"DEBUG 응답: {text[:500]}")

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

        # 3. ``` ... ``` 형식 (json 표시 없이)
        json_match = re.search(r"```\s*([\s\S]*?)\s*```", text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except:
                pass

        # 4. 중괄호로 시작하는 JSON 찾기 (가장 바깥쪽 중괄호)
        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except:
                # JSON 내부의 특수문자 처리 시도
                json_str = json_match.group(0)
                # 줄바꿈을 이스케이프
                json_str = json_str.replace("\n", "\\n")
                try:
                    return json.loads(json_str)
                except:
                    pass

        # 5. 키-값 패턴으로 수동 추출 시도
        try:
            result = {}

            # is_ai_related 추출
            ai_match = re.search(
                r'"is_ai_related"\s*:\s*(true|false)', text, re.IGNORECASE
            )
            if ai_match:
                result["is_ai_related"] = ai_match.group(1).lower() == "true"

            # rejection_reason 추출
            reason_match = re.search(r'"rejection_reason"\s*:\s*"([^"]*)"', text)
            if reason_match:
                result["rejection_reason"] = reason_match.group(1)

            # summary 추출
            summary_match = re.search(r'"summary"\s*:\s*"([^"]*)"', text)
            if summary_match:
                result["summary"] = summary_match.group(1)

            # importance 추출
            importance_match = re.search(r'"importance"\s*:\s*"([^"]*)"', text)
            if importance_match:
                result["importance"] = importance_match.group(1)

            # organization 추출
            org_match = re.search(r'"organization"\s*:\s*"([^"]*)"', text)
            if org_match:
                result["organization"] = org_match.group(1)

            if "is_ai_related" in result:
                # 기본값 설정
                result.setdefault("rejection_reason", "")
                result.setdefault("summary", "")
                result.setdefault("key_sentences", [])
                result.setdefault("technologies", ["기타"])
                result.setdefault("organization", "기타")
                result.setdefault("importance", "📌 일반")
                return result
        except:
            pass

        print(f"JSON 추출 실패. 응답: {text[:100]}...")
        return None

    def _fallback_analysis(self, title: str, content: str) -> dict:
        """키워드 기반 폴백 분석"""
        text = (title + " " + content).lower()

        # AI 관련성 체크 (키워드 기반)
        ai_keywords = [
            "ai",
            "artificial intelligence",
            "인공지능",
            "machine learning",
            "머신러닝",
            "deep learning",
            "딥러닝",
            "neural network",
            "신경망",
            "llm",
            "gpt",
            "claude",
            "gemini",
            "chatgpt",
            "openai",
            "anthropic",
            "transformer",
            "자연어처리",
            "nlp",
            "computer vision",
            "컴퓨터 비전",
            "reinforcement learning",
            "강화학습",
            "generative ai",
            "생성형 ai",
            "foundation model",
            "파운데이션 모델",
            "nvidia",
            "엔비디아",
            "gpu",
            "cuda",
            "tensor",
            "텐서",
            "추론",
            "inference",
        ]

        # 비AI 키워드 (제외 대상)
        non_ai_keywords = [
            "결혼",
            "이혼",
            "열애",
            "연예",
            "아이돌",
            "드라마",
            "예능",
            "가수",
            "배우",
            "축구",
            "야구",
            "농구",
            "올림픽",
            "월드컵",
            "경기 결과",
            "승리",
            "패배",
            "날씨",
            "기온",
            "강수량",
            "미세먼지",
        ]

        # 제목 기반 필터링 (AI로 만든 콘텐츠는 AI 기술 뉴스가 아님)
        title_lower = title.lower()
        ai_content_patterns = [
            "ai웹툰",
            "ai만화",
            "ai 웹툰",
            "ai 만화",
            "ai그림",
            "ai 그림",
            "ai이미지",
            "ai 이미지",
            "ai영상",
            "ai 영상",
            "ai이슈트렌드",
            "ai 이슈트렌드",
            "ai 이슈 트렌드",
            "[ai웹툰]",
            "[ai만화]",
            "[ai 웹툰]",
            "[ai 만화]",
        ]

        is_ai_generated_content = any(
            pattern in title_lower for pattern in ai_content_patterns
        )

        has_ai_keyword = any(keyword in text for keyword in ai_keywords)
        has_non_ai_keyword = any(keyword in text for keyword in non_ai_keywords)

        # AI 키워드가 있고 비AI 키워드가 없으면 관련
        # 단, AI로 만든 콘텐츠(웹툰, 만화 등)는 제외
        is_ai_related = (
            has_ai_keyword and not has_non_ai_keyword and not is_ai_generated_content
        )

        # 거부 사유 설정
        if is_ai_generated_content:
            rejection_reason = "AI로 만든 콘텐츠 (AI 기술 뉴스 아님)"
        elif has_non_ai_keyword:
            rejection_reason = "비AI 관련 콘텐츠 (연예/스포츠/일반)"
        elif not has_ai_keyword:
            rejection_reason = "AI 관련 키워드 없음"
        else:
            rejection_reason = ""

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

        # 폴백용 핵심 문장 추출 (이미지 캡션 제외)
        import re

        sentences = re.split(r"[.!?。]\s+", content)
        raw_sentences = [
            s.strip() + "." for s in sentences if s.strip() and len(s.strip()) > 20
        ]
        key_sentences = self._filter_image_captions(raw_sentences)[:2]

        return {
            "is_ai_related": is_ai_related,
            "rejection_reason": rejection_reason,
            "summary": title,
            "key_sentences": key_sentences,
            "technologies": technologies[:3] if technologies else ["기타"],
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

                    # 본문 및 이미지 추출
                    content_data = self._get_content(entry)

                    news_item = {
                        "title": entry.get("title", ""),
                        "link": entry.get("link", ""),
                        "content": content_data.get("content", ""),
                        "image_url": content_data.get("image_url"),
                        "all_images": content_data.get("all_images", []),  # 모든 이미지
                        "date": pub_date.strftime("%Y-%m-%d"),
                        "source": feed_info["name"],
                    }
                    all_news.append(news_item)

                    # 디버그 출력
                    img_count = len(content_data.get("all_images", []))
                    img_status = f"🖼️({img_count})" if img_count > 0 else "📄"
                    print(
                        f"{img_status} {news_item['title'][:50]}... -> {news_item['date']}"
                    )

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

    def _get_content(self, entry) -> dict:
        """기사 본문 및 이미지 추출 - RSS 내용 + 웹 스크래핑"""
        result = {"content": "", "image_url": None, "all_images": []}

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
            scraped = self._scrape_article(link)
            if scraped.get("content") and len(scraped["content"]) > len(
                self._strip_html(rss_content)
            ):
                result["content"] = scraped["content"]
            else:
                result["content"] = self._strip_html(rss_content)

            # 이미지 URL 저장
            if scraped.get("image_url"):
                result["image_url"] = scraped["image_url"]
            if scraped.get("all_images"):
                result["all_images"] = scraped["all_images"]
        else:
            result["content"] = self._strip_html(rss_content)

        return result

    def _strip_html(self, html_content: str) -> str:
        """HTML 태그 제거하고 순수 텍스트 반환"""
        if not html_content:
            return ""

        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_content, "html.parser")

            # 불필요한 태그 제거
            for tag in soup.select("script, style, nav, footer, aside, figure, img"):
                tag.decompose()

            # 텍스트 추출
            text = soup.get_text(separator="\n", strip=True)

            # 연속 공백/줄바꿈 정리
            import re

            text = re.sub(r"\n{3,}", "\n\n", text)
            text = re.sub(r" {2,}", " ", text)

            return text.strip()
        except ImportError:
            # BeautifulSoup 없으면 간단한 정규식으로 처리
            import re

            text = re.sub(r"<[^>]+>", "", html_content)
            text = re.sub(r"\s+", " ", text)
            return text.strip()
        except:
            return html_content

    def _scrape_article(self, url: str) -> dict:
        """기사 페이지에서 본문과 모든 이미지 스크래핑"""
        result = {"content": "", "image_url": None, "all_images": []}

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            # HTML 파싱
            from bs4 import BeautifulSoup
            from urllib.parse import urljoin

            soup = BeautifulSoup(response.text, "html.parser")

            # 모든 이미지 추출
            all_images = self._extract_all_images(soup, url)
            if all_images:
                result["image_url"] = all_images[0]  # 첫 번째는 대표 이미지
                result["all_images"] = all_images  # 모든 이미지

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
                        "script, style, nav, footer, aside, .ad, .advertisement, .social-share, .related-article, .related_article, .sns_share, .article-sns, .byline, .reporter-info, .copyright, .article-footer, .tag-group, .keyword, .article-tag"
                    ):
                        tag.decompose()

                    content = element.get_text(separator="\n", strip=True)
                    if content and len(content) > 200:
                        break

            if content:
                # 콘텐츠 정리
                content = self._clean_article_content(content)
                result["content"] = content[:8000]  # 더 많은 내용 포함

        except ImportError:
            print("⚠️ BeautifulSoup 미설치. pip install beautifulsoup4 실행 필요")
        except Exception as e:
            # 스크래핑 실패 시 조용히 넘어감
            pass

        return result

    def _clean_article_content(self, content: str) -> str:
        """기사 본문에서 불필요한 메타데이터 제거"""
        import re

        if not content:
            return ""

        lines = content.split("\n")
        cleaned_lines = []

        # 제외할 패턴들
        skip_patterns = [
            r"^좋아요\s*$",
            r"^\d+\s*$",  # 숫자만 있는 줄
            r"^관련기사\s*$",
            r"^다른기사\s*보기",
            r"^키워드\s*$",
            r"^#\w+",  # 해시태그
            r"^저작권자",
            r"무단전재",
            r"재배포.*금지",
            r"^기자$",
            r"@.*\.com",  # 이메일
            r"^news@",
            r"^\S+기자$",
            r"^▶",  # 관련 기사 링크
            r"^☞",
            r"^\[관련기사\]",
            r"^\[.*기자\]$",
            r"^사진=",
            r"^\(사진=",
            r"^출처=",
            r"^\(출처=",
            r"^ⓒ",
            r"^©",
            r"^Copyrights",
            r"AI학습.*금지",
            r"뉴스제공",
        ]

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 너무 짧은 줄 제외 (3자 미만)
            if len(line) < 3:
                continue

            # 패턴 매칭으로 제외
            should_skip = False
            for pattern in skip_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    should_skip = True
                    break

            if should_skip:
                continue

            cleaned_lines.append(line)

        return "\n\n".join(cleaned_lines)

    def _extract_main_image(self, soup, base_url: str) -> str:
        """기사의 대표 이미지 URL 추출"""
        from urllib.parse import urljoin

        # 이미지 선택자 (우선순위 순)
        image_selectors = [
            # Open Graph 이미지 (가장 신뢰할 수 있음)
            'meta[property="og:image"]',
            # Twitter 카드 이미지
            'meta[name="twitter:image"]',
            # 기사 본문 내 첫 번째 이미지
            "article img",
            "#article-view-content-div img",
            ".article-body img",
            ".article_body img",
            ".article-content img",
            'div[itemprop="articleBody"] img',
        ]

        for selector in image_selectors:
            element = soup.select_one(selector)
            if element:
                # meta 태그인 경우
                if element.name == "meta":
                    image_url = element.get("content")
                # img 태그인 경우
                else:
                    image_url = element.get("src") or element.get("data-src")

                if image_url:
                    # 상대 경로를 절대 경로로 변환
                    image_url = urljoin(base_url, image_url)

                    # 유효한 이미지 URL인지 확인 (기본적인 필터링)
                    if self._is_valid_image_url(image_url):
                        return image_url

        return None

    def _extract_all_images(self, soup, base_url: str) -> list:
        """기사의 모든 이미지 URL 추출"""
        from urllib.parse import urljoin

        images = []
        seen_urls = set()

        # 1. Open Graph 이미지 먼저 추가
        og_image = soup.select_one('meta[property="og:image"]')
        if og_image:
            url = og_image.get("content")
            if url and self._is_valid_image_url(url):
                full_url = urljoin(base_url, url)
                if full_url not in seen_urls:
                    images.append(full_url)
                    seen_urls.add(full_url)

        # 2. 기사 본문 내 모든 이미지
        article_selectors = [
            "#article-view-content-div img",
            "article img",
            ".article-body img",
            ".article_body img",
            ".article-content img",
            'div[itemprop="articleBody"] img',
        ]

        for selector in article_selectors:
            for img in soup.select(selector):
                url = img.get("src") or img.get("data-src") or img.get("data-original")
                if url:
                    full_url = urljoin(base_url, url)
                    if full_url not in seen_urls and self._is_valid_image_url(full_url):
                        images.append(full_url)
                        seen_urls.add(full_url)

        # 최대 10개까지만 (너무 많으면 페이지가 무거워짐)
        return images[:10]

    def _is_valid_image_url(self, url: str) -> bool:
        """유효한 이미지 URL인지 확인"""
        if not url:
            return False

        # 광고/트래킹 이미지 제외
        exclude_patterns = [
            "pixel",
            "tracking",
            "analytics",
            "beacon",
            "advertisement",
            "banner",
            "ad.",
            "ads.",
            "1x1",
            "spacer",
            "blank",
            "transparent",
        ]

        url_lower = url.lower()
        for pattern in exclude_patterns:
            if pattern in url_lower:
                return False

        # 이미지 확장자 또는 이미지 서비스 확인
        valid_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        has_valid_ext = any(ext in url_lower for ext in valid_extensions)

        # 이미지 서비스 URL (확장자 없이 이미지 제공)
        image_services = ["wp-content/uploads", "images", "img", "photo", "media"]
        is_image_service = any(svc in url_lower for svc in image_services)

        return has_valid_ext or is_image_service


# =============================================================================
# 마크다운 파일 저장
# =============================================================================


class MarkdownArchive:
    """뉴스를 월별 마크다운 파일로 저장"""

    def __init__(self, base_dir: str = None):
        """
        Args:
            base_dir: 저장 기본 경로. None이면 스크립트 위치 사용
        """
        if base_dir:
            self.base_dir = base_dir
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))

    def save_news(self, news: dict, analysis: dict) -> bool:
        """
        뉴스를 일별 마크다운 파일에 저장

        Args:
            news: 뉴스 데이터 (title, link, content, date, source)
            analysis: 분석 결과 (summary, technologies, organization, importance, key_points)

        Returns:
            bool: 저장 성공 여부 (중복이면 False)
        """
        # 날짜 파싱
        try:
            news_date = datetime.strptime(news["date"], "%Y-%m-%d")
        except:
            news_date = datetime.now()

        year = str(news_date.year)
        month = f"{news_date.month:02d}월"
        day = f"{news_date.month:02d}-{news_date.day:02d}"

        # 폴더 생성: 연도/월/
        month_dir = os.path.join(self.base_dir, year, month)
        os.makedirs(month_dir, exist_ok=True)

        # 파일 경로: 연도/월/MM-DD.md
        md_file = os.path.join(month_dir, f"{day}.md")

        # 중복 체크
        if self._is_duplicate(md_file, news["title"], news["link"]):
            return False

        # 마크다운 내용 생성
        md_content = self._format_news(news, analysis)

        # 일별 파일에 추가
        self._append_to_file(md_file, md_content, news_date)

        # 월 총괄 파일 업데이트
        self._update_monthly_index(month_dir, news_date)

        return True

    def regenerate_all_indexes(self):
        """모든 월별 README.md 재생성"""
        regenerated = 0

        # 연도 폴더 탐색
        for year_dir in os.listdir(self.base_dir):
            year_path = os.path.join(self.base_dir, year_dir)
            if not os.path.isdir(year_path) or not year_dir.isdigit():
                continue

            # 월 폴더 탐색
            for month_dir in os.listdir(year_path):
                month_path = os.path.join(year_path, month_dir)
                if not os.path.isdir(month_path) or "월" not in month_dir:
                    continue

                # 일별 파일이 있는지 확인
                has_daily_files = any(
                    f.endswith(".md") and f != "README.md"
                    for f in os.listdir(month_path)
                )

                if has_daily_files:
                    # 임의의 날짜로 월 인덱스 업데이트 (월 정보만 필요)
                    month_num = int(month_dir.replace("월", ""))
                    dummy_date = datetime(int(year_dir), month_num, 1)
                    self._update_monthly_index(month_path, dummy_date)
                    print(f"✅ 재생성: {year_dir}/{month_dir}/README.md")
                    regenerated += 1

        return regenerated

    def _update_monthly_index(self, month_dir: str, news_date: datetime):
        """월 총괄 파일(README.md) 업데이트"""
        import re

        index_file = os.path.join(month_dir, "README.md")
        month_title = news_date.strftime("%Y년 %m월")

        # 해당 월의 모든 일별 파일 수집
        daily_files = []
        for filename in sorted(os.listdir(month_dir), reverse=True):  # 최신순
            if filename.endswith(".md") and filename != "README.md":
                daily_files.append(filename)

        # 각 일별 파일에서 뉴스 제목 추출
        toc_content = []
        total_count = 0

        for daily_file in daily_files:
            filepath = os.path.join(month_dir, daily_file)
            day_name = daily_file.replace(".md", "")  # "12-27"

            # 날짜 파싱해서 보기 좋게
            try:
                month_num, day_num = day_name.split("-")
                display_date = f"{int(month_num)}월 {int(day_num)}일"
            except:
                display_date = day_name

            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # 뉴스 제목 추출 (### 뒤에 오는 제목, 단 📑 목차 제외)
            news_titles = re.findall(r"^### (?!📑)(.+)", content, re.MULTILINE)
            news_count = len(news_titles)
            total_count += news_count

            # 일별 섹션 추가
            toc_content.append(f"\n### 📅 {display_date} ({news_count}건)")
            toc_content.append(f"📄 [{day_name}.md](./{daily_file})\n")

            for title in news_titles:
                display_title = title[:50] + "..." if len(title) > 50 else title
                toc_content.append(f"- {display_title}")

        # README.md 생성
        readme_content = f"""# 🤖 AI 뉴스 아카이브 - {month_title}

> 총 **{total_count}건**의 뉴스가 수집되었습니다.

## 📑 목차

{''.join(chr(10) + line for line in toc_content)}

---

*이 파일은 자동으로 생성됩니다.*
"""

        with open(index_file, "w", encoding="utf-8") as f:
            f.write(readme_content)

    def _is_duplicate(self, filepath: str, title: str, link: str) -> bool:
        """파일에서 중복 뉴스 체크"""
        if not os.path.exists(filepath):
            return False

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                # 제목이나 링크로 중복 확인
                if title in content or link in content:
                    return True
        except:
            pass

        return False

    def _format_news(self, news: dict, analysis: dict) -> str:
        """뉴스를 마크다운 형식으로 변환"""
        lines = []

        # 제목 (제목에서 날짜 태그 제거하여 깔끔하게)
        import re

        clean_title = re.sub(
            r"^\[\d{1,2}월\d{1,2}일\]\s*", "", news["title"]
        )  # [12월26일] 형식 제거
        clean_title = re.sub(
            r"^\[\d{4}\.\d{2}\.\d{2}\]\s*", "", clean_title
        )  # [2025.12.26] 형식 제거

        lines.append(f"### {clean_title}")
        lines.append("")

        # 메타 정보 (발행일 추가)
        importance = analysis.get("importance", "📌 일반")
        org = analysis.get("organization", "기타")
        techs = ", ".join(analysis.get("technologies", []))

        lines.append(
            f"> 📅 **{news['date']}** | **{importance}** | {org} | {news['source']}"
        )
        if techs:
            lines.append(f"> 🏷️ {techs}")
        lines.append("")

        # 요약
        summary = analysis.get("summary", "")
        if summary:
            lines.append("**💡 요약**")
            lines.append(f"{summary}")
            lines.append("")

        # 핵심 포인트
        key_points = analysis.get("key_points", [])
        if key_points:
            lines.append("**📌 핵심 포인트**")
            for point in key_points[:5]:
                lines.append(f"- {point}")
            lines.append("")

        # 원문 내용 (최대 1000자)
        content = news.get("content", "")
        if content:
            lines.append("<details>")
            lines.append("<summary><b>📄 원문 보기</b></summary>")
            lines.append("")
            # 원문 정리 (너무 길면 자르기)
            clean_content = content[:1500].strip()
            if len(content) > 1500:
                clean_content += "..."
            lines.append(clean_content)
            lines.append("")
            lines.append("</details>")
            lines.append("")

        # 출처 링크
        lines.append(f"🔗 [원문 보기]({news['link']})")
        lines.append("")
        lines.append("---")
        lines.append("")

        return "\n".join(lines)

    def _append_to_file(self, filepath: str, content: str, news_date: datetime):
        """파일에 내용 추가 (목차 포함)"""
        date_title = news_date.strftime("%Y년 %m월 %d일")

        # 파일이 없으면 새로 생성
        if not os.path.exists(filepath):
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"# 🤖 AI 뉴스 - {date_title}\n\n")
                f.write("## 📑 목차\n\n")
                f.write("<!-- TOC_START -->\n")
                f.write("<!-- TOC_END -->\n\n")
                f.write("---\n\n")
                f.write(content)
            self._update_toc(filepath)
            return

        # 기존 파일에 추가
        with open(filepath, "r", encoding="utf-8") as f:
            existing = f.read()

        # 구분선(---) 뒤에 새 콘텐츠 추가
        # 마지막 --- 찾아서 그 뒤에 추가
        new_content = existing.rstrip() + "\n\n" + content

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)

        # 목차 업데이트
        self._update_toc(filepath)

    def _update_toc(self, filepath: str):
        """파일의 목차를 업데이트"""
        import re

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # 뉴스 제목 추출
        toc_entries = []

        # 뉴스 제목 찾기 (### 제목 형식)
        news_pattern = r"### ([^#\n].+)"

        lines = content.split("\n")
        for line in lines:
            news_match = re.match(news_pattern, line)
            if news_match:
                title = news_match.group(1)
                # 앵커 생성
                anchor = self._create_anchor(title)
                toc_entries.append({"title": title, "anchor": anchor})

        # 목차 생성
        toc_lines = []
        for i, entry in enumerate(toc_entries, 1):
            # 제목이 너무 길면 자르기
            display_title = (
                entry["title"][:60] + "..."
                if len(entry["title"]) > 60
                else entry["title"]
            )
            toc_lines.append(f"{i}. [{display_title}](#{entry['anchor']})")

        toc_content = "\n".join(toc_lines) if toc_lines else "(뉴스 없음)"

        # 목차 영역 교체
        new_content = re.sub(
            r"<!-- TOC_START -->.*?<!-- TOC_END -->",
            f"<!-- TOC_START -->\n{toc_content}\n<!-- TOC_END -->",
            content,
            flags=re.DOTALL,
        )

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)

    def _create_anchor(self, title: str) -> str:
        """마크다운 앵커 생성 (GitHub 스타일)"""
        import re

        # 소문자 변환
        anchor = title.lower()
        # 이모지 및 특수문자 제거 (한글, 영문, 숫자, 공백, 하이픈만 유지)
        anchor = re.sub(r"[^\w\s가-힣-]", "", anchor)
        # 공백을 하이픈으로
        anchor = re.sub(r"\s+", "-", anchor)
        anchor = anchor.strip("-")
        return anchor


# =============================================================================
# 메인 실행
# =============================================================================


class AINewsBot:
    """AI 뉴스 자동화 봇"""

    def __init__(self, archive_dir: str = None, provider: str = "openai"):
        """
        Args:
            archive_dir: 마크다운 아카이브 저장 경로 (None이면 스크립트 위치)
            provider: AI 제공자 - "openai" (기본) 또는 "claude"
        """
        self.notion = NotionClient(NOTION_API_KEY)
        self.collector = NewsCollector(RSS_FEEDS)
        self.archive = MarkdownArchive(archive_dir)
        self.provider = provider.lower()

        # API 키 설정
        if self.provider == "claude":
            if not ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다.")
            self.analyzer = NewsAnalyzer(ANTHROPIC_API_KEY, provider="claude")
            print(f"🤖 Claude API 사용 (모델: claude-sonnet-4-20250514)")
        else:
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
            self.analyzer = NewsAnalyzer(OPENAI_API_KEY, provider="openai")
            print(f"🤖 OpenAI API 사용 (모델: gpt-5-nano) - 💰 최저가!")

    def run(self, days: int = 1, use_ai: bool = True, no_notion: bool = False):
        """뉴스 수집 및 업로드 실행

        Args:
            days: 수집할 기간 (일)
            use_ai: AI API 사용 여부
            no_notion: True면 Notion 업로드 건너뛰기
        """
        print(f"🔍 최근 {days}일 AI 뉴스 수집 중...")
        if no_notion:
            print("📝 Notion 업로드 비활성화 - 마크다운만 저장합니다.")

        # 뉴스 수집
        news_list = self.collector.collect_news(days=days)
        print(f"📰 {len(news_list)}개 뉴스 발견")

        uploaded = 0
        skipped = 0
        filtered = 0
        md_saved = 0
        saved_dates = set()  # 저장된 날짜들 수집

        for news in news_list:
            # 중복 체크 (Notion) - no_notion 모드에서는 건너뛰기
            if not no_notion:
                notion_duplicate = self.notion.check_duplicate(DATABASE_ID, news["title"])
                if notion_duplicate:
                    print(f"⏭️ 중복 건너뛰기: {news['title'][:30]}...")
                    skipped += 1
                    continue

            # 뉴스 분석
            if use_ai:
                analysis = self.analyzer.analyze_news(news["title"], news["content"])
            else:
                analysis = self.analyzer._fallback_analysis(
                    news["title"], news["content"]
                )

            # AI 관련성 필터
            if not analysis.get("is_ai_related", True):
                reason = analysis.get("rejection_reason", "AI 비관련")
                print(f"🚫 AI 비관련 제외: {news['title'][:30]}... ({reason})")
                filtered += 1
                continue

            # 날짜에서 연도/월 추출
            try:
                news_date = datetime.strptime(news["date"], "%Y-%m-%d")
                year = str(news_date.year)
                month = f"{news_date.month:02d}월"
            except:
                year = str(datetime.now().year)
                month = f"{datetime.now().month:02d}월"

            # Notion 속성 구성
            properties = {
                "제목": {"title": [{"text": {"content": news["title"][:100]}}]},
                "날짜": {"date": {"start": news["date"]}},
                "연도": {"select": {"name": year}},
                "월": {"select": {"name": month}},
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

            # Notion에 업로드 (no_notion 모드에서는 건너뛰기)
            if not no_notion:
                try:
                    # 페이지 내용에 사용할 데이터
                    page_content = {
                        "summary": analysis.get("summary", ""),
                        "key_sentences": analysis.get(
                            "key_sentences", []
                        ),  # 핵심 문장 (1~5개)
                        "image_url": news.get("image_url"),
                        "all_images": news.get("all_images", []),
                        "link": news["link"],
                        "date": news["date"],
                        "source": news["source"],
                    }

                    result = self.notion.create_page(DATABASE_ID, properties, page_content)
                    if "id" in result:
                        img_icon = "🖼️" if news.get("image_url") else "📄"
                        print(f"✅ {img_icon} Notion 업로드 완료: {news['title'][:40]}...")
                        uploaded += 1
                    else:
                        print(
                            f"❌ Notion 업로드 실패: {result.get('message', 'Unknown error')}"
                        )
                except Exception as e:
                    print(f"❌ Notion 오류: {e}")

            # 마크다운 파일에 저장
            try:
                if self.archive.save_news(news, analysis):
                    print(f"📝 마크다운 저장 완료: {news['title'][:40]}...")
                    md_saved += 1
                    # 저장된 날짜 수집 (MM/DD 형식)
                    try:
                        news_date = datetime.strptime(news["date"], "%Y-%m-%d")
                        saved_dates.add(f"{news_date.month}/{news_date.day}")
                    except:
                        pass
                else:
                    print(f"⏭️ 마크다운 중복 건너뛰기: {news['title'][:30]}...")
            except Exception as e:
                print(f"❌ 마크다운 저장 오류: {e}")

        print(f"\n📊 완료!")
        print(f"   - Notion 업로드: {uploaded}개")
        print(f"   - 마크다운 저장: {md_saved}개")
        print(f"   - AI 비관련 제외: {filtered}개")
        print(f"   - 중복 건너뛰기: {skipped}개")

        # 결과 반환: (업로드 수, 마크다운 저장 수, 저장된 날짜 리스트)
        return {
            "uploaded": uploaded,
            "md_saved": md_saved,
            "filtered": filtered,
            "skipped": skipped,
            "saved_dates": sorted(saved_dates),  # 정렬된 날짜 리스트
        }


# =============================================================================
# 실행
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI 뉴스 자동 수집기")
    parser.add_argument("--days", type=int, default=1, help="수집할 기간 (일)")
    parser.add_argument(
        "--no-ai", action="store_true", help="AI API 사용하지 않음 (키워드 기반)"
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="openai",
        choices=["openai", "claude"],
        help="AI 제공자 선택 (기본: openai - gpt-5-nano)",
    )
    parser.add_argument(
        "--archive-dir", type=str, default=None, help="마크다운 아카이브 저장 경로"
    )
    parser.add_argument(
        "--no-notion", action="store_true", help="Notion 업로드 비활성화 (마크다운만 저장)"
    )
    parser.add_argument(
        "--regenerate-index", action="store_true", help="모든 월별 README.md 재생성"
    )

    args = parser.parse_args()

    # --regenerate-index 모드
    if args.regenerate_index:
        print("🔄 월별 README.md 재생성 중...")
        archive = MarkdownArchive()
        count = archive.regenerate_all_indexes()
        print(f"\n✅ {count}개의 README.md 파일이 재생성되었습니다.")
        exit(0)

    # API 키 확인 (no_notion 모드가 아닐 때만 Notion API 키 필요)
    if not args.no_notion and not NOTION_API_KEY:
        print("❌ NOTION_API_KEY 환경 변수를 설정해주세요.")
        exit(1)

    if not args.no_ai:
        if args.provider == "openai" and not OPENAI_API_KEY:
            print("❌ OPENAI_API_KEY 환경 변수를 설정해주세요.")
            exit(1)
        elif args.provider == "claude" and not ANTHROPIC_API_KEY:
            print("❌ ANTHROPIC_API_KEY 환경 변수를 설정해주세요.")
            exit(1)

    bot = AINewsBot(archive_dir=args.archive_dir, provider=args.provider)
    bot.run(days=args.days, use_ai=not args.no_ai, no_notion=args.no_notion)
