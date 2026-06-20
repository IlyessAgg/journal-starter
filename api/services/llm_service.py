import json

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

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
    """
    if client is None:
        client = _default_client()

    messages: list[ChatCompletionMessageParam] = [
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

    if response_text is None:
        raise ValueError("LLM response is empty")

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
