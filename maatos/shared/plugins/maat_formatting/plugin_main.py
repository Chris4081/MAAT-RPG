"""Optional output conventions; no second model call or destructive case fixes."""
from shared.core.ai_plugin_settings import settings_for, language_for
from shared.core.maat_style import normalize_heading_mode, normalize_list_mode


class Plugin:
    type = 'chat'
    commands = {}

    def generation_prompt(self, language=None, context=None):
        settings = settings_for(context)
        if not settings.get('response_formatting_enabled', True):
            return ''
        en = language_for(context, language) == 'en'
        forms = ['bold', 'small pipe tables'] if en else ['Fettdruck', 'kleine Pipe-Tabellen']
        if not settings.get('maat_style_enabled', False) or normalize_heading_mode(settings.get('style_heading_mode')) != 'none':
            forms.append('Markdown headings' if en else 'Markdown-Überschriften')
        if not settings.get('maat_style_enabled', False) or normalize_list_mode(settings.get('style_list_mode')) != 'none':
            forms.append('lists' if en else 'Listen')
        intro = ('Use clear paragraphs and correct capitalization. Use ' + ', '.join(forms) + ' only when useful. ' if en else
                 'Nutze klare Absätze und korrekte Groß- und Kleinschreibung. Nutze ' + ', '.join(forms) + ' nur bei Bedarf. ')
        if settings.get('maat_style_enabled', False):
            intro += ('MAAT Style chooses layout; this block describes notation only. ' if en else
                      'MAAT Style bestimmt den Aufbau; dieser Block beschreibt nur die Schreibweise. ')
        if en:
            text = intro + ('Put code in fenced blocks with its language and preserve exact case and indentation. '
                    'Write formulas in readable Unicode (×, √, ², subscripts) or simple LaTeX inside $…$ / $$…$$. '
                    'Explain symbols briefly when needed. Preserve names, quotations, variable names, values and the requested reply language. '
                    'Do not add calculations unless asked. No HTML or external images.')
        else:
            text = intro + ('Setze Code in umzäunte Blöcke mit Sprachangabe '
                    'und erhalte Schreibweise und Einrückung exakt. Schreibe Formeln in lesbarem Unicode (×, √, ², Tiefstellungen) '
                    'oder einfachem LaTeX in $…$ / $$…$$. Erkläre Symbole bei Bedarf kurz. Erhalte Namen, Zitate, Variablennamen, Werte '
                    'und die gewünschte Antwortsprache. Keine ungefragten Berechnungen, kein HTML, keine externen Bilder.')
        return '[MAAT_FORMATTING]\n' + text + '\n[/MAAT_FORMATTING]'
