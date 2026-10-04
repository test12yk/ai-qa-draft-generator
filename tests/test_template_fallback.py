"""run_pipeline.py의 template fallback 경로 검증.
실제 LLM(OpenAI/Anthropic)은 전혀 호출하지 않는다 - call_llm을 monkeypatch로 대체한다.
"""
import run_pipeline


def test_template_fallback_includes_bug_note_and_hint():
    bug_note = "[Feature] 테스트 기능\n[Platform] iOS\n"
    result = run_pipeline.template_fallback(bug_note)

    assert bug_note in result
    assert "ANTHROPIC_API_KEY" in result or "OPENAI_API_KEY" in result


def test_generate_issue_text_uses_llm_result_when_call_llm_succeeds(monkeypatch):
    monkeypatch.setattr(run_pipeline, "call_llm", lambda system, user: "LLM이 생성한 초안")

    result = run_pipeline.generate_issue_text("버그 메모")

    assert result == "LLM이 생성한 초안"


def test_generate_issue_text_falls_back_when_call_llm_is_none(monkeypatch):
    """requirements.txt의 anthropic/openai가 설치되지 않아 import가 실패한 상황과 동일
    (run_pipeline.py 33-37행: ImportError 시 call_llm = None)."""
    monkeypatch.setattr(run_pipeline, "call_llm", None)

    result = run_pipeline.generate_issue_text("버그 메모")

    assert "버그 메모" in result
    assert "템플릿" in result


def test_generate_issue_text_falls_back_when_call_llm_raises(monkeypatch):
    """API key는 있지만 네트워크 오류/요금 한도 등으로 실제 호출이 실패하는 상황."""
    def boom(system, user):
        raise RuntimeError("네트워크 오류 시뮬레이션")

    monkeypatch.setattr(run_pipeline, "call_llm", boom)

    result = run_pipeline.generate_issue_text("버그 메모")  # 예외가 밖으로 전파되면 안 됨

    assert "버그 메모" in result
    assert "템플릿" in result
