import re
from functools import lru_cache

import httpx

from app.core.config import Settings, get_settings
from app.services.prompts import UNKNOWN_RESPONSE, render_academic_prompt

RAG_SYSTEM_PROMPT = f"""You are a college academic assistant. Answer only from the supplied context for college-specific facts. If context is insufficient, say exactly: {UNKNOWN_RESPONSE} Preserve source markers like [1]. Be clear and concise."""
BASELINE_SYSTEM_PROMPT = """You are a general-purpose assistant. Answer normally from general knowledge. You do not have access to this college's private documents, so never claim that you do."""


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
        return (
            "Requirements vary by institution. Based on general knowledge, consult the "
            "college's official published guidance to verify the specific answer."
        )


class OllamaLLMService(LLMService):
    def __init__(self, settings: Settings):
        self.settings = settings

    def _call(
        self,
        prompt: str,
        history: list[dict] | None = None,
        system_prompt: str = RAG_SYSTEM_PROMPT,
    ) -> str:
        messages = [{"role": "system", "content": system_prompt}]
        for message in (history or [])[-8:]:
            role = "assistant" if message.get("role") == "assistant" else "user"
            messages.append({"role": role, "content": str(message.get("content", ""))})
        messages.append({"role": "user", "content": prompt})
        for attempt in range(2):
            try:
                response = httpx.post(
                    f"{self.settings.ollama_base_url.rstrip('/')}/api/chat",
                    json={
                        "model": self.settings.llm_model,
                        "messages": messages,
                        "stream": False,
                        "options": {"temperature": 0},
                    },
                    timeout=self.settings.llm_timeout_seconds,
                )
                response.raise_for_status()
                answer = str(response.json().get("message", {}).get("content", "")).strip()
                if not answer:
                    raise LLMError("Ollama returned an empty response")
                return answer
            except httpx.HTTPStatusError as exc:
                if attempt == 0 and exc.response.status_code >= 500:
                    continue
                raise LLMError("Ollama generation request failed") from exc
            except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
                if attempt == 1:
                    raise LLMError("Ollama generation request failed") from exc
        raise LLMError("Ollama generation request failed")

    def answer(self, question: str, context: str, history: list[dict] | None = None) -> str:
        return self._call(render_academic_prompt(question, context), history)

    def baseline(self, question: str) -> str:
        return self._call(question, system_prompt=BASELINE_SYSTEM_PROMPT)


class GeminiLLMService(LLMService):
    def __init__(self, settings: Settings):
        if not settings.gemini_api_key:
            raise LLMError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")
        self.settings = settings

    def _call(
        self,
        prompt: str,
        history: list[dict] | None = None,
        system_prompt: str = RAG_SYSTEM_PROMPT,
    ) -> str:
        contents = []
        for message in (history or [])[-8:]:
            role = "model" if message.get("role") == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": str(message.get("content", ""))}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})
        request = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": contents,
            "generationConfig": {"temperature": 0},
        }
        response = None
        for attempt in range(2):
            try:
                response = httpx.post(
                    f"{self.settings.gemini_base_url.rstrip('/')}/models/{self.settings.llm_model}:generateContent",
                    headers={"x-goog-api-key": self.settings.gemini_api_key},
                    json=request,
                    timeout=self.settings.llm_timeout_seconds,
                )
                response.raise_for_status()
                break
            except httpx.HTTPStatusError as exc:
                if attempt == 0 and exc.response.status_code >= 500:
                    continue
                raise LLMError("Gemini generation request failed") from exc
            except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
                if attempt == 1:
                    raise LLMError("Gemini generation request failed") from exc
        if response is None:
            raise LLMError("Gemini generation request failed")
        try:
            payload = response.json()
            candidates = payload.get("candidates") or []
            if not candidates:
                reason = payload.get("promptFeedback", {}).get("blockReason", "no candidate")
                raise LLMError(f"Gemini did not return an answer ({reason})")
            parts = candidates[0].get("content", {}).get("parts", [])
            answer = "".join(part.get("text", "") for part in parts).strip()
            if not answer:
                raise LLMError("Gemini returned an empty response")
            return answer
        except (httpx.HTTPError, KeyError, IndexError, TypeError, AttributeError) as exc:
            raise LLMError("Gemini generation request failed") from exc

    def answer(self, question: str, context: str, history: list[dict] | None = None) -> str:
        return self._call(render_academic_prompt(question, context), history)

    def baseline(self, question: str) -> str:
        return self._call(question, system_prompt=BASELINE_SYSTEM_PROMPT)


def _build_llm(settings: Settings) -> LLMService:
    if settings.llm_provider == "ollama":
        return OllamaLLMService(settings)
    if settings.llm_provider == "gemini":
        return GeminiLLMService(settings)
    return LocalLLMService()


@lru_cache(maxsize=1)
def _cached_llm() -> LLMService:
    return _build_llm(get_settings())


def get_llm_service(settings: Settings | None = None) -> LLMService:
    return _build_llm(settings) if settings is not None else _cached_llm()
