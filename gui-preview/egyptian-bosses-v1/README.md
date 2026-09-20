# Ägyptische Bossgrafiken · 19.09.2026

25 Kampagnenbosse plus 5 eigenständige Finalgegner. Boss 1–5 und alle Finalgrafiken bleiben unverändert. Für Boss 6–25 wurden 20 eigene Figuren und 200 Attacken-SVGs erstellt.

Die Grafiken erweitern direkt die vorhandenen bearbeitbaren SVGs. Kein Imagegen-Aufruf, keine rasterisierten Platzhalter. Gestaltungsauftrag: ägyptische Fantasy-Motive, klare unterschiedliche Silhouetten, transparente Hintergründe, 240×240-Koordinaten, bestehende Kontur-/Farbtokens und goldene Akzente auf dem dunkelblauen Kampfdesign. Die Motive sind stilisierte Fantasy, keine historischen Rekonstruktionen.

- `bosses.png`: sämtliche 25 Bossformen.
- `attacks.png`: die 20 neuen Standbilder mit ihrem normalen Angriff.
- `battle-08/18/25*.png`: gerenderte Kampfansichten mit der echten GUI-Komponente und Testwerten.
- `manifest.json`: Bossnummern, Motive und Asset-Pfade.

Dateien im Spiel: `gui/assets/combat/boss*.svg` und `gui/assets/combat/attacks/boss*-*.svg`.
Reproduzierbar mit `tools/build_boss_art.py`; Übersicht mit `tools/render_boss_gallery.py <Ordner>`.
Die gemeinsame Auswahl erfolgt in `gui.battle_arena.artwork_for`; diese wird auch von Demo, Kartenmarkern und Monsterkatalog verwendet. Spielstände, Bossnamen, Kampfwerte, Freischaltungen und Belohnungen werden nicht geändert. Der Monsterkatalog zeigt jetzt alle 25 nummerierten Bosse und 5 Finalformen, zusätzlich zu den 20 normalen Gegnertypen. Deutsch/Englisch verwenden dieselben Assets.

English: twenty new Egyptian fantasy silhouettes with all ten existing attack effects each. The first five bosses and five finale portraits remain intact. Combat, title demo, postgame map and level-50 bestiary share the canonical boss-number mapping. Attack poses return to the matching idle silhouette; existing sway and red hit feedback remain active.
