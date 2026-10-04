"""generate_test_cases.py / generate_issue_draft.py 검증.
- build_bug_note(): 순수 데이터 가공 함수
- generate_test_cases()/generate_issue_draft(): call_llm을 monkeypatch해서 프롬프트 조립과
  결과 전달이 올바른지 확인 (실제 LLM 호출 없음)
- main()의 예외 처리: RuntimeError(기존 동작)와, SDK가 던질 수 있는 그 외 예외(이번에 보강한 부분)
  둘 다 사용자에게 traceback 대신 정리된 오류 메시지로 종료되는지 확인
"""
import sys

import pytest

import generate_test_cases
import generate_issue_draft
from run_pipeline import build_bug_note


# ── build_bug_note (핵심 데이터 가공 로직) ────────────────────────────────

def test_build_bug_note_includes_all_fields():
    row = {
        "Feature": "출금 한도 알림", "Precondition": "누적 90%", "Procedure": "출금 진입",
        "Expected": "배너 노출", "iOS Actual": "배너 노출 안 됨", "Priority": "High",
    }
    note = build_bug_note(row, "iOS", "iOS Actual")

    assert "[Feature] 출금 한도 알림" in note
    assert "[Platform] iOS" in note
    assert "[Actual] 배너 노출 안 됨" in note
    assert "[Priority] High" in note


def test_build_bug_note_tolerates_missing_columns():
    """CSV에 일부 컬럼이 없어도 KeyError 없이 빈 문자열로 채워야 한다."""
    note = build_bug_note({}, "AOS", "AOS Actual")
    assert "[Platform] AOS" in note
    assert "[Feature] " in note


# ── generate_test_cases / generate_issue_draft: 프롬프트 조립 + 결과 전달 ──

def test_generate_test_cases_passes_platform_and_requirement_into_prompt(monkeypatch):
    captured = {}

    def fake_call_llm(system_prompt, user_prompt, **kwargs):
        captured["system"] = system_prompt
        captured["user"] = user_prompt
        return "생성된 테스트케이스"

    monkeypatch.setattr(generate_test_cases, "call_llm", fake_call_llm)

    result = generate_test_cases.generate_test_cases("요구사항 본문", "Android,iOS")

    assert result == "생성된 테스트케이스"
    assert "요구사항 본문" in captured["user"]
    assert "Android,iOS" in captured["user"]


def test_generate_issue_draft_passes_bug_note_into_prompt(monkeypatch):
    captured = {}

    def fake_call_llm(system_prompt, user_prompt, **kwargs):
        captured["user"] = user_prompt
        return "생성된 이슈 초안"

    monkeypatch.setattr(generate_issue_draft, "call_llm", fake_call_llm)

    result = generate_issue_draft.generate_issue_draft("버그 재현 메모")

    assert result == "생성된 이슈 초안"
    assert "버그 재현 메모" in captured["user"]


# ── main()의 예외 처리 ──────────────────────────────────────────────────

def test_generate_test_cases_main_handles_missing_api_key_cleanly(tmp_path, monkeypatch, capsys):
    """기존 동작(RuntimeError) - 이번 변경으로 깨지면 안 됨."""
    input_file = tmp_path / "req.md"
    input_file.write_text("요구사항", encoding="utf-8")

    def raise_runtime_error(system_prompt, user_prompt, **kwargs):
        raise RuntimeError("ANTHROPIC_API_KEY가 설정되어 있지 않습니다.")

    monkeypatch.setattr(generate_test_cases, "call_llm", raise_runtime_error)
    monkeypatch.setattr(sys, "argv", ["generate_test_cases.py", "--input", str(input_file)])

    with pytest.raises(SystemExit) as exc_info:
        generate_test_cases.main()

    assert exc_info.value.code == 1
    assert "API_KEY" in capsys.readouterr().err


def test_generate_test_cases_main_handles_unexpected_sdk_error_cleanly(tmp_path, monkeypatch, capsys):
    """이번에 보강한 부분 - RuntimeError가 아닌 예외(SDK의 네트워크/요금 오류 등을 흉내)도
    처리되지 않은 traceback이 아니라 깔끔한 오류 메시지 + 종료코드 1로 끝나야 한다."""
    input_file = tmp_path / "req.md"
    input_file.write_text("요구사항", encoding="utf-8")

    def raise_unexpected_error(system_prompt, user_prompt, **kwargs):
        raise ConnectionError("일시적인 네트워크 오류 시뮬레이션")

    monkeypatch.setattr(generate_test_cases, "call_llm", raise_unexpected_error)
    monkeypatch.setattr(sys, "argv", ["generate_test_cases.py", "--input", str(input_file)])

    with pytest.raises(SystemExit) as exc_info:
        generate_test_cases.main()

    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert "ConnectionError" in err  # 디버깅할 수 있도록 원인 타입은 남겨야 함


def test_generate_issue_draft_main_handles_unexpected_sdk_error_cleanly(tmp_path, monkeypatch, capsys):
    input_file = tmp_path / "bug.md"
    input_file.write_text("재현 메모", encoding="utf-8")

    def raise_unexpected_error(system_prompt, user_prompt, **kwargs):
        raise ConnectionError("일시적인 네트워크 오류 시뮬레이션")

    monkeypatch.setattr(generate_issue_draft, "call_llm", raise_unexpected_error)
    monkeypatch.setattr(sys, "argv", ["generate_issue_draft.py", "--input", str(input_file)])

    with pytest.raises(SystemExit) as exc_info:
        generate_issue_draft.main()

    assert exc_info.value.code == 1
    assert "ConnectionError" in capsys.readouterr().err
