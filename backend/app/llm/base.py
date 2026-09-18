"""
Abstract interface for LLM providers.

Barebones ships with one implementation (Gemini). Fellows will add
more providers (OpenAI, local/Ollama, etc.) behind this same interface
-- see ISSUES.md, "LLM Integration" section.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class LLMProvider(ABC):
    @abstractmethod
    def generate_reply(self, history: list[dict], system_prompt: str) -> str:
        """
        Given conversation history as a list of {"role": ..., "content": ...}
        dicts, return the assistant's full text reply.

        `system_prompt` holds instructions that guide the model's behaviour.
        It is sent alongside the history, not as a message within it.
        """
        raise NotImplementedError

    @abstractmethod
    def stream_reply(
        self, history: list[dict], system_prompt: str
    ) -> AsyncIterator[str]:
        raise NotImplementedError
