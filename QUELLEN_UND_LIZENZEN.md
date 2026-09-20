# MAAT RPG – Medienquellen und Lizenzen

Stand: **20. September 2026** · Projekt und kreative Leitung: **Christof Krieg**  
[English credits](#english-credits)

Die Welt von MAAT RPG verbindet KI-unterstützte Illustrationen, im Projekt
gezeichnete Figuren und eigene synthetisierte Soundeffekte. Die Suno-Hintergrundmusik
der getrennten offiziellen Musikausgabe ist nicht in diesem Repository enthalten.
Diese Übersicht nennt ihre Herkunft und die zugehörigen Nutzungsbedingungen.

| Bereich | Herkunft |
| --- | --- |
| Programmcode | MAAT-RPG-Projekt · GNU AGPL v3 |
| Grafiken und Animationen | KI-unterstützte Projektillustrationen, eigene SVGs und im Code gezeichnete Effekte |
| Hintergrundmusik und Musik-Cover | Nicht enthalten; die offizielle Musikausgabe wird getrennt bereitgestellt |
| Soundeffekte | Eigene prozedurale Klangerzeugung ohne externe Samples |

Die kurzen Spielpfade beziehen sich auf den Ordner `maatos/`. Für den Programmcode
gelten die [GNU AGPL v3](LICENSE.txt) und der [ergänzende ethische Hinweis](LICENSE_ADDITIONAL.md).
Die [Medienfreigabe](MEDIA_LICENSE.md) regelt die Weiterverwendung:
Projektgrafiken und eigene Soundeffekte unter CC BY 4.0; für Suno-Musik und
eingebettete Cover wird keine zusätzliche Nutzungslizenz eingeräumt. Gesetzliche
Befugnisse und gemäß GitHub-Bedingungen eingeräumte Rechte bleiben unberührt.
Diese Quellenübersicht dokumentiert die Herkunft.

## 1. Grafiken und Animationen

Die Klassenbilder, Terra-Landschaften und Storyillustrationen entstanden im
KI-unterstützten Entwicklungsprozess. Klassen- und Titelgrafiken wurden mit dem
integrierten OpenAI-Bildgenerator erstellt. Die Gegner, Angriffsvarianten und
Robo-Reaktionen wurden als SVG-Grafiken im Projekt gestaltet. Pyramide, Weltkarte,
Minispielfelder und Effekte wie Partikel oder Trefferfeedback werden außerdem
direkt im Programm gezeichnet.

Das App-Symbol und die fünf älteren Story-/Porträtillustrationen stammen laut
Bestätigung von Christof Krieg ebenfalls aus dem damaligen KI-unterstützten
Projektworkflow. Die [Bildübersicht](docs/media/ILLUSTRATIONEN.md) zeigt diese
Illustrationen. Screenshots und Website-Ansichten verwenden die Projektmedien;
einige Entwicklungsaufnahmen enthalten synthetische Testwerte.

Für die mit OpenAI-Werkzeugen erstellten Bilder sind die jeweils geltenden
[OpenAI-Ausgabebedingungen](https://openai.com/policies/eu-terms-of-use/)
maßgeblich. Die Zurechnung von Ausgaberechten zwischen Anbieter und Nutzer
ist keine Übertragung fremder Rechte. Betriebssystem-Schriftarten und
Emoji-Darstellungen unterliegen weiterhin ihren jeweiligen Bedingungen.

<details>
<summary>Grafikgruppen, Dateien und Herstellungsdokumentation</summary>

Unter `gui/assets/` sind 721 Grafikdateien erfasst: 142 PNGs und 579 SVGs.

| Grafikgruppe | Dateien / Herstellung |
| --- | --- |
| Klassen-Grundbilder | `gui/assets/classes/maatis-*.png` · sechs KI-unterstützte Grundbilder |
| Freigestellte Klassen | `gui/assets/classes/transparent-v1/` · sechs Fassungen derselben Grundbilder |
| Klassenaktionen | `gui/assets/classes/actions-v1/` · 120 Posen aus sechs Posenbögen |
| Terra-Titelbilder | `gui/assets/title-worlds/` · fünf Landschaften |
| Story und Rollenwahl | `intro-awakening.png`, `story-reflection.png`, `story-temple.png`, `maatis-human.png`, `ai-keeper.png` unter `gui/assets/` |
| Kampffiguren | `gui/assets/combat/*.svg` · Maatis, 20 normale Gegner, 25 Kampagnenbosse und fünf Finalgegner |
| Angriffe und Reaktionen | `gui/assets/combat/attacks/` · 520 Varianten; `gui/assets/combat/maatis/` · acht Robo-Reaktionen |
| App-Symbol | `packaging/macos/app-template/Contents/Resources/MAAT-RPG.icns` |

Prompts, Referenzen und Herstellungsmanifeste:

- [Klassenentwürfe](gui-preview/class-concepts-v2/prompts.json)
- [Klassen-Posenbögen](gui-preview/class-action-sets-v1/README.md) und [Prompts](gui-preview/class-action-sets-v1/prompts.json)
- [Freistellungsmanifest](maatos/gui/assets/classes/transparent-v1/manifest.json)
- [Manifest der Klassenaktionen](maatos/gui/assets/classes/actions-v1/manifest.json)
- [Terra-Titelbilder](maatos/gui/assets/title-worlds/artwork-manifest.json)
- [Ägyptische Bossgrafiken](gui-preview/egyptian-bosses-v1/README.md) und [Gegnergrafiken](gui-preview/egyptian-enemies-v2/README.md)
- [Herkunft der Website-Ansichten](docs/media/WEBSITE-ASSETS-PROVENANCE.txt)
- [Bilder der READMEs](docs/media/readme-images.json)

</details>

## 2. Hintergrundmusik – getrennte Ausgabe

**Dieses Repository enthält keine Suno-Musik und keine eingebetteten Suno-Cover.**
Das Spiel startet mit ausgeschalteter Hintergrundmusik. Die eigenen Soundeffekte
in den nächsten Abschnitten bleiben enthalten und nutzbar.

Die Musik der getrennten offiziellen Ausgabe wurde laut Projektinhaber mit dessen
**Suno-Pro-Account [@maatis](https://suno.com/@maatis)** erstellt. Auch die in diesen
Musikdateien eingebetteten Cover stammen laut seiner Angabe aus Suno.

**Songtexte:** Christof Krieg mit Unterstützung von ChatGPT. Beim Titel
**„Harmonie der Erde (Maat KI)“** (`credits_en.mp3` in der Musikausgabe) entstand der
Text laut Projektinhaber mit **„Llama 120k 8B“**.

Diese Musik steht weder unter AGPL noch unter CC BY. Eine zusätzliche Erlaubnis zur
Weiterverwendung erteilt dieses Repository nicht. Für die getrennte Musikausgabe
gelten die jeweiligen Rechte und [Suno-Bedingungen](https://suno.com/terms).
Forks können ohne Hintergrundmusik spielen oder eigene, passend lizenzierte
Stücke ergänzen; siehe [Musik und Soundeffekte](docs/MUSIC.md#deutsch).

## 3. Eigene Level-up- und Siegesklänge

Die beiden kurzen Spielsignale wurden im Projekt prozedural erzeugt — mit
eigenen Tonfolgen, Sinusschwingungen, deterministischem Rauschen und berechnetem
Nachhall. Es wurden keine fremden Samples verwendet.

| Verwendung | Datei im Spielordner | Titel / Dauer |
| --- | --- | --- |
| Levelaufstieg | `apps/maat_rpg/plugins/battle/sounds/levelup.mp3` | **Aufstieg des Lichts** · 8 Sekunden |
| Sieg / Level-up-Ersatz | `apps/maat_rpg/plugins/battle/music/victory.mp3` | **Sieg der Resonanz** · 6 Sekunden |

Die Dauer bezieht sich auf die PCM-Fassungen. Deutsch und Englisch verwenden
dieselben Klänge. Seit dem 20. September 2026 ersetzen sie die früheren Platzhalter.

[Generator](tools/build_celebration_sounds.py) ·
[Herstellungsmanifest](maatos/apps/maat_rpg/plugins/battle/sounds/original-cues-manifest.json) ·
[Level-up als WAV](gui-preview/celebration-sounds-v1/levelup.wav) ·
[Siegesklang als WAV](gui-preview/celebration-sounds-v1/victory.wav)

## 4. Weitere eigene Soundeffekte

Sieben weitere WAV-Dateien wurden ebenfalls lokal ohne externe Samples erzeugt.

| Effekte | Dateien unter `gui/assets/audio/` | Generator |
| --- | --- | --- |
| Fünf Prinzipien H/B/S/V/R | `principles-v1/h_harmony.wav`, `b_balance.wav`, `s_creation.wav`, `v_connection.wav`, `r_respect.wav` im selben Ordner | [Prinzipienklänge](tools/build_principle_sounds.py) |
| Story weiterblättern | `ui-v1/story_advance.wav` | [Klicksound](tools/build_ui_sounds.py) |
| Maatis verliert KP | `combat-v1/maatis_hurt.wav` | [Schadenssound](tools/build_damage_sound.py) |

In jedem Effektordner dokumentiert ein `manifest.json` die Herstellung.
Zusammen mit Level-up und Sieg enthält das Projekt damit neun prozedural erzeugte
Spieleffekte. Ihre Generatoren sind Teil des Programmcodes; die Audiodateien
werden als Projektmedien separat von der Softwarelizenz geführt.

## 5. Weiterverwendung

Programmcode, Projektgrafiken und eigene Soundeffekte haben getrennte
Lizenzhinweise. Die [Medienfreigabe](MEDIA_LICENSE.md) beschreibt die Freigabe der
mitgelieferten Medien unter CC BY 4.0; für den Programmcode gilt GNU AGPL v3.
Nachträglich ergänzte Musik benötigt eigene passende Nutzungsrechte.

## Offline-Wikipedia und eigene Inhalte

MAAT RPG liefert keine GGUF-Modelle, ZIM-Archive oder Wikipedia-Inhalte mit.
Für selbst hinzugefügte Modelle, Archive und Medien gelten deren jeweilige
Bedingungen. Die optionale Wiki-Funktion ist in den
[Wiki-Hinweisen auf Deutsch und Englisch](docs/WIKI_HINWEISE.md) erläutert.
Softwarebibliotheken wie libzim haben unabhängig vom Archivinhalt eigene Lizenzen.

## English credits

MAAT RPG was created under the creative direction of **Christof Krieg**.
Its visuals combine AI-assisted project illustrations, original SVG characters,
code-drawn effects and interface captures. Class and landscape artwork was
created with the integrated OpenAI image generator; prompts and production
manifests are linked above. According to the project owner, the app icon and
five earlier story/portrait illustrations also originated in the project's
AI-assisted development workflow.

**Background music:** no Suno tracks or embedded Suno covers are included in this
repository. Music starts off by default. The official music edition is intended for separate
distribution by the project owner. Its soundtrack was created with Suno Pro using the
[@maatis](https://suno.com/@maatis) account, according to the owner. Lyrics were
written by Christof Krieg with assistance from ChatGPT, except **“Harmonie der Erde
(Maat KI)”**, whose lyrics the owner credits to work with **“Llama 120k 8B”**.
That separate music retains its own terms; it is not covered by AGPL or CC BY.

**Sound effects:** nine original project cues synthesized locally without
external samples. These include the eight-second level-up cue and six-second
victory cue, which replaced earlier placeholders on September 20, 2026.

**Licensing:** the program code is covered by the [GNU AGPL v3](LICENSE.txt).
[Media permissions](MEDIA_LICENSE.md) place project artwork and original sound
effects under CC BY 4.0. Suno music and embedded covers are not included; no additional reuse license
for the separate soundtrack is granted by the repository. This page documents provenance; the permissions page defines scope. User-supplied GGUF
models and ZIM archives are not included; see the
[offline-wiki notes](docs/WIKI_HINWEISE.md).
