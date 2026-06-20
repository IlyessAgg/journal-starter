"""Task 4: Implement analyze_journal_entry using any OpenAI-compatible API.

This project mandates the OpenAI Python SDK, which works with:
  - GitHub Models (default, free, no credit card required)
  - OpenAI proper
  - Azure OpenAI
  - Groq, Together, OpenRouter, Fireworks, DeepInfra
  - Ollama, LM Studio, vLLM (local)
  - Anthropic via their OpenAI-compat endpoint

Set OPENAI_API_KEY, and optionally OPENAI_BASE_URL and OPENAI_MODEL
in your .env file. Settings are loaded by ``api.config.Settings``.
"""

import json

from openai import AsyncOpenAI

from api.config import get_settings


def _default_client() -> AsyncOpenAI:
    """Construct the real OpenAI client from application settings.

    Called lazily from ``analyze_journal_entry`` so tests can inject a
    ``MockAsyncOpenAI`` without ever triggering this code path.
    """
    settings = get_settings()
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )


async def analyze_journal_entry(
    entry_id: str,
    entry_text: str,
    client: AsyncOpenAI | None = None,
) -> dict:
    """Analyze a journal entry using an OpenAI-compatible LLM.

    Args:
        entry_id: ID of the entry being analyzed (pass through to the result).
        entry_text: Combined work + struggle + intention text.
        client: OpenAI client. If None, a default one is constructed from
            application settings. Tests pass in a MockAsyncOpenAI here; production code
            in the router calls this with no ``client`` argument.

    Returns:
        A dict matching AnalysisResponse:
            {
                "entry_id":  str,
                "sentiment": str,   # "positive" | "negative" | "neutral"
                "summary":   str,
                "topics":    list[str],
            }

    TODO (Task 4):
      1. If ``client is None``, call ``_default_client()`` to construct one.
      2. Build a messages list that includes ``entry_text`` somewhere
         (the unit tests check that the entry text reaches the LLM).
      3. Call ``client.chat.completions.create(...)`` with a model name
         (use ``get_settings().openai_model`` — defaults to "gpt-4o-mini").
      4. Parse the assistant's JSON response with ``json.loads()``.
      5. Return a dict with ``entry_id``, ``sentiment``, ``summary``, ``topics``.
    """
    if client is None:
        client = _default_client()
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant that analyzes journal entries. "
                "You will receive a journal entry and must return a JSON object "
                "with the following fields: sentiment (one of 'positive', 'negative', 'neutral'), "
                "summary (a brief summary of the entry), and topics (a list of key topics). "
                "Respond only with the JSON object, no additional text."
            ),
        },
        {
            "role": "user",
            "content": entry_text,
        },
    ]
    completion = await client.chat.completions.create(
        model=get_settings().openai_model,
        messages=messages,
    )
    response_text = completion.choices[0].message.content

    try:
        response_data = json.loads(response_text)
    except json.JSONDecodeError as err:
        raise ValueError("Failed to parse LLM response as JSON") from err

    return {
        "entry_id": entry_id,
        "sentiment": response_data.get("sentiment"),
        "summary": response_data.get("summary"),
        "topics": response_data.get("topics"),
    }
