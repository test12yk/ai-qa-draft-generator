"""run_pipeline.sync_resolved_tickets() - BTS(Jira) -> Sheet 역방향 동기화 로직 검증.
실제 CSV 파일이나 run_pipeline.main() 전체를 실행하지 않고, 함수 자체만 단위로 검증한다.
"""
from mock_jira_client import MockJiraClient
from run_pipeline import sync_resolved_tickets


def make_client(tmp_path):
    return MockJiraClient(
        store_dir=str(tmp_path / "tickets"),
        counter_file=str(tmp_path / "counter.json"),
        status_file=str(tmp_path / "status.json"),
    )


def test_sync_reflects_resolved_ticket_into_cell(tmp_path):
    jira = make_client(tmp_path)
    ticket = jira.create_ticket(title="A", body="")
    jira.resolve_ticket(ticket["key"])

    row = {"iOS Ticket": ticket["key"], "AOS Ticket": "", "Web Ticket": ""}
    synced = sync_resolved_tickets([row], jira)

    assert synced == 1
    assert row["iOS Ticket"] == f"{ticket['key']} (Resolved)"


def test_sync_does_not_reprocess_already_synced_cell(tmp_path):
    """이미 '(Resolved)'가 반영된 셀은 다시 세거나 덮어쓰지 않아야 한다."""
    jira = make_client(tmp_path)
    ticket = jira.create_ticket(title="A", body="")
    jira.resolve_ticket(ticket["key"])

    row = {"iOS Ticket": f"{ticket['key']} (Resolved)", "AOS Ticket": "", "Web Ticket": ""}
    synced = sync_resolved_tickets([row], jira)

    assert synced == 0
    assert row["iOS Ticket"] == f"{ticket['key']} (Resolved)"


def test_sync_leaves_still_open_ticket_untouched(tmp_path):
    jira = make_client(tmp_path)
    ticket = jira.create_ticket(title="A", body="")  # 아직 resolve 안 함 -> 여전히 Open

    row = {"iOS Ticket": ticket["key"], "AOS Ticket": "", "Web Ticket": ""}
    synced = sync_resolved_tickets([row], jira)

    assert synced == 0
    assert row["iOS Ticket"] == ticket["key"]


def test_sync_ignores_empty_and_unknown_ticket_cells(tmp_path):
    """빈 셀이나 jira가 모르는 티켓 키가 있어도 예외 없이 건너뛰어야 한다."""
    jira = make_client(tmp_path)

    row = {"iOS Ticket": "", "AOS Ticket": "QA-9999", "Web Ticket": ""}
    synced = sync_resolved_tickets([row], jira)

    assert synced == 0
    assert row["AOS Ticket"] == "QA-9999"


def test_sync_handles_multiple_rows_independently(tmp_path):
    jira = make_client(tmp_path)
    t1 = jira.create_ticket(title="A", body="")
    t2 = jira.create_ticket(title="B", body="")
    jira.resolve_ticket(t1["key"])  # t1만 resolve, t2는 Open 유지

    rows = [
        {"iOS Ticket": t1["key"], "AOS Ticket": "", "Web Ticket": ""},
        {"iOS Ticket": "", "AOS Ticket": t2["key"], "Web Ticket": ""},
    ]
    synced = sync_resolved_tickets(rows, jira)

    assert synced == 1
    assert rows[0]["iOS Ticket"] == f"{t1['key']} (Resolved)"
    assert rows[1]["AOS Ticket"] == t2["key"]  # 변화 없음
