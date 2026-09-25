"""Google Gemini implementation of LLMProvider.

Uses the free-tier-eligible Gemini API. Get a key at
https://aistudio.google.com/apikey
"""

from collections.abc import AsyncIterator
from contextlib import closing

from google import genai
from google.genai import types
from starlette.concurrency import iterate_in_threadpool

from app.config import settings
from app.llm.base import LLMProvider, LLMReply, TokenUsage
from app.schemas import MAX_TITLE_LENGTH

model = settings.gemini_model


def _token_count(usage, attribute: str) -> int | None:
    """Gemini omits usage on some responses, and counts can be None."""
    count = getattr(usage, attribute, None)
    return count if isinstance(count, int) else None


class GeminiProvider(LLMProvider):
    def __init__(self) -> None:
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.last_usage: TokenUsage | None = None

    def generate_reply(self, history: list[dict], system_prompt: str) -> LLMReply:
        # Gemini uses "model" instead of "assistant" for the assistant role,
        # and expects content as a list of Part objects rather than a plain string.
        contents = [
            types.Content(
                role="model" if m["role"] == "assistant" else "user",
                parts=[types.Part(text=m["content"])],
            )
            for m in history
        ]

        response = self.client.models.generate_content(
            model=model,
            contents=contents,
            # Gemini takes the system prompt as config, not as an entry in contents.
            config=types.GenerateContentConfig(system_instruction=system_prompt),
        )
        usage = getattr(response, "usage_metadata", None)
        return LLMReply(
            text=response.text,
            prompt_tokens=_token_count(usage, "prompt_token_count"),
            completion_tokens=_token_count(usage, "candidates_token_count"),
        )

    def generate_conversation_title(self, message: str) -> str:
        response = self.client.models.generate_content(
            model=model,
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part(text=message)],
                )
            ],
            config=types.GenerateContentConfig(
                system_instruction=(
                    "Generate a short, plain-text title (3-6 words) summarizing "
                    "this message. No quotes, no markdown, no trailing punctuation."
                ),
            ),
        )
        if not response.text:
            finish_reason = None
            if response.candidates:
                finish_reason = response.candidates[0].finish_reason
            raise ValueError(
                f"Gemini returned no title text (finish_reason={finish_reason})"
            )

        title = response.text.strip()[:MAX_TITLE_LENGTH]
        if not title:
            raise ValueError("Gemini returned a blank title after stripping")

        return title

    async def stream_reply(
        self, history: list[dict], system_prompt: str
    ) -> AsyncIterator[str]:
        contents = [
            types.Content(
                role="model" if m["role"] == "assistant" else "user",
                parts=[types.Part(text=m["content"])],
            )
            for m in history
        ]
        stream = self.client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                http_options=types.HttpOptions(timeout=30000),
            ),
        )
        self.last_usage = None
        with closing(stream):
            async for chunk in iterate_in_threadpool(stream):
                # Usage arrives on the final chunk and is cumulative, so the
                # last one seen wins.
                usage = TokenUsage(
                    prompt_tokens=_token_count(
                        getattr(chunk, "usage_metadata", None), "prompt_token_count"
                    ),
                    completion_tokens=_token_count(
                        getattr(chunk, "usage_metadata", None),
                        "candidates_token_count",
                    ),
                )
                if usage != TokenUsage():
                    self.last_usage = usage
                if chunk.text:
                    yield chunk.text
