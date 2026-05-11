"""
OmniOS AI Manager
=================
Multi-provider AI chat backend. Supports OpenAI (and OpenAI-compatible),
Anthropic Claude, and Google Gemini. Configuration is stored in
.omnios-ai-config.json; API keys live in the .env file.
"""
import json
import os
import requests
from pathlib import Path

BASE_DIR      = Path(__file__).parent.parent
AI_CFG_FILE   = BASE_DIR / ".omnios-ai-config.json"

PROVIDERS: dict[str, dict] = {
    "openai": {
        "label":       "OpenAI",
        "models":      ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
        "key_env":     "OPENAI_API_KEY",
        "placeholder": "sk-...",
    },
    "anthropic": {
        "label":       "Anthropic",
        "models":      ["claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-3-5"],
        "key_env":     "ANTHROPIC_API_KEY",
        "placeholder": "sk-ant-...",
    },
    "google": {
        "label":       "Google Gemini",
        "models":      ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
        "key_env":     "GOOGLE_AI_KEY",
        "placeholder": "AIza...",
    },
    "custom": {
        "label":       "Custom / OpenAI-compatible",
        "models":      [],
        "key_env":     "CUSTOM_AI_KEY",
        "placeholder": "Your API key",
    },
}

_SAFE_CFG_KEYS = {
    "provider", "model", "system_prompt", "custom_base_url",
    "custom_model", "temperature", "max_tokens",
}


# ── Config I/O ────────────────────────────────────────────────────────────────

def get_ai_config() -> dict:
    if AI_CFG_FILE.exists():
        try:
            return json.loads(AI_CFG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "provider":      "openai",
        "model":         "gpt-4o-mini",
        "system_prompt": (
            "You are a helpful assistant integrated into OmniOS Hub, "
            "a personal web OS. Be concise, clear, and direct."
        ),
        "custom_base_url": "",
        "custom_model":    "",
        "temperature":     0.7,
        "max_tokens":      2048,
    }


def save_ai_config(data: dict) -> None:
    cfg = get_ai_config()
    for k, v in data.items():
        if k in _SAFE_CFG_KEYS:
            cfg[k] = v
    AI_CFG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))


def get_provider_info() -> dict:
    return {
        pid: {
            "label":       p["label"],
            "models":      p["models"],
            "key_set":     bool(os.environ.get(p["key_env"], "").strip()),
            "key_env":     p["key_env"],
            "placeholder": p.get("placeholder", ""),
        }
        for pid, p in PROVIDERS.items()
    }


# ── Chat dispatch ─────────────────────────────────────────────────────────────

def chat(messages: list[dict], override_config: dict | None = None) -> dict:
    """
    Send *messages* (user/assistant turns, no system) to the configured
    provider. Returns {"ok": True, "content": "…", "model": "…", "usage": {}}
    or {"ok": False, "error": "…"}.
    """
    cfg = get_ai_config()
    if override_config:
        for k, v in override_config.items():
            if k in _SAFE_CFG_KEYS:
                cfg[k] = v

    provider      = cfg.get("provider", "openai")
    model         = cfg.get("model", "gpt-4o-mini")
    system_prompt = cfg.get("system_prompt", "You are a helpful assistant.")
    temperature   = float(cfg.get("temperature", 0.7))
    max_tokens    = int(cfg.get("max_tokens", 2048))
    full_messages = [{"role": "system", "content": system_prompt}] + messages

    try:
        if provider == "openai":
            return _openai(full_messages, model, temperature, max_tokens)
        if provider == "anthropic":
            return _anthropic(messages, model, system_prompt, temperature, max_tokens)
        if provider == "google":
            return _google(full_messages, model, temperature, max_tokens)
        if provider == "custom":
            base = cfg.get("custom_base_url", "").rstrip("/") or "https://api.openai.com"
            cm   = cfg.get("custom_model", "").strip() or model
            return _openai(full_messages, cm, temperature, max_tokens, base_url=base, use_custom_key=True)
        return {"ok": False, "error": f"Unknown provider: {provider}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


# ── Provider implementations ──────────────────────────────────────────────────

def _openai(messages, model, temperature, max_tokens,
            base_url="https://api.openai.com", use_custom_key=False):
    env_key = "CUSTOM_AI_KEY" if use_custom_key else "OPENAI_API_KEY"
    api_key = os.environ.get(env_key, "").strip()
    if not api_key:
        name = "Custom AI" if use_custom_key else "OpenAI"
        return {"ok": False, "error": f"{name} API key not set. Configure it in Connections."}

    r = requests.post(
        f"{base_url}/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages,
              "temperature": temperature, "max_tokens": max_tokens},
        timeout=60,
    )
    if r.status_code != 200:
        return {"ok": False, "error": f"API {r.status_code}: {r.text[:300]}"}
    data    = r.json()
    content = data["choices"][0]["message"]["content"]
    usage   = data.get("usage", {})
    _log(f"Chat ({model}) — {usage.get('total_tokens', '?')} tokens")
    return {"ok": True, "content": content, "model": model, "usage": usage}


def _anthropic(messages, model, system_prompt, temperature, max_tokens):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return {"ok": False, "error": "Anthropic API key not set. Configure it in Connections."}

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key":          api_key,
            "anthropic-version":  "2023-06-01",
            "content-type":       "application/json",
        },
        json={
            "model":       model,
            "max_tokens":  max_tokens,
            "system":      system_prompt,
            "messages":    messages,
            "temperature": temperature,
        },
        timeout=60,
    )
    if r.status_code != 200:
        return {"ok": False, "error": f"Anthropic {r.status_code}: {r.text[:300]}"}
    data    = r.json()
    content = data["content"][0]["text"]
    usage   = data.get("usage", {})
    total   = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
    _log(f"Chat ({model}) — {total} tokens")
    return {"ok": True, "content": content, "model": model, "usage": usage}


def _google(messages, model, temperature, max_tokens):
    api_key = os.environ.get("GOOGLE_AI_KEY", "").strip()
    if not api_key:
        return {"ok": False, "error": "Google AI key not set. Configure it in Connections."}

    contents, system_text = [], ""
    for m in messages:
        if m["role"] == "system":
            system_text = m["content"]
            continue
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})

    payload: dict = {
        "contents":       contents,
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    }
    if system_text:
        payload["systemInstruction"] = {"parts": [{"text": system_text}]}

    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
        json=payload, timeout=60,
    )
    if r.status_code != 200:
        return {"ok": False, "error": f"Google AI {r.status_code}: {r.text[:300]}"}
    data    = r.json()
    content = data["candidates"][0]["content"]["parts"][0]["text"]
    _log(f"Chat ({model}, Google Gemini)")
    return {"ok": True, "content": content, "model": model, "usage": {}}


def _log(msg: str, error: bool = False) -> None:
    try:
        from .log_manager import write_log
        write_log("ai", "error" if error else "info", msg)
    except Exception:
        pass
