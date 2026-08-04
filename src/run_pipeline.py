#!/usr/bin/env python3
"""
다운로드 후 아무 설정 없이 바로 실행 가능한 end-to-end 데모 파이프라인.

data/mock_test_sheet.csv 하나를 실제 Google Sheet처럼 취급합니다 — 매번 같은 파일을
읽고, 같은 파일에 그대로 덮어씁니다 (별도의 "결과 파일"을 만들지 않습니다).
이 파일이 아직 없으면(최초 실행) data/mock_test_sheet_seed.csv(데모용 초기 데이터)에서
자동으로 만듭니다.

실행할 때마다 두 방향을 모두 처리합니다.

1) BTS -> 시트 (역방향 동기화): 이전에 생성한 티켓 중 resolve_ticket.py로
   Resolved 처리된 것이 있으면, 시트의 Ticket 칸에 그 상태를 반영합니다.
   (실제 서비스라면 Jira 웹훅/polling으로 감지하는 부분)
2) 시트 -> BTS (기존 흐름): Fail 이면서 아직 티켓이 없는 행을 찾아
   (LLM API 키가 있으면) LLM으로 이슈 초안을 생성 / (없으면) 템플릿으로 대체하고,
   MockJiraClient로 로컬에 티켓을 생성해 시트에 티켓 번호를 채웁니다.

실제 QA 자동화 봇(시트 감시 <-> Jira 티켓 생성/상태 동기화)의 구조를, 실제 계정/시크릿
없이도 그대로 체험할 수 있도록 만든 데모입니다.

사용법:
    python src/run_pipeline.py            # 시트를 이어서 읽고 씀 (실제 서비스와 동일한 방식)
    python src/run_pipeline.py --reset    # 티켓 이력을 모두 지우고 데모 데이터로 처음부터 시작
"""
import argparse
import csv
import shutil
from pathlib import Path

from mock_jira_client import MockJiraClient

try:
    from llm_client import call_llm
    from prompts import ISSUE_DRAFT_SYSTEM_PROMPT, ISSUE_DRAFT_USER_PROMPT_TEMPLATE
except ImportError:
    call_llm = None

PLATFORMS = [
    ("iOS", "iOS Actual", "iOS Ticket"),
    ("AOS", "AOS Actual", "AOS Ticket"),
    ("Web", "Web Actual", "Web Ticket"),
]

DEFAULT_SHEET = "data/mock_test_sheet.csv"
SEED_SHEET = "data/mock_test_sheet_seed.csv"
TICKETS_DIR = "tickets"
COUNTER_FILE = "data/.ticket_counter.json"
STATUS_FILE = "data/.ticket_status.json"


def build_bug_note(row: dict, platform: str, actual_col: str) -> str:
    return (
        f"[Feature] {row.get('Feature', '')}\n"
        f"[Platform] {platform}\n"
        f"[Precondition] {row.get('Precondition', '')}\n"
        f"[Procedure] {row.get('Procedure', '')}\n"
        f"[Expected] {row.get('Expected', '')}\n"
        f"[Actual] {row.get(actual_col, '')}\n"
        f"[Priority] {row.get('Priority', '')}\n"
    )


def template_fallback(bug_note: str) -> str:
    """LLM API 키가 없을 때 사용하는 규칙 기반 이슈 초안 (오프라인에서도 파이프라인이 끝까지 동작하도록)."""
    return (
        "## 이슈 초안 (템플릿 fallback)\n\n"
        f"{bug_note}\n"
        "> ANTHROPIC_API_KEY 또는 OPENAI_API_KEY를 .env에 설정하면, "
        "위 정보를 바탕으로 LLM이 재현 절차 정리·우선순위 제안까지 포함한 "
        "더 상세한 이슈 초안을 생성합니다.\n"
    )


def generate_issue_text(bug_note: str) -> str:
    if call_llm is None:
        return template_fallback(bug_note)
    try:
        user_prompt = ISSUE_DRAFT_USER_PROMPT_TEMPLATE.format(bug_note=bug_note)
        return call_llm(ISSUE_DRAFT_SYSTEM_PROMPT, user_prompt)
    except Exception as e:
        print(f"  (LLM 호출 실패: {e} -> 템플릿으로 대체)")
        return template_fallback(bug_note)


def sync_resolved_tickets(rows: list, jira: MockJiraClient) -> int:
    """
    BTS(Jira) -> 시트 방향 동기화.
    시트의 Ticket 칸에 있는 티켓들의 현재 상태를 조회해서, Open이 아니면
    "QA-1001 (Resolved)" 형식으로 셀을 갱신합니다. 이미 최신 상태면 건드리지 않습니다.
    """
    synced = 0
    for row in rows:
        for _, _, ticket_col in PLATFORMS:
            cell = row.get(ticket_col, "").strip()
            if not cell:
                continue
            key = cell.split()[0]
            status = jira.get_status(key)
            if status is None:
                continue
            new_cell = key if status == "Open" else f"{key} ({status})"
            if new_cell != cell:
                row[ticket_col] = new_cell
                synced += 1
                print(f"동기화됨: {key} -> {status}")
    return synced


def reset_demo_state(sheet_path: Path) -> None:
    """티켓 이력을 모두 지우고, 시트를 시드 데이터로 되돌립니다."""
    shutil.rmtree(TICKETS_DIR, ignore_errors=True)
    Path(COUNTER_FILE).unlink(missing_ok=True)
    Path(STATUS_FILE).unlink(missing_ok=True)
    shutil.copy(SEED_SHEET, sheet_path)
    print(f"초기화 완료: {SEED_SHEET} -> {sheet_path} (티켓 이력 삭제됨)\n")


def main():
    parser = argparse.ArgumentParser(description="목업 시트 기반 이슈 초안/티켓 생성 + 상태 동기화 데모 파이프라인")
    parser.add_argument(
        "--sheet", default=DEFAULT_SHEET,
        help="읽고 쓰는 시트 CSV 경로 (실제 서비스라면 Google Sheet 자체에 해당하는, 유일한 하나의 파일)",
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="티켓 이력을 모두 지우고 시트를 데모 데이터(seed)로 되돌린 뒤 처음부터 시작",
    )
    args = parser.parse_args()

    sheet_path = Path(args.sheet)

    if args.reset or not sheet_path.exists():
        if not Path(SEED_SHEET).exists():
            raise SystemExit(f"시드 파일을 찾을 수 없습니다: {SEED_SHEET}")
        reset_demo_state(sheet_path)

    with sheet_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise SystemExit("시트에 데이터가 없습니다.")

    jira = MockJiraClient(store_dir=TICKETS_DIR, counter_file=COUNTER_FILE, status_file=STATUS_FILE)

    synced = sync_resolved_tickets(rows, jira)
    if synced:
        print()

    created = 0

    for row in rows:
        for platform, actual_col, ticket_col in PLATFORMS:
            result = row.get(platform, "").strip().lower()
            existing_ticket = row.get(ticket_col, "").strip()
            if result == "fail" and not existing_ticket:
                bug_note = build_bug_note(row, platform, actual_col)
                issue_text = generate_issue_text(bug_note)
                ticket = jira.create_ticket(
                    title=f"[{platform}] {row.get('Feature', '')} - {row.get('Title', '')}",
                    body=issue_text,
                    priority=row.get("Priority", "Medium"),
                )
                row[ticket_col] = ticket["key"]
                created += 1
                print(f"생성됨: {ticket['key']}  ({platform} / {row.get('Feature', '')} - {row.get('Title', '')})")

    with sheet_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n동기화된 티켓 상태: {synced}건 / 새로 생성한 이슈 티켓: {created}건")
    print("- 티켓 상세 파일: tickets/ 폴더")
    print(f"- 최신 상태가 반영된 시트: {sheet_path} (같은 파일을 계속 이어서 읽고 씁니다)")
    if call_llm is None:
        print("- LLM 모듈을 불러오지 못해 템플릿 fallback으로 실행되었습니다. (pip install -r requirements.txt 확인)")


if __name__ == "__main__":
    main()
