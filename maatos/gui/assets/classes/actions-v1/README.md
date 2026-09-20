# Maatis · Klassenposen

120 RGBA-Ausschnitte aus den sechs bestätigten, vorhandenen Posenbögen.
Keine neu generierten Figuren. Die Quellen unter `gui-preview/class-action-sets-v1`
bleiben erhalten; `manifest.json` dokumentiert Ausschnitte, Fußanker und Prüfsummen.

Reproduzierbar mit `tools/prepare_class_actions.py` (Pillow/NumPy/SciPy nur beim
Entwickeln). Die 416-Pixel-Fläche enthält einen 320-Pixel-Körperrahmen und
48 Pixel freien Rand für überstehende Effekte. Der Renderer vergrößert diese
Fläche entsprechend, damit Körpergröße und Fußlinie beim Bildwechsel gleich bleiben.

19 Posen pro Figur werden im Kampf verwendet. `standard.png` ist der zusätzliche
Ausschnitt zur Kontrolle; im Ruhezustand nutzt das Spiel weiter das höher
aufgelöste Porträt aus `../transparent-v1`.
