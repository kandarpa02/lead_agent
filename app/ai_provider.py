from openai import APIConnectionError, APIStatusError, AsyncOpenAI, AuthenticationError
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import AIProviderConfiguration


class AIProviderError(RuntimeError):
    pass


def normalize_api_base_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if not normalized.endswith("/v1"):
        normalized = f"{normalized}/v1"
    return normalized


async def fetch_model_ids(base_url: str, api_key: str, timeout_seconds: float) -> list[str]:
    try:
        async with AsyncOpenAI(
            api_key=api_key,
            base_url=normalize_api_base_url(base_url),
            timeout=timeout_seconds,
        ) as client:
            response = await client.models.list()
    except AuthenticationError as exc:
        raise AIProviderError("The provider rejected the API key.") from exc
    except APIConnectionError as exc:
        raise AIProviderError("Could not connect to the provider. Check the base URL and try again.") from exc
    except APIStatusError as exc:
        raise AIProviderError(
            f"The provider returned HTTP {exc.status_code} while listing models."
        ) from exc
    return sorted({model.id for model in response.data})


def resolve_ai_settings(settings: Settings, db: Session) -> Settings:
    provider = db.get(AIProviderConfiguration, 1)
    if provider is None:
        return settings.model_copy(update={"ai_base_url": "", "ai_api_key": "", "ai_model": ""})
    return settings.model_copy(
        update={
            "ai_base_url": provider.base_url,
            "ai_api_key": provider.api_key,
            "ai_model": provider.selected_model or "",
        }
    )


def provider_read(provider: AIProviderConfiguration | None) -> dict[str, str | bool | None]:
    return {
        "base_url": provider.base_url if provider else None,
        "selected_model": provider.selected_model if provider else None,
        "configured": provider is not None,
        "has_api_key": bool(provider and provider.api_key),
    }
