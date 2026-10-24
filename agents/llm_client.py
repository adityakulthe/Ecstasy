"""
Provider-Agnostic Universal LLM Client for Ecstasy Agents.

Supports any OpenAI-compatible HTTP endpoint (OpenAI, Anthropic/OpenRouter,
Google Gemini OpenAI API, or local Ollama/vLLM/LM Studio) using standard
`requests` with zero vendor SDK lock-in. Automatically returns `None` when
no LLM credentials are configured so agents seamlessly use deterministic
LLVM/Z3 synthesis.
"""

import os
from typing import Any, Dict, List, Optional
import requests
from dotenv import load_dotenv

load_dotenv()


class UniversalLLMClient:
    """Lightweight OpenAI-compatible chat completions client with zero cloud-vendor lock-in."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_id: Optional[str] = None,
        timeout: int = 45,
    ) -> None:
        self.api_key = (
            api_key
            or os.getenv("LLM_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("OPENROUTER_API_KEY")
        )
        self.base_url = (
            base_url
            or os.getenv("LLM_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or "https://api.openai.com/v1"
        ).rstrip("/")
        self.model_id = (
            model_id
            or os.getenv("LLM_MODEL")
            or os.getenv("OPENAI_MODEL")
            or "gpt-4o-mini"
        )
        self.timeout = int(os.getenv("LLM_TIMEOUT", str(timeout)))

    def chat(
        self,
        messages: List[Dict[str, str]],
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a chat completion request returning OpenAI-formatted dict."""
        if not self.api_key and "localhost" not in self.base_url and "127.0.0.1" not in self.base_url:
            raise RuntimeError("LLM_API_KEY is not configured")

        params = params or {}
        max_tokens = params.get("max_new_tokens") or params.get("max_tokens") or int(os.getenv("LLM_MAX_TOKENS", "4096"))
        temperature = params.get("temperature", float(os.getenv("LLM_TEMPERATURE", "0.1")))

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        endpoint = (
            self.base_url
            if self.base_url.endswith("/chat/completions")
            else f"{self.base_url}/chat/completions"
        )
        payload = {
            "model": self.model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        resp = requests.post(endpoint, headers=headers, json=payload, timeout=self.timeout)
        if resp.status_code != 200:
            raise RuntimeError(f"LLM API error ({resp.status_code}): {resp.text[:300]}")
        return resp.json()


_cached_client: Optional[UniversalLLMClient] = None


def is_llm_configured() -> bool:
    """Return True if an LLM API key or local LLM endpoint is configured."""
    if os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY"):
        return True
    base = os.getenv("LLM_BASE_URL", "")
    return "localhost" in base or "127.0.0.1" in base


def get_model() -> Optional[UniversalLLMClient]:
    """Lazily initialize the provider-agnostic UniversalLLMClient when configured."""
    global _cached_client
    if _cached_client is not None:
        return _cached_client
    if not is_llm_configured():
        return None
    _cached_client = UniversalLLMClient()
    return _cached_client


class LazyModelProxy:
    """Proxy object that delegates `.chat()` to the configured `UniversalLLMClient`."""

    def chat(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        client = get_model()
        if client is None:
            raise RuntimeError("LLM_API_KEY not configured; running in deterministic LLVM/Z3 mode")
        return client.chat(*args, **kwargs)
