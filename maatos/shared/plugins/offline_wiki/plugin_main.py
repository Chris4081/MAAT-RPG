"""MAAT Offline-Wikipedia: optional local ZIM, never an online fallback."""
import json
from pathlib import Path
from shared.core.maat_paths import state_file
from shared.core.offline_wiki import OfflineWiki, WikiError, settings, queries_from_text, context_blocks
from shared.core.wiki_i18n import tr


class Plugin:
    type = 'chat'
    commands = {
        '/wiki': {'de': 'Offline-Wikipedia: /wiki <Begriff> (lokale ZIM erforderlich).', 'en': 'Offline Wikipedia: /wiki <term> (local ZIM required).'},
        '/wiki status': {'de': 'Zeigt die gewählte ZIM-Datei.', 'en': 'Shows the selected ZIM file.'},
        '/wiki cache': {'de': 'Zeigt die zuletzt lokal gelesenen Artikel.', 'en': 'Shows recently read local articles.'},
        '/wiki debug on': {'de': 'Zeigt den kompakten Wiki-Kontext.', 'en': 'Shows compact wiki context.'},
        '/wiki debug off': {'de': 'Schaltet Wiki-Debug aus.', 'en': 'Disables wiki debug.'},
        '/wiki debug once': {'de': 'Zeigt den nächsten Wiki-Kontext einmalig.', 'en': 'Shows the next wiki context once.'},
        '/wiki zim': {'de': 'ZIM-Pfad setzen: /wiki zim <Pfad> oder /wiki zim clear.', 'en': 'Set ZIM path: /wiki zim <path> or /wiki zim clear.'},
    }

    def __init__(self):
        self.wiki = OfflineWiki()
        self.debug = self.debug_once = False

    def ui(self,text,**values):
        return tr(text,self.wiki.language,**values)

    def command(self, cmd, context=None):
        parts = (cmd or '').strip().split(maxsplit=1)
        if not parts or parts[0].lower() != '/wiki':
            return None
        query = parts[1] if len(parts) > 1 else ''
        config = settings()
        self.wiki.language = config.get('language','de')
        path = config.get('offline_wiki_zim_path', '')
        if query.lower() in ('', 'status'):
            return self.ui('📚 Offline-Wikipedia\nZIM: {path}\nAutomatisch: {auto}\n/wiki <Begriff> · /wiki zim <Pfad> · /wiki cache\nKeine Online-Abfragen.',path=path or self.ui('nicht gewählt (optional)'),auto=self.ui('an' if config.get('offline_wiki_auto',True) else 'aus'))
        if query.lower().startswith('zim '):
            chosen = query[4:].strip().strip('"\'')
            chosen = '' if chosen.lower() == 'clear' else chosen
            try:
                if chosen:
                    self.wiki.open(chosen)
                    chosen = self.wiki.identity[0]
                else:
                    self.wiki.reset()
                config['offline_wiki_zim_path'] = chosen
                target = Path(state_file('settings_state.json'))
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
                return self.ui('📚 ZIM gespeichert: {path}',path=chosen or self.ui('keine Datei'))
            except (WikiError, OSError) as exc:
                return f'📚 {exc}'
        if query.lower().startswith('debug '):
            mode = query[6:].lower()
            if mode not in ('on', 'off', 'once'):
                return self.ui('Nutze /wiki debug on | off | once.')
            self.debug, self.debug_once = mode == 'on', mode == 'once'
            return self.ui('📚 Wiki-Debug: {mode}',mode=mode)
        if query.lower() == 'cache':
            # Never use wiki_cache.db: it may contain old online results.
            try:
                self.wiki.open(path)
            except WikiError as exc:
                return f'📚 {exc}'
            return self.ui('📚 Zuletzt aus dieser ZIM gelesen:\n') + ('\n'.join(hit['title'] for hit in self.wiki.cache.values()) or self.ui('Noch keine Artikel.'))
        try:
            hit = self.wiki.lookup(query, path)
            return self.ui('📚 Wikipedia offline – {title}\n\n{text}\n\nQuelle: {source}',**hit)
        except WikiError as exc:
            return f'📚 {exc}'
        except Exception as exc:
            return self.ui('📚 Offline-Wikipedia nicht verfügbar: {error}',error=exc)

    def before_chat(self, user_input, context=None):
        if not isinstance(context, dict):
            return False, user_input
        context.pop('offline_wiki_context', None)
        context['offline_wiki_status'] = {}
        config = settings()
        self.wiki.language = config.get('language','de')
        if not config.get('offline_wiki_auto', True) or not config.get('offline_wiki_zim_path'):
            self.wiki.reset()
            return False, user_input
        # Earlier plugins may prepend memory text. Search the actual new message.
        terms = queries_from_text(context.get('last_user_input', user_input) or '', max_terms=2)
        context['offline_wiki_status'] = {'terms': terms,'language':self.wiki.language}
        from shared.core.rpg_generation_context import is_llama_model
        max_hits = 1 if is_llama_model(context.get('llm')) else 2
        hits, sources = [], set()
        for term in terms:
            try:
                hit = self.wiki.lookup(term, config['offline_wiki_zim_path'])
                if hit['source'] not in sources:
                    sources.add(hit['source'])
                    hits.append(hit)
                if len(hits) >= max_hits:
                    break
            except Exception as exc:
                context['offline_wiki_status']['error'] = str(exc)
                if self.debug or self.debug_once:
                    print(f'📚 Offline-Wikipedia: {exc}')
        if hits:
            context['offline_wiki_context'] = context_blocks(hits,self.wiki.language)
            if self.debug or self.debug_once:
                print(context['offline_wiki_context'])
        if terms:
            self.debug_once = False
        return False, user_input
