# GGUF (Intel) — Adapter 0.4.2

Die Modellseite zeigt genau einen Adapter: **GGUF (Intel)** auf x86-64
(macOS und Linux, einschließlich AMD64), auf Apple Silicon
**GGUF (ARM · Metal)** und auf Linux ARM **GGUF (ARM)**.
Der Worker wählt anhand seiner eigenen Hardware
erneut; ein aus einem anderen Rechner übernommener Profilwert erzwingt keinen
falschen Adapter. Modelle und Profilnamen bleiben erhalten.

Der Intel-Adapter verwendet weiterhin llama.cpp als Rechenbibliothek, besitzt
aber einen eigenen CPU-Lader. Es handelt sich nicht um eine neue
Inferenz-Engine oder einen nachgewiesenen universellen Geschwindigkeitsrekord.
Der vorhandene ARM-Lader nutzt auf Apple Silicon in Auto alle GPU-Layer,
Flash Attention sowie ausdrücklich KQV- und Operations-Offload über Metal.
Linux ARM verwendet die von seiner Bibliothek unterstützte Beschleunigung.

## Automatische Vorgaben

| Einstellung | GGUF (Intel) |
|---|---|
| Kontext | Standard 20.000; einstellbar bis 100.000 |
| Antwort-Threads | höchstens physische Kerne und höchstens 80 % der logischen Threads, mindestens 1 |
| Prompt-Threads | verfügbare logische Threads |
| Batch / Mikro-Batch | 256 / 128; Mikro-Batch 64 für Gemma 4 |
| GPU-Layer / KQV- / Operations-Offload | 0 / aus / aus |
| mmap / mlock | an / aus |
| Flash Attention | aus; an für die bestehende Gemma-4-Kompatibilität |
| Gewichts-Repacking | aus |

Repacking kann die spätere Generierung beschleunigen, verursacht aber
zusätzliche Arbeit und möglichen Speicherbedarf beim Laden. **Manuell**
bietet deshalb eine eigene Repacking-Option; ihr Standard ist aus. Bei
Aktivierung berücksichtigt die Speicherabschätzung eine zusätzliche Kopie
der Gewichte. Die bestehende 99-%-Grenze und die Speicherüberwachung bleiben.
Dies garantiert keine passende Modellgröße für jeden Rechner.

Der native Parameter heißt `use_extra_bufts`. Da der Python-Konstruktor in
der geprüften Version 0.3.34 diesen nicht als Argument anbietet, verwendet
`IntelLlama` für genau einen Konstruktoraufruf eine weiterleitende API-Referenz.
Sie verändert ausschließlich die frisch erzeugten Modellparameter.
Globale Funktionen, die bestehende Llama-Klasse und installierte Dateien
werden nicht verändert. Auf älteren Bibliotheken ohne diesen Parameter
bleiben die nativen Vorgaben aktiv und die GUI meldet die fehlende Steuerung.

## Plattformen

Das macOS-Paket enthält die portable und die AVX/AVX2/FMA/F16C/BMI2-Variante
einschließlich Apple Accelerate. Vor dem nativen Import erfolgt die
CPU-Prüfung; nicht unterstützte Befehle werden nicht erzwungen.

Unter Linux verwendet der Adapter das installierte llama-cpp-python.
Eine zusätzlich vorhandene `llama_cpp/lib/avx2/libllama.so` wird nur bei
passenden CPU-Flags ausgewählt. Andere Installationen behalten ihre
Bibliotheksauswahl, einschließlich deren eigener CPU-Dispatch-Funktion.
Die Optimierungsmöglichkeiten der installierten nativen Bibliothek bleiben
maßgeblich; der Adapter erzeugt keine fehlenden AVX- oder BLAS-Kernels.
CPU-Affinität und die physische CPU-Topologie werden unter Linux berücksichtigt.
Es gibt keine unbedingten macOS-Aufrufe im Linux-Ladeweg.

## Prüfstand

54 gezielte Tests unter x86-64/Rosetta bestanden:
Adapter-Auswahl, Intel-Parameter, lokale Konstruktorsteuerung ohne globale
Änderung, Modellwechsel, Prompt-Erhaltung, Streaming-Anbindung, Esc,
Speicherprüfung und deutsche/englische Bedienelemente.

Ein echtes `Meta-Llama-3.1-8B-Instruct-128k-Q4_0.gguf` wurde mit dem neuen
Adapter und 20.000 Kontext erfolgreich geladen und für eine kurze Ausgabe
verwendet: rund 7,9 Sekunden Gesamtlaufzeit, ungefähr 6,9 GiB Peak-RSS.
Der Test lief mit der portablen x86-64-Bibliothek unter Rosetta.
Dies ist kein Vergleich gegen den alten Adapter unter kontrollierten
Cachebedingungen und kein Benchmark auf einem echten Intel-Mac.

Ein echtes Qwen2.5-Coder-7B-Q4_0 streamte mit 20.000 Kontext sowohl über den
Intel-Adapter unter Rosetta als auch nativ über ARM/Metal erfolgreich.
Dabei wurde ein Fehler in der Dateiprüfung behoben: `split.count=0` bezeichnet
wie ein fehlendes Feld oder der Wert 1 eine einzelne GGUF-Datei; erst Werte
größer als 1 bezeichnen ein aufgeteiltes Modell.

Die Obergrenze 100.000 wurde bis zum Ladeaufruf getestet, ohne dafür einen
großen nativen Cache anzulegen. Modellfähigkeit und verfügbarer RAM begrenzen
den praktisch nutzbaren Kontext weiterhin. Ein zusätzlicher ARM-Llama-Test
bei 20.000 wurde wegen der strengeren freien RAM-Reserve des Testwerkzeugs
nicht gestartet; dies war kein Ladefehler des Adapters.

Linux-Hardware-Auswahl und Topologie werden in Tests simuliert.
Ein vollständiger Linux-Lauf sowie ein Test auf dem betroffenen Intel-MacBook
stehen noch aus. Diagnoseprotokolle nennen Adapter, native Bibliothek,
CPU-Funktionen und tatsächlich übernommene Modellparameter.

## English

The GUI shows **GGUF (Intel)** on x86-64, **GGUF (ARM · Metal)** on Apple
Silicon and **GGUF (ARM)** on Linux ARM.
The Intel adapter has a dedicated CPU loading path, physical-core-aware thread
defaults, memory mapping and repacking disabled by default. Manual mode can
enable repacking, with its possible memory cost included in the estimate.
Context defaults to 20,000 tokens and can be set up to 100,000, subject to
model support and memory checks. Apple Silicon explicitly uses full GPU
offload, Flash Attention and KQV/operation offload through Metal.
Existing chat templates, memories, streaming
and cancellation are preserved.

The macOS installer includes compatible and AVX2-optimized native libraries.
On Linux, the adapter uses the installed llama-cpp-python and respects CPU
affinity. Real Llama 8B inference was verified under Rosetta and Qwen 7B chat
streaming on both adapters; native Intel performance
and a complete Linux run still require testing.
