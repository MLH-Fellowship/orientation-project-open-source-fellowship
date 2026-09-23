import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.config import settings
from app.llm.gemini_provider import GeminiProvider


@pytest.mark.asyncio
async def test_gemini_streams_text_and_maps_roles(monkeypatch):
    closed = []
    thread_ids = []

    def chunks():
        try:
            for text in [None, "", "Hello", " world"]:
                thread_ids.append(threading.get_ident())
                yield SimpleNamespace(text=text)
        finally:
            closed.append(True)

    client = Mock()
    client.models.generate_content_stream.return_value = chunks()
    monkeypatch.setattr(
        "app.llm.gemini_provider.genai.Client", Mock(return_value=client)
    )
    provider = GeminiProvider()
    history = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]

    assert [text async for text in provider.stream_reply(history, "Be concise.")] == [
        "Hello",
        " world",
    ]
    client.models.generate_content_stream.assert_called_once()
    kwargs = client.models.generate_content_stream.call_args.kwargs
    assert kwargs["model"] == settings.gemini_model
    assert kwargs["config"].system_instruction == "Be concise."
    assert [content.role for content in kwargs["contents"]] == ["user", "model"]
    assert [content.parts[0].text for content in kwargs["contents"]] == ["hi", "hello"]
    assert closed == [True]
    assert all(thread_id != threading.get_ident() for thread_id in thread_ids)
    client.models.generate_content.assert_not_called()


@pytest.mark.asyncio
async def test_gemini_closes_upstream_when_stopped(monkeypatch):
    closed = []

    def chunks():
        try:
            yield SimpleNamespace(text="first")
            yield SimpleNamespace(text="second")
        finally:
            closed.append(True)

    client = Mock()
    client.models.generate_content_stream.return_value = chunks()
    monkeypatch.setattr(
        "app.llm.gemini_provider.genai.Client", Mock(return_value=client)
    )
    stream = GeminiProvider().stream_reply([], "Be concise.")

    assert await anext(stream) == "first"
    await stream.aclose()
    assert closed == [True]
