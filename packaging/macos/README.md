> Source repository: GUI setup is documented in [GUI-START.md](../../GUI-START.md).
> The release notes below describe previous packaged builds; no installer is included here.

# MAAT RPG 0.4.11 · macOS-Testpaket

Ein gemeinsames Setup für Intel (x86_64) und Apple Silicon (arm64).
Voraussetzung: **macOS 13.3 Ventura oder neuer**. macOS 15 gehört dazu.

## Neu in 0.4.11 · Ägyptische Gegner, Heiltränke und englischer Abspann

Die 20 regulären Gegnerformen erhalten neue Grafiken im Stil des alten Ägypten,
einschließlich 200 passender Angriffsbilder. Alle 25 Kampagnenbosse haben eigene
Motive: Die ersten fünf behalten ihre bisherigen Bilder, für Boss 6 bis 25 sind
20 neue Motive mit 200 Angriffsbildern enthalten. Kampf, Demo, Karte und Katalog
verwenden die passenden Grafiken.

Der Heiltrankbestand wird jetzt während des Kampfes auch in der Anzeige und
Seitenleiste aktualisiert. Die deutschen Aktionen heißen **Heiltrank** und
**Wegrennen**; englisch **Healing potion** und **Run away**. Der TinyLlama-Hinweis
in den Einstellungen ist entfernt, die Modellanpassungen bleiben erhalten.
Der englische Abspann nutzt nun **credits_en.mp3** (Harmonie der Erde).

Dieses Mac-Paket enthält den aktuellen Spielstand der Entwicklung nach der
Linux-Anpassung. Die vorhandenen Mac-Laufzeiten und die Intel-Auswahl zwischen
AVX2-Beschleunigung und portablem Rückfall bleiben erhalten. Linux benötigt das
separate Linux-Paket. Modelle, ZIM-Dateien und persönliche Spielstände sind
nicht enthalten; bestehende Profile bleiben im Benutzerordner erhalten.

**Prüfgrenze dieser Ausgabe:** Quellcode-Tests, Paketinhalt und native Bibliotheken
werden lokal geprüft. Die gebündelten Laufzeiten lassen sich in der aktuellen
Testumgebung nicht vollständig ausführen; insbesondere liegt für diese Ausgabe
kein neuer Lauf auf einem echten Intel-Mac vor. Frühere Laufzeitergebnisse in der
Versionshistorie sind keine erneuten Tests von 0.4.11. Details stehen in den
beiliegenden Prüfberichten.

English: Version 0.4.11 includes Egyptian artwork for all 20 regular enemy forms
and individual artwork for campaign bosses 6–25, with matching attack poses.
The first five bosses retain their artwork. Potion counts now refresh during
battle; the actions read **Healing potion** and **Run away**. The TinyLlama
settings hint is removed without removing model support. English credits now
play **credits_en.mp3**. Existing Mac runtimes and Intel AVX2/portable selection
are retained. Source tests, package contents and native libraries are checked;
this release has not been tested on physical Intel hardware, and bundled-runtime
execution is limited by the current test environment. Existing saves are kept.

## Neu in 0.4.10 · Vollständiges MAAT Style und natürliche Antwortlängen

**Einstellungen → Plugins → MAAT Style** bietet nun sechs Grundtöne,
automatische Tonanpassung, Einstieg/Anrede, Absatzdichte, Überschriften, Listen,
Emojis und klassische Smileys. Dazu kommen kurze Begrüßungen und eine lokale
Stil-Diagnose mit Beispieltext-Test. Alle Einstellungen und Prompts sind auf
Deutsch und Englisch vorhanden und werden pro Profil gespeichert.

**Antwortstil** steuert weiterhin Länge, Ausführlichkeit und Anschlussfragen.
MAAT Style regelt Ton und Aufbau; ausgeschaltete Listen und Überschriften werden
auch vom Formatierungs-Plugin berücksichtigt. Für einen festen Grundton die
automatische Tonanpassung ausschalten. MAAT Style bleibt standardmäßig aus.

Das harte Mindesttoken-Limit ist entfernt, auch für GPT-OSS. Der frühere Haken
„Textlänge erzwingen“ heißt **„Inhaltliche Antworten vertiefen“** und gibt nur
ein weiches Ziel vor. Begrüßungen dürfen kurz bleiben. Erkannte anhaltende
Wiederholungsschleifen stoppen Antwort und Sprache; die abgebrochene Nachricht
erhält keinen Chatfortschritt und wird nicht als Erinnerung gespeichert.
Abgeschlossene Kämpfe und Story-Entscheidungen bleiben erhalten. Die Erkennung
ist heuristisch, kein Schutz gegen jede mögliche Wiederholung.

English: **Settings → Plugins → MAAT Style** now exposes all tone, opening,
paragraph, heading, list, emoji and classic-smiley choices, plus automatic tone,
brief greetings and local style diagnostics. **Reply style** retains control of
length and follow-up questions. Disabling headings/lists also affects the
formatting prompt. Settings are saved per profile and apply to the next reply.

Hard minimum-token enforcement is removed, including GPT-OSS. **Develop
substantive answers** is a soft target; greetings may stay short. Detected
sustained loops stop the reply and speech, without chat progress or a memory
save. Completed game events remain intact. Detection is heuristic.

Profile und Modellwahl bleiben bei diesem Update erhalten; GGUF-Modelle sind
nicht enthalten. Die KI benötigt keinen zusätzlichen Modellaufruf für Style
oder den Wiederholungsschutz. Intel wird hier mit der gebündelten x86_64-Laufzeit
unter Rosetta geprüft; ein echter Intel-Leistungstest erfolgt beim Spieler.

## Neu in 0.4.9 · Antwortstil, TinyLlama und flüssigerer Spielablauf

Unter **Einstellungen → Plugins → Antwortstil** stehen Kurz, Normal, Gesprächig
und Sehr gesprächig mit anpassbarem Token-Ziel zur Auswahl. Standard ist Normal.
Vier unabhängige Optionen steuern das Eingehen auf Aussagen, ausführlichere
Gedanken, Anschlussgedanken und eine abschließende Frage. Die Vorgaben gelten
ab der nächsten Antwort, ohne zusätzlichen Modellaufruf oder Modellneustart.

TinyLlama-GGUFs werden ausdrücklich erkannt. Eingebettete Chatvorlagen haben
Vorrang; eindeutig erkannte TinyLlama Chat v1.0 ohne Vorlage erhalten die
passende Ersatzvorlage. TinyLlama nutzt die sparsamen Llama-Kontextregeln.
Für TinyLlama 1.1B Chat v1.0 zunächst **2.048 Kontext-Tokens** wählen; die globale
Voreinstellung von 20.000 und die manuelle Obergrenze bleiben unverändert.
Es ist kein Modell im Installer enthalten.

Im Kampf ersetzt **Klick ins Kampfbild oder den Kampftext, Leertaste oder Enter**
den Button „Text sofort anzeigen“. Die erste Eingabe vervollständigt laufenden
Text. Eine anschließende Weiter-Bestätigung lässt sich mit einer neuen Eingabe
bestätigen; Angriffe werden weiterhin bewusst gewählt. Gedrückthalten bestätigt
keinen zusätzlichen Schritt. Texteingaben behalten ihre eigene Bedienung.

Der zufällige Hinweis „MAAT-KI wacht“ und ähnliche Identitätsmeldungen ersetzen
die Chatantwort nicht mehr: Danach arbeitet das Modell normal weiter.
Die Meldung gelangt nicht als KI-Antwort in Modellverlauf oder Erinnerungen.

English: **Settings → Plugins → Reply style** adds Short, Normal, Chatty and
Very chatty, with editable token targets and four conversation options. Normal
is the default; changes apply to the next reply without reloading the model.
TinyLlama GGUF recognition and the Chat v1.0 fallback template are included.
Embedded templates take precedence. Start TinyLlama 1.1B Chat v1.0 at **2,048
context tokens**. Model weights are not included in the installer.

In battle, **click the scene or battle text, press Space or Enter** to reveal
the remaining text. A subsequent continue prompt needs a new press; actions
are still selected explicitly. Holding a key does not skip another step.
Random identity messages such as “MAAT-KI is awake” now precede the normal model
reply instead of replacing it. The notice is not stored as the AI's reply.

Das Update ersetzt die Anwendung; vorhandene Profile, Verlauf und Erinnerungen
bleiben im Benutzerordner erhalten. Tests verwenden isolierte Profile und
kontrollierte Modellantworten. Intel wird hier unter Rosetta geprüft; ein
Leistungstest mit großen Modellen auf einem echten Intel-Mac erfolgt beim Spieler.

## Neu in 0.4.8 · Kampfbalance, Chatdarstellung und KI-Plugins

Normale Arena- und Zufallskämpfe skalieren proportional zum Level: Grün bietet
KP-Reserve, Gelb bleibt knapp und bei Rot sollte ein Heiltrank eingeplant werden.
Gute Taktik, Talente und Buffs helfen weiterhin. Boss-, Final-, Dungeon- und
Demo-Gegner behalten ihre bisherige Skalierung. Ein Heiltrankfehler ist behoben:
Heilung verwendet jetzt die aktuellen Kampf-KP und verbraucht den Trank korrekt.

Der Kampfverlauf erscheint zusätzlich im sichtbaren Chat, ohne als Dialog an
das Modell, Super Memory oder die Sprachausgabe weitergegeben zu werden.
Die Kampfarena bleibt die Standardansicht. KI-Antworten werden beim Streamen,
bei Antwortkorrekturen und mit Markdown-Formatierung weiß dargestellt;
eigene „Du / You“-Nachrichten bleiben gelb.

Unter **Einstellungen → Plugins** stehen Emotionserkennung, PLP-Anti-Hallu,
MAAT Style, MAAT Identity, Zeit-/Realitätskontext und Antwortformatierung bereit.
MAAT Style bietet getrennte Einstellungen für Emojis und klassische Smileys.
Die Optionen sind pro Profil gespeichert und auf Deutsch und Englisch verfügbar.
GPT-OSS-20B-GGUF wird über den vorhandenen lokalen Adapter unterstützt.

English: Version 0.4.8 adds proportional level scaling for ordinary arena and
random battles: green offers a margin, yellow stays close, and red usually needs
a potion. Tactics, talents and buffs still help. Boss, finale, dungeon and demo
enemy scaling is unchanged. Potions now heal actual current battle HP and consume
an item correctly. Combat is mirrored into the visible chat without becoming
model dialogue, Super Memory or speech input; the arena remains the default view.
AI replies stay white during streaming, corrections and Markdown formatting;
your own messages stay gold.

**Settings → Plugins** provides emotion detection, PLP Anti-Hallu, MAAT Style,
MAAT Identity, time/reality context and reply formatting. Style includes separate
emoji and classic-smiley settings. Controls are bilingual and saved per profile.
GPT-OSS-20B GGUF support uses the existing local adapter. Models and Wikipedia ZIM
files remain separate, and installation preserves existing profiles and memories.

## Neu in 0.4.7 · Monster, Kampfeditor, MAAT-Guide und Modellfreigabe

Der reguläre Gegnerpool umfasst jetzt 20 Grundformen mit passenden
Angriffsgrafiken, Bewegung und Trefferfeedback. Die letzten fünf Gegnertypen
werden nach Möglichkeit vermieden. Katalog und Namen folgen Deutsch/Englisch.

Nach dem Abschluss aller fünf Finalkämpfe steht im Hauptmenü oben der
**Kampfeditor / Battle editor** bereit. Eigene Gegner können ein vorhandenes
Motiv oder ein eigenes Bild sowie angepasste Werte und Texte erhalten.
Editor-Testkämpfe verändern den regulären Spielstand nicht und vergeben keine
dauerhaften Belohnungen. Kategorien und Beschreibungen unter Aktionen sind
ebenfalls zweisprachig.

Der **MAAT-Guide** enthält nach seiner Freischaltung ab 20 Nachrichten acht
Formelbereiche mit Erklärungen und Beispielen auf Deutsch und Englisch.
Die freiwillige Übung unterscheidet MAAT-Durchschnitt und Stability.

Modelle werden beim Wechsel und beim Beenden des KI-Unterprozesses ausdrücklich
freigegeben. Das behebt den auf dem M4 reproduzierten Metal-Abbruch während der
Prozessbereinigung. Weitere abgefangene Python-Fehler erhalten Diagnoseeinträge
mit Fehlertyp und Aufrufstellen. Das isolierte Vorher-/Nachher-Experiment nutzte
ein winziges künstliches GGUF; es ist kein Leistungstest eines großen Modells.

English: Version 0.4.7 adds 20 regular enemy forms with matching attack artwork
and effects, avoids the five most recent enemy types when possible, and includes
the bilingual Battle editor at the top of the main menu after all five final
battles. Custom editor battles preserve normal progression and award no permanent
rewards. Actions categories and descriptions are translated. The MAAT Guide adds
eight bilingual formula explanations and examples after its 20-message unlock.
Native models are explicitly released before replacement and worker shutdown,
fixing the reproduced Metal cleanup abort. Additional Python diagnostic records
include error types and call sites. Existing profiles, chat history and memories
are preserved by installation; model weights and Wikipedia ZIMs remain separate.

## Neu in 0.4.6 · Englische Erfolge, Terra-Karte, Shop und Erinnerungen

Alle 94 Erfolge haben jetzt englische Namen und Beschreibungen: Wort-, Gefühls-,
Kampf- und Minispielerfolge. Übersicht, Filter, Suche, Fortschrittsbalken,
Freischaltungsmeldungen und letzte Erfolge in der Seitenleiste folgen der
Spielsprache. Wort- und Gesprächserfolge lassen sich im englischen Modus auch
mit passenden englischen Wörtern und Formulierungen freischalten. Gespeicherte
Erfolgs-IDs, Belohnungen und bestehende Freischaltungen bleiben erhalten.

Kleine und große Terra-Karte übersetzen nun auch die dynamischen Reiseanzeigen,
alle fünf Regionen, Boss-/Finalfortschritt und die Ansicht nach dem Spielende.
Das gilt einschließlich „End of the World / Watch credits“, Zurück-Button,
Legende, Tooltips und Fehlermeldungen beim Öffnen des Abspanns. Ein Sprachwechsel
behält die ausgewählte Kartenregion und Erfolgskategorie bei.

Der Basar und das Auftragsbrett folgen ebenfalls der Spielsprache: Artikel,
Wirkungen, Mengen, Preise, Kaufbuttons und Statusanzeigen sind zweisprachig.
Alle 25 kaufbaren Aufträge zeigen englische Titel, Ziele und Belohnungen;
auch Fortschritt, Pfadboni und die fünf Sammeltitel werden übersetzt.
Käufe, Gold, Inventar, Quest-IDs und Belohnungen bleiben unverändert.

Auch Erinnerungen → Chatverlauf / Saves ist nun zweisprachig: Speicherhinweise,
Filter, Quellen und Spielrollen, Optionen, Datumsübersichten, Statistiken und
Löschdialoge folgen der Spielsprache. Gespeicherte Gesprächs- und Erinnerungstexte
bleiben im Original erhalten. Die Archiv-Freischaltung nach fünf Nachrichten
wird im englischen Modus ebenfalls auf Englisch angekündigt.

Bossansagen aus älteren Dungeons übersetzen Namen vor der Ankündigung. Bekannte
Bossnamen erkennen auch Umlautvarianten aus älteren Spielständen. Zusätzliche
Bossprofile werden nach ihrer Zusammenführung übersetzt; Maatis' Pfadtitel und
Motive bleiben auch in Bossdialogen und bei Schutz-Pfaden englisch.

English: All 94 achievements now have English names and descriptions, including
word, emotional, battle and minigame badges. Filters, search, progress indicators,
unlock messages and recent achievements follow the game language. English words
and phrases unlock the same saved achievement IDs with the original rewards.
Both Terra maps translate journey progress, all five regions, boss/final counters
and the postgame view, including the End of the World credits button, legend,
tooltips and errors. Language changes preserve the selected region and category.

The bazaar and contract board also follow the game language: items, effects,
quantities, prices, purchase buttons and status messages are bilingual. All 25
paid contracts show English titles, objectives and rewards, including progress,
path bonuses and the five collectible titles. Gold, inventory, quest IDs and
rewards retain their original rules and saved values.

Memories → Chat history / Saves is bilingual as well: save notices, filters,
sources and game roles, options, dated overviews, statistics and deletion dialogs
follow the game language. Saved conversations and memory content stay verbatim.
The five-message archive unlock notice is translated. Older dungeon boss
announcements translate names before displaying them, and known name variants
from older saves are recognised. Boss profile overrides, Maatis' path titles and
path motifs are translated in English boss dialogue, including protection paths.

## Neu in 0.4.5 · Chatverlauf, Super Memory und Kontextauswahl

Unter **Einstellungen → Dialog & Sprachausgabe → Nachrichten im KI-Kontext**
lassen sich pro Profil 2–20 vorherige Nachrichten einstellen; Standard ist 10.
Eigene Eingaben und KI-Antworten zählen einzeln. Die aktuelle Eingabe kommt hinzu.
Die Änderung gilt ab der nächsten Antwort in beiden Spielrollen. Systemprompt,
die getrennten Erinnerungsauszüge und das vollständige Chatarchiv bleiben erhalten.
Dies ist eine Nachrichtengrenze, keine zusätzliche Tokenprüfung für überlange Texte.

Kann das Chatarchiv beim Start nicht geöffnet werden, versucht der Worker es beim
Speichern erneut. Bei einem Schreibfehler bleiben ausstehende Einträge während
der laufenden Sitzung zum erneuten Versuch im RAM. Ein Hinweis meldet den Fehler;
bei dauerhaftem Speicherfehler das Spiel bis zur Klärung geöffnet lassen.
Ein Fehler beim nachträglichen Speichern einer KI-Erinnerung unterbricht den
Abschluss und das Archivieren einer erfolgreichen Chatantwort nicht mehr.

Super Memory erkennt jetzt auch kurze englische Vorlieben und Arbeits-/Projektangaben.
Eine unbrauchbare oder wiederholte KI-Notiz unterdrückt keine wichtige Nutzeraussage
mehr. Generierte Platzhalter wie „das“ werden nicht als neue Erinnerungen gespeichert;
bestehende Einträge werden nicht gelöscht. Die Anweisung für neue Modellnotizen
berücksichtigt Deutsch/Englisch. Ein fehlgeschlagener Speicherabschluss kann mit
derselben Gesprächskennung erneut versucht werden.

Kampfverlauf und Kampfergebnis bleiben in der Arena und werden im GUI-Chat
nicht erneut ausgegeben. Die Zufallskampf-Ankündigung sowie Erfolge und andere
Statusmeldungen bleiben sichtbar. Erfolge, XP-Meldungen und Statusabfragen
unterbrechen die vorgelesene KI-Antwort nicht mehr. Intros, Geschichten,
Kampfbeginn, Entscheidungen und Hauptmenü stoppen weiterhin die Stimme;
eine neue Chatantwort unterbricht die vorherige beim ersten ausgegebenen Token.

English: Version 0.4.5 adds **Settings → Dialogue & Speech → Messages in AI context**,
with 2–20 previous individual messages per profile (default 10), plus the current
input. Both game roles use this setting; archives and saved memories are preserved.
Archive opening/writing can recover after temporary failures, and memory-write
errors no longer interrupt successful chat archiving. Pending archive entries stay
in RAM until a retry succeeds; keep the game open if a write-error notice persists.
English automatic memory recognition and bilingual save instructions are improved.
Vague model notes no longer suppress useful user statements. Actual confirmation
of the reported archive problem on the Intel Mac is still needed.

Battle logs and results stay in the arena instead of appearing in the GUI chat.
Encounter announcements, achievements and status notices remain visible.
Achievements, XP notices and status queries no longer interrupt spoken replies.
Intros, story scenes, combat, decisions and the main menu still stop speech;
the next reply interrupts the previous one at its first output token.

## Neu in 0.4.4 · Mistral/Ministral und die aktuelle Reise

Mistral- und Ministral-GGUFs verwenden ihre eingebettete Chatvorlage. MAAT-Prompt,
Spielsprache und Erinnerungen bleiben bei der Übergabe erhalten. Ältere Modelle
mit interner `llama`-Architektur werden als Mistral erkannt. Fehlende oder
ungeeignete Chatvorlagen führen zu einer verständlichen Ladefehlermeldung.
Ziel für den nächsten Intel-Test ist **Ministral 3 3B Instruct Q4_K_M**.
Die Modellgewichte sind nicht enthalten; sie werden lokal ausgewählt.

Das Update enthält außerdem die vereinfachten MAAT-Bewertungen auf der
Zehnerskala, die überarbeiteten Sprachvorgaben, stärkere normale Zufalls- und
Arenagegner sowie den Kartenbutton „Zufallskämpfe“ nach dem Spielende.
Nach einer normalen Bossniederlage beträgt der Rückweg fünf Felder;
Finalgegner behalten ihren bisherigen Rückweg von zehn Feldern.

Intel nutzt weiterhin seinen CPU-Adapter mit automatischer AVX2-Auswahl auf
geeigneten Prozessoren. Der Standardkontext bleibt 20.000 Tokens. Ein echter
Ministral-Lade- und Geschwindigkeitstest auf dem Intel-Mac steht noch aus.

English: Version 0.4.4 adds Mistral/Ministral template handling while preserving
the MAAT prompt, selected language and memories. It includes the latest
ten-point MAAT assessments, language rules, stronger ordinary encounters,
a five-step retreat after ordinary boss defeats, and postgame random encounters
from the world map. Final defeats retain the ten-step retreat. The intended
next Intel test is Ministral 3 3B Instruct Q4_K_M; model weights are not bundled.
Default context remains 20,000. Actual Intel loading and performance still
require testing on the target Mac.

## Auf dem MacBook installieren

1. `MAAT-RPG-macOS-Intel-ARM.pkg` auf das MacBook kopieren, etwa per AirDrop oder USB.
2. Das Paket doppelklicken und dem macOS-Installer folgen.
3. Unter **Programme → MAAT RPG** das Spiel öffnen.
4. Beim allerersten App-Start Deutsch oder Englisch wählen; danach das Profil auswählen.
5. Unter **KI & Modelle → Modell aus Pfad wählen** eine eigene GGUF-Datei auswählen.

Das Paket bringt Python, Qt, llama.cpp, den Offline-Wiki-Leser, Spielgrafiken und
Musik mit. Homebrew, Xcode und eine separate Python-Installation sind auf dem
Spielrechner nicht erforderlich. Auch die Installation selbst benötigt kein Internet.
Modelle und ZIM-Archive sind nicht enthalten. Eine Modell-Datei vom anderen Mac
muss separat kopiert und auf dem Zielgerät ausgewählt werden.

Dies ist ein privates, **nicht mit einem Apple-Entwicklerzertifikat signiertes
und nicht notarisiertes Testpaket**. Falls macOS das Öffnen blockiert, nach dem
Öffnungsversuch unter **Systemeinstellungen → Datenschutz & Sicherheit →
Dennoch öffnen** dieses konkrete Paket freigeben. Gatekeeper muss nicht
global deaktiviert werden. Nur das bewusst von dir übertragene Paket freigeben.

## Prozessor und Speicher

- Apple Silicon: native ARM-Python-Laufzeit und Metal-KI-Backend.
- Intel: native x86_64-Python-Laufzeit und CPU-KI-Backend mit Apple Accelerate.
  Das Paket enthält zusätzlich AVX2/FMA/F16C/BMI2. Die Laufzeit prüft
  vor dem Laden, ob die CPU alle benötigten Befehle unterstützt, und wählt dann
  diese optimierte Variante; andernfalls bleibt die portable Variante aktiv.
- Auch beim Start aus einer Rosetta-Umgebung wird auf einem ARM-Mac die native
  ARM-Laufzeit ausgewählt. Rosetta ist für den normalen Start nicht erforderlich.
- GGUF (Intel) begrenzt die Antwort-Threads auf die physischen Kerne und höchstens
  80 % der logischen Threads. Zum Einlesen nutzt es alle verfügbaren Threads.
  ARM behält die bisherige Automatik.
  Der Standardkontext bleibt bei 20.000 Tokens. Die Gewichte werden per mmap
  geladen; mlock bleibt in Auto ausgeschaltet, damit RAM nicht gesperrt wird.
- Unter **KI & Modelle → Leistung & Laden → Manuell** lassen sich Threads,
  GPU-Layer, Batchgrößen, Flash Attention und Speicheroptionen pro Profil ändern.
  **Auto · Standard** wählt wieder die automatischen Werte.
- 16 GB RAM sind keine Garantie, dass jedes GGUF hineinpasst. Modellgewichte,
  Kontextcache, macOS und andere Programme teilen sich den Arbeitsspeicher.
  Bei Speichermangel ein kleineres Modell oder einen kleineren Kontext wählen.
- MLX ist in diesem GGUF-Testpaket nicht enthalten; Llama, Qwen und Gemma werden
  über llama.cpp geladen, soweit die konkrete Modellarchitektur unterstützt wird.

## Eigene Daten und Updates

Stand 13. September 2026: Enthalten sind auch die manuellen Modelloptionen,
Esc zum Abbrechen einer KI-Antwort ohne Chatfortschritt, der separate
Audio-Prozess für Ausgangswechsel und die korrigierten englischen Chatlabels.
Bereits abgeschlossene Kämpfe und Story-Entscheidungen bleiben bei Esc erhalten.

Update 0.4.0 enthält die neuesten deutschen/englischen Story-Sequenzen,
MAAT Thinking, die überarbeitete Modell-Speicherprüfung und die Titelbilder
entlang der Terra-Reise: Pyramide am Anfang, danach ein neues Motiv für jede
der fünf Regionen. Startbildschirm und Hauptmenü folgen dem gewählten Profil.
Die Profilwahl unterstützt zehn Profile. Sprache gilt für die gesamte App.

Update 0.4.1 sichert den globalen Eingabefilter gegen Ereignisse beim Erzeugen
und Entfernen von Widgets ab. Das adressiert den gemeldeten Intel-Absturz in
QMainWindow/Shiboken beim Erzeugen eines Buttons. Die vom Python-Log benannte
Dungeon-Liste verwendet ihre vorhandenen Zeilen und Buttons bei Level-, Rekord-
und Sprachwechseln wieder. Levelaufstiege erscheinen als
kompakte deutsche/englische GUI-Anzeige mit gezeichneten Sternen und dem bisherigen
Sound. Terminal-Effekte und Fortschrittsregeln bleiben erhalten.
Die Tests prüfen Level-/Profilaktualisierungen, Texteingabe und Widget-Erzeugung
auf ARM sowie unter Rosetta. Der ursprüngliche Absturz wurde hier nicht reproduziert;
die Korrektur muss auf dem betroffenen Intel-Mac bestätigt werden.
Das separat gemeldete 8B-Ladeproblem auf dem MacBook ist noch nicht geklärt.
Das vorhandene Llama-3.1-8B-Q4_0-GGUF wurde hier mit 20.000 Kontext in der portablen
Intel-Laufzeit unter Rosetta erfolgreich geladen und für eine kurze Ausgabe genutzt.
Dies ist kein Geschwindigkeitsnachweis für einen echten Intel-Mac oder dessen
AVX2-Variante. Die kompilierten AVX/AVX2/FMA/F16C/BMI2-Fähigkeiten beider
Intel-Bibliotheken werden beim Paketbau zusätzlich statisch geprüft. Neue Worker-Protokolle
halten Architektur, CPU-Variante, Ladeoptionen, Speicherprüfung und Ladefehler fest.
Der Standardkontext bleibt 20.000; die RAM-Grenze bleibt 99 Prozent.

Spielstände, Chatverlauf, Erinnerungen und Profile liegen weiterhin unter
`~/Library/Application Support/MAAT-RPG` und werden vom Installer nicht ersetzt.
Das Paket enthält keine persönlichen Spielstände, Chatlogs, Modellpfade oder
ZIM-Dateien des Entwicklungsrechners. Es installiert keine Hintergrunddienste.
Vor einem Update das Spiel auf dem Zielgerät schließen.

Startdiagnosen liegen unter `~/Library/Logs/MAAT-RPG`.
GUI- und Worker-Diagnosen liegen unter `~/Library/Application Support/MAAT-RPG/logs`.
Diese technischen Protokolle zeichnen keine Chattexte oder Modellprompts auf.
Der integrierte Selbsttest verwendet nur vorübergehende Testprofile und lädt
kein Modell:

```sh
"/Applications/MAAT RPG.app/Contents/MacOS/run.sh" --self-test
```

## Prüfgrenzen

Beide Bibliothekssätze werden für ihre jeweilige Prozessorarchitektur gebaut.
ARM kann auf dem Entwicklungs-Mac nativ geprüft werden; Intel kann dort über
Rosetta auf Startfähigkeit geprüft werden. Ein Test auf echter Intel-Hardware
bleibt für Grafik, Audio, Modellgeschwindigkeit und RAM-Verhalten erforderlich.

## English

Copy the `.pkg` to the target Mac, double-click it, and open **Applications →
MAAT RPG** after installation. Requires **macOS 13.3 or later**, Intel or Apple
Silicon. Python, the GUI, GGUF backend and offline Wikipedia reader are bundled;
installation needs no internet. Choose your language and your own local GGUF
file on first use. ZIM archives and models are selected separately.

This private test installer is not Apple Developer ID signed or notarized.
If blocked, use **System Settings → Privacy & Security → Open Anyway** for this
specific package. Existing local saves and memories are preserved. A real
Intel-Mac test is still needed; testing under Rosetta is not a hardware test.

Version 0.4.0 includes the latest German/English story scenes, MAAT Thinking,
updated model memory checks, ten profiles and five new region-specific title
illustrations. The original pyramid remains the starting image. Your selected
profile determines the title and main-menu artwork.

Version 0.4.1 isolates application input filtering from widget lifecycle events,
addressing the reported Intel QMainWindow/Shiboken crash during button construction.
The dungeon list identified in the Python traceback now reuses its existing rows
and buttons across level, record and language updates.
Level-ups use a compact native notice with painted stars and the existing sound.
ARM and Rosetta tests cover level/profile refreshes, text input and widget creation;
confirmation on the affected Intel Mac is still required. The separate 8B loading
issue on the affected MacBook remains under investigation. The local Llama-3.1-8B-Q4_0
model passed a real load and short generation test at 20,000 context with the portable
Intel runtime under Rosetta; this does not benchmark native Intel or AVX2 performance. Both packaged Intel variants also undergo a static check of
their compiled AVX/AVX2/FMA/F16C/BMI2 capabilities.
New worker logs record loading stages, settings,
CPU variant and memory checks without chat text or prompts. They are stored in
`~/Library/Application Support/MAAT-RPG/logs`. The default context stays at 20,000
tokens and the memory threshold remains 99 percent.

## Rebuild

On a development Mac with Python 3.11, CMake and Xcode Command Line Tools:

```sh
python3 tools/build_macos_setup.py --fetch
python3 tools/build_macos_setup.py --build
```

Downloads come from official Python-build-standalone, PyPI and llama-cpp-python
sources. Versioned archive hashes are checked. The resolved wheel hashes and
the installer checksum are supplied with the build. The build directory is
`build/macos`; the release output is `dist/macos`.

References: [Qt 6.8 platforms](https://doc.qt.io/qt-6.8/supported-platforms.html), [Apple: opening a known unsigned app](https://support.apple.com/en-us/102445).

## Update 0.4.2 · GGUF (Intel)

Auf Intel erscheint jetzt ausschließlich der neue Adapter GGUF (Intel).
Er lädt auf der CPU, mit mmap und standardmäßig ohne Gewichts-Repacking.
Manuell lässt sich Repacking einschalten. Der ARM-Adapter nutzt auf Apple
Silicon ausdrücklich Metal, volle GPU-Auslagerung und Flash Attention.
Der Standardkontext bleibt 20.000 Tokens; die einstellbare Obergrenze beträgt
100.000, abhängig von Modell und RAM. AVX2 wird weiterhin nur bei unterstützter
CPU ausgewählt. Ein echter 8B-Test mit dem neuen Adapter war unter Rosetta
erfolgreich; das ersetzt keinen Test der Geschwindigkeit auf dem Intel-MacBook.

English: Version 0.4.2 adds the dedicated GGUF (Intel) CPU adapter, with
repacking off by default. The ARM adapter explicitly uses Metal, full GPU
offload and Flash Attention on Apple Silicon. Context defaults to 20,000 and
can be set up to 100,000, subject to model support and available memory.
The new path was verified with a real Llama 8B GGUF at 20,000 context under
Rosetta; Qwen 7B chat streaming passed on both adapters. Native Intel
performance and a full Linux run still require testing.

## Update 0.4.3 · Chat, MAAT-Fragen und Modellanzeige

Nachträgliche Plugin-Korrekturen ersetzen die bereits gestreamte Antwort,
statt den vollständigen Text noch einmal anzuhängen. Das gilt für beide
GGUF-Adapter und beide Spielrollen. Spielmeldungen bleiben erhalten.

Der Systemprompt ist deutlich kürzer. Im normalen Gespräch soll die KI keine
Berechnungen anbieten. Die kompakte Formelreferenz kommt nur bei passenden
Fragen hinzu, etwa „MAAT-Wert“, „maatwert“, „MAAT value“, „MAAT score“,
Weltformel oder PLP. Die Wiki-Erkennung nutzt dieselben Bewertungsbegriffe.
Erinnerungen und Offline-Wiki bleiben verfügbar. Die Promptübertragung und
Erkennung sind getestet; die Antwortqualität hängt weiterhin vom Modell ab.

Unter der Levelleiste stehen Modellstatus und Zeitmessung. Nach dem ersten
Durchlauf werden Ladezeit und Zeit bis zum ersten Antwort-Token geschätzt,
getrennt nach Modell, Einstellungen und System. Die Wiki-Quelle steht darunter.
Restzeiten sind Schätzungen; Eingabelänge und Systemlast können sie verändern.
Nach dem Update das Spiel neu starten, damit der neue Prompt geladen wird.

English: Version 0.4.3 replaces post-stream plugin edits in place, preventing
the complete answer from being appended twice. Shorter bilingual role prompts
keep ordinary conversation free of unsolicited calculation offers. The formula
reference is supplied only for relevant questions, including German/English
spelling variants shared with the offline wiki. A status panel below the XP bar
times model loading and the first response token, then estimates subsequent
runs. Wiki sources remain below it. Restart after updating to load the new
prompt. Timings are estimates, and response quality still depends on the model.
