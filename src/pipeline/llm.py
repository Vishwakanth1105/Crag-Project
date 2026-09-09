"""Provider-agnostic chat-model factory.

Local mode routes generation and structured extraction through Ollama;
``gemini`` mode keeps the previous ChatGoogleGenerativeAI behavior.
"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from src.config import Settings


def build_chat_model(
    settings: Settings,
    *,
    num_ctx: int = 4096,
    num_predict: int | None = None,
) -> BaseChatModel:
    """Return the configured chat model.

    ``num_predict`` caps the number of tokens the model may generate, which
    bounds worst-case latency on slow local hardware.

    Raises ``ConfigurationError`` when the Gemini provider is selected without
    an API key. Local mode never requires external credentials.
    """
    if settings.use_local_llm:
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0,
            num_ctx=num_ctx,
            num_predict=num_predict,
            client_kwargs={"timeout": settings.local_request_timeout_seconds},
        )

    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=settings.generation_model,
        api_key=settings.require_gemini(),
        temperature=0,
        max_output_tokens=num_predict,
        timeout=settings.request_timeout_seconds,
    )
