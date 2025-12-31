#!/usr/bin/env python3
"""
AI 뉴스 수집 및 GitHub 자동 커밋 스크립트

이 스크립트는 다음을 수행합니다:
1. ai_news_collector.py를 --no-notion 옵션으로 실행 (Notion 저장 안함)
2. 새로 저장된 날짜를 기반으로 커밋 메시지 생성
3. git add, commit, push 실행

사용법:
    python run_daily.py
    python run_daily.py --days 3  # 최근 3일 뉴스 수집
"""

import subprocess
import sys
import os

# 스크립트 디렉토리로 이동
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from ai_news_collector import AINewsBot


def run_git_command(command: list) -> tuple:
    """Git 명령 실행"""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="AI 뉴스 수집 및 GitHub 자동 커밋")
    parser.add_argument("--days", type=int, default=1, help="수집할 기간 (일)")
    parser.add_argument(
        "--provider",
        type=str,
        default="openai",
        choices=["openai", "claude"],
        help="AI 제공자 선택",
    )
    parser.add_argument(
        "--no-ai", action="store_true", help="AI API 사용하지 않음 (키워드 기반)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Git 커밋/푸시 없이 테스트만 실행"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("🚀 AI 뉴스 자동 수집 시작")
    print("=" * 60)

    # 1. 뉴스 수집 실행 (Notion 업로드 없이)
    try:
        bot = AINewsBot(provider=args.provider)
        result = bot.run(days=args.days, use_ai=not args.no_ai, no_notion=True)
    except Exception as e:
        print(f"❌ 뉴스 수집 실패: {e}")
        sys.exit(1)

    # 2. 저장된 날짜 확인
    saved_dates = result.get("saved_dates", [])
    md_saved = result.get("md_saved", 0)

    if md_saved == 0:
        print("\n📭 새로 저장된 뉴스가 없습니다. 커밋을 건너뜁니다.")
        sys.exit(0)

    print(f"\n📅 저장된 날짜: {', '.join(saved_dates)}")

    if args.dry_run:
        print("\n🧪 [Dry Run] Git 작업을 건너뜁니다.")
        sys.exit(0)

    # 3. Git 작업
    print("\n" + "=" * 60)
    print("📦 Git 커밋 및 푸시")
    print("=" * 60)

    # git add
    success, stdout, stderr = run_git_command(["git", "add", "."])
    if not success:
        print(f"❌ git add 실패: {stderr}")
        sys.exit(1)
    print("✅ git add 완료")

    # 커밋 메시지 생성 (docs: 12/29 또는 docs: 12/29, 12/30)
    commit_message = f"docs: {', '.join(saved_dates)}"
    print(f"📝 커밋 메시지: {commit_message}")

    # git commit
    success, stdout, stderr = run_git_command(["git", "commit", "-m", commit_message])
    if not success:
        if "nothing to commit" in stderr or "nothing to commit" in stdout:
            print("📭 커밋할 변경사항이 없습니다.")
            sys.exit(0)
        print(f"❌ git commit 실패: {stderr}")
        sys.exit(1)
    print("✅ git commit 완료")

    # git push
    success, stdout, stderr = run_git_command(["git", "push"])
    if not success:
        print(f"❌ git push 실패: {stderr}")
        sys.exit(1)
    print("✅ git push 완료")

    print("\n" + "=" * 60)
    print("🎉 모든 작업 완료!")
    print(f"   - 저장된 뉴스: {md_saved}개")
    print(f"   - 커밋 메시지: {commit_message}")
    print("=" * 60)


if __name__ == "__main__":
    main()
