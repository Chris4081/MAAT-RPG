# MAAT-RPG / MAAT-OS Funktionen

Stand: 10.04.2026

Diese Datei beschreibt die sichtbaren Funktionen, Systeme und Kommandos des aktuellen MAAT-RPG- und MAAT-OS-Repos in Deutsch und Englisch.

## Deutsch

### Kernfunktionen

- Zweisprachiger Start von MAAT-OS Loader und MAAT-RPG
- Sprachwahl beim Start und im Menü
- Titelbildschirm `Version 0.2` mit Enter-Schritt
- Persistenter Spielstand in `Application Support`
- Lokales Modell-Setup mit Modell-Auswahl und Downloader
- Say-TTS mit Sprach-Standardstimmen `Anna` und `Samantha`
- Musiksystem für Menü, Intro und Kämpfe
- Plugin-Architektur mit Command Router
- DE/EN-Hilfetexte und lokalisierte Plugin-Befehle
- Mac-Setup für Intel und Apple Silicon

### Gameplay

- Geführte Demo-Kämpfe ohne spielerischen Vorteil
- Zufallskämpfe nach der Einführung
- Boss- und Finalbosskämpfe mit Auren, Charge und Spezialangriffen
- Resonanz-System mit `MAAT Impuls`
- Fokus-System mit Heilung und Schild
- Shop mit Heiltränken und Schutz-Siegeln
- Kampf-Erfolge und Kampfanalyse
- Pfadprofil, Rang und Motiv für Maatis
- Story-Entscheidungen mit späteren Konsequenzen
- Journal und Boss-Codex
- Quests mit pfadabhängigen Bonusbelohnungen
- Dungeon-Systeme `60`, `500` und `1000`

### Story und Welt

- Cinematic Intro für MAAT-RPG
- Hauptstory mit Zwischenakten und inneren Reflexionen
- Mehrsprachige Story-Szenen und Journal-Einträge
- Reaktive Welt auf Basis des Pfadprofils
- Boss-Reaktionen auf Maatis’ Weg
- Beziehungsanzeige zwischen Maatis und MAAT-KI
- Lore-, Origin- und Identitätsansichten

### Wichtige Kommandos

#### Basis und Navigation

- `/help`, `/h`, `/hilfe` → Zeigt alle Kommandos
- `/clear`, `/cls` → Leert den Bildschirm
- `/exit`, `/quit` → Beendet das Programm
- `/menu` → Zeigt das MAAT-RPG-Startmenü
- `/motivate` → Gibt eine motivierende Zeile aus
- `/evo` → Zeigt den Status der Self-Evolution-Engine

#### Story, Journal und Identität

- `/storyreset` → Setzt den Story-Fortschritt zurück
- `/journal` → Zeigt Maatis bisherigen Weg und seine Entscheidungen
- `/whoismaat` → Zeigt, wer MAAT bzw. Maatis ist
- `/origin` → Zeigt die Ursprungsgeschichte
- `/lore` → Zeigt Lore und Hintergrundwelt
- `/maatbond` → Zeigt die aktuelle Beziehung zu MAAT-KI
- `/rpgdemo` → Startet das Cinematic-Intro

#### Kampf, Fortschritt und Shop

- `/fight` → Startet einen geführten MAAT-Testkampf
- `/fightboss` → Startet einen geführten Boss-Testkampf
- `/fightfinal` → Startet einen geführten Finalboss-Testkampf
- `/xp` → Zeigt Level- und XP-Status
- `/shop` → Öffnet den Shop
- `/shop buy potion <n>` → Kauft Heiltränke
- `/shop buy sigil <n>` → Kauft Schutz-Siegel
- `/usepotion` → Benutzt einen Heiltrank
- `/battletest` → Führt einen Battle-Core-Selbsttest aus

#### Quests und Erfolge

- `/quests` → Zeigt verfügbare, aktive und abgeschlossene Quests
- `/quest accept <id>` → Nimmt eine Quest an
- `/quest info <id>` → Zeigt Quest-Details und Pfadbonus
- `/erfolge` → Zeigt freigeschaltete Erfolge
- `/ach` → Zeigt emotionale oder narrative Achievements

#### Dungeons und Felder

- `/dungeon60` → Betritt Dungeon 60
- `/d500` → Betritt Dungeon 500
- `/d1000` → Betritt Dungeon 1000
- `/test_fields` → Testet oder zeigt die MAAT-Felder

#### Modelle, Profil und System

- `/model` → Modellverwaltung und Modell-Auswahl
- `/restart` → Startet die Software neu
- `/safe-restart` → Speichert und startet neu
- `/profile` → Profil-Befehle
- `/plugins` → Plugin-Management
- `/sysinfo` → Systemdiagnose
- `/meminfo` → RAM-/VRAM-Verbrauch
- `/update` → Führt `git pull` mit Neustart aus

#### Sprache, Audio und TTS

- `/say` → Zeigt die Say-TTS-Hilfe
- `/say on` → Aktiviert Say-TTS
- `/say off` → Deaktiviert Say-TTS
- `/say voice <name>` → Ändert die TTS-Stimme

#### Zeit, Analyse und MAAT-Metriken

- `/time`, `/zeit` → Zeigt die aktuelle Zeit
- `/runtime`, `/laufzeit` → Zeit seit der letzten Antwort
- `/timeinfo`, `/zeitkontext` → Vollständiger Zeitkontext
- `/timelog` → Zeigt die letzten Time-Memory-Einträge
- `/time topic <thema>` → Zeit seit der letzten Erwähnung eines Themas
- `/time stats`, `/timestats` → Statistiken über das Time-Memory
- `/maat` → Zeigt den aktuellen MAAT-Score der letzten Antwort
- `/bias` → Zeigt den letzten Bias-Score
- `/uncertainty` → Zeigt den letzten Unsicherheitswert
- `/prethought` → Zeigt die letzte Vor-Analyse
- `/emotion` → Zeigt die letzte erkannte Emotions-Resonanz
- `/userstyle` → Zeigt den anonymen User-Stil-Snapshot

#### Wissen, Denken und Bewusstseinsanalyse

- `/wiki <begriff>` → Holt und cached einen Wikipedia-Artikel
- `/wiki cache` → Zeigt Cache-Einträge
- `/wiki debug on/off/once` → Steuert Wiki-Debug
- `/think` und Unterbefehle → Auto-Think Hilfe, Status und Debug
- `/bki` und Unterbefehle → Bewusstseinsindex Psi, Status und Verlauf

#### Memory und Erinnerungen

- `/mem` und Unterbefehle → Memory-v5-Übersicht, Suche und Debug
- `/mem6` und Unterbefehle → Memory-v6-Übersicht, Hybrid-Suche und Debug
- `/memauto` und Unterbefehle → Triggerbasierte Erinnerungen
- `/antirepeat` und Unterbefehle → Anti-Repeat-Filter

### Automatische Systeme

- Passive HP-Regeneration nach Chat-Nachrichten
- Battle-Core-Selbsttest für Stabilität
- Sprachabhängige TTS-Stimme
- Plugin-Startdiagnose und Modellprüfung
- Lokalisierte Start-, Lade- und Diagnosemeldungen
- Automatische Kampfauslösung nach der Einführung
- Profilabhängige Boss-Reaktionen
- Journal-Einträge aus Story-, Boss- und Quest-Ereignissen
- Auto-Think, BKI und MAAT-Analyse-Plugins

### Hinweise

- Demo-Kämpfe `/fight`, `/fightboss` und `/fightfinal` geben keinen XP-, Gold- oder Item-Vorteil.
- Einige Kommandos haben Unterbefehle mit Parametern, zum Beispiel `/quest accept`, `/shop buy`, `/wiki <begriff>`, `/mem search`, `/mem6 search`.

---

## English

### Core Features

- Bilingual startup for the MAAT-OS loader and MAAT-RPG
- Language selection at startup and in the menu
- `Version 0.2` title screen with Enter step
- Persistent save state in `Application Support`
- Local model setup with model selection and downloader
- Say-TTS with language-specific default voices `Anna` and `Samantha`
- Music system for menu, intro, and battles
- Plugin architecture with command router
- DE/EN help texts and localized plugin commands
- Mac setup for Intel and Apple Silicon

### Gameplay

- Guided demo battles with no gameplay advantage
- Random battles after the introduction
- Boss and final boss fights with auras, charge, and special attacks
- Resonance system with `MAAT Impulse`
- Focus system with healing and shield
- Shop with healing potions and warding sigils
- Combat achievements and battle analysis
- Path profile, rank, and motive for Maatis
- Story choices with later consequences
- Journal and boss codex
- Quests with path-dependent bonus rewards
- Dungeon systems `60`, `500`, and `1000`

### Story and World

- Cinematic intro for MAAT-RPG
- Main story with interludes and inner reflections
- Multilingual story scenes and journal entries
- Reactive world based on the path profile
- Boss reactions to Maatis' path
- Relationship display between Maatis and MAAT-KI
- Lore, origin, and identity views

### Key Commands

#### Base and Navigation

- `/help`, `/h`, `/hilfe` → Shows all commands
- `/clear`, `/cls` → Clears the screen
- `/exit`, `/quit` → Exits the program
- `/menu` → Shows the MAAT-RPG start menu
- `/motivate` → Gives you a motivational line
- `/evo` → Shows the self-evolution engine status

#### Story, Journal, and Identity

- `/storyreset` → Resets story progress
- `/journal` → Shows Maatis' path and decisions
- `/whoismaat` → Shows who MAAT / Maatis is
- `/origin` → Shows the origin story
- `/lore` → Shows lore and background worldbuilding
- `/maatbond` → Shows the current bond with MAAT-KI
- `/rpgdemo` → Starts the cinematic intro

#### Battle, Progress, and Shop

- `/fight` → Starts a guided MAAT test battle
- `/fightboss` → Starts a guided boss test battle
- `/fightfinal` → Starts a guided final boss test battle
- `/xp` → Shows level and XP status
- `/shop` → Opens the shop
- `/shop buy potion <n>` → Buys healing potions
- `/shop buy sigil <n>` → Buys warding sigils
- `/usepotion` → Uses a healing potion
- `/battletest` → Runs a battle-core self-test

#### Quests and Achievements

- `/quests` → Shows available, active, and completed quests
- `/quest accept <id>` → Accepts a quest
- `/quest info <id>` → Shows quest details and path bonus
- `/erfolge` → Shows unlocked achievements
- `/ach` → Shows emotional or narrative achievements

#### Dungeons and Fields

- `/dungeon60` → Enters Dungeon 60
- `/d500` → Enters Dungeon 500
- `/d1000` → Enters Dungeon 1000
- `/test_fields` → Tests or shows the MAAT fields

#### Models, Profile, and System

- `/model` → Model management and model selection
- `/restart` → Restarts the software
- `/safe-restart` → Saves and restarts
- `/profile` → Profile commands
- `/plugins` → Plugin management
- `/sysinfo` → System diagnostics
- `/meminfo` → RAM/VRAM usage
- `/update` → Runs `git pull` and restarts

#### Language, Audio, and TTS

- `/say` → Shows Say-TTS help
- `/say on` → Enables Say-TTS
- `/say off` → Disables Say-TTS
- `/say voice <name>` → Changes the TTS voice

#### Time, Analysis, and MAAT Metrics

- `/time`, `/zeit` → Shows the current time
- `/runtime`, `/laufzeit` → Time since the last response
- `/timeinfo`, `/zeitkontext` → Full time context
- `/timelog` → Shows the latest time-memory entries
- `/time topic <topic>` → Time since a topic was last mentioned
- `/time stats`, `/timestats` → Statistics about time memory
- `/maat` → Shows the current MAAT score of the last response
- `/bias` → Shows the last bias score
- `/uncertainty` → Shows the latest uncertainty score
- `/prethought` → Shows the last pre-analysis
- `/emotion` → Shows the last detected emotional resonance
- `/userstyle` → Shows the anonymous user-style snapshot

#### Knowledge, Thinking, and Consciousness Analysis

- `/wiki <term>` → Fetches and caches a Wikipedia article
- `/wiki cache` → Shows cache entries
- `/wiki debug on/off/once` → Controls wiki debug
- `/think` and subcommands → Auto-Think help, status, and debug
- `/bki` and subcommands → Consciousness index Psi, status, and history

#### Memory and Recall

- `/mem` and subcommands → Memory v5 overview, search, and debug
- `/mem6` and subcommands → Memory v6 overview, hybrid search, and debug
- `/memauto` and subcommands → Trigger-based memory storage
- `/antirepeat` and subcommands → Anti-repeat filter

### Automatic Systems

- Passive HP regeneration after chat messages
- Battle-core self-test for stability
- Language-dependent TTS voice
- Plugin startup diagnostics and model checks
- Localized startup, loading, and diagnostic messages
- Automatic battle triggering after the introduction
- Profile-dependent boss reactions
- Journal entries from story, boss, and quest events
- Auto-Think, BKI, and MAAT analysis plugins

### Notes

- Demo battles `/fight`, `/fightboss`, and `/fightfinal` do not grant XP, gold, or item advantages.
- Some commands use subcommands with parameters, such as `/quest accept`, `/shop buy`, `/wiki <term>`, `/mem search`, and `/mem6 search`.
