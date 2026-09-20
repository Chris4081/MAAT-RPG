# Ägyptische Gegnerformen · 19. September 2026

Alle 20 normalen Gegnerformen wurden im bestehenden SVG-Stil neu gezeichnet.
Es sind ägyptisch inspirierte Fantasy-Motive für Terra, keine historischen Rekonstruktionen.

- `before-after.png`: acht Beispiele mit identischer Namensfarbe vor und nach dem Umbau.
- `enemies-and-attacks.png`: alle 20 Standbilder mit ihrem normalen Angriff.
- `battle-*.png`: echte Qt-Kampfoberfläche mit synthetischen Testwerten, ohne Laden eines Nutzerprofils oder KI-Modells.
- `before/`: gesicherte frühere Standbilder.
- `manifest.json`: SHA-256-Werte der 20 ersetzten Standbilder und 200 Attackenbilder.
- `before-hashes.json`: Ausgangszustand der Kampfgrafiken für den Abgleich.

Neue Motive umfassen Sphinx, Mumiengeist, Tempelwächter mit Chepesch, Uschebti,
Udjat-Amulett, Tempelfeuer, geflügelten Skarabäus, Uräusschlange, Nilgeist und
einen schlangenartigen Tempeldrachen. Die bestehenden Familiennamen, IDs,
deutschen/englischen Namen und Kampfregeln bleiben verwendbar.

Die gemeinsame Grafikzuordnung gilt für Zufallskämpfe, Arena, Dungeons, Demo,
Monsterkatalog und die entsprechenden Auswahlgrafiken im Kampfeditor.

## Reproduzieren

Im Verzeichnis `MAAT RPG.app/Contents/Resources/maatos`:

```sh
python3 tools/build_monster_art.py
QT_QPA_PLATFORM=offscreen python3 tools/render_monster_gallery.py /tmp/maat-enemies.png
```

Die Bildquellen liegen in `tools/egyptian_enemy_shapes.py`. Der Builder erzeugt
ausschließlich die 20 normalen Formen und deren jeweils zehn Angriffsbilder.
Die Attacken verwenden denselben Körper wie das jeweilige Standbild und die
bereits vorhandenen Effekte, Bewegung, Trefferanzeige und Rückkehranimation.

## Prüfung

34 Tests bestanden: `test_boss_art`, `test_monster_catalog`,
`test_monster_variety`, `test_minigame_monster_language`, `test_battle_arena`,
`test_terra_replay`, `test_demo_progression`.

Native macOS/Python-Qt-Prüfung mit isolierten Testprofilen. Zusätzlich wurden
sämtliche 220 neuen SVGs geladen und die Einbettung des richtigen Körpers in
jedes Attackenbild geprüft. Alle 359 anderen erfassten Kampfgrafiken sind
bytegleich geblieben, darunter die Boss-, Final- und Maatis-Grafiken.

`review.py` wiederholt den Assetabgleich und erstellt die Vergleichsbilder.
