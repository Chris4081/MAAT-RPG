# KI-Plugins / AI plugins

## Deutsch

Öffne **Einstellungen → Plugins**. Neben **Allgemein** gibt es dafür einen eigenen
Reiter direkt im Spielfenster. Die bisherigen Plugin-Buttons und das separate
Plugin-Fenster entfallen. Die Schalter werden pro Profil gespeichert
und gelten ab der nächsten Nachricht, ohne Modellneustart oder Musikwechsel.

| Plugin | Standard | Wirkung |
| --- | --- | --- |
| Antwortstil | An · Normal | Vier Gesprächsstile mit veränderbarem Token-Ziel und vier unabhängigen Gesprächsoptionen. |
| Antworten formatieren | An | Kurzer Formatierungs-Prompt und native Darstellung fertiger Antworten mit Markdown-Tabellen, Überschriften, Listen, Code und einfachen Formeln. |
| MAAT Reality | An | Frische lokale Systemzeit mit Datum, Wochentag und UTC-Offset bei jeder Antwort; bei vorhandenem Chatarchiv auch der letzte gespeicherte Aktivitätszeitpunkt. |
| Emotionserkennung | An | Vorhandene Worterkennung für Stimmungshinweise; nun schaltbar und um englische Ausdrücke ergänzt. |
| PLP Anti-Hallu | Aus | Zusätzliche Anweisung und heuristische Prüfung der vollständigen Antwort vor Anzeige, Sprachausgabe und Erinnerungsspeicherung. |
| MAAT Style | Aus | Passt Ton und Aufbau an die Anfrage an; eigene Längenvorgaben nur bei ausgeschaltetem Antwortstil. |
| MAAT Identity | Aus | Verstärkt die aktuelle Spielrolle und ihre ehrlichen Grenzen; im umgekehrten Modus bleibt das Modell Maatis. |

Unter **Antwortstil** stehen **Kurz (40–100 Tokens)**, **Normal (80–180)**,
**Gesprächig (150–300)** und **Sehr gesprächig (300–600)** bereit. Standard ist
Normal, auch in bestehenden Profilen ohne gespeicherte Auswahl. Die Unter- und
Obergrenze lassen sich zwischen 20 und 2.000 Tokens verändern. Ein Stilwechsel
übernimmt wieder dessen Vorgabebereich; die Grenzen können sich nicht kreuzen.
Tokens sind Textbausteine, keine Wörter. Der Bereich ist immer eine flexible
Prompt-Vorgabe. **Inhaltliche Antworten vertiefen** bittet bei substanziellen
Fragen zusätzlich um passende Erklärungen oder Beispiele in Richtung des unteren
Zielwerts. Begrüßungen, Dank, einfache Fragen und bereits vollständige Antworten
dürfen kurz bleiben. Der Haken ist standardmäßig aus. Bereits gespeichertes
**Textlänge erzwingen** verwendet automatisch das neue weiche Verhalten.

Die frühere EOS-Sperre ist entfernt, einschließlich des GPT-OSS-Sonderfalls.
Es gibt weder ein hartes Minimum noch eine automatische zweite Anfrage.
Ausgabe- und Kontextlimits bleiben unverändert; Modelle dürfen natürlich enden.
Die Einstellung gilt pro Profil ab der nächsten Nachricht.

Ein gemeinsamer Streaming-Schutz stoppt anhaltende exakte Wort-, Satz- und
Emoji-Schleifen vor weiteren Ausgabe-Hooks. Er verlangt mindestens acht direkt
aufeinanderfolgende Kopien eines Musters (höchstens 160 Zeichen) sowie mindestens
40 Zeichen bei Symbolen bzw. 96 bei Wörtern. Er arbeitet mit begrenztem Speicher,
verändert keine normalen Text-Deltas und läuft auch bei ausgeschaltetem Antwortstil.
Codeblöcke, Inline-Code, Markdown-Zitate und erkannte ausdrückliche Aufträge zu
literalen Wiederholungen sind ausgenommen. Das ist ein konservativer heuristischer
Schutz, keine Erkennung aller semantischen Wiederholungen. Bereits gestreamte
Textteile können sichtbar bleiben. Im GUI endet eine erkannte Schleife wie ein
Abbruch: Sprachausgabe stoppt, kein Chatfortschritt, keine KI-Entwicklung und keine
Archivierung oder Super-Memory-Speicherung dieser Antwort. Abgeschlossene
Spielereignisse bleiben bestehen. Eine zweisprachige Meldung erklärt den Stopp.

Vier Haken sind anfangs an: auf Nutzeraussagen eingehen, Gedanken etwas ausführen,
natürliche Anschlussgedanken erlauben und jede Gesprächsantwort mit einer Frage
beenden. Die Frage wird vom Modell angefordert, nicht an den Text angehängt;
ausdrückliche Nutzerwünsche und exakte Ausgabeformate gehen vor. Der Antwortstil
funktioniert unabhängig von MAAT Style. Sind beide an, steuert Antwortstil den
Umfang und MAAT Style weiterhin Ton, Aufbau und Smileys. Ausgeschaltet entfällt
der Antwortstil-Prompt; MAAT Style nutzt wieder seine bisherigen Längenvorgaben.
Die Einstellungen gelten pro Profil ab der nächsten Antwort, auch nach Modell-
oder Sprachwechsel. Ein laufender Stream behält seinen Einstellungsstand.
Der Zusatzprompt wird pro Antwort ersetzt und gelangt nicht ins gespeicherte
Gespräch oder in Super Memory. Llama/ARM, GGUF Intel und die übrigen Modelle
verwenden denselben Prompt-Hook; Token-Streaming bleibt direkt erhalten.

**MAAT Style** bietet die vollständige Einstellungs-Auswahl des lokalen
Web-Core-Moduls `backend/maat_style.py`, mit deutschen und englischen Prompts:

| Einstellung | Auswahl | Standard |
| --- | --- | --- |
| Grundton | Sachlich, Freundlich, Begeistert, Wissenschaftlich, Mentor, Philosophisch | Freundlich |
| Ton automatisch anpassen | An / Aus | An |
| Einstieg / Anrede | Direkt, Abwechslungsreich, Warm, Persönlich | Abwechslungsreich |
| Absatzdichte | Kompakt, Normal, Luftig | Normal |
| Überschriften | Keine, Einfach, Ausdrucksvoll | Einfach |
| Listen | Automatisch, Keine, Aufzählungspunkte, Nummeriert | Automatisch |
| Emojis · 🙂 ✨ | Keine, Wenige, Viele | Wenige |
| Klassische Smileys · `:) :D ^^ xD ;)` | Keine, Wenige, Viele | Keine |
| Reine Begrüßungen kurz halten | An / Aus | An |
| Stil-Diagnose anzeigen | An / Aus | Aus |

Die automatische Erkennung kann den Grundton je nach Nachricht ersetzen; für
einen festen Ton den Automatik-Haken ausschalten. Die Absatzdichte steuert nur
Absätze und Leerzeilen. Bei aktivem **Antwortstil** kommen Länge, Ausführlichkeit
und Anschlussfragen ausschließlich von dort. Nur ohne Antwortstil nutzt MAAT
Style seine aufgabenabhängigen Wort-Richtwerte. Es gibt keine Decoder-Sperre oder
zweite Modellanfrage. Reine Begrüßungen dürfen unabhängig vom Tokenziel kurz sein;
„Hallo, hilf bei Python“ wird nicht als bloße Begrüßung eingestuft.

**Antworten formatieren** berücksichtigt ausgeschaltete Überschriften und Listen.
Die Style-Regeln wirken auch auf Deutsch einzeln; vorher wurden dort Einstieg,
Absatzdichte, Überschriften und Listen durch allgemeine Hinweise ersetzt.
Ausdrückliche Nutzerwünsche, exakte Ausgabeformate, Spielrolle und erforderliche
MAAT-Reflexion bleiben erhalten. Der Original-Cleanup zum Abschneiden routinemäßiger
Einstiege wird im RPG nicht nachträglich auf den gestreamten Text angewendet;
die Einstiegsauswahl steuert den Prompt, sodass Anzeige, TTS und Speicher denselben
Text erhalten und keine legitimen Wörter verschwinden.

Die **Stil-Diagnose** bietet einen lokalen Beispieltext-Test ohne Modellaufruf.
Sie zeigt erkanntes Anliegen, Grundton und effektiven Ton sowie die übrigen
Einstellungen. Der Beispieltext wird nicht gespeichert. Im laufenden Spiel
protokolliert sie nur diese abgeleiteten Stilwerte im lokalen Worker-Diagnoselog,
keine Eingaben, Antworten oder Prompts. Die Erkennung ist eine Wort-Heuristik,
keine Diagnose der Person und keine Anzeige interner Modellgedanken.

Die Auswahl wirkt bei aktiviertem MAAT Style ab der nächsten Nachricht und wird
pro Profil gespeichert. Für ausschließlich klassische Smileys: Emojis auf Keine,
klassische Smileys auf Wenige oder Viele. Die Vorgaben gelten für eigenen
Antworttext, nicht für Code oder Zitate; sie steuern den Prompt, statt Zeichen
nachträglich zu erzwingen. Scrollen und Sprachwechsel verändern die Auswahl nicht.

Anti-Hallu beginnt erst nach Erzeugung und Prüfung mit der sichtbaren Ausgabe.
Es braucht keinen zusätzlichen Modellaufruf, kann aber wegen seiner heuristischen
Regeln auch eine richtige Antwort zurückhalten. Es ist keine externe Faktenprüfung.
Ausgeschaltet bleibt das direkte Token-Streaming erhalten. Ein abgelehnter
Antwortentwurf wird nicht vorgelesen und seine `save:`-Anweisungen werden nicht
als Erinnerungen übernommen. Esc bricht auch die gepufferte Erzeugung ab.

MAAT Thinking, Super Memory, Offline-Wikipedia und Sprachausgabe bleiben bei
ihren bestehenden Einstellungen. Der ältere `uncertainty_guard` wird durch die
neue PLP-Anti-Hallu-Anbindung ersetzt, damit nicht zwei Guards dieselbe Antwort
bearbeiten. `/plp`, `/plp status`, `/plp last` und `/uncertainty` zeigen den neuen
heuristischen Prüfbericht. `/emotion` berücksichtigt den neuen Schalter.

Reality verwendet die Uhr und Zeitzone des Computers, ohne Internetabfrage.
Der kurze Systemblock wird für jede Modellantwort neu aufgebaut und ersetzt
einen früheren Zeitblock. Er bleibt außerhalb des gespeicherten Chatverlaufs.
Er gilt auch bei ausgeblendetem Spielkontext und im Modus „Ich bin die KI“.
Der Zeitstempel der letzten Aktivität stammt ausschließlich aus dem bestehenden
Profilarchiv; gelöschte Einträge werden nicht in einem separaten Protokoll behalten.
Ohne nutzbaren Zeitstempel wird der vorherige Zeitpunkt als unbekannt markiert.
Die aktuelle Systemzeit dient auch dem optionalen Anti-Hallu-Guard als Beleg.
Der RPG-Port umgeht für Zeitfragen weder die normale Antwortgenerierung noch
Sprachausgabe, Abbruch oder Fortschrittszählung.

„Antworten formatieren“ gilt ab der nächsten Antwort. Während des Streams bleibt
Text direkt sichtbar; nach Abschluss wird nur die KI-Antwort formatiert, auch im
umgekehrten Spielmodus. Nachträgliche Plugin-Korrekturen ersetzen denselben Bereich.
Ausgeschaltet entfallen der Zusatzprompt und die Formatierung neuer Antworten.
Vorhandene Nachrichten werden nicht rückwirkend umgeschrieben. Code-Schreibweise,
Einrückung, Zahlen, Originaltext im Archiv und Erinnerungen bleiben erhalten.
Groß-/Kleinschreibung wird vom Modell angefordert, nicht blind nachbearbeitet.
Einfache LaTeX-Formeln in `$…$`, `$$…$$`, `\(…\)` oder `\[…\]` werden lesbar
dargestellt (z. B. Wurzeln, Brüche als Division, Hoch-/Tiefstellungen und griechische
Symbole); komplexe/unbekannte Befehle bleiben als Quelltext sichtbar.
Markdown-HTML wird nicht ausgeführt; Bilder und aktive Links werden nicht geladen.

## English

Open **Settings → Plugins**, the tab beside **General** inside the game window.
The previous Plugins buttons and separate plugin window have been removed.
Controls are saved per profile and apply from the next message without reloading
the model or restarting music.

| Plugin | Default | Effect |
| --- | --- | --- |
| Reply style | On · Normal | Four conversation styles with an editable token target and four independent conversation preferences. |
| Format replies | On | A short formatting prompt and native display of completed replies with Markdown tables, headings, lists, code and simple formulas. |
| MAAT Reality | On | Fresh local system date, weekday, time and UTC offset for each reply; the last retained activity timestamp when a chat archive is available. |
| Emotion detection | On | Existing keyword-based mood cues, now switchable with expanded English vocabulary. |
| PLP Anti-Hallu | Off | Prompt guidance and a heuristic whole-answer guard before display, speech and memory saves. |
| MAAT Style | Off | Adapts tone and structure; supplies its own length guidance only when Reply style is off. |
| MAAT Identity | Off | Reinforces the selected RPG role and honest boundaries; the model remains Maatis in the reversed perspective. |

**Reply style** offers **Short (40–100 tokens)**, **Normal (80–180)**,
**Chatty (150–300)** and **Very chatty (300–600)**. Normal is the default,
including existing profiles without saved preferences. Edit either bound between
20 and 2,000 tokens; bounds cannot cross. Selecting a style restores its preset
range. Tokens are pieces of text, not words. The range is always flexible prompt
guidance. **Develop substantive answers** additionally asks for relevant
explanations or examples approaching the lower target for substantial questions.
Greetings, thanks, trivial questions and already complete answers may stay short.
The checkbox starts off. Saved **Enforce minimum length** preferences
automatically use this new soft behavior.

The old EOS suppression is removed, including the GPT-OSS special case. There is
no hard minimum or automatic second request. Output/context caps are unchanged;
models may end naturally. Preferences apply per profile from the next reply.

A shared streaming guard stops sustained exact word, sentence and emoji loops
before further output hooks. It requires at least eight contiguous copies of a
motif (up to 160 characters), covering at least 40 symbol or 96 word characters.
It uses bounded memory, preserves ordinary text deltas and also runs when Reply
style is off. Fenced/inline code, Markdown quotations and recognized explicit
requests for literal repetition are exempt. This is a conservative heuristic,
not a detector of all semantic repetition. Already streamed portions may remain
visible. In the GUI, detection cancels the reply: speech stops, with no chat
progress, AI-development reward, archiving or Super Memory save for that reply.
Completed game events are retained. A bilingual notice explains the stop.

All four preferences start enabled: engage with the user's statements, develop
ideas, allow natural follow-up thoughts, and end every conversational reply with
a question. The model is asked for a question; one is never mechanically appended.
Explicit user requests and exact output formats take priority. Reply style works
without MAAT Style. With both enabled, Reply style controls length while MAAT
Style keeps tone, structure and smileys. Switching Reply style off removes its
prompt and restores MAAT Style's previous length guidance. Preferences are saved
per profile and apply to the next reply, including after model or language changes;
active streams keep their original snapshot. The transient prompt is replaced
each turn and stays out of stored dialogue and Super Memory. ARM and Intel GGUF
adapters share this hook with the other models, preserving direct streaming.

**MAAT Style** exposes the complete settings selection of the local Web Core
`backend/maat_style.py`, with matching German and English prompts:

| Setting | Choices | Default |
| --- | --- | --- |
| Base tone | Neutral, Friendly, Enthusiastic, Scientific, Mentor, Philosophical | Friendly |
| Adapt tone automatically | On / Off | On |
| Opening / address | Direct, Varied, Warm, Personal | Varied |
| Paragraph density | Compact, Normal, Airy | Normal |
| Headings | None, Simple, Expressive | Simple |
| Lists | Automatic, None, Bullets, Numbered | Automatic |
| Emojis · 🙂 ✨ | None, Few, Many | Few |
| Classic smileys · `:) :D ^^ xD ;)` | None, Few, Many | None |
| Keep greeting-only replies brief | On / Off | On |
| Show style diagnostics | On / Off | Off |

Automatic detection may override the base tone to match the message; switch it
off to fix a tone. Paragraph density governs layout only. With **Reply style**
enabled, length, elaboration and follow-up questions come from Reply style alone.
MAAT Style uses its own task-specific word guidance only when Reply style is off.
There is no decoder lock or second model request. Greeting-only replies may stay
brief regardless of the token target; “Hello, help with Python” is not classified
as a mere greeting.

**Format replies** respects disabled headings and lists. Every Style option now
affects the German prompt as well, replacing the former generic layout hints.
Explicit user requests, exact output formats, the RPG role and required MAAT
reflection remain authoritative. The original routine-opening cleanup is not
applied after streaming in the RPG: opening preferences guide the prompt, keeping
display, speech and storage consistent without deleting legitimate words.

**Style diagnostics** provides a local example-text test without a model call.
It displays detected intent, base/effective tone and other settings. Example text
is not saved. During play, only derived style values are written to the local
worker diagnostic log, never queries, answers or prompts. Detection uses keyword
heuristics; it neither diagnoses a person nor reveals internal model reasoning.

Preferences apply from the next message while
MAAT Style is enabled and are saved per profile. For classic smileys only, set
Emojis to None and Classic smileys to Few or Many. These are prompt instructions
for the model's own prose, not destructive edits to code or quotations. Scrolling
and switching languages do not change the saved choices.

Anti-Hallu delays visible output until generation and checking finish. It adds
no second model call, but its heuristics can withhold a correct answer; it is not
an external fact checker. Turning it off preserves direct token streaming.
Rejected drafts and their `save:` instructions do not reach speech or new memory
saves. Esc can cancel buffered generation too.

Existing MAAT Thinking, Super Memory, offline Wikipedia and speech settings stay
in their established menus. The previous uncertainty guard is disabled in favour
of this integration; existing `/plp` and `/uncertainty` commands show the new
heuristic report. `/emotion` respects the new switch.

Reality reads the computer clock and time zone without an internet request.
Its short system block is refreshed per reply, replaces stale snapshots and
stays outside stored chat history. It works with hidden game context and in
“I am the AI” mode too. Last activity comes only from the existing profile archive;
deletion is respected and missing timestamps stay unknown. There is no separate
activity log. The clock snapshot also provides evidence for the optional
Anti-Hallu guard. Time questions use normal model generation, speech,
cancellation and progression handling.

“Format replies” applies from the next reply. Text remains visible while streaming;
only the completed AI response is formatted, including reversed-role mode and
later plugin revisions. Off disables both the extra prompt and rendering of new
replies. Existing messages are not retroactively rewritten. Code case, indentation,
numbers, archived source text and memories stay intact. Correct capitalization is
requested from the model rather than applied as a destructive text transformation.
Simple LaTeX math delimited by `$…$`, `$$…$$`, `\(…\)` or `\[…\]` is rendered as
readable notation, including roots, fractions as division, scripts and Greek letters.
Unsupported commands remain visible as source. Raw HTML is inert; no images or
active links are loaded. There is no additional model call or rendering dependency.

## Port provenance — 2026-09-16

Adapted from the user-supplied MAAT Web Core modules; the RPG contains independent
local copies and never imports the other project's files at runtime:

| Original module | Original SHA-256 |
| --- | --- |
| `maat_plp_anti_hallu.py` | `e6d46ab0a36d5b20dda9301c516ea5cdfd03aafcba13bcf91b55cb945dd6417b` |
| `maat_style.py` | `b58d7edc268c9722404a7d08d6bf826f97e0e47eea822a1efb31c114880ad528` |
| `maat_identity.py` | `478a9761a03e6e84974b9cbd264c7af5b5e1e709b96e75f31f4e03e2c6f2844b` |
| `maat_reality_layer.py` | `992fa13d167d22f39515913ad99b66fa23ffd2e6a9e2f0927643c5745bb74ee2` |

The port retains the Anti-Hallu AHF/HRS scoring structure, style intent/tone
detection, and functional identity guidance. It adds DE/EN prompts and query
patterns, current-role awareness, per-profile defaults and per-turn snapshots.
Grounding uses only sources actually supplied to the model. Source words alone
are not treated as proof. Identity is injected transiently once per generation,
so context trimming and model switches cannot remove it permanently. No person
store, additional model calls or network lookup is introduced.

Tests: `tests/test_ai_plugins.py` covers switches, profile persistence, actual
menu wiring, language changes, role preservation, prompt removal, streaming,
guard cancellation and real temporary Super Memory stores. GUI captures in
`gui-preview/plugins-menu/` show both languages with default settings.
`tests/test_reality_layer.py` additionally checks clock refresh, UTC offsets,
daylight-saving changes, explicit reply-language requests, deletion, cancellation,
profile isolation and the clock/Anti-Hallu integration.
`tests/test_reply_formatting.py` covers actual Qt tables, code preservation,
formula fallbacks, streaming/replacement boundaries, disabled display, transcript
trimming and blocked external resources.
`tests/test_style_smileys.py` checks independent DE/EN prompt combinations,
per-turn changes, profile persistence, language changes and scroll protection.
`tests/test_reply_style.py` checks reply modes, both GGUF streaming routes,
per-turn replacement/removal, explicit reply language, MAAT Style compatibility,
range validation, profile isolation, persistence and wheel protection.
Reply-style implementation and bilingual previews: 2026-09-17.
