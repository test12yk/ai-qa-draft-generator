#!/usr/bin/env python3
"""
개발자가 Jira에서 티켓 상태를 Resolved로 바꾸는 상황을 흉내내는 CLI.

실제 서비스에서는 이 부분이 Jira 자체(개발자가 직접 상태를 바꾸는 행위)이고,
그 변경을 감지하는 쪽(웹훅 수신 또는 주기적 polling)이 별도로 필요합니다.
이 데모에서는 그 "감지 후 시트에 반영"하는 역할을 run_pipeline.py가 매 실행 시
수행합니다 (sync_resolved_tickets 참고).

사용 예:
    python src/resolve_ticket.py QA-1001
    python src/resolve_ticket.py QA-1001 --note "디바운스 로직 추가로 중복 전송 수정 완료"
"""
import argparse
import sys

from mock_jira_client import MockJiraClient


def main():
    parser = argparse.ArgumentParser(description="mock Jira 티켓을 Resolved 상태로 변경")
    parser.add_argument("key", help="티켓 키 (예: QA-1001)")
    parser.add_argument("--note", default="", help="해결 내역 메모 (선택)")
    args = parser.parse_args()

    jira = MockJiraClient()
    try:
        result = jira.resolve_ticket(args.key, resolution_note=args.note)
    except ValueError as e:
        print(f"오류: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"{result['key']} 상태를 {result['status']}로 변경했습니다.")
    print("다음에 run_pipeline.py를 실행하면 이 변경이 시트에 반영됩니다.")


if __name__ == "__main__":
    main()
