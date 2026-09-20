# Freigestellte Klassenporträts

Diese sechs RGBA-PNGs werden über `gui.hero_portrait.portrait_path()` in Kampf,
Demo, Klassenwahl, Seitenleiste, Charakteransicht und direkten Maatis-Porträts
verwendet. Der Spielhintergrund scheint durch; Treffer färben nur die Figur ein.

Die freigegebenen RGB-Originale bleiben eine Verzeichnisebene darüber erhalten.
Die Figuren wurden nicht neu gezeichnet: zusammenhängender äußerer Hintergrund
und die beiden offenen Ringe bei Magier/Priester wurden lokal freigestellt.
Innenfarben bleiben erhalten; nur die antialiasierten Außenkanten wurden vom
dunklen Hintergrund getrennt, damit beim Skalieren kein dunkler Saum entsteht.

Reproduzierbar mit `tools/prepare_class_portraits.py` vom Projektverzeichnis aus
(Pillow, NumPy und SciPy nur für dieses Entwicklungswerkzeug, nicht im Spiel).
Das Werkzeug ist auf die Originale mit 1254 × 1254 Pixeln abgestimmt.
`manifest.json` enthält die Prüfsummen der Originale und Ergebnisse.

Der zuvor versuchte eingebaute Bildgenerator lieferte RGB-Dateien mit gemaltem
Karomuster. Diese Varianten werden nicht verwendet. Das lokale Freistellen
wurde von Christof ausdrücklich freigegeben.
