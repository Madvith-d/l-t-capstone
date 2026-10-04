from app.core.config import Settings
from app.services.embeddings import (
    FastEmbedEmbeddingService,
    LocalEmbeddingService,
    get_embedding_service,
)
from app.services.llm import (
    BASELINE_SYSTEM_PROMPT,
    RAG_SYSTEM_PROMPT,
    GeminiLLMService,
    OllamaLLMService,
)


class FakeResponse:
    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return {"candidates": [{"content": {"parts": [{"text": "Grounded answer [1]."}]}}]}


def test_gemini_generation_uses_configured_model_and_key(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return FakeResponse()

    monkeypatch.setattr("app.services.llm.httpx.post", fake_post)
    settings = Settings(llm_provider="gemini", gemini_api_key="test-key")
    answer = GeminiLLMService(settings).answer("Question?", "Evidence [1].")
    assert answer == "Grounded answer [1]."
    assert settings.llm_model in captured["url"]
    assert captured["headers"]["x-goog-api-key"] == "test-key"
    assert captured["json"]["generationConfig"]["temperature"] == 0
    assert captured["json"]["systemInstruction"]["parts"][0]["text"] == RAG_SYSTEM_PROMPT
    GeminiLLMService(settings).baseline("General question?")
    assert captured["json"]["systemInstruction"]["parts"][0]["text"] == BASELINE_SYSTEM_PROMPT


def test_ollama_generation_uses_configured_gemma_model(monkeypatch):
    captured = {}

    class OllamaResponse(FakeResponse):
        def json(self) -> dict:
            return {"message": {"content": "Grounded Ollama answer [1]."}}

    def fake_post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return OllamaResponse()

    monkeypatch.setattr("app.services.llm.httpx.post", fake_post)
    settings = Settings(
        llm_provider="ollama",
        llm_model="gemma4:e2b",
        ollama_base_url="http://ollama:11434",
    )
    answer = OllamaLLMService(settings).answer("Question?", "Evidence [1].")
    assert answer == "Grounded Ollama answer [1]."
    assert captured["url"] == "http://ollama:11434/api/chat"
    assert captured["json"]["model"] == "gemma4:e2b"
    assert captured["json"]["stream"] is False


def test_lightweight_embedding_provider_is_selected(monkeypatch):
    sentinel = LocalEmbeddingService()
    monkeypatch.setattr(
        "app.services.embeddings.FastEmbedEmbeddingService", lambda settings: sentinel
    )
    service = get_embedding_service(Settings(embedding_provider="fastembed"))
    assert service is sentinel


def test_fastembed_requires_384_dimensions():
    settings = Settings(embedding_provider="fastembed", embedding_dimension=128)
    try:
        FastEmbedEmbeddingService(settings)
    except RuntimeError as exc:
        assert "384" in str(exc)
    else:
        raise AssertionError("Expected an incompatible dimension error")
