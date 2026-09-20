# -*- coding: utf-8 -*-

import json
from typing import Any

from shared.core.maat_paths import state_file


DEFAULT_LANGUAGE = "de"
SUPPORTED_LANGUAGES = ("de", "en")


def load_settings() -> dict:
    path = state_file("settings_state.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_settings(data: dict):
    path = state_file("settings_state.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def set_language(language: str):
    data = load_settings()
    data["language"] = language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
    save_settings(data)


def get_language(valid_languages: tuple[str, ...] | None = None, default: str = DEFAULT_LANGUAGE) -> str:
    valid = valid_languages or SUPPORTED_LANGUAGES
    language = load_settings().get("language", default)
    return language if language in valid else default


def tr(texts: dict[str, dict[str, Any]], key: str, language: str | None = None, default_language: str = DEFAULT_LANGUAGE, **kwargs) -> str:
    lang = language or get_language(tuple(texts.keys()), default=default_language)
    template = texts.get(lang, texts.get(default_language, {})).get(
        key,
        texts.get(default_language, {}).get(key, key),
    )
    if kwargs and isinstance(template, str):
        return template.format(**kwargs)
    return template
