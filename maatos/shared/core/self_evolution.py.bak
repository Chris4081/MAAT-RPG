# SelfEvolutionEngine v4.4 — Chat-Notification Edition
# ----------------------------------------------------
# • Kein Levelsystem
# • XP nur symbolisch (Evo-XP)
# • +5 Battle-XP pro Evo-Patch
# • Max 3 Evolution-Schritte pro Tag
# • Patch-Rotation (max. 20 Files)
# • Ultra-low-context
# • Sichtbarer Chat-Hinweis nach jedem Patch:
#     ✨ KI hat sich verbessert (+50 Evo-XP | +5 Battle-XP)

import os
import json
import datetime


class SelfEvolutionEngine:
    DAILY_LIMIT = 3          # max. 3 Evolutionsschritte pro Tag
    XP_PER_PATCH = 50        # interne symbolische XP
    BATTLE_XP = 5            # XP für BattleCore (wenn vorhanden)
    MAX_PATCH_FILES = 20     # begrenzt Speicher & Kontextverbrauch

    def __init__(self, memory, alignment_kernel, identity_kernel, core=None, base_dir=None):
        self.memory = memory
        self.alignment_kernel = alignment_kernel
        self.identity_kernel = identity_kernel
        self.core = core  # wichtig für BattleXP

        if base_dir is None:
            base_dir = os.path.join(os.getcwd(), "data")

        self.base_dir = os.path.join(base_dir, "evo")
        self.log_path = os.path.join(self.base_dir, "evolution_log.jsonl")
        self.state_path = os.path.join(self.base_dir, "state.json")
        self.patches_dir = os.path.join(self.base_dir, "patches")

        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.patches_dir, exist_ok=True)

        self.state = self._load_state()

    # -----------------------------------------------------------
    # STATE
    # -----------------------------------------------------------
    def _load_state(self):
        if os.path.exists(self.state_path):
            try:
                data = json.load(open(self.state_path, "r"))
                data.setdefault("xp", 0)
                data.setdefault("today", datetime.date.today().isoformat())
                data.setdefault("today_patches", 0)
                return data
            except:
                pass
        today = datetime.date.today().isoformat()
        return {"xp": 0, "today_patches": 0, "today": today}

    def _save_state(self):
        today = datetime.date.today().isoformat()
        if self.state["today"] != today:
            self.state["today"] = today
            self.state["today_patches"] = 0
        json.dump(self.state, open(self.state_path, "w"), indent=2)

    def _today_limit_reached(self):
        today = datetime.date.today().isoformat()
        if self.state["today"] != today:
            self.state["today"] = today
            self.state["today_patches"] = 0
            self._save_state()
        return self.state["today_patches"] >= self.DAILY_LIMIT

    # -----------------------------------------------------------
    # PATCH ERZEUGUNG
    # -----------------------------------------------------------
    def _build_patch(self, trigger):
        now = datetime.datetime.now().replace(microsecond=0)
        patch_id = now.strftime("%Y%m%d-%H%M%S")

        summaries = {
            "low_maat": "Antwort klarer und harmonischer strukturieren.",
            "high_drift": "Identität stabilisieren, Rollenkerne nachschärfen.",
            "high_emotion": "Emotionale Balance verbessern.",
        }

        return {
            "id": patch_id,
            "time": now.isoformat(" "),
            "trigger": trigger,
            "summary": summaries.get(trigger, "Optimierungsschritt"),
            "status": "pending",
        }

    def _write_patch(self, patch):
        # Log schreiben
        with open(self.log_path, "a") as f:
            f.write(json.dumps(patch, ensure_ascii=False) + "\n")

        # Einzeldatei
        path = os.path.join(self.patches_dir, f"{patch['id']}.json")
        with open(path, "w") as f:
            json.dump(patch, f, indent=2)

        # Rotation
        files = sorted(os.listdir(self.patches_dir))
        if len(files) > self.MAX_PATCH_FILES:
            overflow = len(files) - self.MAX_PATCH_FILES
            for old in files[:overflow]:
                try:
                    os.remove(os.path.join(self.patches_dir, old))
                except:
                    pass

    # -----------------------------------------------------------
    # BATTLE XP vergeben
    # -----------------------------------------------------------
    def _grant_battle_xp(self):
        try:
            if self.core and hasattr(self.core, "battle"):
                self.core.battle.state.add_xp(self.BATTLE_XP)
        except Exception:
            pass

    # -----------------------------------------------------------
    # HAUPTFUNKTION
    # -----------------------------------------------------------
    def evaluate_and_evolve(self, reply, meta):
        maat = float(meta.get("maat_score", 0))
        emo = float(meta.get("emotion", 0))
        drift = float(meta.get("identity_drift", 0))

        triggers = []
        if maat < 0.72:
            triggers.append("low_maat")
        if drift > 0.25:
            triggers.append("high_drift")
        if abs(emo) > 0.75:
            triggers.append("high_emotion")

        # Kein Trigger → kein Patch
        if not triggers:
            return None

        # Tageslimit
        if self._today_limit_reached():
            return {
                "status": "blocked",
                "reason": "Limit 3 erreicht.",
                "chat_notice": "⚠️ KI erreicht heute ihr Evolutionslimit.",
                "triggers": triggers,
            }

        # Patch erstellen
        trigger = triggers[0]
        patch = self._build_patch(trigger)
        self._write_patch(patch)

        # XP vergeben
        self.state["xp"] += self.XP_PER_PATCH
        self.state["today_patches"] += 1
        self._save_state()

        # Battle XP
        self._grant_battle_xp()

        patch["status"] = "applied"
        patch["xp_gained"] = self.XP_PER_PATCH
        patch["battle_xp"] = self.BATTLE_XP

        # *** CHAT-NOTIFICATION ***
        patch["chat_notice"] = (
            f"✨ KI hat sich verbessert "
            f"(+{self.XP_PER_PATCH} Evo-XP | +{self.BATTLE_XP} Battle-XP)"
        )

        return patch

    # -----------------------------------------------------------
    # STATUS
    # -----------------------------------------------------------
    def get_status_text(self):
        xp = self.state.get("xp", 0)
        today = self.state.get("today_patches", 0)
        return (
            "📈 Self-Evolution Status\n"
            f"  Evo-XP    : {xp}\n"
            f"  Heute     : {today} / {self.DAILY_LIMIT}\n"
            "  Battle-XP : +5 pro Evolutionsschritt\n"
        )

    # ---------------------------------------------
    # NEU in v4.4: Kontext-Auswertung
    # ---------------------------------------------
    def evaluate_from_context(self, reply: str, context: dict | None):
        """
        Liest Maat-Score + Emotion aus dem gemeinsamen context
        und ruft damit evaluate_and_evolve().
        """
        if context is None:
            context = {}

        maat_meta = context.get("maat_meta") or {}
        fields    = context.get("maat_fields") or {}

        # Defaults, falls Plugins (noch) nichts gesetzt haben
        maat_score = float(maat_meta.get("maat_score", 0.9))      # eher zu hoch → seltene Patches
        emotion_E  = float(fields.get("emotion_E", 0.0))          # -1..1
        identity_drift = float(maat_meta.get("identity_drift", 0.0))  # später per Plugin

        meta = {
            "maat_score": maat_score,
            "emotion": emotion_E,
            "identity_drift": identity_drift,
        }

        return self.evaluate_and_evolve(reply, meta)


    # ---------------------------------------------
    # BRIDGE: Kontext → Meta (für ChatLoop)
    # ---------------------------------------------
    def evaluate_from_context(self, reply, context=None):
        """
        Baut ein meta-Dict aus context["maat_meta"] + context["maat_fields"]
        und ruft damit evaluate_and_evolve().
        """
        context = context or {}

        maat_meta = context.get("maat_meta") or {}
        fields    = context.get("maat_fields") or {}

        meta = {}

        # 1) Maat-Score (aus Maat-Value-Plugin)
        if "maat_score" in maat_meta:
            meta["maat_score"] = maat_meta["maat_score"]

        # 2) Emotion (aggregierter Wert aus Emotion-Plugin)
        if "emotion_E" in fields:
            meta["emotion"] = fields["emotion_E"]

        # 3) Kohärenz-Drift (ΔD aus Emotion-Plugin)
        if "deltaD_from_emotion" in fields:
            meta["identity_drift"] = fields["deltaD_from_emotion"]

        # Fallbacks, falls irgendwas fehlt
        # → evaluate_and_evolve macht dann ganz normal die Trigger-Logik:
        #   low_maat / high_drift / high_emotion
        return self.evaluate_and_evolve(reply, meta)