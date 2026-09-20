from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any, Callable

from .maat_paths import state_file
from .rpg_generation_context import build_rpg_context_message
from .rpg_i18n import get_language


def _settings_path() -> Path:
    return Path(state_file("settings_state.json"))


def _load_settings() -> dict:
    try:
        return json.loads(_settings_path().read_text(encoding="utf-8"))
    except Exception:
        return {}


def thinking_enabled(default: bool = False) -> bool:
    data = _load_settings()
    if "thinking_enabled" in data:
        return bool(data.get("thinking_enabled"))
    return default


def show_thinking_enabled(default: bool = False) -> bool:
    data = _load_settings()
    return thinking_enabled() and bool(data.get("show_thinking", default))


def _thinking_language(language: str | None = None) -> str:
    if language in ("de", "en"):
        return language
    return get_language(("de", "en"))


def thinking_off_instruction(language: str | None = None) -> str:
    if _thinking_language(language) == "en":
        return (
            "[THINKING MODE OFF]\n"
            "Give only the final reply, without <think> tags or internal drafts. "
            "Leave any template thinking section empty. Include explanations the user explicitly requested."
        )
    return (
        "[THINKING-MODUS AUS]\n"
        "Gib nur die fertige Antwort aus, ohne <think>-Tags oder interne Entwürfe. "
        "Lasse einen Template-Denkblock leer. Gib ausdrücklich erbetene Erklärungen mit aus."
    )


def _append_system_messages(prepared: list[dict], contents: list[str]) -> list[dict]:
    insert_at = 0
    while insert_at < len(prepared) and prepared[insert_at].get("role") == "system":
        insert_at += 1

    for content in contents:
        if not content:
            continue
        if any(
            message.get("role") == "system" and message.get("content") == content
            for message in prepared
        ):
            continue
        prepared.insert(insert_at, {"role": "system", "content": content})
        insert_at += 1
    return prepared


def prepare_generation_messages(
    messages: list[dict],
    language: str | None = None,
    runtime_context: dict | None = None,
    llm=None,
    generation_state: dict | None = None,
) -> list[dict]:
    # Replace our previous snapshot rather than accumulating it, including after
    # disabling context or switching to Llama. User text and memories stay intact.
    markers = ('[MAAT-RPG-WELTZUSTAND]', '[MAAT-RPG WORLD CONTEXT]', '[MAAT-OFFLINE-WIKI]', '[MAAT-SUPER-MEMORY]',
               '[THINKING MODE OFF]', '[THINKING-MODUS AUS]', '[MAAT_INTERNAL_QUALITY]',
               '[MAAT_EXTENDED_THINKING]', '[MAAT_QUALITY_CHECK]', '[MAAT-FORMULA-REFERENCE]', '[MAAT-REPLY-LANGUAGE]')
    markers += ('[MAAT_STYLE]', '[MAAT_REPLY_STYLE]', '[MAAT_IDENTITY]', '[MAAT_ANTI_HALLU]', '[MAAT_REALITY]', '[MAAT_FORMATTING]')
    from .conversation_history import recent_messages
    prepared = [dict(message) for message in recent_messages(messages or [])
                if not (message.get('role') == 'system' and
                        str(message.get('content', '')).lstrip().startswith(markers))]

    legacy_gui_appendix = '[RPG] Du bist MAAT-KI in der Welt von Maatis. Bewahre Story, Pfad und Prinzipien als zusammenhängende Spielwelt.'
    for message in prepared:
        if message.get('role') == 'system' and legacy_gui_appendix in str(message.get('content', '')):
            message['content'] = str(message['content']).replace(legacy_gui_appendix, '').rstrip()

    from .reply_language import prepare_reply_language
    fallback_language = language or (runtime_context or {}).get('offline_wiki_status',{}).get('language')
    prepared, reference_context, language, language_instruction = prepare_reply_language(
        prepared, runtime_context, _thinking_language(fallback_language))
    plugin_context = dict(runtime_context or {})
    plugin_context['_ai_reply_language'] = language
    grounding = {'text': '', 'memories': []}
    if generation_state is not None:
        generation_state.update(language=language, grounding=grounding)
    system_messages: list[str] = []
    if language_instruction:
        system_messages.append(language_instruction)
    from .maat_reference import generation_reference
    reference = generation_reference(prepared, reference_context)
    if reference:
        system_messages.append(reference)
    from .model_family import model_family
    if not thinking_enabled() and model_family(llm or (runtime_context or {}).get('llm')) != 'gpt-oss':
        system_messages.append(thinking_off_instruction(language))

    manager = (runtime_context or {}).get('pm')
    generation_hook = getattr(manager, 'generation_system_messages', None)
    if callable(generation_hook):
        plugin_messages = generation_hook(language=_thinking_language(language), context=plugin_context)
        system_messages.extend(plugin_messages)
        # The clock snapshot is factual grounding for the optional output guard.
        # Style/identity instructions are not evidence.
        for message in plugin_messages:
            if message.lstrip().startswith('[MAAT_REALITY]'):
                # Keep the clock fact separate from the longer usage rules:
                # otherwise lexical overlap rejects even a short correct time.
                grounding['clock'] = message.splitlines()[1]
                grounding['text'] += grounding['clock'] + '\n'

    rpg_context_message = build_rpg_context_message(runtime_context, language=language, llm=llm)
    if rpg_context_message:
        system_messages.append(rpg_context_message)
        grounding['text'] += rpg_context_message + '\n'

    from .offline_wiki import generation_context, report_generation_source
    wiki = generation_context((runtime_context or {}).get('offline_wiki_context'),
                              llm or (runtime_context or {}).get('llm'),
                              language=language or (runtime_context or {}).get('offline_wiki_status',{}).get('language'))
    if wiki:
        system_messages.append(wiki)
        grounding['text'] += wiki
    report_generation_source(wiki, (runtime_context or {}).get('offline_wiki_status'))

    memory = (runtime_context or {}).get('super_memory')
    if memory:
        try:
            query = (runtime_context or {}).get('super_memory_query','')
            block = memory.generation_context(query,llm,runtime_context=runtime_context,language=language)
            if block:
                system_messages.append(block)
                grounding['text'] += '\n' + block
                recalls = getattr(memory, 'last_recall', [])
                if isinstance(recalls, list):
                    grounding['memories'] = [dict(item) for item in recalls if isinstance(item, dict)]
        except Exception:
            if isinstance(runtime_context,dict):
                runtime_context['super_memory_error']='Erinnerungen konnten nicht abgerufen werden.'

    # llama.cpp reuses only an unchanged leading token sequence. Put our
    # settings-only instructions before the live clock, query-specific hints,
    # wiki and recall; otherwise a new minute invalidates the long style and
    # MAAT prompts too. Rebuild everything every turn so settings still apply
    # immediately. Unknown/plugin-specific blocks keep their relative order.
    stable_markers = ('[THINKING MODE OFF]', '[THINKING-MODUS AUS]',
                      '[MAAT_INTERNAL_QUALITY]', '[MAAT_REPLY_STYLE]',
                      '[MAAT_FORMATTING]')
    system_messages.sort(key=lambda text: not text.lstrip().startswith(stable_markers))
    return _append_system_messages(prepared, system_messages)


def chat_completion_thinking_kwargs(create_chat_completion: Callable[..., Any] | None) -> dict:
    if thinking_enabled() or not callable(create_chat_completion):
        return {}

    desired = {
        "chat_template_kwargs": {"enable_thinking": False},
        "reasoning": "off",
        "reasoning_budget": 0,
        "reasoning_format": "none",
    }

    try:
        signature = inspect.signature(create_chat_completion)
    except Exception:
        return {}

    accepts_kwargs = any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )
    if accepts_kwargs:
        return desired

    return {
        key: value
        for key, value in desired.items()
        if key in signature.parameters
    }
