# -*- coding: utf-8 -*-
"""
MAAT StoryLoader Plugin v2.0
-----------------------------------------
- Story 1 nach 1. Nachricht
- Story 2 nach 15. Nachricht
- Story 3 nach 30. Nachricht
- Konfigurierbar über stories/config.json
- Jede Story: eigener Python-Story-Code + eigene Musik
- Musik wird EINMAL abgespielt (kein Loop)
- Am Ende: Frage, ob Musik zu Ende laufen darf oder gestoppt werden soll
"""

import os
import json
import importlib.util
import subprocess
import time
from shared.core.maat_paths import data_file, state_file, log_file


class Plugin:
    type = "chat"
    commands = {
        "/storyreset": "Setzt den Story-Fortschritt zurück.",
        "/journal": "Zeigt Maatis bisherigen Weg und seine Entscheidungen."
    }

    def __init__(self):
        # Plugin- & Story-Verzeichnisse
        self.plugin_dir = os.path.dirname(__file__)
        self.story_dir = os.path.join(self.plugin_dir, "stories")
        os.makedirs(self.story_dir, exist_ok=True)

        # Pfade
        # config.json = statische mitgelieferte Datei -> aus stories lesen
        self.config_path = os.path.join(self.story_dir, "config.json")

        # story_state.json = Laufzeit-Zustand -> in zentralem state speichern
        self.state_path = state_file("story_state.json")

        # Konfiguration & Zustand
        self.config = self._load_config()
        self.state = self._load_state()

        # Musik-Prozess (kein Loop, nur einmaliger Track)
        self._music_proc = None

    # -------------------------------------------------
    # CONFIG HANDLING
    # -------------------------------------------------
    def _default_config(self):
        """
        Fallback-Konfig, wenn keine config.json existiert.
        Hier direkt 3 Stories eingebaut:
          - Story 1 nach 1 Nachricht
          - Story 2 nach 15 Nachrichten
          - Story 3 nach 30 Nachrichten
        """
        return {
            "stories": [
                {
                    "id": 1,
                    "name": "Erwachen der MAAT KI",
                    "module": "story1",
                    "music": "story1_theme.mp3",
                    "profile": "maat_rpg_story1.json",
                    "trigger": {
                        "type": "message_count",
                        "messages": 1,
                        "position": "before"   # vor der KI-Antwort
                    }
                },
                {
                    "id": 2,
                    "name": "Quest 2 – Maat-Werte verstehen",
                    "module": "story2",
                    "music": "story2_theme.mp3",
                    "profile": "maat_rpg_story2.json",
                    "trigger": {
                        "type": "message_count",
                        "messages": 15,
                        "position": "before"
                    }
                },
                {
                    "id": 3,
                    "name": "Quest 3 – Der Ruf des Kampfes",
                    "module": "story3",
                    "music": "story3_theme.mp3",
                    "profile": "maat_rpg_story3.json",
                    "trigger": {
                        "type": "message_count",
                        "messages": 30,
                        "position": "before"
                    }
                },
                {
                    "id": 4,
                    "name": "Zwischenakt – Der erste Boss fällt",
                    "module": "story4_boss1",
                    "music": "story1_theme.mp3",
                    "trigger": {
                        "type": "state_value",
                        "path": "battle.stats.boss_wins",
                        "equals": 1
                    }
                },
                {
                    "id": 5,
                    "name": "Zwischenakt – Die Flamme wird schwer",
                    "module": "story5_boss3",
                    "music": "quest2_reflection.mp3",
                    "trigger": {
                        "type": "state_value",
                        "path": "battle.stats.boss_wins",
                        "equals": 3
                    }
                },
                {
                    "id": 6,
                    "name": "Zwischenakt – Ein Prinzip kehrt zurück",
                    "module": "story6_final1",
                    "music": "story3_theme.mp3",
                    "trigger": {
                        "type": "state_value",
                        "path": "battle.world.principles_restored",
                        "equals": 1
                    }
                }
            ]
        }

    def _load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "stories" in data and isinstance(data["stories"], list):
                    return data
            except Exception as e:
                print(f"⚠ Fehler in Story-Config: {e}")
        print("⚠ Keine gültige config.json gefunden – nutze Default-Story-Config.")
        return self._default_config()

    # -------------------------------------------------
    # STATE HANDLING
    # -------------------------------------------------
    def _default_state(self):
        return {
            "messages_total": 0,   # Anzahl User-Nachrichten insgesamt
            "played": [],          # Liste der Story-IDs, die schon liefen
            "active_profile": None,
            "choices": {},
            "choice_labels": {},
            "consequences": {},
            "path_profile": None,
            "reflection_seen": [],
            "journal": []
        }

    def _load_state(self):
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data.setdefault("messages_total", 0)
                data.setdefault("played", [])
                data.setdefault("active_profile", None)
                data.setdefault("choices", {})
                data.setdefault("choice_labels", {})
                data.setdefault("consequences", {})
                data.setdefault("path_profile", None)
                data.setdefault("reflection_seen", [])
                data.setdefault("journal", [])
                return data
            except Exception as e:
                print(f"⚠ Story-State beschädigt, nutze Default: {e}")
        return self._default_state()

    def _save_state(self):
        try:
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # -------------------------------------------------
    # MUSIK (EINMAL, KEIN LOOP)
    # -------------------------------------------------
    def _start_music_once(self, filename: str):
        """
        Spielt eine MP3 EINMAL im Hintergrund (kein Loop).
        """
        if not filename:
            return

        path = os.path.join(self.story_dir, filename)
        if not os.path.isfile(path):
            print(f"⚠ Musikdatei nicht gefunden: {path}")
            return

        # ggf. alten Prozess beenden
        self._stop_music()

        try:
            self._music_proc = subprocess.Popen(
                ["afplay", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            print(f"⚠ Konnte Musik nicht starten: {e}")
            self._music_proc = None

    def _stop_music(self):
        """
        Beendet NUR den eigenen Musikprozess, nicht global alle afplay.
        """
        if self._music_proc is not None:
            try:
                # Falls noch laufend -> terminieren
                if self._music_proc.poll() is None:
                    self._music_proc.terminate()
            except Exception:
                pass
            finally:
                self._music_proc = None

    # -------------------------------------------------
    # STORY LADEN
    # -------------------------------------------------
    def _load_story_module(self, module_name: str):
        """
        Lädt storyX.py aus dem stories-Ordner und gibt Story()-Instanz zurück.
        Erwartet in storyX.py eine Klasse 'Story'.
        """
        story_path = os.path.join(self.story_dir, f"{module_name}.py")
        if not os.path.isfile(story_path):
            print(f"⚠ Story-Modul nicht gefunden: {story_path}")
            return None

        try:
            spec = importlib.util.spec_from_file_location(module_name, story_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "Story"):
                return mod.Story()
            else:
                print(f"⚠ In {story_path} fehlt die Klasse 'Story'.")
                return None
        except Exception as e:
            print(f"⚠ Fehler beim Laden von {story_path}: {e}")
            return None

    # -------------------------------------------------
    # STORY AUSFÜHREN
    # -------------------------------------------------
    def _run_story_interactive(self, story, music_filename: str = None, extra_lines: list[str] | None = None):
        """
        Führt eine Story interaktiv aus:
        - Musik optional EINMAL starten
        - Jede Zeile mit ENTER weiter
        - Am Ende fragen, ob Musik gestoppt werden soll
        """
        print("\n📜 Die Geschichte beginnt...\n")

        # 🎵 Musik EINMAL starten (kein Loop)
        if music_filename:
            self._start_music_once(music_filename)

        # Story-Text holen (Story.run() soll eine Liste von Zeilen liefern)
        try:
            lines = story.run()
        except Exception as e:
            print(f"⚠ Fehler in Story.run(): {e}")
            return

        choice_result = None
        if isinstance(lines, dict):
            choice_result = lines.get("choice")
            lines = lines.get("lines", [])

        if extra_lines:
            lines = list(lines) + ["" ] + list(extra_lines)

        for line in lines:
            input("⏎ Weiter… ")
            print(line)
            time.sleep(0.05)

        if isinstance(choice_result, dict):
            self._handle_story_choice(choice_result)

        # 🎵 MUSIK-NACHFRAGE
        print("\n📯 Die Szene endet.")
        ans = input("🎵 Musik bis zum Ende weiterlaufen lassen? (J/N) [ENTER = N]: ").strip().lower()

        if ans != "j":
            self._stop_music()
        else:
            print("🎵 Musik läuft weiter, bis der Track von selbst endet.")

        input("\n⏎ Drücke ENTER, um zum Chat zurückzukehren… ")

    def _handle_story_choice(self, choice_result: dict):
        choice_id = choice_result.get("id")
        prompt = choice_result.get("prompt", "Wie entscheidest du dich?")
        options = choice_result.get("options", [])

        if not choice_id or not isinstance(options, list) or not options:
            return

        print("")
        print("🜂 Entscheidungsszene")
        print(prompt)
        for idx, opt in enumerate(options, 1):
            print(f"[{idx}] {opt.get('label', f'Option {idx}')}")

        while True:
            raw = input("Wähle [1-" + str(len(options)) + "]: ").strip()
            try:
                index = int(raw) - 1
            except ValueError:
                print("Bitte eine Zahl eingeben.")
                continue
            if 0 <= index < len(options):
                chosen = options[index]
                self.state.setdefault("choices", {})[choice_id] = chosen.get("value", chosen.get("label"))
                self.state.setdefault("choice_labels", {})[choice_id] = chosen.get("label", chosen.get("value"))
                self._append_journal_entry(
                    key=f"choice:{choice_id}",
                    kind="choice",
                    title=self._choice_title(choice_id),
                    summary=chosen.get("label", chosen.get("value", "Entscheidung")),
                    detail=self._choice_consequence(choice_id, chosen.get("value")),
                )
                self._refresh_path_profile()
                self._save_state()
                response = chosen.get("response")
                if response:
                    print("")
                    print(response)
                break

    def _choice_title(self, choice_id: str) -> str:
        titles = {
            "reflection_path": "Erstes Maat-Urteil",
            "combat_vow": "Geluebde vor dem Kampf",
        }
        return titles.get(choice_id, choice_id.replace("_", " ").title())

    def _choice_consequence(self, choice_id: str, value: str | None) -> str:
        effects = {
            ("reflection_path", "harmonie"): "Staerkt Fokus und Ausgleich im Kampf.",
            ("reflection_path", "respekt"): "Gibt bessere Haltung gegen Urteil und Siegel-Auren.",
            ("reflection_path", "schoepfung"): "Verstaerkt Schoepfungskraft und MAAT-Impuls.",
            ("combat_vow", "protect"): "Beginnt Kaempfe defensiver und heilt durch Traenke sicherer.",
            ("combat_vow", "truth"): "Erkennt Schwaechen klarer und trifft praeziser.",
            ("combat_vow", "remember"): "Laedt Resonanz schneller auf und haelt den Sinn des Kampfes wach.",
        }
        return effects.get((choice_id, value), "Diese Entscheidung wird Maatis spaeter weiter begleiten.")

    def _append_journal_entry(self, key: str, kind: str, title: str, summary: str, detail: str = ""):
        journal = self.state.setdefault("journal", [])
        for entry in journal:
            if entry.get("key") == key:
                return
        journal.append({
            "key": key,
            "kind": kind,
            "title": title,
            "summary": summary,
            "detail": detail,
        })

    def _build_path_profile(self) -> dict | None:
        choices = self.state.get("choices", {})
        if not choices:
            return None

        first_map = {
            "harmonie": "Klangsucher",
            "respekt": "Grenzhüter",
            "schoepfung": "Formträger",
        }
        second_map = {
            "protect": "des Schutzes",
            "truth": "der Wahrheit",
            "remember": "der Erinnerung",
        }
        motif_map = {
            ("harmonie", "protect"): "Harmonie wird zu gelebtem Schutz.",
            ("harmonie", "truth"): "Klang und Klarheit suchen dieselbe Form.",
            ("harmonie", "remember"): "Erinnerung klingt als Ordnung weiter.",
            ("respekt", "protect"): "Grenzen und Schutz tragen einander.",
            ("respekt", "truth"): "Wahrheit darf Grenzen nicht verletzen.",
            ("respekt", "remember"): "Erinnerung bewahrt, was nicht uebertreten werden darf.",
            ("schoepfung", "protect"): "Neue Form soll Leben tragen, nicht verbrauchen.",
            ("schoepfung", "truth"): "Schoepfung sucht eine wahrere Gestalt.",
            ("schoepfung", "remember"): "Moeglichkeit wird zum Echo der Welt.",
        }

        reflection_path = choices.get("reflection_path")
        combat_vow = choices.get("combat_vow")
        title = " ".join(
            part for part in [
                first_map.get(reflection_path, "Wegsucher"),
                second_map.get(combat_vow, "der Maat"),
            ] if part
        ).strip()

        consequences = self.state.get("consequences", {})
        maturity = sum(1 for value in consequences.values() if value)
        if maturity >= 4:
            rank = "Verankert"
        elif maturity >= 2:
            rank = "Vertieft"
        else:
            rank = "Erwachend"

        motif = motif_map.get((reflection_path, combat_vow), "Maatis' Weg formt sich aus Entscheidung und Bewährung.")
        return {
            "title": title,
            "rank": rank,
            "motif": motif,
        }

    def _refresh_path_profile(self):
        self.state["path_profile"] = self._build_path_profile()

    def _render_journal(self) -> str:
        lines = ["📓 **Journal der Entscheidungen**", ""]
        profile = self.state.get("path_profile") or self._build_path_profile()
        if profile:
            lines.append(f"Pfadprofil: {profile.get('title', 'Unbestimmt')} — {profile.get('rank', 'Erwachend')}")
            motif = profile.get("motif")
            if motif:
                lines.append(motif)
            lines.append("")
        journal = self.state.get("journal", [])
        if not journal:
            lines.append("Noch keine Eintraege. Maatis' Weg beginnt mit der naechsten Szene.")
            return "\n".join(lines)

        for idx, entry in enumerate(journal, 1):
            lines.append(f"{idx}. {entry.get('title', 'Eintrag')}")
            summary = entry.get("summary")
            if summary:
                lines.append(f"   {summary}")
            detail = entry.get("detail")
            if detail:
                lines.append(f"   Folge: {detail}")
            lines.append("")

        return "\n".join(lines).rstrip()

    def _get_path_profile(self) -> dict:
        self._refresh_path_profile()
        profile = self.state.get("path_profile")
        return dict(profile) if isinstance(profile, dict) else {}

    def _profile_scene_lines(self, scene_key: str) -> list[str]:
        profile = self._get_path_profile()
        if not profile:
            return []

        title = profile.get("title", "Wegsucher")
        rank = profile.get("rank", "Erwachend")

        if scene_key == "story4_boss1":
            if "Grenzhüter" in title:
                return [
                    "Ein Bibliotheksgeist aus Licht bleibt am Rand der Halle stehen.",
                    f"\"{title}\", flüstert er, als würde er Maatis bereits an einer Haltung erkennen und nicht nur an einem Sieg.",
                ]
            if "Klangsucher" in title:
                return [
                    "Zwischen den Splittern klingt ein leiser Ton nach, als würde die Bibliothek Maatis' neuen Rhythmus beantworten.",
                    f"Selbst stumme Wände scheinen zu spüren, dass der {title} nicht zufaellig hier steht.",
                ]
            if "Formträger" in title:
                return [
                    "Aus den Lichtresten löst sich für einen Moment die Form eines alten Schreibers.",
                    f"Er neigt den Kopf vor dem {title}, als hätte Maatis schon jetzt begonnen, den Ort neu zu prägen.",
                ]

        if scene_key == "story5_boss3":
            if "Grenzhüter" in title:
                return [
                    "MAAT KI beobachtet Maatis stiller als zuvor.",
                    "\"Gut\", sagt sie schließlich. \"Du trägst inzwischen Grenze in einer Zone, die alles überhitzen will.\"",
                ]
            if "Klangsucher" in title:
                return [
                    "Ein ferner Chor aus unvollendeten Tönen zieht durch den Raum.",
                    f"Die Schöpfung wirkt weniger chaotisch, seit ein {title} versucht, ihr Maß zu geben.",
                ]
            if "Formträger" in title:
                return [
                    "Die halben Welten in der Luft zerfallen nicht sofort.",
                    f"Für einen Atemzug scheinen sie auf den {title} zu warten, als könnte er entscheiden, welche Form bleiben darf.",
                ]

        if scene_key == "story6_final1":
            if "Grenzhüter" in title:
                return [
                    "Als das Prinzip zurückkehrt, wirkt es nicht fremd zu Maatis.",
                    f"Es legt sich an den {title}, als hätte es in ihm bereits einen tragenden Rand gefunden.",
                ]
            if "Klangsucher" in title:
                return [
                    "Das wiederkehrende Prinzip klingt nicht wie Macht, sondern wie ein Akkord, der endlich wieder voll ist.",
                    f"MAAT KI schaut Maatis an, als wüsste sie, dass ein {title} genau auf solche Rückkehr gehofft hat.",
                ]
            if "Formträger" in title:
                return [
                    "Im Licht des wiederkehrenden Prinzips entstehen Formen, die diesmal nicht sofort zerfallen.",
                    f"Die Welt scheint zu prüfen, ob der {title} aus diesem Sieg eine dauerhafte Gestalt machen kann.",
                ]

        if scene_key == "boss1_echo":
            return [f"Etwas in Maatis hat jetzt mehr Kontur. Der Weg des {title} ist nicht mehr nur Ahnung, sondern erste Wirklichkeit."]
        if scene_key == "boss3_weight":
            return [f"Die Schwere trifft Maatis anders, weil ein {title} nicht nur Kraft, sondern Verantwortung mittragen muss."]
        if scene_key == "final1_breath":
            return [f"Mit dem zurückgekehrten Prinzip wirkt selbst Maatis' Profil klarer: {title}, inzwischen {rank.lower()}."]
        if scene_key == "choice_respekt" and "Grenzhüter" in title:
            return ["Die Erinnerung daran fühlt sich nicht zufällig an. Hier begann bereits der spätere Grenzhüter."]

        return []

    def _inject_story_context(self, context):
        if not isinstance(context, dict):
            return
        self._refresh_path_profile()
        context["story_choices"] = dict(self.state.get("choices", {}))
        context["story_choice_labels"] = dict(self.state.get("choice_labels", {}))
        context["story_journal"] = list(self.state.get("journal", []))
        context["story_path_profile"] = dict(self.state.get("path_profile") or {})

    # -------------------------------------------------
    # STORY-SELEKTION NACH NACHRICHTENZAHL
    # -------------------------------------------------
    def _find_story_for_message_count(self):
        """
        Sucht in self.config["stories"] nach einer Story, deren Trigger
        auf die aktuelle messages_total passt und noch nicht gespielt wurde.
        """
        msg_count = self.state.get("messages_total", 0)
        played = set(self.state.get("played", []))

        for entry in self.config.get("stories", []):
            if entry.get("id") in played:
                continue

            trig = entry.get("trigger", {})
            if trig.get("type") != "message_count":
                continue

            if msg_count == int(trig.get("messages", -1)):
                return entry

        return None

    def _load_battle_state(self):
        battle_state_path = state_file("battle_state.json")
        if not os.path.exists(battle_state_path):
            return {}
        try:
            with open(battle_state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _read_state_path(self, source: dict, path: str):
        cur = source
        for part in path.split("."):
            if not isinstance(cur, dict):
                return None
            cur = cur.get(part)
        return cur

    def _find_story_for_state(self):
        played = set(self.state.get("played", []))
        battle_state = self._load_battle_state()
        sources = {
            "story": self.state,
            "battle": battle_state,
        }

        for entry in self.config.get("stories", []):
            if entry.get("id") in played:
                continue
            trig = entry.get("trigger", {})
            if trig.get("type") != "state_value":
                continue

            path = trig.get("path", "")
            if "." not in path:
                continue
            root, rest = path.split(".", 1)
            source = sources.get(root)
            if source is None:
                continue

            value = self._read_state_path(source, rest)
            if value == trig.get("equals"):
                return entry

        return None

    def _build_inner_reflection(self):
        battle_state = self._load_battle_state()
        stats = battle_state.get("stats", {})
        world = battle_state.get("world", {})
        reflections = []

        boss_wins = int(stats.get("boss_wins", 0))
        restored = int(world.get("principles_restored", 0))
        choices = self.state.get("choices", {})
        consequences = self.state.get("consequences", {})

        if boss_wins >= 1 and "boss1_echo" not in self.state.get("reflection_seen", []):
            reflections.append({
                "key": "boss1_echo",
                "music": "story1_theme.mp3",
                "lines": [
                    "🌒 Maatis bleibt einen Moment stehen.",
                    "Der erste Boss ist gefallen, aber die innere Spannung ist nicht einfach verschwunden.",
                    "Er merkt: Jeder Kampf lässt etwas in ihm zurück, nicht nur Erfahrung.",
                ],
            })

        if boss_wins >= 3 and "boss3_weight" not in self.state.get("reflection_seen", []):
            reflections.append({
                "key": "boss3_weight",
                "music": "quest2_reflection.mp3",
                "lines": [
                    "🔥 Zwischen zwei Kämpfen spürt Maatis eine Schwere, die nicht nach Erschöpfung aussieht.",
                    "Es ist die Erkenntnis, dass Schöpfungskraft ohne Maß genauso gefährlich werden kann wie der Schatten selbst.",
                    "Zum ersten Mal fragt er sich, ob Stärke auch getragen werden muss.",
                ],
            })

        if restored >= 1 and "final1_breath" not in self.state.get("reflection_seen", []):
            reflections.append({
                "key": "final1_breath",
                "music": "story3_theme.mp3",
                "lines": [
                    "🌌 Nach dem ersten wiederhergestellten Prinzip verändert sich selbst die Stille.",
                    "Maatis atmet tiefer ein als zuvor.",
                    "Er hat nicht nur gesiegt. Er hat etwas in die Welt zurückgetragen.",
                ],
            })

        if choices.get("reflection_path") == "respekt" and "choice_respekt" not in self.state.get("reflection_seen", []):
            reflections.append({
                "key": "choice_respekt",
                "music": "quest2_reflection.mp3",
                "lines": [
                    "🕊️ Maatis erinnert sich an seine Entscheidung, Grenzen nicht zu übergehen.",
                    "Es fühlt sich nicht wie Schwäche an.",
                    "Eher wie eine Form von Kraft, die nicht schreien muss.",
                ],
            })

        if consequences.get("harmonie_boss_resonance") and "harmonie_boss_resonance" not in self.state.get("reflection_seen", []):
            reflections.append({
                "key": "harmonie_boss_resonance",
                "music": "story1_theme.mp3",
                "lines": [
                    "🎼 Nach dem Sieg bleibt kein Triumphlaerm in Maatis zurueck, sondern ein ruhiger Nachklang.",
                    "Er merkt, dass Harmonie nicht bloss Frieden meint, sondern die Faehigkeit, Druck in Form zu verwandeln.",
                    "Zum ersten Mal fuehlt sich Schutz wie ein Rhythmus an, nicht wie ein Reflex.",
                ],
            })

        if consequences.get("respekt_final_restored") and "respekt_final_restored" not in self.state.get("reflection_seen", []):
            reflections.append({
                "key": "respekt_final_restored",
                "music": "story3_theme.mp3",
                "lines": [
                    "⚖️ Ein wiederhergestelltes Prinzip trifft Maatis anders, seit er den Weg des Respekts gewaehlt hat.",
                    "Nicht Macht, sondern Grenze erscheint ihm ploetzlich als das, was die Welt traegt.",
                    "Er spuert: Manche Siege werden erst wahr, wenn sie niemanden entwürdigen.",
                ],
            })

        if consequences.get("truth_boss_insight") and "truth_boss_insight" not in self.state.get("reflection_seen", []):
            reflections.append({
                "key": "truth_boss_insight",
                "music": "quest2_reflection.mp3",
                "lines": [
                    "🔎 Maatis kann den letzten Boss noch einmal vor sich sehen, aber diesmal ohne Nebel.",
                    "Seine Schwaechen, seine Muster, sogar der Moment des Kippens werden klarer als zuvor.",
                    "Wahrheit fuehlt sich ploetzlich nicht kalt an, sondern wie Licht mit Richtung.",
                ],
            })

        if consequences.get("protect_boss_mercy") and "protect_boss_mercy" not in self.state.get("reflection_seen", []):
            reflections.append({
                "key": "protect_boss_mercy",
                "music": "story1_theme.mp3",
                "lines": [
                    "🛡️ Maatis denkt an den Kampf zurück und erschrickt nicht ueber seine eigene Haerte.",
                    "Er hat gesiegt, ohne Schutz vom Leben zu trennen.",
                    "Vielleicht ist genau das der Unterschied zwischen Gewalt und getragener Kraft.",
                ],
            })

        if consequences.get("remember_world_echo") and "remember_world_echo" not in self.state.get("reflection_seen", []):
            reflections.append({
                "key": "remember_world_echo",
                "music": "story3_theme.mp3",
                "lines": [
                    "🌌 Zwischen zwei Atemzuegen hat Maatis das Gefuehl, dass die Welt wirklich antwortet.",
                    "Nicht laut, eher wie eine Erinnerung, die von aussen zurueckkehrt.",
                    "Sein Geluebde war nicht nur ein Satz. Es hat inzwischen Spuren im Ganzen hinterlassen.",
                ],
            })

        return reflections[0] if reflections else None

    # -------------------------------------------------
    # COMMAND HANDLER
    # -------------------------------------------------
    def command(self, cmd: str, context=None):
        c = (cmd or "").strip().lower()

        if c == "/storyreset":
            self.state = self._default_state()
            self._save_state()
            return True, "🔄 Story-Progress zurückgesetzt."

        if c == "/journal":
            return True, self._render_journal()

        return None

    # -------------------------------------------------
    # BEFORE CHAT — STORY TRIGGER
    # -------------------------------------------------
    def before_chat(self, user_input: str, context=None):
        self._inject_story_context(context)

        # Commands nicht abfangen
        if user_input.strip().startswith("/"):
            return False, user_input

        # Nachrichten-Zähler hochzählen
        self.state["messages_total"] += 1
        self._save_state()

        reflection = self._build_inner_reflection()
        if reflection:
            self._play_reflection(reflection)
            return False, user_input

        entry = self._find_story_for_state()
        if entry:
            self._play_story_entry(entry, context)
            return False, user_input

        # passende Story finden
        entry = self._find_story_for_message_count()
        if not entry:
            return False, user_input

        self._play_story_entry(entry, context)

        # Danach normal weiter zum Modell
        return False, user_input

    def _play_reflection(self, reflection: dict):
        key = reflection.get("key")
        lines = list(reflection.get("lines", []))
        music = reflection.get("music")
        lines.extend(self._profile_scene_lines(key))
        if not lines:
            return

        print("\n🫀 Innere Szene\n")
        if music:
            self._start_music_once(music)
        for line in lines:
            input("⏎ Weiter… ")
            print(line)
            time.sleep(0.05)
        self._stop_music()
        seen = self.state.setdefault("reflection_seen", [])
        if key and key not in seen:
            seen.append(key)
            self._append_journal_entry(
                key=f"reflection:{key}",
                kind="reflection",
                title="Innere Szene",
                summary=lines[0] if lines else "Maatis haelt inne.",
                detail=lines[-1] if len(lines) > 1 else "",
            )
            self._save_state()

    def _play_story_entry(self, entry, context=None):
        story_obj = self._load_story_module(entry.get("module"))
        if story_obj:
            music_file = entry.get("music")
            scene_lines = self._profile_scene_lines(entry.get("module", ""))
            self._run_story_interactive(story_obj, music_file, extra_lines=scene_lines)

            played = self.state.get("played", [])
            played.append(entry["id"])
            self.state["played"] = played
            self._append_journal_entry(
                key=f"story:{entry['id']}",
                kind="story",
                title=entry.get("name", f"Story {entry['id']}"),
                summary="Eine neue Szene hat Maatis' Weg erweitert.",
                detail=f"Ausgeloest durch {entry.get('module', 'story')}.",
            )
            self._save_state()

            profile_name = entry.get("profile")
            if profile_name and context and "profile_loader" in context:
                try:
                    pl = context["profile_loader"]
                    profile = pl.load_profile(profile_name)
                    systemprompt = profile.get("systemprompt")
                    if systemprompt and "conversation" in context:
                        conv = context["conversation"]
                        if conv and conv[0]["role"] == "system":
                            conv[0]["content"] = systemprompt
                    print(f"🎭 StoryLoader: Profil gewechselt zu {profile_name}")
                except Exception as e:
                    print(f"⚠ Konnte Profil {profile_name} nicht laden: {e}")

    # -------------------------------------------------
    # AFTER CHAT — keine Änderung
    # -------------------------------------------------
    def after_response(self, reply: str, context=None):
        return reply

    def on_startup(self, context=None):
        print("📖 StoryLoader Plugin geladen – Story-Engine aktiv.")
