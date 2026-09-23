"""Provider-level tests for the LLM interface.

The Gemini client is mocked -- these never hit the network.
"""

from unittest.mock import MagicMock

from app.llm.gemini_provider import GeminiProvider


def _provider_with_mock_client():
    provider = GeminiProvider.__new__(GeminiProvider)
    provider.client = MagicMock()
    provider.client.models.generate_content.return_value.text = "Arrr"
    return provider


def test_gemini_sends_system_prompt_as_system_instruction():
    provider = _provider_with_mock_client()

    reply = provider.generate_reply(
        [{"role": "user", "content": "hi"}], "Always reply in pirate speak."
    )

    assert reply.text == "Arrr"
    kwargs = provider.client.models.generate_content.call_args.kwargs
    assert kwargs["config"].system_instruction == "Always reply in pirate speak."


def test_gemini_keeps_system_prompt_out_of_contents():
    """The prompt is config, not a message -- history must be unchanged."""
    provider = _provider_with_mock_client()

    provider.generate_reply([{"role": "user", "content": "hi"}], "Be brief.")

    contents = provider.client.models.generate_content.call_args.kwargs["contents"]
    assert [c.role for c in contents] == ["user"]
    assert [p.text for c in contents for p in c.parts] == ["hi"]


def test_gemini_reads_usage_metadata():
    p = GeminiProvider.__new__(GeminiProvider)
    p.client = MagicMock()
    resp = p.client.models.generate_content.return_value
    resp.text = "hi"
    resp.usage_metadata.prompt_token_count = 42
    resp.usage_metadata.candidates_token_count = 7

    reply = p.generate_reply([{"role": "user", "content": "hi"}], "be brief")
    assert (reply.text, reply.prompt_tokens, reply.completion_tokens) == ("hi", 42, 7)


def test_gemini_tolerates_missing_usage_metadata():
    p = GeminiProvider.__new__(GeminiProvider)
    p.client = MagicMock()
    resp = p.client.models.generate_content.return_value
    resp.text = "hi"
    resp.usage_metadata = None

    reply = p.generate_reply([{"role": "user", "content": "hi"}], "be brief")
    assert (reply.prompt_tokens, reply.completion_tokens) == (None, None)
