"""
실제 Jira API를 대신하는 로컬 mock 클라이언트.

실제 서비스 계정/토큰 없이도 파이프라인 전체 흐름(시트 스캔 -> 이슈 초안 생성 ->
티켓 생성 -> 상태 변경 -> 시트에 반영)을 그대로 체험할 수 있도록, 티켓과 상태를
로컬 파일로 저장합니다.
실제 Jira 클라이언트로 교체하고 싶다면 create_ticket()/resolve_ticket()/get_status()의
구현부만 requests 기반 Jira REST API 호출(또는 Jira 웹훅 수신)로 바꾸면 됩니다.
"""
import json
from datetime import datetime
from pathlib import Path

STATUS_OPEN = "Open"
STATUS_RESOLVED = "Resolved"


class MockJiraClient:
    def __init__(
        self,
        store_dir: str = "tickets",
        counter_file: str = "data/.ticket_counter.json",
        status_file: str = "data/.ticket_status.json",
    ):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.counter_file = Path(counter_file)
        self.counter_file.parent.mkdir(parents=True, exist_ok=True)
        self.status_file = Path(status_file)
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        self._counter = self._load_counter()
        self._statuses = self._load_statuses()

    def _load_counter(self) -> int:
        if self.counter_file.exists():
            return json.loads(self.counter_file.read_text(encoding="utf-8"))["last"]
        return 1000

    def _save_counter(self) -> None:
        self.counter_file.write_text(json.dumps({"last": self._counter}), encoding="utf-8")

    def _load_statuses(self) -> dict:
        if self.status_file.exists():
            return json.loads(self.status_file.read_text(encoding="utf-8"))
        return {}

    def _save_statuses(self) -> None:
        self.status_file.write_text(
            json.dumps(self._statuses, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def create_ticket(self, title: str, body: str, priority: str = "Medium") -> dict:
        """티켓을 생성하고 {key, path} 를 반환합니다. (실제 Jira였다면 issue key/url을 반환)"""
        self._counter += 1
        key = f"QA-{self._counter}"
        self._save_counter()

        ticket_path = self.store_dir / f"{key}.md"
        content = (
            f"# {key}\n\n"
            f"## 제목\n{title}\n\n"
            f"## 우선순위\n{priority}\n\n"
            f"## 상태\n{STATUS_OPEN}\n\n"
            f"## 내용\n{body}\n\n"
            f"---\n_생성 시각: {datetime.now().isoformat(timespec='seconds')} "
            f"(MockJiraClient — 실제 Jira에 등록되지 않았습니다)_\n"
        )
        ticket_path.write_text(content, encoding="utf-8")

        self._statuses[key] = STATUS_OPEN
        self._save_statuses()
        return {"key": key, "path": str(ticket_path)}

    def resolve_ticket(self, key: str, resolution_note: str = "") -> dict:
        """
        개발자가 Jira에서 티켓을 Resolved로 바꾸는 상황을 흉내냅니다.
        (실제 Jira였다면 이 부분이 Jira 웹훅 수신 또는 상태 변경 API 호출에 해당)
        """
        ticket_path = self.store_dir / f"{key}.md"
        if not ticket_path.exists():
            raise ValueError(f"존재하지 않는 티켓입니다: {key}")

        self._statuses[key] = STATUS_RESOLVED
        self._save_statuses()

        # 파일 맨 위 "## 상태" 섹션도 같이 갱신해서, 파일 안에서 상태가
        # 서로 다르게 보이는(위는 Open, 아래는 Resolved) 일이 없도록 함.
        content = ticket_path.read_text(encoding="utf-8")
        content = content.replace(f"## 상태\n{STATUS_OPEN}", f"## 상태\n{STATUS_RESOLVED}", 1)

        note_block = f"\n## 해결 내역\n{resolution_note}\n" if resolution_note else ""
        content += (
            f"{note_block}\n---\n_상태 변경: {STATUS_RESOLVED} "
            f"({datetime.now().isoformat(timespec='seconds')})_\n"
        )
        ticket_path.write_text(content, encoding="utf-8")
        return {"key": key, "status": STATUS_RESOLVED}

    def get_status(self, key: str) -> str:
        """티켓의 현재 상태를 반환합니다. 모르는 티켓이면 None."""
        return self._statuses.get(key)

    def all_statuses(self) -> dict:
        return dict(self._statuses)
