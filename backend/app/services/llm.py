import re

import httpx

from app.core.config import Settings, get_settings
from app.services.prompts import UNKNOWN_RESPONSE, render_academic_prompt

SYSTEM_PROMPT = f"""You are a college academic assistant. Answer only from the supplied context for college-specific facts. If context is insufficient, say exactly: {UNKNOWN_RESPONSE} Preserve source markers like [1]. Be clear and concise."""


class LLMError(RuntimeError):
    pass


class LLMService:
    def answer(self, question: str, context: str, history: list[dict] | None = None) -> str:
        raise NotImplementedError

    def baseline(self, question: str) -> str:
        raise NotImplementedError


class LocalLLMService(LLMService):
    """Safe extractive fallback used only by tests and offline development."""

    def answer(self, question: str, context: str, history: list[dict] | None = None) -> str:
        if not context.strip():
            return UNKNOWN_RESPONSE
        terms = set(re.findall(r"[a-z]{3,}", question.lower()))
        evidence = re.sub(r"Source \[\d+\] — [^\n]+:\n", "", context)
        sentences = re.split(r"(?<=[.!?])\s+", evidence)
        ranked = sorted(
            sentences,
            key=lambda sentence: len(terms & set(re.findall(r"[a-z]{3,}", sentence.lower()))),
            reverse=True,
        )
        chosen = [sentence.strip() for sentence in ranked[:3] if sentence.strip()]
        return (
            " ".join(chosen)
            or UNKNOWN_RESPONSE
        )

    def baseline(self, question: str) -> str:
        return "The local baseline has no college-document context and cannot verify this answer."


class GeminiLLMService(LLMService):
    def __init__(self, settings: Settings):
        if not settings.gemini_api_key:
            raise LLMError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")
        self.settings = settings

    def _call(self, prompt: str, history: list[dict] | None = None) -> str:
        contents = []
        for message in (history or [])[-8:]:
            role = "model" if message.get("role") == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": str(message.get("content", ""))}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})
        try:
            response = httpx.post(
                f"{self.settings.gemini_base_url.rstrip('/')}/models/{self.settings.llm_model}:generateContent",
                headers={"x-goog-api-key": self.settings.gemini_api_key},
                json={
                    "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                    "contents": contents,
                    "generationConfig": {"temperature": 0},
                },
                timeout=self.settings.llm_timeout_seconds,
            )
            response.raise_for_status()
            parts = response.json()["candidates"][0]["content"]["parts"]
            answer = "".join(part.get("text", "") for part in parts).strip()
            if not answer:
                raise LLMError("Gemini returned an empty response")
            return answer
        except (httpx.HTTPError, KeyError, IndexError, TypeError) as exc:
            raise LLMError("Gemini generation request failed") from exc

    def answer(self, question: str, context: str, history: list[dict] | None = None) -> str:
        return self._call(render_academic_prompt(question, context), history)

    def baseline(self, question: str) -> str:
        return self._call(question)


def get_llm_service(settings: Settings | None = None) -> LLMService:
    settings = settings or get_settings()
    return GeminiLLMService(settings) if settings.llm_provider == "gemini" else LocalLLMService()
