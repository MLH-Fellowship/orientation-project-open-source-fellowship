"""
Abstract interface for LLM providers.

Barebones ships with one implementation (Gemini). Fellows will add
more providers (OpenAI, local/Ollama, etc.) behind this same interface
-- see ISSUES.md, "LLM Integration" section.
"""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def generate_reply(self, history: list[dict]) -> str:
        """
        Given conversation history as a list of {"role": ..., "content": ...}
        dicts, return the assistant's full text reply.
        """
        raise NotImplementedError
