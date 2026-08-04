"""
Anthropic / OpenAI 겸용 LLM 호출 래퍼.

환경변수 LLM_PROVIDER 에 따라 사용할 provider를 선택합니다.
- LLM_PROVIDER=anthropic (기본값) -> ANTHROPIC_API_KEY 필요
- LLM_PROVIDER=openai            -> OPENAI_API_KEY 필요
"""
import os
from dotenv import load_dotenv

load_dotenv()

PROVIDER = os.getenv("LLM_PROVIDER", "anthropic").lower()


def call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
    """system/user 프롬프트를 받아 LLM 응답 텍스트를 반환합니다."""
    if PROVIDER == "openai":
        return _call_openai(system_prompt, user_prompt, max_tokens)
    return _call_anthropic(system_prompt, user_prompt, max_tokens)


def _call_anthropic(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY가 설정되어 있지 않습니다. .env 파일을 확인하세요.")

    client = anthropic.Anthropic(api_key=api_key)
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def _call_openai(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되어 있지 않습니다. .env 파일을 확인하세요.")

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", "gpt-4.1")

    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content
