#!/usr/bin/env python3
"""
버그 재현 메모/로그를 입력받아 이슈 등록 초안을 생성하는 CLI.

사용 예:
    python src/generate_issue_draft.py --input examples/sample_bug_report.md
"""
import argparse
import sys
from pathlib import Path

from llm_client import call_llm
from prompts import ISSUE_DRAFT_SYSTEM_PROMPT, ISSUE_DRAFT_USER_PROMPT_TEMPLATE


def generate_issue_draft(bug_note: str) -> str:
    user_prompt = ISSUE_DRAFT_USER_PROMPT_TEMPLATE.format(bug_note=bug_note)
    return call_llm(ISSUE_DRAFT_SYSTEM_PROMPT, user_prompt)


def main():
    parser = argparse.ArgumentParser(description="버그 재현 메모 기반 이슈 초안 생성")
    parser.add_argument("--input", required=True, help="버그 재현 메모/로그 텍스트 파일 경로")
    parser.add_argument("--output", default=None, help="결과를 저장할 파일 경로 (미지정 시 stdout 출력)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"입력 파일을 찾을 수 없습니다: {input_path}", file=sys.stderr)
        sys.exit(1)

    bug_note = input_path.read_text(encoding="utf-8")
    try:
        result = generate_issue_draft(bug_note)
    except RuntimeError as e:
        print(f"오류: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        # call_llm()이 호출하는 Anthropic/OpenAI SDK는 각자 별도의 예외 체계를 가지고 있어서
        # (두 provider를 동시에 import하지 않는 이상) 여기서 특정 타입으로 좁혀 잡기 어렵다.
        # 대신 원인 타입(type(e).__name__)과 메시지는 그대로 남겨서 디버깅 가능하게 하고,
        # 사용자에게는 처리되지 않은 traceback 대신 다음 단계를 안내하는 메시지를 보여준다.
        print(f"이슈 초안 생성 중 오류가 발생했습니다 ({type(e).__name__}): {e}", file=sys.stderr)
        print("API 키/네트워크 연결 상태를 확인한 뒤 다시 시도해주세요.", file=sys.stderr)
        sys.exit(1)

    if args.output:
        Path(args.output).write_text(result, encoding="utf-8")
        print(f"이슈 초안을 저장했습니다: {args.output}")
    else:
        print(result)


if __name__ == "__main__":
    main()
