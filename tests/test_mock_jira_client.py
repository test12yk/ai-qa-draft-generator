"""MockJiraClient의 실제 동작(티켓 생성/조회/상태 변경)을 검증한다.
전부 tmp_path 기반 임시 폴더만 사용하므로 저장소의 tickets/, data/ 는 건드리지 않는다.
"""
from mock_jira_client import MockJiraClient, STATUS_OPEN, STATUS_RESOLVED


def make_client(tmp_path):
    return MockJiraClient(
        store_dir=str(tmp_path / "tickets"),
        counter_file=str(tmp_path / "counter.json"),
        status_file=str(tmp_path / "status.json"),
    )


def test_create_ticket_returns_key_and_writes_file(tmp_path):
    jira = make_client(tmp_path)
    result = jira.create_ticket(title="[iOS] 버그 제목", body="본문 내용", priority="High")

    assert result["key"] == "QA-1001"
    ticket_path = tmp_path / "tickets" / "QA-1001.md"
    assert ticket_path.exists()
    content = ticket_path.read_text(encoding="utf-8")
    assert "[iOS] 버그 제목" in content
    assert "본문 내용" in content
    assert STATUS_OPEN in content


def test_create_ticket_counter_increments_sequentially(tmp_path):
    jira = make_client(tmp_path)
    first = jira.create_ticket(title="A", body="")
    second = jira.create_ticket(title="B", body="")
    assert first["key"] == "QA-1001"
    assert second["key"] == "QA-1002"


def test_counter_persists_across_separate_client_instances(tmp_path):
    """run_pipeline.py가 매 실행마다 새 MockJiraClient 인스턴스를 만드는 것과 동일한 상황을
    재현한다 - 두 번째 인스턴스가 번호를 1000부터 다시 시작하면 안 된다."""
    jira1 = make_client(tmp_path)
    jira1.create_ticket(title="A", body="")

    jira2 = make_client(tmp_path)
    second = jira2.create_ticket(title="B", body="")
    assert second["key"] == "QA-1002"


def test_get_status_for_unknown_ticket_is_none(tmp_path):
    jira = make_client(tmp_path)
    assert jira.get_status("QA-9999") is None


def test_get_status_after_create_is_open(tmp_path):
    jira = make_client(tmp_path)
    ticket = jira.create_ticket(title="A", body="")
    assert jira.get_status(ticket["key"]) == STATUS_OPEN


def test_resolve_ticket_updates_status_and_file(tmp_path):
    jira = make_client(tmp_path)
    ticket = jira.create_ticket(title="A", body="")

    result = jira.resolve_ticket(ticket["key"], resolution_note="수정 완료")

    assert result["status"] == STATUS_RESOLVED
    assert jira.get_status(ticket["key"]) == STATUS_RESOLVED
    content = (tmp_path / "tickets" / f"{ticket['key']}.md").read_text(encoding="utf-8")
    assert STATUS_RESOLVED in content
    assert "수정 완료" in content


def test_resolve_ticket_unknown_key_raises(tmp_path):
    jira = make_client(tmp_path)
    try:
        jira.resolve_ticket("QA-9999")
        assert False, "존재하지 않는 티켓인데 예외가 발생하지 않음"
    except ValueError:
        pass
