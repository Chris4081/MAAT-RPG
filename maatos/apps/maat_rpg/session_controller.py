# -*- coding: utf-8 -*-
from __future__ import annotations

from threading import Lock
from typing import Callable

from shared.core.maat_paths import get_models_dir

from . import session_bootstrap, session_shared
from .session_models import BattleSnapshot, ChoiceRequest, PlayerSnapshot, SystemEvent, UiSnapshot


SnapshotCallback = Callable[[UiSnapshot], None]
TokenCallback = Callable[[str], None]
EventCallback = Callable[[SystemEvent], None]
ChoiceCallback = Callable[[ChoiceRequest], None]
DoneCallback = Callable[[], None]


TEXT = {
    "de": {
        "app_title": "MAAT-RPG Desktop Alpha",
        "model_status": "Lokale Modell-Bruecke bereit",
        "status_ready": "Bereit",
        "welcome": "Die GUI-Session wurde gestartet. Profil, Titelkontext und Settings laufen jetzt schon ueber dieselbe gemeinsame Session-Schicht wie der CLI-Start.",
        "help": "Nutze normalen Text, `/help`, `/fight`, `/quests` oder die Kampfbuttons rechts.",
        "unknown_command": "Unbekannter Befehl: {cmd}",
        "quests": "Aktive Quest: Lerne die MAAT-KI kennen. Noch {remaining}/10 Nachrichten uebrig.",
        "fight_start": "Demo-Kampf gestartet. Resonanz, HUD und Kampfaktionen laufen lokal, aber Profil und Titelkontext kommen schon aus dem echten Spielstand.",
        "battle_missing": "Es ist aktuell kein Kampf aktiv.",
        "battle_win": "Der Demo-Gegner ist besiegt. Rewards bleiben in diesem Scaffold absichtlich nur lokal sichtbar.",
        "battle_status": "Kampf aktiv",
        "chat_status": "Chat aktiv",
        "system_choice": "Waehle eine der Kampfaktionen oder tippe weiter im Chat.",
        "response_maat": "MAAT wirkt hier wie ein guter Resonanztest: Wenn Harmonie, Balance, Schoepfungskraft, Verbundenheit und Respekt gemeinsam tragen, fuehlt sich selbst ein Interface lebendig an.",
        "response_gui": "Eine gute MAAT-RPG-GUI sollte nicht das Terminal nachbauen, sondern Spielzustand, Resonanz und Entscheidungen sichtbar machen.",
        "response_default": "Die GUI teilt sich jetzt schon Profil, Titelkontext und Settings mit dem CLI-Pfad. Als naechstes koennen wir die echte Chat- und Kampfsteuerung weiter aus `basic.py` herausziehen.",
        "battle_enemy": "Echo Wanderer des Risses",
        "weaknesses": ["Harmonie", "Balance", "Schoepfungskraft", "Verbundenheit", "Respekt"],
        "auras": ["keine", "shatter", "resonance", "silence"],
        "battle_logs": {
            "attack": "Du triffst den Gegner mit einem klaren Prinzip-Schlag.",
            "skills": "Eine besondere Faehigkeit verdichtet die Resonanz im Raum.",
            "focus": "Du sammelst Resonanz und stabilisierst deinen Schild.",
            "potion": "Ein Heiltrank bringt neue Kraft zurueck.",
            "impulse": "Ein MAAT-Impuls bricht durch das Feld.",
            "escape": "Du ziehst dich zurück. Keine Belohnung für diesen Übungskampf.",
        },
    },
    "en": {
        "app_title": "MAAT-RPG Desktop Alpha",
        "model_status": "Local model bridge ready",
        "status_ready": "Ready",
        "welcome": "The GUI session has started. Profile state, title context, and settings now already run through the same shared session layer as the CLI startup.",
        "help": "Use plain text, `/help`, `/fight`, `/quests`, or the battle buttons on the right.",
        "unknown_command": "Unknown command: {cmd}",
        "quests": "Active quest: Get to Know MAAT-KI. {remaining}/10 messages remaining.",
        "fight_start": "Demo battle started. Resonance, HUD, and battle actions are still local, but profile and title context already come from the real save state.",
        "battle_missing": "There is no active battle right now.",
        "battle_win": "The demo enemy has been defeated. In this scaffold, rewards intentionally remain local and non-persistent.",
        "battle_status": "Battle active",
        "chat_status": "Chat active",
        "system_choice": "Choose one of the battle actions or continue typing in chat.",
        "response_maat": "MAAT feels like a strong resonance test here: when harmony, balance, creative power, connectedness, and respect carry together, even an interface starts to feel alive.",
        "response_gui": "A good MAAT-RPG GUI should not rebuild the terminal. It should make game state, resonance, and decisions visible.",
        "response_default": "The GUI now already shares profile, title context, and settings with the CLI path. The next step can move more of the real chat and battle flow out of `basic.py`.",
        "battle_enemy": "Echo Wanderer of the Rift",
        "weaknesses": ["Harmony", "Balance", "Creation", "Connectedness", "Respect"],
        "auras": ["none", "shatter", "resonance", "silence"],
        "battle_logs": {
            "attack": "You hit the enemy with a clear principle strike.",
            "skills": "A special ability condenses resonance in the arena.",
            "focus": "You gather resonance and stabilize your shield.",
            "potion": "A healing potion restores your footing.",
            "impulse": "A MAAT impulse breaks through the field.",
            "escape": "You retreat. No rewards for this practice battle.",
        },
    },
}


class MaatRpgSession:
    def __init__(self):
        self._lock = Lock()
        self._token_callbacks: list[TokenCallback] = []
        self._snapshot_callbacks: list[SnapshotCallback] = []
        self._event_callbacks: list[EventCallback] = []
        self._choice_callbacks: list[ChoiceCallback] = []
        self._done_callbacks: list[DoneCallback] = []

        active_slot = session_shared.active_profile_slot()
        self._profile_index = max(0, min(active_slot - 1, session_shared.PROFILE_SLOT_COUNT - 1))
        self._language = session_shared.profile_language(active_slot, fallback="de")

        self._player_state = PlayerSnapshot()
        self._battle_state = BattleSnapshot()
        self._profile_root = ""
        self._messages_total = 0
        self._status_mode = "ready"
        self._music_enabled = False
        self._voice_enabled = True
        self._thinking_enabled = False
        self._rpg_context_enabled = False
        self._hallu_mode = False
        self._command_router = session_bootstrap.build_command_router(
            self._language,
            clear_handler=lambda args: "",
            exit_handler=lambda args: (
                "Schliesse das Fenster oder gehe zurueck ins Menu."
                if self._language == "de"
                else "Close the window or go back to the menu."
            ),
        )

        self._hydrate_from_shared(reset_battle=True)
        self._snapshot = self._build_snapshot()

    def _t(self, key: str):
        return TEXT.get(self._language, TEXT["en"]).get(key)

    def _profile_slot(self) -> int:
        return self._profile_index + 1

    def _profile_names(self) -> list[str]:
        return session_shared.profile_labels(self._language)

    def _update_status_text(self) -> str:
        if self._status_mode == "battle":
            return self._t("battle_status")
        if self._status_mode == "chat":
            return self._t("chat_status")
        return f"{self._t('status_ready')} | {self._profile_root}"

    def _apply_localized_profile_fields(self) -> None:
        ctx = session_shared.title_context(language=self._language, slot=self._profile_slot())
        self._player_state.path_profile = ctx["title"]
        self._player_state.rank = ctx["rank"]
        self._player_state.motive = ctx["motif"]

    def _load_settings_flags(self) -> None:
        settings = session_shared.load_profile_settings(self._profile_slot())
        self._music_enabled = bool(settings.get("music_enabled", False))
        self._voice_enabled = bool(settings.get("say_tts_enabled", True))
        self._thinking_enabled = bool(settings.get("thinking_enabled", False))
        self._rpg_context_enabled = bool(settings.get("rpg_context_enabled", False))
        self._hallu_mode = bool(settings.get("hallu_mode", False))

    def _refresh_command_router(self) -> None:
        self._command_router = session_bootstrap.build_command_router(
            self._language,
            clear_handler=lambda args: "",
            exit_handler=lambda args: (
                "Schliesse das Fenster oder gehe zurueck ins Menu."
                if self._language == "de"
                else "Close the window or go back to the menu."
            ),
        )

    def _hydrate_from_shared(self, reset_battle: bool) -> None:
        summary = session_shared.profile_summary(self._profile_slot(), language=self._language)
        self._profile_root = str(summary["root"])
        self._messages_total = int(summary["messages_total"])
        self._player_state = PlayerSnapshot(
            hp=int(summary["hp"]),
            max_hp=int(summary["max_hp"]),
            level=int(summary["level"]),
            xp=int(summary["xp"]),
            next_xp=int(summary["next_xp"]),
            gold=int(summary["gold"]),
            potions=int(summary["potions"]),
            boss_victories=int(summary["boss_wins"]),
            final_victories=int(summary["final_wins"]),
            principles_restored=int(summary["principles"]),
        )
        self._apply_localized_profile_fields()
        self._load_settings_flags()
        self._refresh_command_router()
        if reset_battle:
            self._battle_state = BattleSnapshot()
            self._status_mode = "ready"

    def _build_snapshot(self) -> UiSnapshot:
        return UiSnapshot(
            language=self._language,
            profile_name=session_shared.profile_slot_label(self._profile_slot(), self._language),
            profile_labels=self._profile_names(),
            app_title=self._t("app_title"),
            model_status=f"{self._t('model_status')} | {get_models_dir()}",
            status_text=self._update_status_text(),
            thinking_enabled=self._thinking_enabled,
            rpg_context_enabled=self._rpg_context_enabled,
            hallu_mode=self._hallu_mode,
            music_enabled=self._music_enabled,
            voice_enabled=self._voice_enabled,
            player=self._player_state,
            battle=self._battle_state,
        )

    def on_token(self, callback: TokenCallback) -> None:
        self._token_callbacks.append(callback)

    def on_snapshot(self, callback: SnapshotCallback) -> None:
        self._snapshot_callbacks.append(callback)

    def on_event(self, callback: EventCallback) -> None:
        self._event_callbacks.append(callback)

    def on_choice(self, callback: ChoiceCallback) -> None:
        self._choice_callbacks.append(callback)

    def on_done(self, callback: DoneCallback) -> None:
        self._done_callbacks.append(callback)

    def _emit_snapshot(self) -> None:
        for callback in list(self._snapshot_callbacks):
            callback(self._snapshot)

    def _emit_event(self, kind: str, message: str) -> None:
        event = SystemEvent(kind=kind, message=message)
        for callback in list(self._event_callbacks):
            callback(event)

    def _emit_choice(self, prompt: str, options: list[str]) -> None:
        request = ChoiceRequest(prompt=prompt, options=options)
        for callback in list(self._choice_callbacks):
            callback(request)

    def _emit_tokens(self, text: str) -> None:
        for chunk in self._chunk_text(text):
            for callback in list(self._token_callbacks):
                callback(chunk)
        for callback in list(self._done_callbacks):
            callback()

    @staticmethod
    def _chunk_text(text: str, size: int = 18) -> list[str]:
        return [text[i:i + size] for i in range(0, len(text), size)] or [""]

    def _quest_text(self) -> str:
        remaining = max(0, 10 - int(self._messages_total))
        return self._t("quests").format(remaining=remaining)

    def start(self) -> None:
        with self._lock:
            session_shared.write_profile_manager_state({"active_profile": self._profile_slot()})
            session_shared.prepare_profile_runtime(self._profile_slot(), language_hint=self._language)
            self._hydrate_from_shared(reset_battle=False)
            self._snapshot = self._build_snapshot()
        self._emit_snapshot()
        self._emit_event("system", self._t("welcome"))
        self._emit_event("system", self._t("help"))

    def shutdown(self) -> None:
        self._emit_event("system", "Session closed.")

    def get_snapshot(self) -> UiSnapshot:
        return self._snapshot

    def set_language(self, language: str) -> None:
        if language not in ("de", "en"):
            return
        with self._lock:
            session_shared.write_application_language(language)
            self._language = language
            self._refresh_command_router()
            self._load_settings_flags()
            self._apply_localized_profile_fields()
            self._snapshot = self._build_snapshot()
        self._emit_snapshot()

    def set_profile_index(self, index: int) -> None:
        names = self._profile_names()
        index = max(0, min(index, len(names) - 1))
        with self._lock:
            self._profile_index = index
            self._language = session_shared.profile_language(self._profile_slot(), fallback="de")
            session_shared.write_profile_manager_state({"active_profile": self._profile_slot()})
            self._hydrate_from_shared(reset_battle=True)
            self._snapshot = self._build_snapshot()
        self._emit_snapshot()

    def set_setting(self, name: str, enabled: bool) -> None:
        key_map = {
            "music": "music_enabled",
            "voice": "say_tts_enabled",
            "thinking": "thinking_enabled",
            "rpg_context": "rpg_context_enabled",
            "hallu": "hallu_mode",
        }
        key = key_map.get(name)
        if not key:
            return
        with self._lock:
            session_shared.write_profile_settings(self._profile_slot(), {key: bool(enabled)})
            self._load_settings_flags()
            self._snapshot = self._build_snapshot()
        self._emit_snapshot()

    def send_text(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        if text.startswith("/"):
            self.send_command(text)
            return

        lower = text.lower()
        if "maat" in lower:
            reply = self._t("response_maat")
        elif "gui" in lower or "fenster" in lower or "window" in lower:
            reply = self._t("response_gui")
        else:
            reply = self._t("response_default")

        with self._lock:
            self._messages_total += 1
            if not self._battle_state.active:
                self._status_mode = "chat"
            self._snapshot = self._build_snapshot()
        self._emit_snapshot()
        self._emit_tokens(reply)

    def send_command(self, command: str) -> None:
        cmd = (command or "").strip()
        lower = cmd.lower()
        if lower == "/fight" and self._battle_state.active:
            return
        if lower == "/quests":
            reply = self._quest_text()
        elif lower == "/fight":
            self._start_demo_battle()
            reply = self._t("fight_start")
        else:
            reply = self._command_router.execute(cmd, {"session_mode": "gui"})
        self._emit_tokens(reply)

    def handle_battle_action(self, action: str) -> None:
        if action not in {"attack", "skills", "focus", "potion", "impulse", "escape"}:
            return
        missing_text = None
        with self._lock:
            if not self._battle_state.active:
                missing_text = self._t("battle_missing")
            elif action == "potion" and self._player_state.potions <= 0:
                missing_text = "Keine Heiltränke übrig." if self._language == "de" else "No potions left."
            elif action == "impulse" and self._battle_state.resonance < 35:
                missing_text = "Du brauchst 35 Resonanz." if self._language == "de" else "You need 35 resonance."
            else:
                logs = self._t("battle_logs")
                self._battle_state.last_log = logs.get(action, logs["attack"])

                if action == "attack":
                    self._battle_state.enemy_hp = max(0, self._battle_state.enemy_hp - 14)
                    self._battle_state.resonance = min(100, self._battle_state.resonance + 12)
                elif action == "skills":
                    self._battle_state.enemy_hp = max(0, self._battle_state.enemy_hp - 18)
                    self._battle_state.resonance = min(100, self._battle_state.resonance + 8)
                elif action == "focus":
                    self._player_state.hp = min(self._player_state.max_hp, self._player_state.hp + 10)
                    self._battle_state.resonance = min(100, self._battle_state.resonance + 20)
                elif action == "potion":
                    if self._player_state.potions > 0:
                        self._player_state.potions -= 1
                        self._player_state.hp = min(self._player_state.max_hp, self._player_state.hp + 28)
                    self._battle_state.resonance = min(100, self._battle_state.resonance + 4)
                elif action == "impulse":
                    self._battle_state.enemy_hp = max(0, self._battle_state.enemy_hp - 26)
                    self._battle_state.resonance = max(0, self._battle_state.resonance - 35)
                elif action == "escape":
                    self._battle_state.active = False
                    self._battle_state.last_log = self._t("battle_logs")["escape"]
                    self._status_mode = "chat"

                if self._battle_state.active and self._battle_state.enemy_hp > 0 and action != "escape":
                    self._player_state.hp = max(0, self._player_state.hp - 6)
                    self._battle_state.charge = (self._battle_state.charge + 1) % max(1, self._battle_state.charge_max)
                    weaknesses = self._t("weaknesses")
                    auras = self._t("auras")
                    self._battle_state.weakness = weaknesses[(self._battle_state.charge + 1) % len(weaknesses)]
                    self._battle_state.aura = auras[self._battle_state.charge % len(auras)]

                if self._player_state.hp <= 0 and self._battle_state.active:
                    self._battle_state.active = False
                    self._status_mode = "chat"
                    self._battle_state.last_log = "Übung beendet: Du bist besiegt." if self._language == "de" else "Practice ended: you were defeated."

                if self._battle_state.enemy_hp <= 0 and self._battle_state.active:
                    self._battle_state.active = False
                    self._status_mode = "chat"
                    self._player_state.gold += 12
                    self._player_state.xp += 22
                    while self._player_state.xp >= session_shared.xp_needed_for_level(self._player_state.level + 1):
                        self._player_state.level += 1
                    self._battle_state.last_log = self._t("battle_win")
                    self._player_state.next_xp = session_shared.xp_needed_for_level(self._player_state.level + 1)

                self._snapshot = self._build_snapshot()

        if missing_text:
            self._emit_tokens(missing_text)
            return

        self._emit_snapshot()
        self._emit_tokens(self._battle_state.last_log)
        if self._battle_state.active:
            self._emit_choice(
                self._t("system_choice"),
                ["attack", "skills", "focus", "potion", "impulse", "escape"],
            )

    def submit_choice(self, value: str) -> None:
        self.handle_battle_action(value)

    def _start_demo_battle(self) -> None:
        with self._lock:
            self._player_state.hp = self._player_state.max_hp
            self._battle_state = BattleSnapshot(
                active=True,
                enemy_name=self._t("battle_enemy"),
                enemy_hp=72,
                enemy_max_hp=72,
                resonance=18,
                weakness=self._t("weaknesses")[2],
                aura=self._t("auras")[0],
                phase="1",
                charge=0,
                charge_max=3,
                last_log=self._t("fight_start"),
            )
            self._status_mode = "battle"
            self._snapshot = self._build_snapshot()
        self._emit_snapshot()
        self._emit_choice(
            self._t("system_choice"),
            ["attack", "skills", "focus", "potion", "impulse", "escape"],
        )
