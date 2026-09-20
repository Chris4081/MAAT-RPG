# MAAT RPG · Level-up und Sieg

Eigene, prozedural erzeugte Klänge vom 20. September 2026, ohne externe Samples.

- **Aufstieg des Lichts** · `levelup.wav` · 8 Sekunden: aufsteigende Glockentöne, heller Abschluss, sanfter Nachhall.
- **Sieg der Resonanz** · `victory.wav` · 6 Sekunden: tiefer Impuls, kurze Tonfolge, warmer Schlussakkord.

Die MP3-Versionen ersetzen direkt `battle/sounds/levelup.mp3` und
`battle/music/victory.mp3` unter den RPG-Plugins. Menü- und Hintergrundmusik bleiben unverändert.
Der Generator liegt unter `tools/build_celebration_sounds.py` im Projektordner;
`manifest.json` enthält Herkunft, Pfade, Dauer, Pegel und Prüfsummen.

Technisch geprüft: MP3s vollständig dekodierbar, Dauer 8/6 Sekunden, Stereo 48 kHz,
keine Übersteuerung, leise ausklingende Enden. Hörtest im Spiel noch offen.

Original procedural cues, generated without external samples. Lossless previews above;
the game uses MP3 files at the existing paths. See the project source/license inventory.
