import json
import time
import logging
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 120
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 2
RETRYABLE_STATUSES = {429}


def call_llm(messages: list[dict], client_type: str = "generator", response_format: dict = None) -> str:
    from config.settings import settings

    if client_type == "evaluator":
        endpoint = settings.EVALUATOR_ENDPOINT or settings.LLM_ENDPOINT
        api_key = settings.EVALUATOR_API_KEY or settings.LLM_API_KEY
        model = settings.EVALUATOR_MODEL or settings.LLM_MODEL
    else:
        endpoint = settings.LLM_ENDPOINT
        api_key = settings.LLM_API_KEY
        model = settings.LLM_MODEL

    payload = {
        "model": model,
        "messages": messages,
        "temperature": settings.LLM_TEMPERATURE,
        "top_p": settings.LLM_TOP_P,
        "max_tokens": settings.LLM_MAX_TOKENS,
    }

    if response_format is not None:
        payload["response_format"] = response_format

    # Only include top_k if it's set and the endpoint is not an OpenAI-compatible one
    is_openai_compat = "/openai/" in endpoint or "/chat/completions" in endpoint
    if not is_openai_compat and settings.LLM_TOP_K is not None:
        payload["top_k"] = settings.LLM_TOP_K


    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        },
        method="POST",
    )


    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
                body = resp.read().decode("utf-8")
                return _extract_content(body)
        except urllib.error.HTTPError as e:
            status = e.code
            body = e.read().decode("utf-8", errors="replace")
            if status in RETRYABLE_STATUSES or (500 <= status < 600):
                logger.warning("LLM call failed with %d on attempt %d, retrying...", status, attempt + 1)
                last_error = RuntimeError(f"LLM HTTP {status}: {body}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY_SECONDS)
                    continue
            else:
                raise RuntimeError(f"LLM HTTP {status}: {body}") from e
        except TimeoutError:
            raise RuntimeError("LLM request timed out after 120s")
        except OSError as e:
            raise RuntimeError(f"LLM request failed: {e}") from e
    raise last_error


def call_llm_raw(prompt: str) -> str:
    return call_llm([{"role": "user", "content": prompt}])


def _extract_content(raw_body: str) -> str:
    try:
        response = json.loads(raw_body)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse LLM response as JSON: {raw_body[:500]}") from e

    # OpenAI format
    try:
        return response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        pass

    # Anthropic format
    try:
        return response["content"][0]["text"]
    except (KeyError, IndexError, TypeError):
        pass

    raise RuntimeError(f"Unknown LLM response format: {json.dumps(response)[:1000]}")
