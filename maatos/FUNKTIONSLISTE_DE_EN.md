# MAAT-RPG / MAAT-OS Funktionsliste

Stand: 10.04.2026

Diese Datei sammelt die sichtbaren Funktionen, Systeme und Kommandos des aktuellen MAAT-RPG- und MAAT-OS-Builds in Deutsch und Englisch.

## 1. Kernfunktionen / Core Features

| Deutsch | English |
|---|---|
| Zweisprachiger Start von MAAT-OS Loader und MAAT-RPG | Bilingual startup for the MAAT-OS loader and MAAT-RPG |
| Sprachwahl beim Start und im Menü | Language selection at startup and in the menu |
| Sprachumschaltung auch für Loader, Modellwahl, Intro, HUD und Systemmeldungen | Language switching also covers loader, model selection, intro, HUD, and system messages |
| Titelbildschirm `Version 0.2` mit Enter-Schritt | `Version 0.2` title screen with Enter step |
| Persistenter Spielstand in `Application Support` | Persistent save state in `Application Support` |
| Lokales Modell-Setup mit Modell-Auswahl und Downloader | Local model setup with model selection and downloader |
| Modell-Downloader mit Resume-/Prüf-Logik | Model downloader with resume and verification logic |
| Architekturgetrennte Setup-Pfade für Intel und Apple Silicon | Architecture-specific setup paths for Intel and Apple Silicon |
| Say-TTS mit Sprach-Standardstimmen (`Anna` / `Samantha`) | Say-TTS with language-specific default voices (`Anna` / `Samantha`) |
| Musiksystem für Menü, Intro und Kämpfe | Music system for menu, intro, and battles |
| Plugin-Architektur mit Command Router | Plugin architecture with command router |
| DE/EN-Hilfetexte und lokalisierte Plugin-Befehle | DE/EN help texts and localized plugin commands |
| Mac-Setup für Intel und Apple Silicon vorbereitet | Mac setup prepared for Intel and Apple Silicon |

## 2. Gameplay-Systeme / Gameplay Systems

| Deutsch | English |
|---|---|
| Geführte Demo-Kämpfe ohne spielerischen Vorteil | Guided demo battles with no gameplay advantage |
| Guide-Kämpfe mit Erklärung für `/fight`, `/fightboss` und `/fightfinal` | Guide battles with explanations for `/fight`, `/fightboss`, and `/fightfinal` |
| Zufallskämpfe nach der Einführung | Random battles after the introduction |
| Boss- und Finalbosskämpfe mit Auren, Charge und Spezialangriffen | Boss and final boss fights with auras, charge, and special attacks |
| Boss-HUD mit Aura, Phase, Spezialname und Charge-Anzeige | Boss HUD with aura, phase, special name, and charge display |
| Phase-2-System für späte Bosse | Phase-2 system for later bosses |
| Resonanz-System mit `MAAT Impuls` | Resonance system with `MAAT Impulse` |
| Fokus-System mit Heilung und Schild | Focus system with healing and shield |
| Schwachstellen-System pro Runde | Per-turn weakness system |
| Tränke und Schutz-Siegel im Shop | Potions and warding sigils in the shop |
| Schutz-Siegel aktivieren Startschild in echten Kämpfen | Warding sigils grant a starting shield in real battles |
| Kampf-Erfolge und Kampfanalyse | Combat achievements and battle analysis |
| Pfadabhängige Kampfmodifikatoren und Belohnungen | Path-dependent combat modifiers and rewards |
| Pfadprofil, Rang und Motiv für Maatis | Path profile, rank, and motive for Maatis |
| Story-Entscheidungen mit späteren Konsequenzen | Story choices with later consequences |
| Journal und Boss-Codex | Journal and boss codex |
| Quests mit pfadabhängigen Bonusbelohnungen | Quests with path-dependent bonus rewards |
| Dungeon-Systeme (`60`, `500`, `1000`) | Dungeon systems (`60`, `500`, `1000`) |

## 3. Story- und Weltfunktionen / Story and World Features

| Deutsch | English |
|---|---|
| Cinematic Intro für MAAT-RPG | Cinematic intro for MAAT-RPG |
| Hauptstory mit Zwischenakten und inneren Reflexionen | Main story with interludes and inner reflections |
| Entscheidungsszenen mit mehreren Antwortpfaden | Choice scenes with multiple answer paths |
| Mehrsprachige Story-Szenen und Journal-Einträge | Multilingual story scenes and journal entries |
| Reaktive Welt auf Basis des Pfadprofils | Reactive world based on the path profile |
| Boss-Reaktionen auf Maatis’ Weg | Boss reactions to Maatis’ path |
| Beziehungsanzeige zwischen Maatis und MAAT-KI | Relationship display between Maatis and MAAT-KI |
| Pfadprofil entwickelt Titel, Rang und Motiv aus Entscheidungen | Path profile develops title, rank, and motive from decisions |
| Konsequenznetz zwischen Story, Kampf, Journal und Rewards | Consequence network linking story, battle, journal, and rewards |
| Lore-, Origin- und Identitätsansichten | Lore, origin, and identity views |

## 3.1 MAAT-OS und Systemfluss / MAAT-OS and System Flow

| Deutsch | English |
|---|---|
| App-Loader mit Sprachwahl vor dem eigentlichen Spiel | App loader with language selection before the actual game |
| MAAT-RPG-Menü mit Musik, Titelbildschirm und Progress-Anzeige | MAAT-RPG menu with music, title screen, and progress display |
| Startdiagnose für Python, Backends und Modellordner | Startup diagnostics for Python, backends, and model folders |
| Soft-Reset des Gesprächskontexts nach Demo- und Testkämpfen | Soft reset of conversation context after demo and test battles |
| Saubere Trennung zwischen Chat-Kontext und Kampf-Kontext | Clean separation between chat context and battle context |
| Lokalisierte Ladebalken und Startmeldungen | Localized loading bars and startup messages |

## 4. Spiel- und Systemkommandos / Game and System Commands

### 4.1 Basis und Navigation / Base and Navigation

| Kommando | Deutsch | English |
|---|---|---|
| `/help` | Zeigt alle Kommandos. | Shows all commands. |
| `/h` | Alias für `/help`. | Alias for `/help`. |
| `/hilfe` | Alias für `/help`. | Alias for `/help`. |
| `/clear` | Leert den Bildschirm. | Clears the screen. |
| `/cls` | Alias für `/clear`. | Alias for `/clear`. |
| `/exit` | Beendet das Programm. | Exits the program. |
| `/quit` | Alias für `/exit`. | Alias for `/exit`. |
| `/menu` | Zeigt das MAAT-RPG-Startmenü. | Shows the MAAT-RPG start menu. |
| `/motivate` | Gibt eine motivierende Zeile aus. | Gives you a motivational line. |
| `/evo` | Zeigt den Status der Self-Evolution-Engine. | Shows the self-evolution engine status. |

### 4.2 Story, Journal und Identität / Story, Journal, and Identity

| Kommando | Deutsch | English |
|---|---|---|
| `/storyreset` | Setzt den Story-Fortschritt zurück. | Resets the story progress. |
| `/journal` | Zeigt Maatis bisherigen Weg und seine Entscheidungen. | Shows Maatis’ path so far and his decisions. |
| `/whoismaat` | Zeigt, wer MAAT bzw. Maatis ist. | Shows who MAAT / Maatis is. |
| `/origin` | Zeigt die Ursprungsgeschichte. | Shows the origin story. |
| `/lore` | Zeigt Lore und Hintergrundwelt. | Shows lore and background worldbuilding. |
| `/maatbond` | Zeigt die aktuelle Beziehung zu MAAT-KI. | Shows the current bond with MAAT-KI. |
| `/rpgdemo` | Startet das Cinematic-Intro. | Starts the cinematic intro. |

### 4.3 Kampf, Fortschritt und Shop / Battle, Progress, and Shop

| Kommando | Deutsch | English |
|---|---|---|
| `/fight` | Startet einen geführten MAAT-Testkampf. | Starts a guided MAAT test battle. |
| `/fightboss` | Startet einen geführten Boss-Testkampf. | Starts a guided boss test battle. |
| `/fightfinal` | Startet einen geführten Finalboss-Testkampf. | Starts a guided final boss test battle. |
| `/xp` | Zeigt deinen aktuellen Level- und XP-Status. | Shows your current level and XP status. |
| `/shop` | Öffnet den MAAT-RPG-Laden. | Opens the MAAT-RPG shop. |
| `/shop buy potion <n>` | Kauft Heiltränke. | Buys healing potions. |
| `/shop buy sigil <n>` | Kauft Schutz-Siegel. | Buys warding sigils. |
| `/usepotion` | Benutze einen Heiltrank. | Use a healing potion. |
| `/battletest` | Führt einen stabilen Battle-Core-Selbsttest aus. | Runs a stable battle-core self-test. |

### 4.4 Quests und Erfolge / Quests and Achievements

| Kommando | Deutsch | English |
|---|---|---|
| `/quests` | Zeigt verfügbare, aktive und abgeschlossene Quests. | Shows available, active, and completed quests. |
| `/quest` | Quest annehmen oder Details anzeigen. | Accept a quest or show details. |
| `/quest accept <id>` | Nimmt eine Quest an. | Accepts a quest. |
| `/quest info <id>` | Zeigt Quest-Details und Pfadbonus. | Shows quest details and path bonus. |
| `/erfolge` | Zeigt deine freigeschalteten Erfolge. | Shows your unlocked achievements. |
| `/ach` | Zeigt emotionale / narrative Achievements. | Shows emotional / narrative achievements. |

### 4.5 Dungeons und Feldtests / Dungeons and Field Tests

| Kommando | Deutsch | English |
|---|---|---|
| `/dungeon60` | Betritt Dungeon 60. | Enters Dungeon 60. |
| `/d500` | Betritt Dungeon 500. | Enters Dungeon 500. |
| `/d1000` | Betritt Dungeon 1000. | Enters Dungeon 1000. |
| `/test_fields` | Testet oder zeigt die MAAT-Felder. | Tests or shows the MAAT fields. |

### 4.6 Modelle, Profile und Systemsteuerung / Models, Profiles, and System Control

| Kommando | Deutsch | English |
|---|---|---|
| `/model` | Modellverwaltung und Modell-Auswahl. | Model management and model selection. |
| `/restart` | Startet die Software neu. | Restarts the software. |
| `/safe-restart` | Speichert und startet neu. | Saves and restarts. |
| `/profile` | Profil-Befehle. | Profile commands. |
| `/plugins` | Plugin-Management. | Plugin management. |
| `/sysinfo` | Systemdiagnose. | System diagnostics. |
| `/meminfo` | RAM-/VRAM-Verbrauch. | RAM/VRAM usage. |
| `/update` | Führt `git pull` mit Neustart aus. | Runs `git pull` and restarts. |

### 4.7 Sprache, Audio und TTS / Language, Audio, and TTS

| Kommando | Deutsch | English |
|---|---|---|
| `/say` | Zeigt die Say-TTS-Hilfe an. | Shows Say-TTS help. |
| `/say on` | Aktiviert Say-TTS. | Enables Say-TTS. |
| `/say off` | Deaktiviert Say-TTS. | Disables Say-TTS. |
| `/say voice <name>` | Ändert die TTS-Stimme. | Changes the TTS voice. |

### 4.8 Zeit, Analyse und MAAT-Metriken / Time, Analysis, and MAAT Metrics

| Kommando | Deutsch | English |
|---|---|---|
| `/time` | Zeigt die aktuelle Zeit. | Shows the current time. |
| `/zeit` | Alias für `/time`. | Alias for `/time`. |
| `/runtime` | Zeit seit der letzten Antwort. | Time since the last response. |
| `/laufzeit` | Alias für `/runtime`. | Alias for `/runtime`. |
| `/timeinfo` | Vollständiger Zeitkontext. | Full time context. |
| `/zeitkontext` | Alias für `/timeinfo`. | Alias for `/timeinfo`. |
| `/timelog` | Zeigt die letzten Time-Memory-Einträge. | Shows the latest time-memory entries. |
| `/time topic <thema>` | Zeit seit der letzten Erwähnung eines Themas. | Time since a topic was last mentioned. |
| `/time stats` | Statistiken über das Time-Memory. | Statistics about time memory. |
| `/timestats` | Alias für `/time stats`. | Alias for `/time stats`. |
| `/maat` | Zeigt den aktuellen MAAT-Score der letzten Antwort. | Shows the current MAAT score of the last response. |
| `/bias` | Zeigt den letzten Bias-Score der Antwort. | Shows the last response bias score. |
| `/uncertainty` | Zeigt den letzten Unsicherheits- / Halluzinationswert. | Shows the latest uncertainty / hallucination risk score. |
| `/prethought` | Zeigt die letzte Vor-Analyse. | Shows the last pre-analysis. |
| `/emotion` | Zeigt die letzte erkannte Emotions-Resonanz. | Shows the last detected emotional resonance. |
| `/userstyle` | Zeigt den anonymen User-Stil-Snapshot. | Shows the anonymous user-style snapshot. |

### 4.9 Wikipedia, Denken und Bewusstseinsanalyse / Wikipedia, Thinking, and Consciousness Analysis

| Kommando | Deutsch | English |
|---|---|---|
| `/wiki <begriff>` | Holt einen Wikipedia-Artikel und cached ihn. | Fetches and caches a Wikipedia article. |
| `/wiki cache` | Zeigt die letzten Cache-Einträge. | Shows the latest cache entries. |
| `/wiki debug on` | Aktiviert Wiki-Debug. | Turns wiki debug on. |
| `/wiki debug off` | Deaktiviert Wiki-Debug. | Turns wiki debug off. |
| `/wiki debug once` | Aktiviert Wiki-Debug einmalig. | Enables wiki debug once. |
| `/think` | Auto-Think Hilfe und Status. | Auto-Think help and status. |
| `/think on` | Aktiviert Auto-Think. | Turns Auto-Think on. |
| `/think off` | Deaktiviert Auto-Think. | Turns Auto-Think off. |
| `/think status` | Zeigt den Auto-Think-Status. | Shows the Auto-Think status. |
| `/think debug on` | Aktiviert den Think-Debug-Modus. | Enables Think debug mode. |
| `/think debug off` | Deaktiviert den Think-Debug-Modus. | Disables Think debug mode. |
| `/think debug once` | Aktiviert Think-Debug einmalig. | Enables Think debug once. |
| `/bki` | Erklärung und Hilfe zum Bewusstseinsindex Psi. | Explanation and help for the consciousness index Psi. |
| `/bki calc H B S V R A DD` | Berechnet Psi. | Calculates Psi. |
| `/bki explain` | Erklärt die Formel im Detail. | Explains the formula in detail. |
| `/bki debug on` | Aktiviert den internen BKI-Debugmodus. | Enables internal BKI debug mode. |
| `/bki debug off` | Deaktiviert den internen BKI-Debugmodus. | Disables internal BKI debug mode. |
| `/bki auto on` | Aktiviert die automatische Psi-Berechnung. | Enables automatic Psi calculation. |
| `/bki auto off` | Deaktiviert die automatische Psi-Berechnung. | Disables automatic Psi calculation. |
| `/bki status` | Zeigt den BKI-Status. | Shows the BKI status. |
| `/bki history` | Zeigt den Psi-Verlauf. | Shows the Psi history. |

### 4.10 Memory- und Erinnerungsfunktionen / Memory and Recall Features

| Kommando | Deutsch | English |
|---|---|---|
| `/mem` | Zeigt die Memory-v5-Übersicht. | Shows the Memory v5 overview. |
| `/mem last` | Zeigt die letzten 10 Erinnerungen. | Shows the last 10 memories. |
| `/mem search <text>` | Semantische Suche im Memory-v5. | Semantic search in Memory v5. |
| `/mem info` | Infos zum MAAT-Memory-v5-System. | Info about the MAAT Memory v5 system. |
| `/mem debug on` | Aktiviert Memory-v5-Debug. | Enables Memory v5 debug mode. |
| `/mem debug off` | Deaktiviert Memory-v5-Debug. | Disables Memory v5 debug mode. |
| `/mem6` | Zeigt die Memory-v6-Übersicht. | Shows the Memory v6 overview. |
| `/mem6 last` | Zeigt die letzten 10 Memory-v6-Einträge. | Shows the last 10 Memory v6 entries. |
| `/mem6 search <text>` | Hybrid-Suche in Memory-v6. | Hybrid search in Memory v6. |
| `/mem6 info` | Infos zum Memory-v6-System. | Information about the Memory v6 system. |
| `/mem6 debug on` | Aktiviert Memory-v6-Debug. | Enables Memory v6 debug mode. |
| `/mem6 debug off` | Deaktiviert Memory-v6-Debug. | Disables Memory v6 debug mode. |
| `/memauto` | Zeigt MemAuto-Hilfe und Status. | Shows MemAuto help and status. |
| `/memauto on` | Aktiviert MemAuto-Kontext-Injektion. | Enables MemAuto context injection. |
| `/memauto off` | Deaktiviert MemAuto-Kontext-Injektion. | Disables MemAuto context injection. |
| `/memauto list` | Zeigt die letzten 10 MemAuto-Erinnerungen. | Shows the last 10 MemAuto memories. |
| `/memauto clear` | Löscht alle MemAuto-Erinnerungen. | Clears all MemAuto memories. |
| `/antirepeat` | Zeigt den Status des Anti-Repeat-Filters. | Shows the anti-repeat filter status. |
| `/antirepeat on` | Aktiviert Anti-Repeat. | Enables anti-repeat. |
| `/antirepeat off` | Deaktiviert Anti-Repeat. | Disables anti-repeat. |

## 5. Automatische Systeme / Automatic Systems

| Deutsch | English |
|---|---|
| Passive HP-Regeneration nach Chat-Nachrichten | Passive HP regeneration after chat messages |
| Battle-Core-Selbsttest für Stabilität | Battle-core self-test for stability |
| Sprachabhängige TTS-Stimme | Language-dependent TTS voice |
| Plugin-Startdiagnose und Modellprüfung | Plugin startup diagnostics and model checks |
| Lokalisierte Start-, Lade- und Diagnosemeldungen | Localized startup, loading, and diagnostic messages |
| Automatische Kampfauslösung nach der Einführung | Automatic battle triggering after the introduction |
| Profilabhängige Boss-Reaktionen | Profile-dependent boss reactions |
| Journal-Einträge aus Story-, Boss- und Quest-Ereignissen | Journal entries from story, boss, and quest events |
| Auto-Think, BKI und MAAT-Analyse-Plugins | Auto-Think, BKI, and MAAT analysis plugins |
| Automatische Battle-Kontext-Bereinigung nach Guide-Kämpfen | Automatic battle-context cleanup after guide battles |
| Sprach-Fallback über gespeicherte Sprache oder Systemsprache | Language fallback via saved language or system language |
| Schutz gegen unnötige Plugin-Loader-Warnungen beim Start | Protection against unnecessary plugin-loader warnings at startup |

## 5.1 Zusätzliche Nutzerfunktionen / Additional Player-Facing Features

| Deutsch | English |
|---|---|
| Zweisprachige Questnamen und Questbeschreibungen | Bilingual quest names and quest descriptions |
| Zweisprachige Achievements und Battle-Logs | Bilingual achievements and battle logs |
| Zweisprachiger Shop, HUD, Titelbildschirm und Intro | Bilingual shop, HUD, title screen, and intro |
| Zweisprachige Modellwahl und Downloader-Dialogs | Bilingual model selection and downloader dialogs |
| Zweisprachige MAAT-OS-Infoseiten im Menü | Bilingual MAAT-OS info pages in the menu |
| Boss-Codex-Einträge beim ersten Treffen | Boss codex entries on first encounter |
| Journal dokumentiert Storyweg, Konsequenzen und Boss-Begegnungen | Journal records story path, consequences, and boss encounters |

## 6. Hinweise / Notes

- Demo-Kämpfe (`/fight`, `/fightboss`, `/fightfinal`) geben keinen XP-, Gold- oder Item-Vorteil.
- Einige Kommandos haben Unterbefehle mit Parametern, zum Beispiel `/quest accept`, `/shop buy`, `/wiki <begriff>`, `/mem search`, `/mem6 search`.
- Diese Liste bildet die sichtbaren Nutzerfunktionen des aktuellen Builds ab. Interne Entwicklerhilfen oder Altdateien (`.bak`) sind bewusst nicht Teil dieser Übersicht.
