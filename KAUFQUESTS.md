# Auftragsbrett ab Level 50

Der Basar hat neben den Vorräten ein Auftragsbrett. Über `/contracts` öffnet die GUI direkt diesen Bereich; im Terminal zeigt der Befehl den Katalog. Kaufen: `/contracts buy contract50_01` (IDs bis `contract50_25`).

Der Questbestand umfasst jetzt **148 unterschiedliche Definitionen**: 123 bisherige plus 25 einmalig kaufbare Aufträge. Wiederholungen einer Daily zählen nicht als zusätzliche Definitionen.

| Aufträge | Preis pro Auftrag | Ziel ab Kauf | Basis-EP | Gegenstände |
| --- | --- | --- | --- | --- |
| 10 Expeditionen | 500 Gold | 5 Siege oder 10 Chatnachrichten | 800 | 1 Heiltrank |
| 10 Prüfungen | 1.000 Gold | 12 Siege oder 25 Chatnachrichten | 1.800 | 2 Heiltränke, 1 Schutz-Siegel |
| 5 große Aufträge | 2.000 Gold | 30 Siege oder 50 Chatnachrichten | 4.000 | 3 Heiltränke, 2 Schutz-Siegel, je ein Sammeltitel |

Jeder Auftrag hat genau eines der beiden Ziele. Erzählerische Gesprächsideen sind frei; gezählt werden normale Chatnachrichten, ohne Bewertung ihres Inhalts. Befehle zählen nicht. Kampfaufträge zählen den tatsächlichen Siegzähler; Arena und Zufallskämpfe gehören dazu. Die Startdemo schreibt keine Siege ins Profil.

- Der Server prüft Level, Gold und bisherigen Besitz. Mehrfachkäufe sind ausgeschlossen.
- Alte Siege und Nachrichten zählen nicht rückwirkend. Ein beim Kauf gespeicherter Zählerstand bildet den Startpunkt.
- Mehrere gekaufte Aufträge können parallel laufen; eine neue Nachricht oder ein Sieg kann mehreren passenden Aufträgen Fortschritt geben.
- Aufträge haben kein Zeitlimit, erscheinen im Questlog und bleiben über Neustarts hinweg erhalten.
- Basis-EP bleiben für Kaufaufträge konstant. Bestehende Pfadboni kommen hinzu und werden vor dem Kauf angezeigt.
- Die fünf Titel sind Sammeltitel auf dem Auftragsbrett; sie ersetzen den bestehenden Leveltitel nicht.
- Kostenlose Quests und Dailys behalten ihre Freischaltungen.

Geprüft mit temporären Profilen: alle 25 Käufe und Abschlüsse, Level-/Goldgrenzen, doppelte Käufe und Belohnungen, gespeicherte Ausgangszähler, Neustart, Befehlsverdrahtung und GUI-Steuerung. Die bestehenden Shop-, Quest-, Daily- und Ablaufprüfungen bestehen ebenfalls. Vorschau: `gui-preview/contracts.png`.
