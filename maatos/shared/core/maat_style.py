from __future__ import annotations

import re
from typing import Any

STYLE_DEFAULTS = {
    'style_tone_mode': 'friendly', 'style_tone_auto': True,
    'style_opening_mode': 'varied', 'style_density_mode': 'normal',
    'style_heading_mode': 'simple', 'style_list_mode': 'auto',
    'style_emoji_mode': 'few', 'style_old_smiley_mode': 'none',
    'style_greeting_override': True, 'style_debug': False,
}
STYLE_CHOICES = {
    'style_tone_mode': (('neutral', ('Sachlich', 'Neutral')), ('friendly', ('Freundlich', 'Friendly')),
        ('enthusiastic', ('Begeistert', 'Enthusiastic')), ('scientific', ('Wissenschaftlich', 'Scientific')),
        ('mentor', ('Mentor', 'Mentor')), ('philosophical', ('Philosophisch', 'Philosophical'))),
    'style_opening_mode': (('direct', ('Direkt', 'Direct')), ('varied', ('Abwechslungsreich', 'Varied')),
        ('warm', ('Warm', 'Warm')), ('personal', ('Persönlich', 'Personal'))),
    'style_density_mode': (('compact', ('Kompakt', 'Compact')), ('normal', ('Normal', 'Normal')), ('airy', ('Luftig', 'Airy'))),
    'style_heading_mode': (('none', ('Keine', 'None')), ('simple', ('Einfach', 'Simple')), ('rich', ('Ausdrucksvoll', 'Expressive'))),
    'style_list_mode': (('auto', ('Automatisch', 'Automatic')), ('none', ('Keine', 'None')),
        ('bullets', ('Aufzählungspunkte', 'Bullets')), ('numbers', ('Nummeriert', 'Numbered'))),
    'style_emoji_mode': (('none', ('Keine', 'None')), ('few', ('Wenige', 'Few')), ('many', ('Viele', 'Many'))),
    'style_old_smiley_mode': (('none', ('Keine', 'None')), ('few', ('Wenige', 'Few')), ('many', ('Viele', 'Many'))),
}
STYLE_CHECKS = (
    ('style_tone_auto', ('Ton automatisch an die Nachricht anpassen', 'Adapt tone to the message automatically')),
    ('style_greeting_override', ('Reine Begrüßungen kurz halten', 'Keep greeting-only replies brief')),
    ('style_debug', ('Stil-Diagnose anzeigen', 'Show style diagnostics')),
)
INTENT_LABELS = {
    'greeting': ('Begrüßung', 'Greeting'), 'technical': ('Technik', 'Technical'),
    'analysis': ('Analyse', 'Analysis'), 'philosophical': ('Reflexion', 'Reflection'),
    'creative': ('Kreativ', 'Creative'), 'emotional': ('Persönliches Anliegen', 'Personal concern'),
    'general': ('Allgemein', 'General'),
}


GREETINGS = [
    "hallo",
    "hi",
    "hey",
    "guten morgen",
    "guten tag",
    "guten abend",
    "servus",
    "moin",
    "hello",
]

GREETING_REQUEST_HINTS = [
    "kannst",
    "bitte",
    "hilf",
    "hilfe",
    "baue",
    "mach",
    "erstelle",
    "schreibe",
    "fix",
    "fehler",
    "code",
    "warum",
    "wie",
    "was",
]

TECHNICAL = [
    "code",
    "python",
    "latex",
    "fehler",
    "bug",
    "programmieren",
    "script",
    "skript",
    "datei",
    "ordner",
    "modul",
    "loader",
    "webui",
    "textgen",
    "gguf",
    "mlx",
    "llama",
    "llama.cpp",
    "terminal",
    "install",
    "server",
    "api",
    "json",
    "yaml",
    "css",
    "html",
    "javascript",
]

ANALYSIS = [
    "was hältst du",
    "was haeltst du",
    "meinung",
    "einschätzung",
    "einschaetzung",
    "besser",
    "vergleich",
    "warum",
    "argument",
    "bewerte",
    "analyse",
    "risiko",
    "pros",
    "contras",
]

PHILOSOPHICAL = [
    "spirituell",
    "bewusstsein",
    "symbolik",
    "vision",
    "theorie",
    "philosophie",
    "ethik",
    "maat",
    "respekt",
    "harmonie",
    "balance",
    "schöpfung",
    "schoepfung",
    "verbundenheit",
    "kosmos",
    "universum",
]

CREATIVE = [
    "erstelle",
    "schreibe",
    "baue",
    "formuliere",
    "entwirf",
    "design",
    "idee",
    "ideen",
    "story",
    "text",
    "song",
    "musik",
    "generiere",
    "mach mir",
    "schreib",
    "zeichne",
]

EMOTIONAL = [
    "ich bin traurig",
    "ich bin wütend",
    "ich bin wuetend",
    "ich fühle",
    "ich fuehle",
    "mir geht es",
    "sorge",
    "angst",
    "verzweifelt",
    "vermiss",
    "trauere",
    "einsam",
    "weinen",
]

CASUAL = [
    "haha",
    "xd",
    ":d",
    "^^",
    ";)",
    ":)",
    "lol",
    "cool",
    "nice",
    "danke",
    "perfekt",
    "super",
]

# RPG adaptation: bilingual intent detection; no additional model invocation.
GREETINGS += ["good morning", "good afternoon", "good evening"]
GREETING_REQUEST_HINTS += ["can you", "please", "help", "build", "write", "why", "how", "what"]
TECHNICAL += ["error", "programming", "file", "folder", "module", "debug"]
ANALYSIS += ["what do you think", "opinion", "assessment", "compare", "why", "evaluate", "analysis", "risk", "better"]
PHILOSOPHICAL += ["consciousness", "philosophy", "ethics", "respect", "harmony", "creation", "connection", "universe"]
CREATIVE += ["create", "write", "build", "compose", "imagine", "draw", "ideas", "music"]
EMOTIONAL += ["i am sad", "i'm sad", "i feel", "i am angry", "worried", "afraid", "lonely", "grieving", "i miss", "overwhelmed"]
CASUAL += ["thanks", "thank you", "great"]

STYLE_RULES: dict[str, dict[str, Any]] = {
    "greeting": {
        "max_words": 40,
        "structure": "minimal",
        "skip_deep_regulators": True,
        "skip_counterperspective": True,
        "skip_cci": True,
    },
    "technical": {"max_words": 350, "structure": "steps"},
    "analysis": {"max_words": 300, "structure": "balanced"},
    "philosophical": {"max_words": 400, "structure": "reflective"},
    "creative": {"max_words": 500, "structure": "free_but_clear"},
    "emotional": {"max_words": 220, "structure": "warm_direct"},
    "general": {"max_words": 180, "structure": "simple"},
}


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def _has_any(text: str, markers: list[str]) -> bool:
    return any(marker in text for marker in markers)


def _is_greeting(text: str) -> bool:
    compact = (text or "").lower().strip()
    if not compact or _word_count(compact) > 6:
        return False
    if "?" in compact and _word_count(compact) > 2:
        return False
    if _has_any(compact, GREETING_REQUEST_HINTS + TECHNICAL + ANALYSIS + CREATIVE):
        return False
    return any(re.search(r"\b" + re.escape(greeting) + r"\b", compact) for greeting in GREETINGS)


def detect_intent(user_input: str) -> str:
    text = (user_input or "").lower().strip()
    if not text:
        return "general"
    if _is_greeting(text):
        return "greeting"
    if _has_any(text, EMOTIONAL):
        return "emotional"
    if _has_any(text, TECHNICAL):
        return "technical"
    if _has_any(text, ANALYSIS):
        return "analysis"
    if _has_any(text, CREATIVE):
        return "creative"
    if _has_any(text, PHILOSOPHICAL):
        return "philosophical"
    return "general"


def detect_tone_vector(user_input: str) -> dict[str, float]:
    text = (user_input or "").lower().strip()
    if not text:
        return {"technical": 0.0, "casual": 0.0, "emotional": 0.0, "creative": 0.0}

    def score(markers: list[str], extra: int = 0) -> float:
        hits = sum(1 for marker in markers if marker.lower() in text) + extra
        return round(min(1.0, hits / 3.0), 2)

    casual_extra = 1 if re.search(r"(?:xD|\^\^|:D|;\)|:\))", user_input or "") else 0
    return {
        "technical": score(TECHNICAL),
        "casual": score(CASUAL, casual_extra),
        "emotional": score(EMOTIONAL),
        "creative": score(CREATIVE),
    }


def _normalize(value: object, default: str, aliases: dict[str, str]) -> str:
    text = str(value or default).strip().lower()
    return aliases.get(text, default)


def normalize_emoji_mode(value: object) -> str:
    return _normalize(
        value,
        "few",
        {
            "none": "none",
            "no": "none",
            "off": "none",
            "aus": "none",
            "keine": "none",
            "0": "none",
            "few": "few",
            "low": "few",
            "wenig": "few",
            "wenige": "few",
            "1": "few",
            "many": "many",
            "viel": "many",
            "viele": "many",
            "high": "many",
            "2": "many",
        },
    )


def normalize_old_smiley_mode(value: object) -> str:
    return _normalize(
        value,
        "none",
        {
            "none": "none",
            "no": "none",
            "off": "none",
            "aus": "none",
            "keine": "none",
            "0": "none",
            "few": "few",
            "low": "few",
            "wenig": "few",
            "wenige": "few",
            "1": "few",
            "many": "many",
            "viel": "many",
            "viele": "many",
            "high": "many",
            "2": "many",
        },
    )


def normalize_tone_mode(value: object) -> str:
    return _normalize(
        value,
        "friendly",
        {
            "neutral": "neutral",
            "klar": "neutral",
            "sachlich": "neutral",
            "friendly": "friendly",
            "freundlich": "friendly",
            "warm": "friendly",
            "enthusiastic": "enthusiastic",
            "enthusiastisch": "enthusiastic",
            "begeistert": "enthusiastic",
            "scientific": "scientific",
            "wissenschaftlich": "scientific",
            "mentor": "mentor",
            "coach": "mentor",
            "philosophical": "philosophical",
            "philosophisch": "philosophical",
            "reflective": "philosophical",
        },
    )


def normalize_opening_mode(value: object) -> str:
    return _normalize(
        value,
        "varied",
        {
            "direct": "direct",
            "direkt": "direct",
            "none": "direct",
            "varied": "varied",
            "abwechslungsreich": "varied",
            "variabel": "varied",
            "auto": "varied",
            "warm": "warm",
            "personal": "personal",
            "persönlich": "personal",
            "persoenlich": "personal",
        },
    )


def normalize_density_mode(value: object) -> str:
    return _normalize(
        value,
        "normal",
        {
            "compact": "compact",
            "kompakt": "compact",
            "dense": "compact",
            "normal": "normal",
            "airy": "airy",
            "luftig": "airy",
            "locker": "airy",
        },
    )


def normalize_heading_mode(value: object) -> str:
    return _normalize(
        value,
        "simple",
        {
            "none": "none",
            "no": "none",
            "keine": "none",
            "off": "none",
            "simple": "simple",
            "einfach": "simple",
            "plain": "simple",
            "rich": "rich",
            "reich": "rich",
            "fancy": "rich",
        },
    )


def normalize_list_mode(value: object) -> str:
    return _normalize(
        value,
        "auto",
        {
            "none": "none",
            "no": "none",
            "keine": "none",
            "off": "none",
            "bullets": "bullets",
            "bullet": "bullets",
            "punkte": "bullets",
            "numbers": "numbers",
            "numbered": "numbers",
            "nummeriert": "numbers",
            "zahlen": "numbers",
            "auto": "auto",
            "automatisch": "auto",
        },
    )


def adaptive_tone_mode(base_tone: str, intent: str, tone_vector: dict[str, float], enabled: bool = True) -> str:
    base = normalize_tone_mode(base_tone)
    if not enabled:
        return base
    if intent == "technical" or tone_vector.get("technical", 0.0) >= 0.34:
        return "scientific"
    if intent == "emotional" or tone_vector.get("emotional", 0.0) >= 0.34:
        return "mentor"
    if intent == "creative" or tone_vector.get("creative", 0.0) >= 0.34:
        return "enthusiastic"
    if tone_vector.get("casual", 0.0) >= 0.34:
        return "friendly"
    if intent == "philosophical":
        return "philosophical"
    return base


def _tone_instruction(mode: str) -> str:
    return {
        "neutral": "Use a neutral, clear, calm tone.",
        "friendly": "Use a warm, friendly, direct tone. Keep it natural and not sugary.",
        "enthusiastic": "Use more energy in casual or creative answers, but avoid hype.",
        "scientific": "Use a precise, sober, evidence-aware tone.",
        "mentor": "Use a supportive mentor tone and explain clearly.",
        "philosophical": "Use a reflective, concept-oriented tone without empty mystification.",
    }[normalize_tone_mode(mode)]


def _emoji_instruction(mode: str, language='en') -> str:
    if language == 'de':
        return {
            'none': 'Verwende keine Emojis.',
            'few': 'Verwende höchstens ein passendes Emoji, wenn es Wärme vermittelt; bei technischen oder ernsten Antworten keines.',
            'many': 'Verwende mehrere passende Emojis in lockeren oder spielerischen Antworten; halte technische Antworten gut lesbar.',
        }[normalize_emoji_mode(mode)]
    return {
        "none": "Do not use emojis.",
        "few": "Use at most one fitting emoji when it adds warmth; avoid emojis in technical or serious answers.",
        "many": "Use several fitting emojis in casual or playful answers; keep technical answers readable.",
    }[normalize_emoji_mode(mode)]


def _old_smiley_instruction(mode: str, language='en') -> str:
    if language == 'de':
        return {
            'none': 'Verwende keine klassischen ASCII-Smileys wie xD, ;), :D, :), ^^.',
            'few': 'In lockeren oder spielerischen Antworten darfst du höchstens einen passenden klassischen ASCII-Smiley verwenden, etwa xD, ;), :D, :), ^^.',
            'many': 'Verwende klassische ASCII-Smileys in lockeren oder spielerischen Antworten häufiger, zum Beispiel xD, ;), :D, :), ^^.',
        }[normalize_old_smiley_mode(mode)]
    return {
        "none": "Do not use ASCII smileys like xD, ;), :D, :), ^^.",
        "few": "In casual or playful answers, you may use at most one fitting ASCII smiley such as xD, ;), :D, :), or ^^.",
        "many": "In casual or playful answers, use old ASCII smileys more freely, for example xD, ;), :D, :), ^^.",
    }[normalize_old_smiley_mode(mode)]


def _opening_instruction(mode: str) -> str:
    return {
        "direct": "Start directly with the substance. Do not use routine greetings unless the user only greeted you.",
        "varied": "Do not start every answer with the same greeting or name. Vary naturally.",
        "warm": "Warm openings are allowed, but vary them. For technical answers, start directly after a short acknowledgement.",
        "personal": "Personal openings and the user's name are allowed more often, but never mechanically.",
    }[normalize_opening_mode(mode)]


def _density_instruction(mode: str) -> str:
    return {
        "compact": "Use compact paragraphs with few blank lines; this is not an instruction to shorten the answer.",
        "normal": "Use normal spacing with short readable paragraphs.",
        "airy": "Use more paragraph breaks and one idea per paragraph when helpful; do not add content just for layout.",
    }[normalize_density_mode(mode)]


def _heading_instruction(mode: str) -> str:
    return {
        "none": "Do not use headings unless the user explicitly asks for them.",
        "simple": "Use short plain headings only when they help scanning.",
        "rich": "Use expressive short headings when helpful; keep technical answers restrained.",
    }[normalize_heading_mode(mode)]


def _list_instruction(mode: str) -> str:
    return {
        "none": "Avoid bullet and numbered lists; use prose.",
        "bullets": "Prefer bullet lists when there are multiple comparable points.",
        "numbers": "Prefer numbered lists for steps, sequences, and procedures.",
        "auto": "Choose prose, bullets, or numbered lists based on the task.",
    }[normalize_list_mode(mode)]


def style_state(settings: Any, user_input: str = "") -> dict[str, Any]:
    settings_dict = settings if isinstance(settings, dict) else vars(settings)
    intent = detect_intent(user_input or "")
    tone_vector = detect_tone_vector(user_input or "")
    base_tone = normalize_tone_mode(settings_dict.get("style_tone_mode", "friendly"))
    tone = adaptive_tone_mode(
        base_tone,
        intent,
        tone_vector,
        bool(settings_dict.get("style_tone_auto", True)),
    )
    rules = dict(STYLE_RULES.get(intent, STYLE_RULES["general"]))
    short_greeting = bool(settings_dict.get('style_greeting_override', True))
    if intent == "greeting" and not short_greeting:
        rules.update(STYLE_RULES['general'])
        rules["skip_deep_regulators"] = False
        rules["skip_counterperspective"] = False
        rules["skip_cci"] = False
    return {
        "enabled": bool(settings_dict.get("maat_style_enabled", False)),
        "debug": bool(settings_dict.get("style_debug", False)),
        "greeting_short": short_greeting,
        "intent": intent,
        "rules": rules,
        "tone_vector": tone_vector,
        "tone_mode": tone,
        "base_tone_mode": base_tone,
        "tone_auto": bool(settings_dict.get("style_tone_auto", True)),
        "emoji_mode": normalize_emoji_mode(settings_dict.get("style_emoji_mode", "few")),
        "old_smiley_mode": normalize_old_smiley_mode(settings_dict.get("style_old_smiley_mode", "none")),
        "opening_mode": normalize_opening_mode(settings_dict.get("style_opening_mode", "varied")),
        "density_mode": normalize_density_mode(settings_dict.get("style_density_mode", "normal")),
        "heading_mode": normalize_heading_mode(settings_dict.get("style_heading_mode", "simple")),
        "list_mode": normalize_list_mode(settings_dict.get("style_list_mode", "auto")),
    }


def build_style_prompt(settings: Any, user_input: str, visible_reasoning: bool = False, *, language='de') -> tuple[str, dict[str, Any]]:
    state = style_state(settings, user_input)
    if not state['enabled']:
        return '', state
    intent = state['intent']
    en = language == 'en'
    hints = {
        'greeting': ('Begrüße natürlich und passend zum Gespräch; keine ungefragte Theorie.', 'Greet naturally and in context; no unsolicited theory.'),
        'technical': ('Antworte präzise und praktisch zur technischen Frage.', 'Answer the technical question precisely and practically.'),
        'analysis': ('Gib eine klare Einschätzung mit Gründen und relevanten Alternativen.', 'Give a clear assessment with reasons and relevant alternatives.'),
        'philosophical': ('Prüfe Begriffe und Zusammenhänge, ohne unbelegte Gewissheit.', 'Examine concepts and connections without unfounded certainty.'),
        'creative': ('Liefere ein einfallsreiches, konkretes Ergebnis zur Aufgabe.', 'Provide an imaginative, concrete result for the task.'),
        'emotional': ('Antworte warm, aufmerksam und direkt; vermeide vorschnelle Zuschreibungen.', 'Be warm, attentive and direct; avoid premature assumptions.'),
        'general': ('Antworte natürlich und passend zum Anliegen.', 'Answer naturally and address the request.'),
    }
    de_tone = {
        'neutral': 'Sprich neutral, klar und ruhig.', 'friendly': 'Sprich freundlich und direkt, ohne Übertreibung.',
        'enthusiastic': 'Zeige bei kreativen Aufgaben Energie, ohne Hype.', 'scientific': 'Sprich präzise, sachlich und evidenzbewusst.',
        'mentor': 'Erkläre unterstützend und verständlich.', 'philosophical': 'Sprich reflektiert und verständlich, ohne leere Mystifizierung.',
    }
    max_words = state['rules']['max_words']
    settings_dict = settings if isinstance(settings, dict) else vars(settings)
    reply_style = bool(settings_dict.get('reply_style_enabled', True))
    lines = [hints[intent][int(en)], _tone_instruction(state['tone_mode']) if en else de_tone[state['tone_mode']]]
    if intent == 'greeting' and state['greeting_short']:
        lines.append('A greeting-only reply may stay short regardless of the target length; avoid unsolicited headings, lists and theory.' if en else
                     'Eine reine Begrüßung darf unabhängig vom Zielumfang kurz bleiben; keine ungefragten Überschriften, Listen oder Theorie.')
    if not reply_style:
        lines.append(f'Aim for at most {max_words} words unless the requested task needs more.' if en else
                     f'Orientiere dich an höchstens {max_words} Wörtern; die konkrete Aufgabe kann mehr benötigen.')
    if en:
        lines += [_opening_instruction(state['opening_mode']), _density_instruction(state['density_mode']),
                  _heading_instruction(state['heading_mode']), _list_instruction(state['list_mode']),
                  _emoji_instruction(state['emoji_mode']), _old_smiley_instruction(state['old_smiley_mode']),
                  'Finish the thought cleanly. Preserve the RPG role, requested calculations and the required MAAT reflection.']
    else:
        lines += [
                  {'direct': 'Beginne direkt mit dem Inhalt; begrüße nur, wenn der Nutzer selbst nur grüßt.',
                   'varied': 'Variiere Einstiege; wiederhole nicht ständig dieselbe Begrüßung oder denselben Namen.',
                   'warm': 'Ein warmer Einstieg ist erlaubt; variiere ihn und komme bei Sachfragen bald zum Inhalt.',
                   'personal': 'Persönliche Einstiege sind erlaubt; nutze einen bekannten Nutzernamen passend, nie mechanisch.'}[state['opening_mode']],
                  {'compact': 'Setze kompakte Absätze mit wenigen Leerzeilen; das ist keine Kürzungsvorgabe.',
                   'normal': 'Nutze normale Abstände und gut lesbare Absätze.',
                   'airy': 'Nutze mehr Absatzumbrüche, möglichst einen Gedanken pro Absatz; keine zusätzlichen Inhalte nur für die Form.'}[state['density_mode']],
                  {'none': 'Keine Überschriften, außer sie werden ausdrücklich verlangt.',
                   'simple': 'Nutze kurze, schlichte Überschriften nur wenn hilfreich.',
                   'rich': 'Nutze bei Bedarf ausdrucksvolle kurze Überschriften; bei Sachfragen zurückhaltend.'}[state['heading_mode']],
                  {'none': 'Vermeide Aufzählungen und nummerierte Listen; nutze Fließtext.',
                   'bullets': 'Bevorzuge Aufzählungspunkte bei mehreren vergleichbaren Punkten.',
                   'numbers': 'Bevorzuge nummerierte Listen für Schritte, Abläufe und Anleitungen.',
                   'auto': 'Wähle Fließtext, Aufzählungen oder nummerierte Listen passend zur Aufgabe.'}[state['list_mode']],
                  _emoji_instruction(state['emoji_mode'], 'de'), _old_smiley_instruction(state['old_smiley_mode'], 'de'),
                  'Beende Gedanken vollständig. Bewahre die RPG-Rolle, erbetene Berechnungen und die vorgeschriebene MAAT-Reflexion.']
    lines.append('Emoji/smiley rules apply to your prose; preserve code and quotations exactly.' if en else
                 'Emoji-/Smiley-Regeln gelten für deinen eigenen Text; erhalte Code und Zitate unverändert.')
    if reply_style:
        lines.append('Reply style controls length, elaboration and follow-up questions. These style preferences govern tone and layout only; paragraph density does not change the target length.' if en else
                     'Antwortstil steuert Länge, Ausführlichkeit und Anschlussfragen. Diese Stilregeln betreffen Ton und Aufbau; Absatzdichte verändert den Zielumfang nicht.')
    lines.append('Explicit user requests and exact output formats take priority; never invent names or memories for a personal opening.' if en else
                 'Ausdrückliche Nutzerwünsche und exakte Ausgabeformate gehen vor; erfinde keine Namen oder Erinnerungen für persönliche Einstiege.')
    return '[MAAT_STYLE]\n' + '\n'.join(lines) + '\n[/MAAT_STYLE]', state


ROUTINE_OPENING_RE = re.compile(
    r"^\s*(?:hey|hallo|hi|moin|guten morgen|guten tag|guten abend)\s+[\wÄÖÜäöüß-]{2,40}\b"
    r"\s*(?:xD|\^\^|:D|:\)|;\)|[^\w\s]{1,4})*"
    r"\s*[,.:;!\-–—]*\s*",
    re.IGNORECASE,
)


def _split_leading_codeblocks(text: str) -> tuple[str, str]:
    prefix = ""
    rest = text or ""
    while rest.startswith("```"):
        end = rest.find("\n```", 3)
        if end < 0:
            break
        close = rest.find("\n", end + 4)
        if close < 0:
            return prefix + rest, ""
        prefix += rest[: close + 1]
        rest = rest[close + 1 :]
    return prefix, rest


def _capitalize_start(text: str) -> str:
    match = re.match(r"^(\s*)([a-zäöü])", text or "")
    if not match:
        return text
    index = len(match.group(1))
    return text[:index] + text[index].upper() + text[index + 1 :]


def strip_routine_opening(user_input: str, output: str, settings: Any) -> str:
    state = style_state(settings, user_input)
    if not state["enabled"] or state["intent"] == "greeting":
        return output
    if state["opening_mode"] not in {"direct", "varied", "warm"}:
        return output
    prefix, rest = _split_leading_codeblocks(output or "")
    stripped = ROUTINE_OPENING_RE.sub("", rest, count=1)
    if stripped == rest:
        return output
    return prefix + _capitalize_start(stripped.lstrip())


def status_text(settings: Any, user_input: str = "") -> str:
    state = style_state(settings, user_input)
    return (
        f"MAAT Style: {'on' if state['enabled'] else 'off'} | "
        f"intent={state['intent']} | tone={state['tone_mode']} | "
        f"opening={state['opening_mode']} | density={state['density_mode']} | "
        f"headings={state['heading_mode']} | lists={state['list_mode']} | "
        f"emojis={state['emoji_mode']} | smileys={state['old_smiley_mode']}"
    )


def diagnostic_text(settings, user_input='', language='de'):
    """Local rule preview; never includes user text, prompts or claimed model thoughts."""
    state = style_state(settings, user_input)
    en = language == 'en'
    def label(key, value):
        return dict(STYLE_CHOICES[key])[value][int(en)]
    tone = label('style_tone_mode', state['tone_mode'])
    base = label('style_tone_mode', state['base_tone_mode'])
    source = ('automatic' if en else 'automatisch') if state['tone_auto'] else ('fixed' if en else 'fest')
    lines = [
        ('MAAT Style: on' if en else 'MAAT Style: an') if state['enabled'] else ('MAAT Style: off' if en else 'MAAT Style: aus'),
        ('Detected intent: ' if en else 'Erkanntes Anliegen: ') + INTENT_LABELS[state['intent']][int(en)],
        ('Tone: ' if en else 'Ton: ') + f'{tone} ({source}; ' + ('base: ' if en else 'Basis: ') + base + ')',
    ]
    for key, field, captions in (
        ('style_opening_mode', 'opening_mode', ('Einstieg', 'Opening')),
        ('style_density_mode', 'density_mode', ('Absätze', 'Paragraphs')),
        ('style_heading_mode', 'heading_mode', ('Überschriften', 'Headings')),
        ('style_list_mode', 'list_mode', ('Listen', 'Lists')),
        ('style_emoji_mode', 'emoji_mode', ('Emojis', 'Emojis')),
        ('style_old_smiley_mode', 'old_smiley_mode', ('Smileys', 'Smileys')),
    ):
        lines.append(captions[int(en)] + ': ' + label(key, state[field]))
    short = ('on' if en else 'an') if state['greeting_short'] else ('off' if en else 'aus')
    lines.append(('Brief greetings: ' if en else 'Kurze Begrüßungen: ') + short)
    source = ('Reply style' if en else 'Antwortstil') if settings.get('reply_style_enabled', True) else 'MAAT Style'
    lines.append(('Length guidance: ' if en else 'Längenvorgabe: ') + source)
    return '\n'.join(lines)
