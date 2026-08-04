#!/usr/bin/env python3
"""
기능 요구사항 문서를 입력받아 테스트케이스 초안을 생성하는 CLI.

사용 예:
    python src/generate_test_cases.py --input examples/sample_requirement.md --platform "Android,iOS,Web"
"""
import argparse
import sys
from pathlib import Path

from llm_client import call_llm
from prompts import TEST_CASE_SYSTEM_PROMPT, TEST_CASE_USER_PROMPT_TEMPLATE


def generate_test_cases(requirement_text: str, platform: str) -> str:
    user_prompt = TEST_CASE_USER_PROMPT_TEMPLATE.format(
        platform=platform, requirement=requirement_text
    )
    return call_llm(TEST_CASE_SYSTEM_PROMPT, user_prompt)


def main():
    parser = argparse.ArgumentParser(description="요구사항 기반 테스트케이스 초안 생성")
    parser.add_argument("--input", required=True, help="요구사항 텍스트 파일 경로")
    parser.add_argument(
        "--platform", default="Android,iOS,Web", help="대상 플랫폼 (쉼표로 구분)"
    )
    parser.add_argument("--output", default=None, help="결과를 저장할 파일 경로 (미지정 시 stdout 출력)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"입력 파일을 찾을 수 없습니다: {input_path}", file=sys.stderr)
        sys.exit(1)

    requirement_text = input_path.read_text(encoding="utf-8")
    try:
        result = generate_test_cases(requirement_text, args.platform)
    except RuntimeError as e:
        print(f"오류: {e}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        Path(args.output).write_text(result, encoding="utf-8")
        print(f"테스트케이스 초안을 저장했습니다: {args.output}")
    else:
        print(result)


if __name__ == "__main__":
    main()
