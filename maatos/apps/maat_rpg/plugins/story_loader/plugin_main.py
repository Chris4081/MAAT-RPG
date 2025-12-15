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


class Plugin:
    type = "chat"
    commands = {
        "/storyreset": "Setzt den Story-Fortschritt zurück."
    }

    def __init__(self):
        # Plugin- & Story-Verzeichnisse
        self.plugin_dir = os.path.dirname(__file__)
        self.story_dir = os.path.join(self.plugin_dir, "stories")
        os.makedirs(self.story_dir, exist_ok=True)

        # Pfade
        self.config_path = os.path.join(self.story_dir, "config.json")
        self.state_path = os.path.join(self.plugin_dir, "story_state.json")

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
            "active_profile": None
        }

    def _load_state(self):
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data.setdefault("messages_total", 0)
                data.setdefault("played", [])
                data.setdefault("active_profile", None)
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
    def _run_story_interactive(self, story, music_filename: str = None):
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

        for line in lines:
            input("⏎ Weiter… ")
            print(line)
            time.sleep(0.05)

        # 🎵 MUSIK-NACHFRAGE
        print("\n📯 Die Szene endet.")
        ans = input("🎵 Musik bis zum Ende weiterlaufen lassen? (J/N) [ENTER = N]: ").strip().lower()

        if ans != "j":
            self._stop_music()
        else:
            print("🎵 Musik läuft weiter, bis der Track von selbst endet.")

        input("\n⏎ Drücke ENTER, um zum Chat zurückzukehren… ")

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

    # -------------------------------------------------
    # COMMAND HANDLER
    # -------------------------------------------------
    def command(self, cmd: str, context=None):
        c = (cmd or "").strip().lower()

        if c == "/storyreset":
            self.state = self._default_state()
            self._save_state()
            return True, "🔄 Story-Progress zurückgesetzt."

        return None

    # -------------------------------------------------
    # BEFORE CHAT — STORY TRIGGER
    # -------------------------------------------------
    def before_chat(self, user_input: str, context=None):
        # Commands nicht abfangen
        if user_input.strip().startswith("/"):
            return False, user_input

        # Nachrichten-Zähler hochzählen
        self.state["messages_total"] += 1
        self._save_state()

        # passende Story finden
        entry = self._find_story_for_message_count()
        if not entry:
            return False, user_input

        story_obj = self._load_story_module(entry.get("module"))
        if story_obj:
            music_file = entry.get("music")

            # Story laufen lassen
            self._run_story_interactive(story_obj, music_file)

            # Story als abgespielt markieren
            played = self.state.get("played", [])
            played.append(entry["id"])
            self.state["played"] = played
            self._save_state()

            # Optional: Profilwechsel
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

        # Danach normal weiter zum Modell
        return False, user_input

    # -------------------------------------------------
    # AFTER CHAT — keine Änderung
    # -------------------------------------------------
    def after_response(self, reply: str, context=None):
        return reply

    def on_startup(self, context=None):
        print("📖 StoryLoader Plugin geladen – Story-Engine aktiv.")