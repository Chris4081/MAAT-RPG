"""Explicit GUI captions for the first bilingual release.

Only translate registered chrome. User text, transcripts, filenames and saves are
never rewritten. Internal IDs and combo item data remain language-independent.
"""
import re
from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QLabel, QAbstractButton, QComboBox, QLineEdit

EN = {
    'Nachrichten im KI-Kontext': 'Messages in AI context',
    '2–20 vorherige Nachrichten · Standard: 10. Eigene Eingaben und KI-Antworten zählen einzeln; deine neue Eingabe kommt hinzu.': '2–20 previous messages · Default: 10. Your messages and AI replies count separately; your new input is added.',
    'Pro Profil · Gilt ab der nächsten Antwort in beiden Spielrollen. Chatarchiv und gespeicherte Erinnerungen bleiben erhalten. Lange Texte können trotzdem viel Kontext benötigen.': 'Per profile · Applies from the next reply in both game roles. Chat archive and saved memories are preserved. Long texts can still use a lot of context.',
    'Die Sprache gilt für das gesamte Spiel und alle Profile. Ein Wechsel startet die Spielverbindung neu.': 'The language applies to the whole game and all profiles. Changing it restarts the game connection.',
    'Jedes Profil hat seinen eigenen Spielstand, Erinnerungen und Modelleinstellungen.': 'Each profile has its own save, memories and model settings.',
    '+ Neues Profil': '+ New profile',
    'Neues Profil': 'New profile',
    'Umbenennen …': 'Rename …',
    'Profil umbenennen': 'Rename profile',
    'Wie soll dein Profil heißen? (1–48 Zeichen)': 'What would you like to name your profile? (1–48 characters)',
    'Profil konnte nicht gespeichert werden': 'The profile could not be saved',
    'Bitte einen Namen mit 1 bis 48 Zeichen ohne Zeilenumbrüche eingeben.': 'Enter a name with 1 to 48 characters and no line breaks.',
    'Ungültiger Profilplatz.': 'Invalid profile slot.',
    'Alle zehn Profilplätze sind belegt.': 'All ten profile slots are in use.',
    '{count}/10 Profile · Wähle deine Reise oder lege ein neues Profil an.': '{count}/10 profiles · Choose your journey or create a new profile.',
    'Noch kein Profil vorhanden. Lege dein erstes Abenteuer an.': 'No profiles yet. Create your first adventure.',
    'Noch kein Modell gewählt': 'No model selected yet',
    'Modell: {name}': 'Model: {name}',
    'Profil wählen': 'Choose profile',
    'DEINE REISEN DURCH TERRA': 'YOUR JOURNEYS THROUGH TERRA',
    'Wähle dein Profil': 'Choose your profile',
    'Zehn Plätze für deine Abenteuer. Wähle eine Reise oder beginne neu.': 'Ten slots for your adventures. Choose a journey or start a new one.',
    'Jedes Profil hat seinen eigenen Spielstand, seine Sprache, Erinnerungen und Modelleinstellungen.': 'Each profile has its own save, language, memories and model settings.',
    '← Zum Startbildschirm': '← Back to the title screen',
    '← Zurück zu den Einstellungen': '← Back to settings',
    'Zuletzt gewählt': 'Last selected',
    'Gespeicherte Reise': 'Saved journey',
    'Freier Platz': 'Empty slot',
    'Löschen …': 'Delete …',
    'Kämpfe: {fights}  ·  Siege: {wins}  ·  Boss-Siege: {bosses}\nDungeons: {done}/{runs} abgeschlossen\nDungeon+ · Rekord: Welle {best}': 'Battles: {fights}  ·  Wins: {wins}  ·  Boss wins: {bosses}\nDungeons: {done}/{runs} completed\nDungeon+ · Best: wave {best}',
    'Diese Reise wählen →': 'Choose this journey →',
    'Neues Abenteuer →': 'New adventure →',
    'Spielstand konnte nicht vollständig gelesen werden.': 'The save could not be read completely.',
    'Aktive Ladeeinstellungen · noch kein Modell geladen.': 'Active load settings · no model loaded yet.',
    'Leistung & Laden': 'Performance & loading',
    'Standard: 20.000 Tokens · Maximal: 100.000 Tokens. Der tatsächliche Speicherbedarf hängt vom Modell ab.': 'Default: 20,000 tokens · Maximum: 100,000 tokens. Actual memory requirements depend on the model.',
    'Diese KI-Bibliothek bietet keine Repacking-Steuerung. Ihre nativen Vorgaben bleiben aktiv.': 'This AI library has no repacking control. Its native defaults remain active.',
    'GGUF (Intel) · Physische CPU-Kerne für Antworten, parallele Verarbeitung für den Kontext · Repacking aus.': 'GGUF (Intel) · Physical CPU cores for replies, parallel context processing · Repacking off.',
    'Intel: Modellgewichte beim Laden umordnen · Repacking': 'Intel: rearrange model weights during loading · Repacking',
    'Kann Antworten beschleunigen, braucht beim Laden aber zusätzliche Zeit und Speicher. Standard: aus.': 'May speed up replies, but takes extra time and memory during loading. Default: off.',
    'GGUF (Intel) verwendet die CPU. GPU-Layer werden hier auf 0 gesetzt.': 'GGUF (Intel) uses the CPU. GPU layers are set to 0 here.',
    'Auto · Standard': 'Auto · Default',
    'Manuell': 'Manual',
    'Automatisch passend zum System · ca. 80 % der CPU-Threads für Antworten.': 'Adjusted to your system · about 80% of CPU threads for responses.',
    'CPU-Threads · Antworten': 'CPU threads · Responses',
    'CPU-Threads · Prompt einlesen': 'CPU threads · Prompt processing',
    'Anzahl der CPU-Threads beim Erzeugen neuer Tokens.': 'Number of CPU threads used to generate new tokens.',
    'Anzahl der CPU-Threads beim Verarbeiten von Eingabe und Kontext.': 'Number of CPU threads used to process your prompt and context.',
    'GPU-Layer': 'GPU layers',
    '−1: alle möglichen Layer · 0: nur CPU · positive Zahl: begrenzte GPU-Auslagerung.': '−1: all possible layers · 0: CPU only · positive number: limited GPU offloading.',
    'GPU-Layer: −1 = alle möglichen · 0 = nur CPU': 'GPU layers: −1 = all possible · 0 = CPU only',
    'Batchgröße': 'Batch size',
    'Mikro-Batchgröße': 'Micro-batch size',
    'Maximale Anzahl von Prompt-Tokens pro Verarbeitungsschritt.': 'Maximum number of prompt tokens per processing step.',
    'Gleichzeitig berechnete Tokens. Kleinere Werte sparen Arbeitsspeicher.': 'Tokens computed together. Smaller values use less memory.',
    'Auto · Modellvorgabe': 'Auto · Model default',
    'Ein': 'On',
    'Aus': 'Off',
    'Optimierte Aufmerksamkeitsberechnung. Auto berücksichtigt das Modell und die Hardware.': 'Optimized attention computation. Auto takes the model and hardware into account.',
    'Speicherschonend laden · mmap': 'Memory-mapped loading · mmap',
    'Speichergrenze: 99 % RAM. Alle manuellen Ladeoptionen bleiben wählbar. Achtung: Diese Einstellungen können den Computer verlangsamen oder zum Absturz bringen. Der Schutz kann das nicht sicher verhindern.': 'Memory limit: 99% RAM. All manual loading options remain selectable. Warning: These settings may slow down or crash your computer. Memory protection cannot reliably prevent this.',
    'Modellgewichte direkt aus der Datei einblenden. Meist die passende Wahl.': 'Map model weights directly from the file. Usually the preferred option.',
    'Modell im RAM halten · mlock': 'Keep model in RAM · mlock',
    'Verhindert das Auslagern von Modellgewichten, sofern das System es erlaubt. Benötigt genügend freien RAM.': 'Prevents swapping model weights if permitted by the system. Requires enough free RAM.',
    'Pro Profil gespeichert · Wird beim nächsten „Modell laden“ übernommen.': 'Saved per profile · Applied the next time you choose “Load model”.',
    'Geladen: {mode} · {platform} · {acceleration}\n{threads} Threads für Antworten · {batch} beim Einlesen': 'Loaded: {mode} · {platform} · {acceleration}\n{threads} response threads · {batch} prompt threads',
    'Keine GPU-Auslagerung verfügbar · CPU wird verwendet.': 'GPU offloading is unavailable · Using the CPU.',
    'Die Batchgröße wurde auf die Kontextgröße begrenzt.': 'Batch size was limited to the context size.',
    'KI antwortet · Esc: abbrechen, ohne Chatfortschritt zu zählen.': 'AI is responding · Esc: cancel without counting chat progress.',
    'Antwort wird abgebrochen …': 'Cancelling response …',
    '⏹ Antwort abgebrochen · Diese Nachricht zählt nicht zum Fortschritt.': '⏹ Response cancelled · This message does not count towards progress.',
    'Der Audioausgang reagiert nicht. Bitte einen anderen Ausgang wählen oder Audio neu verbinden.': 'The audio output is not responding. Choose another output or reconnect audio.',
    'Audio-Prozess konnte nicht gestartet werden.': 'The audio process could not be started.',
    'Audio-Prozess wurde beendet. Bitte Audio neu verbinden.': 'The audio process stopped. Please reconnect audio.',
    "Die Rückkehr der Prinzipien": "Return of the Principles",
    "Eine Reise durch Erinnerung, Resonanz und die fünf Prinzipien.": "A journey through memory, resonance and the five principles.",
    "DAS ZEITALTER DER RESONANZ": "THE AGE OF RESONANCE",
    "DIE WELT ERINNERT SICH": "THE WORLD REMEMBERS",
    "Zum Startbildschirm zurückkehren": "Return to the title screen",
    "Zur großen Pyramide · Nach 20 Sekunden startet die Demo": "Return to the pyramid · The demo starts after 20 seconds",
    "Zum Titelbild · Nach 20 Sekunden startet die Demo": "Return to the title artwork · The demo starts after 20 seconds",
    "Hauptmenü": "Main menu",
    "BOSS-SIEGE": "BOSS WINS",
    "1   Spiel starten  →": "1   Start game  →",
    "1   Spiel fortsetzen  →": "1   Continue game  →",
    "✧   KI & Modelle · GGUF": "✧   AI && Models · GGUF",
    "Modell aus Pfad wählen …": "Choose model from file …",
    "2   Optionen": "2   Options",
    "3   Neues Spiel": "3   New game",
    "5   Beenden": "5   Quit",
    "Die Reise von Maatis · Du sprichst mit der KI": "Maatis's journey · Talk to the AI",
    "Ich bin die KI · Maatis spricht mit dir": "I am the AI · Maatis talks to you",
    "◇   Hauptmenü": "◇   Main menu",
    "◈   Charakter": "◈   Character",
    "⚔   Kampfarena": "⚔   Battle arena",
    "≡   MAAT-KI": "≡   MAAT-AI",
    "MAAT-KI": "MAAT-AI",
    "⚙   Einstellungen": "⚙   Settings",
    "📜   Quests && Aktionen": "📜   Quests && Actions",
    "Questlog · Spielaktionen · Shop · Erfolge · Monsterkatalog": "Quest log · Actions · Shop · Achievements · Bestiary",
    "REISE": "JOURNEY",
    "KÄMPFE & SPIELE": "BATTLES & GAMES",
    "HILFE & MENÜ": "HELP & MENU",
    "◈   Erinnerungen": "◈   Memories",
    "🔒   Erinnerungen": "🔒   Memories",
    "🔒   Talentbaum": "🔒   Talent tree",
    "🏰   Dungeons": "🏰   Dungeons",
    "🎮   Spielhalle": "🎮   Arcade",
    "Fünf Prinzipien.\nDein eigener Weg.": "Five principles.\nYour own path.",
    "Klassentalente ansehen und lernen": "View and learn class talents",
    "Nach dem ersten Kampf eine Klasse wählen.": "Choose a class after your first battle.",
    "MAAT verstehen und eine Situation reflektieren": "Understand MAAT and reflect on a situation",
    "Wird nach 20 Chatnachrichten freigeschaltet.": "Unlocks after 20 chat messages.",
    "Chatverlauf nach Tag, Monat und Jahr": "Chat history by day, month and year",
    "Arena · halbe Kampf-EP": "Arena · half battle XP",
    "Wird mit dem Zufallskampfmodus freigeschaltet.": "Unlocks with random encounters.",
    "OPTIONEN": "OPTIONS",
    "Dein Ort. Dein Klang.": "Your space. Your sound.",
    "Profile, Musik und das lokale KI-Modell.": "Profiles, music and your local AI model.",
    "← Zurück zum Hauptmenü": "← Back to main menu",
    "Spielprofil": "Game profile",
    "Einzelnes Profil löschen …": "Delete a profile …",
    "Profilwechsel ist möglich, sobald die laufende Aktion beendet ist.": "You can switch profiles once the current action has finished.",
    "Sprache / Language": "Sprache / Language",
    "Sprache ändern …": "Change language …",
    "Die Sprache gilt für dieses Profil. Ein Wechsel startet die Spielverbindung neu.": "Language is saved for this profile. Changing it restarts the game connection.",
    "Schriftgröße": "Text size",
    "Klein · 18 px": "Small · 18 px",
    "Mittel · 26 px · Standard": "Medium · 26 px · Default",
    "Groß · 36 px": "Large · 36 px",
    "Die Welt erinnert sich. Deine Reise beginnt.": "The world remembers. Your journey begins.",
    "Gilt sofort für Chat, Eingabe und Erzählverlauf. Der kompakte Kampftext bleibt bei 18 px.": "Applies immediately to chat, input and narration. Compact battle text stays at 18 px.",
    "Musik & Sound": "Music & Sound",
    "Musik im Menü, in Geschichten und im Kampf": "Music in menus, stories and battles",
    "Die Quellcode-Version enthält keine Hintergrundmusik. Eigene Soundeffekte sind enthalten; Musik ist standardmäßig aus.": "The source edition includes original sound effects but no background music. Music is off by default.",
    "Soundeffekte und Levelaufstieg": "Sound effects and level-ups",
    "Audio bereit": "Audio ready",
    "Systemstandard": "System default",
    "Audioausgabe": "Audio output",
    "Audioausgabe neu verbinden": "Reconnect audio output",
    "Lokale KI": "Local AI",
    "Hardware-Automatik · wird beim Laden ermittelt": "Automatic hardware settings · detected when loading",
    "Noch kein Modell geladen.": "No model loaded yet.",
    "Kein KI-Modell geladen": "No AI model loaded",
    "Modell laden": "Load model",
    "KI laden": "Load AI",
    "Kontextgröße": "Context size",
    "Kreativität / Temperatur": "Creativity / Temperature",
    "Llama · TinyLlama · Qwen · Gemma · Mistral · GPT-OSS — Chatvorlage aus der GGUF-Datei; TinyLlama Chat v1.0 auch mit passender Ersatzvorlage. Die Datei bleibt an ihrem Speicherort.": "Llama · TinyLlama · Qwen · Gemma · Mistral · GPT-OSS — Embedded GGUF chat template, with a matching fallback for TinyLlama Chat v1.0. The file stays in its original location.",
    "GPT-OSS: aus = niedrige Denkstufe, an = mittlere Denkstufe. Der Chat zeigt nur die fertige Antwort.": "GPT-OSS: off = low reasoning effort, on = medium reasoning effort. Chat shows only the final answer.",
    "Nutze ein Instruct-/Chat-Modell. Neue Modellarchitekturen benötigen eine passende llama.cpp-Version. Mehr Kontext benötigt mehr Arbeitsspeicher.": "Use an Instruct/Chat model. New model architectures require a compatible llama.cpp version. More context needs more RAM.",
    "KI & Modelle öffnen": "Open AI && Models",
    "MAAT RPG · KI & Modelle": "MAAT RPG · AI & Models",
    "Die Stimme deiner Reise": "The voice of your journey",
    "Fertig · Zurück zum Spiel": "Done · Back to game",
    "Dialog & Sprachausgabe": "Dialogue & Speech",
    "Thinking-Modus": "Thinking mode",
    "MAAT Thinking aktivieren": "Enable MAAT Thinking",
    "MAAT Thinking verbessert vor der Modellausgabe intern den Denkprozess.": "MAAT Thinking improves the internal thinking process before the model responds.",
    "MAAT100 · Standardmäßig an · Gilt ab der nächsten Antwort. Die Wirkung hängt vom Modell ab.": "MAAT100 · On by default · Applies to the next response. Results depend on the model.",
    "Stufe 100 · Stille Qualitätsprüfung nach H/B/S/V/R mit höchstens drei angeleiteten Überarbeitungen. Die Wirkung hängt vom Modell ab.": "Level 100 · Silent H/B/S/V/R quality check with up to three guided revisions. Results depend on the model.",
    "Spielkontext ausblenden": "Hide game context",
    "Sprachausgabe über das vorhandene TTS-Plugin": "Read aloud using the installed TTS plugin",
    "Standardmäßig aus. Die sichtbare MAAT-Reflexion bleibt Teil der Antwort.": "Off by default. The visible MAAT reflection remains part of the response.",
    "Verfügbarkeit der Stimme hängt vom vorhandenen TTS-Backend deines Systems ab.": "Voice availability depends on the TTS backend installed on your system.",
    "Spielverbindung neu starten": "Restart game connection",
    "Offline-Wikipedia · optional": "Offline Wikipedia · optional",
    "MAAT RPG liefert keine ZIM-Dateien oder Wikipedia-Inhalte mit. Für dein selbst gewähltes Archiv gelten dessen Quellen- und Lizenzangaben. Wenn du Artikeltexte oder daraus bearbeitete Texte weitergibst, beachte die jeweilige Lizenz, Quellenangabe und gegebenenfalls Weitergabe unter gleichen Bedingungen.": "MAAT RPG does not include ZIM files or Wikipedia content. Your chosen archive retains its own source and license notices. When sharing article text or adaptations of it, follow the applicable license, attribution and any share-alike requirements.",
    "Wähle eine lokale Wikipedia-ZIM. Die Datei wird am gewählten Ort gelesen; es gibt keine Online-Abfragen. Ohne Datei bleibt die Suche inaktiv.": "Choose a local Wikipedia ZIM file. It is read from its current location; no online requests are made. Search stays inactive without a file.",
    "Keine ZIM-Datei gewählt": "No ZIM file selected",
    "ZIM-Datei wählen …": "Choose ZIM file …",
    "Entfernen": "Remove",
    "Passende Begriffe automatisch in der Offline-Wikipedia nachschlagen": "Automatically look up relevant terms in offline Wikipedia",
    "Wiki-Wissen ist getrennt vom Spielkontext. Llama: ein Artikel mit maximal 400 Zeichen. Andere Modelle: bei Vergleichen bis zu zwei Artikel mit zusammen maximal 1.000 Zeichen. Gespräch und Erinnerungen bleiben erhalten.": "Wiki knowledge is separate from game context. Llama: one article, up to 400 characters. Other models: up to two articles for comparisons, with 1,000 characters in total. Conversations and memories are preserved.",
    "Testbegriff, z. B. Pyramide": "Test term, e.g. pyramid",
    "Offline-Suche testen": "Test offline search",
    "Keine ZIM ausgewählt.": "No ZIM file selected.",
    "Datei gespeichert. Mit einem Testbegriff kannst du sie prüfen.": "File saved. Enter a search term to test it.",
    "Lokale Wikipedia-ZIM auswählen": "Choose a local Wikipedia ZIM file",
    "Bitte eine vorhandene .zim-Datei wählen.": "Please choose an existing .zim file.",
    "Bitte einen Suchbegriff eingeben.": "Please enter a search term.",
    "Modell wird geladen …": "Loading model …",
    "Modell auswählen": "Choose a model",
    "Laden fehlgeschlagen · Modell auswählen": "Loading failed · Choose a model",
    "KI bereit": "AI ready",
    "Kein Modell geladen": "No model loaded",
    "Wähle eine GGUF-Datei und klicke auf „Modell laden“. Sie wird beim nächsten Start automatisch geladen.": "Choose a GGUF file and click “Load model”. It will load automatically the next time you start.",
    "Keine lokalen Modelle gefunden. Die Spielaktionen funktionieren auch ohne KI.": "No local models found. Game actions also work without AI.",
    "Kein Modell gefunden. Im Hauptmenü unter KI & Modelle eine GGUF-Datei auswählen.": "No model found. Select a GGUF file under AI & Models in the main menu.",
    "WÄHLE DEINE PERSPEKTIVE": "CHOOSE YOUR PERSPECTIVE",
    "Zwei Perspektiven. Eine Welt.": "Two perspectives. One world.",
    "MAATIS\nDer klassische Modus\nDu reist durch Terra und sprichst mit der MAAT-KI.": "MAATIS\nClassic mode\nTravel through Terra and talk to the MAAT-AI.",
    "ICH BIN DIE KI\nDer Begleitermodus\nMaatis fragt dich. Du antwortest als seine KI.": "I AM THE AI\nCompanion mode\nMaatis asks questions. You answer as his AI.",
    "Beide Modi bleiben erhalten. Wähle Maatis oder seine Begleiter-KI.": "Both modes are available. Choose Maatis or his companion AI.",
    "PROLOG / DAS ERWACHEN": "PROLOGUE / THE AWAKENING",
    "Intro überspringen": "Skip intro",
    "Weiter  →": "Next  →",
    "Klick / Enter · Satz anzeigen   |   Esc · Überspringen": "Click / Enter · Reveal sentence   |   Esc · Skip",
    "Satz anzeigen": "Reveal sentence",
    "Spiel beginnen  →": "Begin game  →",
    "Klick / Enter · Spiel beginnen   |   Esc · Überspringen": "Click / Enter · Begin game   |   Esc · Skip",
    "Klick / Enter · Nächster Satz   |   Esc · Überspringen": "Click / Enter · Next sentence   |   Esc · Skip",
    "Maatis entdeckt das leuchtende Artefakt in der verlassenen Bibliothek": "Maatis discovers the glowing artifact in the abandoned library",
    "Text überspringen": "Skip text",
    "Szene überspringen": "Skip scene",
    "Hintergrundgeschichte · Klick / Enter: weiter · Esc: Szene überspringen": "Story · Click / Enter: next · Esc: skip scene",
    "Abspann · Leertaste: Pause · Esc: Zurück ins Spiel": "Credits · Space: pause · Esc: back to game",
    "Zurück ins Spiel  →": "Back to game  →",
    "DEIN ABENTEUER / DIALOG": "YOUR ADVENTURE / DIALOGUE",
    "Dein Gespräch mit der lokalen MAAT-KI und die Ereignisse deiner Reise.": "Your conversation with the local MAAT-AI and the events of your journey.",
    "Sprich mit Maatis oder nutze einen Spielbefehl …": "Talk to Maatis or enter a game command …",
    "Senden  →": "Send  →",
    "Senden": "Send",
    "Nachricht senden · Enter": "Send message · Enter",
    "Die aktuelle Antwort läuft noch. Du kannst schon tippen; dein Entwurf bleibt erhalten.": "The current response is still running. You can keep typing; your draft is preserved.",
    "Antwort sofort anzeigen": "Reveal response",
    "Text sofort anzeigen": "Reveal text",
    "Klick ins Kampfbild oder den Text · Leertaste · Enter: Text vervollständigen": "Click the battle scene or text · Space · Enter: reveal the remaining text",
    "Klick · Leertaste · Enter: weiter": "Click · Space · Enter: continue",
    "Ich bin die KI": "I am the AI",
    "Spiel wird geladen …": "Loading game …",
    "Wähle „Spiel starten“, um deine Reise zu beginnen.": "Choose “Start game” to begin your journey.",
    "RPG bereit · Wähle deinen nächsten Schritt.": "RPG ready · Choose your next step.",
    "Deine Reise beginnt. Sprich mit MAAT-KI.": "Your journey begins. Talk to MAAT-AI.",
    "Deine Entscheidung ist gefragt.": "Choose your next step.",
    "Prolog · Klick oder Enter: weiter · Esc: Intro überspringen.": "Prologue · Click or Enter: next · Esc: skip intro.",
    "Neues Spiel": "New game",
    "Alle Profilplätze sind belegt. Wähle unter Optionen ein vorhandenes Profil.": "All profile slots are in use. Choose an existing profile under Options.",
    "Freien Profilplatz wählen:": "Choose an empty profile slot:",
    "Die Rückkehr der Prinzipien\n\nStartmenü → Intro → MAAT-KI\n\nHarmonie · Balance · Schöpfungskraft · Verbundenheit · Respekt\n\nOriginalgeschichten und Spielregeln in einer nativen Oberfläche. Musik und KI laufen lokal.": "Return of the Principles\n\nMain menu → Intro → MAAT-AI\n\nHarmony · Balance · Creativity · Connection · Respect\n\nOriginal stories and game rules in a native interface. Music and AI run locally.",
    "Gewählter Ausgang nicht verbunden": "Selected output is disconnected",
    "Für Llama immer aktiviert: kein Spielkontext. Erinnerungen und Gesprächsverlauf bleiben erhalten.": "Always enabled for Llama: no game context. Memories and conversation history are preserved.",
    "An: keine automatischen Spielfakten. Aus: nur Level, HP und Bossfortschritt; keine Dungeon- oder Kampfprotokolle. Erinnerungen bleiben erhalten.": "On: no automatic game facts. Off: only level, HP and boss progress; no dungeon or battle logs. Memories are preserved.",
    "Modell aus Pfad wählen": "Choose model from file",
    "GGUF-Modelle (*.gguf *.GGUF)": "GGUF models (*.gguf *.GGUF)",
    "Profil löschen": "Delete profile",
    "Keine zusätzlichen Profile vorhanden. Das Standardprofil enthält auch gemeinsame Modelle und bleibt geschützt.": "No additional profiles found. The standard profile also contains shared models and is protected.",
    "Welches Profil möchtest du löschen?": "Which profile would you like to delete?",
    "Profil endgültig löschen?": "Permanently delete profile?",
    "{name} wirklich löschen?\n\nSpielstand, Erinnerungen, Quests und Einstellungen dieses Profils werden endgültig gelöscht. Gemeinsame Modelle und andere Profile bleiben erhalten.": "Really delete {name}?\n\nThis profile’s save data, memories, quests and settings will be permanently deleted. Shared models and other profiles are preserved.",
    "Profil konnte nicht gelöscht werden": "Could not delete profile",
    "Profil {slot} gelöscht. Der Platz ist wieder frei.": "Profile {slot} deleted. The slot is available again.",
    "Laufende Aktion beenden?": "End current action?",
    "Die aktuelle Aktion wird abgebrochen. Noch ungespeicherter Fortschritt kann verloren gehen. Spielverbindung neu starten?": "The current action will be interrupted. Unsaved progress may be lost. Restart the game connection?",
    "Spiel beenden?": "Quit game?",
    "Ausgewählt · {name} — zum Aktivieren „Modell laden“ wählen.": "Selected · {name} — choose “Load model” to activate.",
    "Ausgewählt · {name} — zum Aktivieren „KI laden“ wählen.": "Selected · {name} — choose “Load AI” to activate.",
    "Klick / Enter · Zurück ins Spiel   |   Esc · Szene überspringen": "Click / Enter · Back to game   |   Esc · Skip scene",
    "Zum Kampf  →": "To battle  →",
    "Zur Dungeon-Auswahl  →": "Choose a dungeon  →",
    "Klick / Enter · Zum Kampf   |   Esc · Text überspringen": "Click / Enter · To battle   |   Esc · Skip text",
    "Klick / Enter · Zur Dungeon-Auswahl   |   Esc · Text überspringen": "Click / Enter · Choose a dungeon   |   Esc · Skip text",
    "Spielverbindung wird nach Modell-Ladefehler wiederhergestellt …": "Restoring game connection after a model loading failure …",
    "Spielverbindung beendet. Neustart unter Einstellungen möglich.": "Game connection ended. You can restart it under Settings.",
    "🌟 MAAT-KI RPG ist bereit.\nDie Welt erinnert sich. Deine Reise beginnt.\n\n": "🌟 MAAT-AI RPG is ready.\nThe world remembers. Your journey begins.\n\n",
    "Spiel verlassen?": "Leave game?",
    "Eine Spielaktion läuft noch. Beim Beenden kann ihr noch ungespeicherter Fortschritt verloren gehen. Wirklich schließen?": "A game action is still running. Quitting may lose its unsaved progress. Really close?",
    "Musik pausiert": "Music paused",
    "MAAT RPG · Die Rückkehr der Prinzipien": "MAAT RPG · Return of the Principles"
}
TEMPLATES = {
    "Lautstärke {value} %": "Volume {value} %",
    "✦   Talente · {value} TP": "✦   Talents · {value} TP",
    "Wird nach fünf Chatnachrichten freigeschaltet. · {value}/5": "Unlocks after five chat messages. · {value}/5"
}
from shared.core.gameplay_i18n import EN as GAMEPLAY_EN
EN['Der letzte Modellladeversuch wurde nicht erfolgreich abgeschlossen. Automatisches Laden ist gestoppt. Prüfe Modell und Einstellungen und starte das Laden bewusst erneut.'] = 'The last model load did not complete successfully. Automatic loading is stopped. Check the model and settings, then explicitly start loading again.'
EN.update(GAMEPLAY_EN)
from shared.core.minigame_i18n import EN as MINIGAME_EN
EN.update(MINIGAME_EN)
from shared.core.progression_i18n import EN as PROGRESSION_EN
EN.update(PROGRESSION_EN)
from shared.core.wiki_i18n import EN as WIKI_EN
EN.update(WIKI_EN)
from shared.core.achievement_i18n import EN as ACHIEVEMENT_EN
EN.update(ACHIEVEMENT_EN)
from shared.core.shop_i18n import EN as SHOP_EN
EN.update(SHOP_EN)
from shared.core.memory_i18n import EN as MEMORY_EN
EN.update(MEMORY_EN)
from shared.core.command_i18n import EN as COMMAND_EN
EN.update(COMMAND_EN)

REVERSE = {value: key for key, value in EN.items()}
PATTERNS = []
for de, en in TEMPLATES.items():
    for source, target, language in ((de, en, 'en'), (en, de, 'de')):
        pattern = re.escape(source).replace(r'\{value\}', r'(?P<value>\d+)')
        PATTERNS.append((re.compile(pattern), target, language))


def tr(text, language='de'):
    if not text:
        return text
    source = REVERSE.get(text, text)
    if source in EN:
        return EN[source] if language == 'en' else source
    for pattern, target, target_language in PATTERNS:
        if target_language == language:
            match = pattern.fullmatch(text)
            if match:
                return target.format(**match.groupdict())
    return text


class LocalizedUI:
    """Per-view language; changing captions never changes the underlying IDs."""
    language = 'de'

    def ui(self, text, **values):
        text = tr(text, self.language)
        return text.format(**values) if values else text

    def set_language(self, language):
        if language not in ('de', 'en') or language == self.language:
            return
        self.language = language
        self.retranslate()

    def retranslate(self):
        translate_widgets(self, self.language)


def translate_widgets(root, language):
    """Update menu captions without emitting edits or touching user content."""
    if root is None:
        return
    widgets = [root] + root.findChildren(QLabel) + root.findChildren(QAbstractButton) + root.findChildren(QComboBox) + root.findChildren(QLineEdit)
    for widget in widgets:
        if isinstance(widget, (QLabel, QAbstractButton)):
            current = widget.text()
            translated = tr(current, language)
            if current != translated:
                widget.setText(translated)
        if isinstance(widget, QComboBox):
            with QSignalBlocker(widget):
                for index in range(widget.count()):
                    current = widget.itemText(index)
                    translated = tr(current, language)
                    if current != translated:
                        widget.setItemText(index, translated)
        if isinstance(widget, QLineEdit):
            widget.setPlaceholderText(tr(widget.placeholderText(), language))
        widget.setToolTip(tr(widget.toolTip(), language))
        widget.setAccessibleName(tr(widget.accessibleName(), language))
