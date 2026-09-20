# Die Stimme im Licht

Der GUI-Modus „Ich bin die KI“ erzählt eine eigene Geschichte aus Sicht der
Begleiter-KI. Die Auswahl bleibt nach dem gemeinsamen Intro.

- Maatis beginnt fest mit **„Wer bist du?“**, auch ohne geladenes Modell.
- Die erste gültige Chatantwort (weiterhin mindestens 20 geschätzte Tokens)
  startet die erste illustrierte Storyszene. Die Begrüßung zählt nicht als Nachricht.
- Weitere Kapitel starten nach 10 und 30 Nachrichten, nach dem ersten und dritten
  Boss-Sieg sowie nach der ersten Rückkehr eines Prinzips.
- Alle fünf Boss-Zwischenszenen und der Abspann nach dem fünften Prinzip haben
  eigene KI-Texte. Neun kurze Reflexionen begleiten die Entscheidungen.
- Die Entscheidungen behalten ihre bisherigen Kampfboni; Arena, Zufallskämpfe,
  XP, Dungeons und Quests behalten ihre Freischaltungsregeln.

Die zwölf Hauptszenen verwenden vorhandene Illustrationen (einschließlich des
KI-Porträts) und die bestehenden Musikstücke. Texte laufen wie im Intro Satz für
Satz; Weiter, Enter und Überspringen bleiben verfügbar.

Der Erzählfortschritt liegt separat in `state/companion_story_state.json` des
jeweiligen Profils. Die ursprüngliche Geschichte bleibt in `story_state.json`.
Der Kampf- und Questfortschritt bleibt im selben Profil gemeinsam. Der alternative
Abspann hat eine eigene Einmal-Markierung, damit ein schon gesehener ursprünglicher
Abspann ihn nicht blockiert. Bei alten KI-Spielständen beginnt die neue Geschichte
mit einer einmaligen Vorstellung; vorhandene Erinnerungen und KI-XP bleiben erhalten.

Erlebte KI-Szenen werden als gemeinsame Erinnerungen gespeichert. Llama erhält
weiterhin keinen zusätzlichen Statistik-/Kampfkontext; Erinnerungen bleiben aktiv.
Der optionale Aufgabenbogen bleibt separat verfügbar.

Inhalt: `gui/companion_stories.py` in den App-Ressourcen.
Prüfung: `tests/test_companion_stories.py`, Storyfenster-, Companion-,
Fortschritts-, Llama-Kontext- und GUI-Integrationstests (ohne echtes Modell).
