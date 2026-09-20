"""Small, transient conversation preferences shared by all model adapters."""

PRESETS = {
    'short': (40, 100),
    'normal': (80, 180),
    'chatty': (150, 300),
    'very_chatty': (300, 600),
}
MODE_LABELS = {
    'short': ('Kurz', 'Short'),
    'normal': ('Normal', 'Normal'),
    'chatty': ('Gesprächig', 'Chatty'),
    'very_chatty': ('Sehr gesprächig 😂', 'Very chatty 😂'),
}
OPTIONS = (
    ('reply_style_engage', ('Auf Aussagen des Nutzers eingehen', 'Engage with what the user says')),
    ('reply_style_develop', ('Gedanken etwas ausführen', 'Develop ideas a little further')),
    ('reply_style_followups', ('Natürliche Anschlussgedanken erlauben', 'Allow natural follow-up thoughts')),
    ('reply_style_end_question', ('Jede Antwort mit einer Frage beenden', 'End every reply with a question')),
)
DEFAULTS = {
    'reply_style_mode': 'normal',
    'reply_style_min_tokens': 80,
    'reply_style_max_tokens': 180,
    # Keep the saved key for existing profiles; it now means soft elaboration.
    'reply_style_force_length': False,
    **{key: True for key, _ in OPTIONS},
}
MIN_TARGET, MAX_TARGET = 20, 2000


def normalize_settings(settings):
    settings = settings if isinstance(settings, dict) else {}
    mode = str(settings.get('reply_style_mode', 'normal'))
    if mode not in PRESETS:
        mode = 'normal'

    def target(key, fallback):
        try:
            value = settings.get(key, fallback)
            if isinstance(value, bool):
                return fallback
            return min(MAX_TARGET, max(MIN_TARGET, int(value)))
        except (TypeError, ValueError, OverflowError):
            return fallback

    low, high = PRESETS[mode]
    low = target('reply_style_min_tokens', low)
    high = max(low, target('reply_style_max_tokens', high))
    return {
        'reply_style_mode': mode,
        'reply_style_min_tokens': low,
        'reply_style_max_tokens': high,
        'reply_style_force_length': settings.get('reply_style_force_length', False) is True,
        **{key: settings.get(key, True) is not False for key, _ in OPTIONS},
    }


def build_reply_style_prompt(settings, language='de'):
    if not settings.get('reply_style_enabled', True):
        return ''
    config = normalize_settings(settings)
    en = language == 'en'
    mode = MODE_LABELS[config['reply_style_mode']][int(en)].removesuffix(' 😂')
    low, high = config['reply_style_min_tokens'], config['reply_style_max_tokens']
    if en:
        lines = [f'Reply style: {mode}. Aim for {low}–{high} tokens of visible reply, not words.',
                 'This is a flexible target: no padding, repetition or token-count announcements. Keep greetings proportionate.',
                 'This setting controls length instead of other general style limits. Explicit user requests and exact output formats take priority. Preserve the reply language and RPG role.']
        rules = (
            ('Respond to the user’s concrete statements instead of giving a generic reply.', None),
            ('Develop useful ideas with a brief explanation or fitting example.', 'Keep explanations focused; add no optional elaboration.'),
            ('Allow a natural related thought when useful; stay on topic.', 'Stay with the requested topic; add no optional tangents.'),
            ('End every conversational reply with one relevant, varied question, unless the user asks otherwise or requests an exact output format.', 'Do not routinely end with a question; ask only when clarification is needed.'),
        )
    else:
        lines = [f'Antwortstil: {mode}. Ziel: {low}–{high} Tokens sichtbare Antwort, nicht Wörter.',
                 'Flexibler Richtwert: keine Füllsätze, Wiederholungen oder Tokenangaben ausgeben. Begrüßungen bleiben angemessen kurz.',
                 'Diese Einstellung bestimmt die Länge statt anderer allgemeiner Stil-Limits. Ausdrückliche Nutzerwünsche und exakte Ausgabeformate gehen vor. Bewahre Antwortsprache und RPG-Rolle.']
        rules = (
            ('Gehe konkret auf die Aussagen des Nutzers ein, statt allgemein zu antworten.', None),
            ('Führe hilfreiche Gedanken mit einer kurzen Erklärung oder einem passenden Beispiel aus.', 'Halte Erklärungen fokussiert; keine zusätzlichen Ausführungen.'),
            ('Erlaube einen natürlichen Anschlussgedanken, wenn er hilft; bleibe beim Thema.', 'Bleibe beim angefragten Thema; keine zusätzlichen Abschweifungen.'),
            ('Beende jede Gesprächsantwort mit einer passenden, abwechslungsreichen Frage, außer der Nutzer wünscht es anders oder verlangt ein exaktes Ausgabeformat.', 'Beende Antworten nicht routinemäßig mit einer Frage; frage nur bei nötiger Klärung.'),
        )
    if config['reply_style_force_length']:
        lines.insert(1, (
            f'For substantive questions, try to reach roughly {low} tokens by adding relevant explanation, nuance or a useful example supported by the available context. '
            'This is a soft lower target, never a required minimum. Greetings, thanks, trivial questions and already complete answers may be much shorter. '
            'Stop naturally when done; never invent RPG events, facts or shared memories to make the answer longer.' if en else
            f'Versuche bei inhaltlichen Fragen ungefähr {low} Tokens zu erreichen: ergänze passende Erklärungen, Einordnungen oder ein hilfreiches Beispiel, das der vorhandene Kontext trägt. '
            'Das ist eine weiche Untergrenze, keine Pflichtlänge. Begrüßungen, Dank, einfache Fragen und bereits vollständige Antworten dürfen deutlich kürzer sein. '
            'Beende die Antwort natürlich; erfinde keine RPG-Ereignisse, Fakten oder gemeinsamen Erinnerungen, um sie zu verlängern.'))
    for (key, _), (on, off) in zip(OPTIONS, rules):
        instruction = on if config[key] else off
        if instruction:
            lines.append(instruction)
    return '[MAAT_REPLY_STYLE]\n' + '\n'.join(lines) + '\n[/MAAT_REPLY_STYLE]'


def generation_length_options(perf, settings):
    """Discard the retired hard minimum; retain the user's output/context caps."""
    options = dict(perf or {})
    options.pop('_reply_min_tokens', None)
    return options
