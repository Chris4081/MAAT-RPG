"""Localized offline-Wikipedia chrome; archive text stays in its own language."""
EN = {
 'Keine ZIM-Datei gewählt. Wähle sie optional unter Einstellungen → Offline-Wikipedia.':'No ZIM file selected. You can choose one under Settings → Offline Wikipedia.',
 'ZIM-Datei nicht verfügbar: {path} ({error})':'ZIM file unavailable: {path} ({error})',
 'keine vorhandene .zim-Datei':'not an existing .zim file',
 'Offline-Wikipedia benötigt libzim im Python des Spiels. Installiere requirements-wiki.txt und starte das Spiel neu.':'Offline Wikipedia needs libzim in the game\'s Python environment. Install requirements-wiki.txt and restart the game.',
 'ZIM-Datei kann nicht geöffnet werden: {error}':'Cannot open ZIM file: {error}',
 'Bitte einen Suchbegriff eingeben.':'Please enter a search term.',
 'Kein direkter Titel gefunden; die Volltextsuche ist für diese ZIM nicht verfügbar.':'No exact title found; full-text search is unavailable for this ZIM.',
 'Kein Offline-Wikipedia-Treffer für „{term}“.':'No offline Wikipedia result for “{term}”.',
 'Der Treffer ist kein lesbarer Textartikel.':'The result is not a readable text article.',
 'Dieser Artikel ist für den kompakten Wiki-Auszug zu groß.':'This article is too large for a compact wiki excerpt.',
 'Der Artikel enthält keinen lesbaren Text.':'The article contains no readable text.',
 'Artikel konnte nicht gelesen werden: {error}':'Cannot read article: {error}',
 'nicht gewählt (optional)':'not selected (optional)', 'an':'on', 'aus':'off', 'keine Datei':'no file',
 '📚 Offline-Wikipedia\nZIM: {path}\nAutomatisch: {auto}\n/wiki <Begriff> · /wiki zim <Pfad> · /wiki cache\nKeine Online-Abfragen.':'📚 Offline Wikipedia\nZIM: {path}\nAutomatic: {auto}\n/wiki <term> · /wiki zim <path> · /wiki cache\nNo online requests.',
 '📚 ZIM gespeichert: {path}':'📚 ZIM saved: {path}',
 'Nutze /wiki debug on | off | once.':'Use /wiki debug on | off | once.',
 '📚 Wiki-Debug: {mode}':'📚 Wiki debug: {mode}',
 '📚 Zuletzt aus dieser ZIM gelesen:\n':'📚 Recently read from this ZIM:\n', 'Noch keine Artikel.':'No articles yet.',
 '📚 Wikipedia offline – {title}\n\n{text}\n\nQuelle: {source}':'📚 Offline Wikipedia – {title}\n\n{text}\n\nSource: {source}',
 '📚 Offline-Wikipedia nicht verfügbar: {error}':'📚 Offline Wikipedia unavailable: {error}',
 '{title}\n\n{text}\n\nQuelle: {source}':'{title}\n\n{text}\n\nSource: {source}',
 'Offline-Wikipedia: {error}':'Offline Wikipedia: {error}',
 '📚 Offline-Quelle für diese Antwort: {titles}':'📚 Offline source for this answer: {titles}',
 '📚 Kein Offline-Auszug verfügbar: {terms}':'📚 No offline excerpt available: {terms}',
 'Keine passende Quelle gefunden.':'No matching source found.',
 'Die Suche erkennt deutsche und englische Fragen. Die Artikelsprache richtet sich nach deiner ZIM; für englische Artikeltitel empfiehlt sich eine englische Wikipedia-ZIM.':'Search recognises German and English questions. Article language depends on your ZIM; use an English Wikipedia ZIM for English article titles.',
}


def tr(text,language='de',**values):
    text=EN.get(text,text) if language=='en' else text
    return text.format(**values) if values else text
