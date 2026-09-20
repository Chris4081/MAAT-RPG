# Offline-Wikipedia im MAAT-RPG

Unter **Einstellungen → Offline-Wikipedia → ZIM-Datei wählen …** eine lokale `.zim` auswählen. Der Pfad wird im aktuellen Spielprofil gespeichert. Die große Datei bleibt am gewählten Ort und wird weder kopiert noch hochgeladen. Mit **Entfernen** wird nur die Auswahl gelöscht.

Das frühere Terminal-Plugin `Wiki_Fetcher` wurde durch `offline_wiki` ersetzt. Seine alte Plugin-ID ist deaktiviert, damit keine zusätzliche alte Mod-Kopie geladen wird.

Ohne ausgewählte Datei bleibt die Funktion inaktiv. Es gibt keine Online-Abfragen und keinen Rückfall auf die frühere Online-Cache-Datenbank.

- **Offline-Suche testen**: Begriff eingeben, Ergebnis direkt in den Einstellungen lesen.
- **Quelle im Chat**: Über dem Chat steht der Artikeltitel des Auszugs, der für diese Antwort an die KI-Anfrage angehängt wurde. Der Tooltip zeigt den übergebenen Auszug. Bei fehlendem Auszug erscheint eine entsprechende Meldung. Das zeigt die bereitgestellte Quelle, garantiert aber nicht, dass das Modell sie korrekt verwendet.
- **Automatisch**: Übernimmt die vollständigen Wortregeln der ursprünglichen MAAT-Offline-Wiki-Erweiterung: Frageformen, Stopwörter, Namen, Pluralformen, bekannte Tippfehler, Einwohnerfragen, Vergleiche, Ortsrouten, Musik- und Kreativanfragen, MAAT-Wert-Fragen und die ursprünglichen Themenzuordnungen. Die zusätzlichen RPG-Ortsfragen („Wo liegt …?“) bleiben erhalten. Die Erkennung sucht in der aktuellen Nutzernachricht und entfernt eingebettete Testprotokolle. Suchheuristiken können auch einen unpassenden Begriff oder Treffer wählen.
- **Kontextgrenzen**: Llama erhält höchstens einen Treffer mit 400 Zeichen Artikeltext. Bei Vergleichen bekommen andere Modelle bis zu zwei Treffer mit zusammen maximal 1.000 Zeichen Artikeltext; der gesamte Wiki-Block bleibt auf 1.800 Zeichen begrenzt. Wiki-Wissen ist separat vom Spielkontext schaltbar und wird nur der aktuellen Modellanfrage hinzugefügt, nicht im Gespräch angesammelt.
- **/wiki Pyramide**: manuell einen Artikel nachschlagen; maximal 1.400 Zeichen Artikeltext.
- **/wiki status**: Dateiauswahl anzeigen.
- **/wiki cache**: bis zu 24 zuletzt lokal gelesene Artikel der aktuell ausgewählten ZIM anzeigen. Dieser Sitzungscache wird bei Dateiwechselsuche verworfen.
- **/wiki zim /Pfad/Datei.zim**: Dateipfad auch im Terminal setzen.
- **/wiki zim clear**: Auswahl entfernen.

Bei fehlender, beschädigter oder nicht erreichbarer Datei zeigt der manuelle Suchtest eine Fehlermeldung. Ohne Volltextindex funktioniert weiterhin die Suche nach einem genauen Artikeltitel. Automatische Suchen ohne Treffer ergänzen keinen Kontext; `/wiki debug once` zeigt die nächste Diagnose.

Die optionale Bibliothek `libzim` muss im selben Python installiert sein, das das Spiel startet:

```sh
python3 -m pip install -r requirements-wiki.txt
```

Technische Grundlage: [openZIM Python Reader](https://python-libzim.readthedocs.io/en/latest/api_reference/libzim.reader/) und [Such-API](https://python-libzim.readthedocs.io/en/latest/api_reference/libzim.search/). Die Umsetzung orientiert sich an `maat_offline_wiki.py` aus der MAAT-Textgen-Erweiterung; sie benötigt diese Erweiterung zur Laufzeit nicht.

Artikel stammen aus dem gewählten Archiv und entsprechen dessen Stand und Lizenzangaben. Die Ausgabe nennt Archiv und Artikel über eine lokale `zim://`-Quellenkennung; sie öffnet keinen Online-Link. Die Recherche kann bei freien oder mehrdeutigen Fragen danebenliegen. `/wiki <genauer Artikeltitel>` ermöglicht eine gezielte Suche.


## MAAT-Bewertungen mit Wiki-Grundlage

Bei „Berechne den MAAT-Wert von **Mona Lisa**“ wird der Artikel **Mona Lisa** gesucht. Die ursprüngliche Frage bleibt für die KI erhalten. Unterstützt werden unter anderem `MAAT-Wert`, `Maatwert`, `MAAT_Wert`, `MAAT-Score`, `MAAT value`, `MAAT-Bewertung`, `MAAT-Analyse`, `Ma’at-Wert` und „Bewerte … nach MAAT“, auch mit umgestelltem Satzbau wie „Berechne für Mona Lisa den MAAT-Wert“.

Titel in Anführungszeichen bleiben ganz: „Krieg und Frieden“ wird als ein Werk gesucht. Zwei getrennt zitierte Titel können zwei Suchbegriffe ergeben; Llama erhält weiterhin maximal einen Treffer mit 400 Zeichen Artikeltext. Die Großschreibung im Artikel wird bei erfolgreicher Suche aus der ZIM übernommen.

Das Wiki liefert Sachinformationen zum Gegenstand. Eine daraus abgeleitete MAAT-Bewertung ist eine Einschätzung der KI, kein in Wikipedia gemessener MAAT-Wert. Nicht jeder Gegenstand oder jede Formulierung führt zu einem passenden Archivtreffer.
