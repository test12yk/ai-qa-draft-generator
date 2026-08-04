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

    if args.output:
        Path(args.output).write_text(result, encoding="utf-8")
        print(f"이슈 초안을 저장했습니다: {args.output}")
    else:
        print(result)


if __name__ == "__main__":
    main()
