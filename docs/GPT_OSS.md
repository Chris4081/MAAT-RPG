# GPT-OSS im MAAT RPG / GPT-OSS in MAAT RPG

## Deutsch

Die Entwicklungsfassung unterstützt GPT-OSS-GGUFs zusätzlich zu den bisherigen
Modellfamilien. Ziel dieses Ausbaus ist GPT-OSS 20B. Wähle die lokale Datei unter
**Einstellungen → KI & Modelle → Modell aus Pfad wählen …**. Die Modellfamilie
wird automatisch aus den GGUF-Metadaten erkannt. Ein Download oder API-Schlüssel
ist nicht erforderlich, wenn die passende GGUF-Datei bereits vorhanden ist.

- Apple Silicon verwendet den bisherigen GGUF-/Metal-Adapter; Intel verwendet
  GGUF (Intel). Die Hardware-, Speicher- und manuellen Einstellungen bleiben aktiv.
- Kontext: weiterhin standardmäßig 20.000, maximal 100.000 Tokens. Die tatsächlich
  nutzbare Größe hängt auch von Modell, Quantisierung und freiem Speicher ab.
- GPT-OSS benötigt die eingebettete **Harmony-Chatvorlage**. MAAT-Anweisungen,
  Spielsprache, optionale Wiki-Auszüge und Erinnerungen werden als
  Entwickleranweisungen übernommen. Alte interne Analysen werden nicht erneut geladen.
- **Thinking-Modus aus:** niedrige Denkstufe (`low`). **An:** mittlere Denkstufe
  (`medium`). GPT-OSS unterstützt kein vollständiges Abschalten dieses Denkprozesses.
  Der getrennte Schalter **MAAT Thinking** behält seine bisherige Funktion.
- Nur der Kanal `final` wird gestreamt, vorgelesen und an die Chat-Plugins übergeben.
  Analyse, Werkzeugaufrufe und Harmony-Steuerzeichen bleiben verborgen. Es werden
  keine modellgesteuerten Werkzeuge aktiviert.
- Esc bricht auch die Analyse ab. Die vorhandene Regel gilt weiter: kein
  Nachrichtenpunkt, keine Chat-EP und kein neuer Erinnerungseintrag für den Abbruch.
- Ist der Kontext voll oder entsteht innerhalb des Tokenlimits keine fertige
  Antwort, wird ein Fehler gemeldet; es wird kein Analysentext als Antwort ausgegeben.

Für Installationen aus dem Quellcode ist `llama-cpp-python==0.3.34` vorgesehen,
wie bereits in den gebündelten macOS-Laufzeiten. Die Entwicklungsänderung allein
ersetzt keinen bereits erstellten macOS-Installer.

## English

The development build adds GPT-OSS GGUF support, targeting GPT-OSS 20B. Choose
your local file in **Settings → AI & Models → Choose model from path …**. Its
family is detected from GGUF metadata; no API key is needed for local inference.

- Apple Silicon keeps the GGUF/Metal adapter; Intel keeps GGUF (Intel), including
  existing hardware detection, memory guards and manual controls.
- Context remains 20,000 tokens by default, with a 100,000-token setting limit.
  Actual capacity depends on the model, quantization and available memory.
- The embedded **Harmony template** preserves MAAT instructions, reply language,
  optional offline Wiki excerpts and memories as developer instructions. Previous
  internal analyses are excluded from subsequent chat history.
- **Thinking mode off** selects `low` reasoning effort; **on** selects `medium`.
  This does not fully disable GPT-OSS reasoning. **MAAT Thinking** remains a
  separate setting. Only final answers are streamed, spoken and sent to plugins.
- Esc cancels analysis as well as answers. Existing cancellation rules continue
  to exclude cancelled turns from chat progress, XP and new memory saves.
- Context exhaustion or a missing final answer produces an error instead of
  exposing analysis. Model-driven tool execution is not enabled.

Source installations use `llama-cpp-python==0.3.34`, matching the bundled macOS
runtimes. Existing installer files are not changed by this source update.

## Tests / Tests

Deutsch: Die Protokolltests nutzen kleine, im Projekt geschriebene Testvorlagen
und kontrollierte Tokenfolgen. Sie prüfen beide Rollen-/Token-Schreibweisen,
Deutsch und Englisch, Erinnerungen, Streaming, Abbruch und Kontextgrenzen.
Die Originalvorlage wird beim Spielen aus der gewählten GGUF gelesen.
Die Tests laden kein Modell und ersetzen keine Prüfung mit einer echten GGUF.

English: Protocol tests use small project-written synthetic templates and
controlled token sequences. They cover both role/token spellings, German and
English, memories, streaming, cancellation and context limits. During gameplay,
the template comes from the selected GGUF. These tests do not load model weights
or replace testing with an actual GGUF.

The GPT-OSS handler uses llama.cpp's native `generate()` API because a generic
completion helper may treat a Harmony message boundary as the end of the entire
answer. Native sampling and prefix-cache reuse stay in llama.cpp.

Reference: [OpenAI Harmony format](https://developers.openai.com/cookbook/articles/openai-harmony).
