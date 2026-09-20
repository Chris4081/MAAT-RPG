# TinyLlama GGUF · Deutsch / English

## Deutsch

TinyLlama verwendet die vorhandenen **GGUF (Intel)**- und **GGUF / ARM**-Adapter.
Wähle eine lokale Chat-GGUF über **KI & Modelle → Modell aus Pfad wählen**.
Die Adapterauswahl folgt der Hardware; es wird keine zusätzliche Laufzeit und
kein Modell automatisch heruntergeladen.

Die Erkennung berücksichtigt GGUF-Metadaten und Dateiname. TinyLlama wird als
eigene Chat-Familie erkannt, behält aber die sparsamen Llama-Regeln: kein
zusätzlicher Spiel-/Kampfkontext, höchstens drei abgerufene Erinnerungen und
ein kurzer Offline-Wiki-Auszug. MAAT-Rolle, Sprache und Antwortstil bleiben
über die vorhandenen gemeinsamen Generierungs-Hooks erhalten.

Eine eingebettete `tokenizer.chat_template` hat immer Vorrang. Fehlt sie und
identifizieren Metadaten oder Dateiname eindeutig **TinyLlama Chat v1.0**,
verwendet das RPG dessen offizielle Vorlage mit `<|system|>`, `<|user|>`,
`<|assistant|>` und `</s>`. Andere TinyLlama-Varianten ohne Vorlage erhalten
eine verständliche Fehlermeldung statt stillschweigend Llama-2-Formatierung.
Für die TinyLlama-Vorlage stoppen native Stop-Sequenzen auch vor einer neu
generierten Sprecherrolle. Die Ausgabe wird weiter direkt gestreamt und
nicht nachträglich verdoppelt oder gepuffert.

**TinyLlama 1.1B Chat v1.0 ist ursprünglich für 2.048 Kontext-Tokens ausgelegt.**
Dieser Bereich umfasst Eingabe und Ausgabe. Stelle für dieses Modell zunächst
2.048 ein; ein höherer Wert garantiert keine zuverlässige Erweiterung. Viele
Plugins, lange Systemvorgaben oder Nachrichten können dieses kleine Fenster
schnell füllen. Das RPG verändert globale Kontext-Vorgaben (20.000 / maximal
100.000), eigene Ladeeinstellungen oder gespeicherte Unterhaltungen nicht.
Bei langen Gesprächen entsprechend weniger vorherige Nachrichten wählen.

Geprüft: Erkennung, offizielle Rollenformatierung, Ersatzvorlage, Vorrang eigener
Vorlagen, klare Fehler, Entladen bei Fehlern, Stop-Parameter, beide Adapter,
einmalige Streaming-Ausgabe und Erhalt des Antwortstil-Prompts. Die Tests nutzen
den echten Jinja-Formatter und die Chat-Streaming-Konvertierung von llama-cpp-python
mit kontrollierten Modell-Tokenfolgen. Keine Aussage über Antwortqualität oder
Leistung auf einem echten TinyLlama-GGUF; hierfür wurde kein Modell heruntergeladen.

## English

Open a local chat GGUF through **AI & models → Choose model from path**.
TinyLlama uses the existing hardware-selected Intel or ARM GGUF adapter.
No extra runtime or model download is introduced.

GGUF metadata and filenames identify the TinyLlama chat family. It retains
Llama's compact context rules: no extra game/battle context, at most three
recalled memories, and a short offline-Wikipedia excerpt. RPG role, reply
language and Reply style continue through the shared generation hooks.

An embedded chat template always wins. Only clearly identified **TinyLlama
Chat v1.0** exports without one receive the official v1.0 fallback. Unknown
base/chat variants without templates fail clearly rather than receiving
Llama-2 formatting. Native stops prevent a simulated next speaker in the
TinyLlama role format; direct token streaming remains intact.

**TinyLlama 1.1B Chat v1.0 originally supports 2,048 context tokens**, including
input and output. Start at 2,048; larger settings do not guarantee a reliable
extension. Long prompts, numerous plugins and chat history can fill this small
window quickly. Global 20,000/default and 100,000/maximum preferences, manual
settings and stored conversations are unchanged. Use fewer previous messages
for longer conversations.

Tests use the real llama-cpp-python Jinja formatter and chat-stream conversion
with controlled model output, on the development runtime and bundled Intel
runtime under Rosetta. No real TinyLlama weights were loaded; answer quality
and native Intel performance have not been measured.

## Sources · checked 2026-09-17

- [Official TinyLlama Chat v1.0 tokenizer and chat template](https://huggingface.co/TinyLlama/TinyLlama-1.1B-Chat-v1.0/blob/main/tokenizer_config.json)
- [Official model configuration and context length](https://huggingface.co/TinyLlama/TinyLlama-1.1B-Chat-v1.0/blob/main/config.json)
- [TinyLlama project](https://github.com/jzhang38/TinyLlama)

The fallback template is extracted from the Apache-2.0 TinyLlama model repository.
See [attribution](../packaging/licenses/TINYLLAMA-NOTICE.md) and the
[included license](../packaging/licenses/Apache-2.0.txt).
Regression tests: `tests/test_tinyllama.py`.
