"""Live availability of each configured LLM provider, for the model picker.

A key being present (``factory._is_real``) only means a call *would be attempted* —
not that it works. So for each provider with a real key we make a one-token ping
(``LLMClient.verify``) and report whether it actually succeeded, plus a short reason
when it did not (bad key, model not accessible, rate limited, unreachable).

The pings hit the network, so results are cached for a short TTL and the per-provider
pings run concurrently — the whole check costs about one slow round-trip, not four.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from anthropic import APIConnectionError as AnthropicConnError
from anthropic import APIStatusError as AnthropicStatusError
from openai import APIConnectionError as OpenAIConnError
from openai import APIStatusError as OpenAIStatusError

from app.llm.factory import PROVIDERS, ProviderInfo, _build_client, _is_real, provider_key

# Cache the (relatively expensive) live pings: long enough to absorb refreshes and
# avoid tripping rate limits, short enough that fixing a key shows up quickly.
_CACHE_TTL_S = 60.0

_lock = threading.Lock()
_cache: tuple[float, list[dict]] | None = None  # (expires_at_monotonic, results)


def _check(info: ProviderInfo) -> dict:
    """Availability of one provider. Pure for a no-key provider (no network);
    otherwise pings and maps the outcome to (available, reason)."""
    base = {"id": info.id, "label": info.label, "model": info.model}
    key = provider_key(info)
    if not _is_real(key):
        return {**base, "available": False, "reason": "no API key"}

    try:
        _build_client(info, key).verify()
        return {**base, "available": True, "reason": ""}
    except (AnthropicStatusError, OpenAIStatusError) as exc:
        status = getattr(exc, "status_code", None)
        if status in (401, 403):
            return {**base, "available": False, "reason": "key rejected"}
        if status == 404:
            return {**base, "available": False, "reason": "model not accessible"}
        if status == 429:
            # The key works; we're just throttled right now. Keep it selectable.
            return {**base, "available": True, "reason": "rate limited (key valid)"}
        return {**base, "available": False, "reason": "provider error"}
    except (AnthropicConnError, OpenAIConnError):
        # Covers timeouts too (APITimeoutError subclasses APIConnectionError).
        return {**base, "available": False, "reason": "unreachable"}
    except Exception:
        return {**base, "available": False, "reason": "verification failed"}


def _verify_all() -> list[dict]:
    """Ping every provider concurrently, returning results in priority order."""
    with ThreadPoolExecutor(max_workers=max(len(PROVIDERS), 1)) as pool:
        # map preserves input order, so the output stays in PROVIDERS (priority) order.
        return list(pool.map(_check, PROVIDERS))


def get_model_availability(*, force: bool = False) -> list[dict]:
    """Return ``[{id, label, model, available, reason}]`` in priority order.

    Cached for ``_CACHE_TTL_S``. Double-checked under a lock so a burst of requests
    (multiple tabs, a refresh mid-ping) triggers a single round of pings, not one per
    request. Pass ``force=True`` to bypass the cache.
    """
    global _cache
    now = time.monotonic()
    if not force and _cache is not None and now < _cache[0]:
        return _cache[1]

    with _lock:
        now = time.monotonic()
        if not force and _cache is not None and now < _cache[0]:
            return _cache[1]
        results = _verify_all()
        _cache = (time.monotonic() + _CACHE_TTL_S, results)
        return results
