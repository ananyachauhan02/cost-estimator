"""
groq_client.py
──────────────────────────────────────────────────────────────────────────────
Shared Groq API key rotation utility.

Reads up to 3 API keys from the environment:
  GROQ_API_KEY          – primary key
  GROQ_API_KEY_2        – first fallback
  GROQ_API_KEY_3        – second fallback

When a key is rate-limited or its daily quota is exhausted, the next key is
tried automatically.  All callers (node_distributor, chatbot) use
`groq_completion()` instead of calling the Groq SDK directly.
"""

from __future__ import annotations
import os
import time
from dotenv import load_dotenv

load_dotenv(override=True)

# ── Key pool ──────────────────────────────────────────────────────────────────
def _load_keys() -> list[str]:
    """Return all non-empty API keys in priority order."""
    candidates = [
        os.getenv("GROQ_API_KEY",   ""),
        os.getenv("GROQ_API_KEY_2", ""),
        os.getenv("GROQ_API_KEY_3", ""),
    ]
    return [k.strip() for k in candidates if k.strip()]


def any_key_available() -> bool:
    """True if at least one API key is configured."""
    return bool(_load_keys())


# ── Error classification ───────────────────────────────────────────────────────
def _is_rate_limit(err: str) -> bool:
    return "429" in err or "rate_limit" in err.lower() or "rate limit" in err.lower()

def _is_quota_exhausted(err: str) -> bool:
    return "quota" in err.lower() and "exceeded" in err.lower()

def _is_loop_detection(err: str) -> bool:
    return "looping content" in err.lower() or "loop detection" in err.lower()

def _should_rotate_key(err: str) -> bool:
    """True if the error means this key is no longer usable and we should try the next."""
    return _is_quota_exhausted(err) or ("invalid_api_key" in err.lower())


# ── Core completion helper ─────────────────────────────────────────────────────
def groq_completion(
    messages:    list[dict],
    models:      list[str],
    temperature: float = 0.0,
    max_tokens:  int   = 1500,
    max_retries_per_model: int = 3,
) -> tuple[str, str, str]:
    """
    Attempt a chat completion, rotating both models and API keys on failure.

    Returns:
        (content, model_used, key_index_used)  on success
        raises RuntimeError if all keys × all models are exhausted.

    Strategy
    ────────
    Outer loop  → API keys   (rotate on quota-exhausted / invalid-key errors)
    Middle loop → models     (try each model with the current key)
    Inner loop  → retries    (back-off on transient rate-limits)
    """
    try:
        from groq import Groq
    except ImportError:
        raise RuntimeError("groq package not installed.  Run:  pip install groq")

    keys = _load_keys()
    if not keys:
        raise RuntimeError("No Groq API key configured.  Add GROQ_API_KEY to .env")

    last_error = "unknown"

    for key_idx, api_key in enumerate(keys):
        client = Groq(api_key=api_key)
        key_label = f"key #{key_idx + 1}"

        for model in models:
            for attempt in range(max_retries_per_model):
                try:
                    resp = client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    content = resp.choices[0].message.content
                    print(f"[groq_client] ✅ {model} / {key_label} succeeded")
                    return content, model, key_label

                except Exception as exc:
                    err = str(exc)
                    last_error = err

                    if _should_rotate_key(err):
                        # This key is dead — skip remaining models for it
                        print(f"[groq_client] {key_label} quota/invalid — rotating to next key")
                        break   # break model loop → try next key

                    elif _is_rate_limit(err):
                        if attempt < max_retries_per_model - 1:
                            wait = (2 ** attempt) * 3   # 3 s, 6 s, 12 s
                            print(f"[groq_client] Rate-limited on {model}/{key_label}, "
                                  f"retrying in {wait}s (attempt {attempt + 1})")
                            time.sleep(wait)
                        else:
                            print(f"[groq_client] {model}/{key_label} rate-limit exhausted — "
                                  f"trying next model")
                            break   # break retry loop → try next model

                    elif _is_loop_detection(err):
                        # Model flagged its own output — try next model, different phrasing may help
                        print(f"[groq_client] {model}/{key_label} loop-detection flag — trying next model")
                        break   # break retry loop → try next model

                    else:
                        # Non-retryable error (bad JSON, auth issue etc.)
                        print(f"[groq_client] {model}/{key_label} non-retryable error: {err}")
                        raise   # propagate immediately
            else:
                continue   # model loop: next model (no break from retry loop)
            break           # model loop: key was rotated — break to next key

    raise RuntimeError(
        f"All Groq API keys and models exhausted.  Last error: {last_error}"
    )
