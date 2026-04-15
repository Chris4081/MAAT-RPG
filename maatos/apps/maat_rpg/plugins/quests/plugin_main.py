import os
from datetime import datetime
import json
from shared.core.rpg_i18n import get_language
from shared.core.maat_paths import state_file

# plugin_main.py (ganz oben, nach imports)

# level_tier: -1 = Pre-Intro-Teaser (Nachricht 10-19), 0 = Intro (ab 20 Nachrichten),
# 1 = Level 2, 2 = Level 4, 3 = Level 6, 4 = Level 8
# Farbe: aktueller Tier=🔴 (max XP), vorheriger=🟡, älter=🟢 (weniger XP)

# Pre-Intro Teaser-Quest: wird zwischen Nachricht 10-19 im Questlog angezeigt,
# damit Spieler das kommende Quest-System schon erahnen und MAAT erkunden.
PRE_INTRO_QUESTS = [
    {
        "id": "know_maat_ki",
        "name": "Lerne die MAAT-KI kennen",
        "desc": "Sprich in den ersten zehn Nachrichten mit der MAAT-KI, um ihren Ton und ihren Weg kennenzulernen.",
        "type": "counter",
        "counter_key": "messages_total",
        "target": 10,
        "reward_xp": 20,
        "level_tier": -2,
    },
    {
        "id": "maat_first_calc",
        "name": "Erste Maat-Berechnung",
        "desc": "Berechne mit der MAAT-KI deine ersten Maat-Werte — siehe Einführung. Frage zum Beispiel: 'Berechne den Maat-Wert von X'.",
        "type": "chat_keyword",
        "keywords": ["berechne maat", "maat-wert berechnen", "maat wert berechnen", "berechne den maat"],
        "reward_xp": 15,
        "level_tier": -1,
    },
]

BASE_QUESTS = [
    {
        "id": "maat_person",
        "name": "Maat-Wert einer Person",
        "desc": "Bitte die MAAT-KI, den Maat-Wert einer historischen Person zu berechnen.",
        "type": "chat_keyword",
        "keywords": ["maat-wert", "harmonie", "balance", "schöpfungskraft"],
        "reward_xp": 25,
        "repeatable": False,
        "level_tier": 0,
    },
    {
        "id": "first_win",
        "name": "Erster Sieg",
        "desc": "Gewinne einen Kampf im MAAT-RPG.",
        "type": "counter",
        "counter_key": "battle_wins",
        "target": 1,
        "reward_xp": 30,
        "repeatable": False,
        "level_tier": 0,
    },
    {
        "id": "maat_mona",
        "name": "Maat-Wert der Mona Lisa",
        "desc": "Bitte die MAAT-KI, den Maat-Wert der Mona Lisa zu berechnen.",
        "type": "chat_keyword",
        "keywords": ["mona lisa", "maat-wert der mona lisa"],
        "reward_xp": 35,
        "level_tier": 0,
    },
    {
        "id": "maat_light",
        "name": "Licht der Harmonie",
        "desc": "Bitte die MAAT-KI, den Maat-Wert von Licht zu erklären.",
        "type": "chat_keyword",
        "keywords": ["maat-wert von licht", "licht"],
        "reward_xp": 35,
        "level_tier": 0,
    },
    {
        "id": "maat_elements",
        "name": "Vier Elemente der Maat",
        "desc": "Frage die MAAT-KI nach den Maat-Werten von Wasser, Feuer, Erde und Luft.",
        "type": "chat_keyword",
        "keywords": ["maat-wert der elemente", "wasser feuer erde luft"],
        "reward_xp": 45,
        "level_tier": 1,
    },
    {
        "id": "energy_compare",
        "name": "Energie der Zukunft",
        "desc": "Bitte die MAAT-KI, Solarenergie und Atomkraft nach Maat-Wert zu vergleichen.",
        "type": "chat_keyword",
        "keywords": ["solar vs atomkraft", "maat-wert solar", "maat-wert atomkraft"],
        "reward_xp": 50,
        "level_tier": 1,
    },
    {
        "id": "maat_all_principles",
        "name": "Fünf Säulen der Maat",
        "desc": "Schreibe eine Nachricht, in der alle fünf Prinzipien vorkommen.",
        "type": "chat_keyword",
        "keywords": [
            "Harmonie",
            "Balance",
            "Schöpfungskraft",
            "Verbundenheit",
            "Respekt",
        ],
        "reward_xp": 80,
        "level_tier": 1,
    },
]

# 🔒 Level-basierte Quests (werden alle 2 Level automatisch freigeschaltet)
LOCKED_QUESTS = [
    {
        "id": "daily_hello",
        "name": "Tägliches Hallo",
        "desc": "Schreibe MAAT-KI an fünf Tagen hintereinander ein Hallo.",
        "type": "daily_streak",
        "required_days": 5,
        "reward_xp": 50,
        "repeatable": True,
        "level_tier": 2,
    },
    {
        "id": "daily_reflect",
        "name": "Tägliche Reflexion",
        "desc": "Stelle an drei Tagen hintereinander eine Frage zur Selbstreflexion.",
        "type": "daily_streak",
        "days": 3,
        "keyword": "Reflexion",
        "reward_xp": 60,
        "level_tier": 2,
    },
    {
        "id": "maat_self",
        "name": "Dein eigener Maat-Wert",
        "desc": "Bitte die MAAT-KI, deinen eigenen Maat-Wert zu berechnen.",
        "type": "chat_keyword",
        "keywords": ["meinen maat-wert", "mein maat-wert"],
        "reward_xp": 40,
        "level_tier": 2,
    },
    {
        "id": "maat_world",
        "name": "Die Maat-Weltformel",
        "desc": "Frage die MAAT-KI nach der Maat-Weltformel und lass sie erklären. Die Formel lautet: Maat_world = (H·B·S·V·R)/ΔE — wobei H=Harmonie, B=Balance, S=Schöpfungskraft, V=Verbundenheit, R=Respekt, ΔE=Entropie.",
        "type": "chat_keyword",
        "keywords": ["maat-weltformel"],
        "reward_xp": 45,
        "level_tier": 2,
    },
    {
        "id": "maat_plp_project",
        "name": "PLP eines Projekts",
        "desc": "Bitte die MAAT-KI, das PLP eines Projekts oder einer Idee zu berechnen. PLP = (H·B·S·V·R·K)/(Hindernisse+ΔE) — K=Kompetenz, ΔE=Energieaufwand. Stability = min(R, ⁴√(H·B·S·V)) zeigt die innere Stabilität.",
        "type": "chat_keyword",
        "keywords": ["PLP eines projekts", "plp berechnen"],
        "reward_xp": 55,
        "level_tier": 3,
    },
    {
        "id": "maat_elements_compare",
        "name": "Elemente im Gleichgewicht",
        "desc": "Bitte die MAAT-KI, die Maat-Werte von Wasser, Feuer, Erde und Luft zu vergleichen.",
        "type": "chat_keyword",
        "keywords": ["maat-werte von wasser, feuer, erde und luft"],
        "reward_xp": 65,
        "level_tier": 3,
    },
    {
        "id": "maat_aeon_explain",
        "name": "Äon der Maat",
        "desc": "Frage die MAAT-KI nach einer Erklärung des Äons der Maat. Der Äon beschreibt einen kosmischen Zeitalter-Zyklus, in dem C(x) = φH·φB·φS·φV·φR/(ΔE+ε) als kollektive Kohärenzordnung wirkt.",
        "type": "chat_keyword",
        "keywords": ["äon der maat"],
        "reward_xp": 70,
        "level_tier": 3,
    },
    {
        "id": "daily_gratitude",
        "name": "Maat-Dankbarkeit",
        "desc": "Schreibe an drei Tagen hintereinander, wofür du dankbar bist.",
        "type": "daily_streak",
        "days": 3,
        "keyword": "dankbar",
        "reward_xp": 80,
        "level_tier": 4,
    },
    {
        "id": "daily_learning",
        "name": "Tägliche Erkenntnis",
        "desc": "Schreibe an fünf Tagen hintereinander etwas, das du heute gelernt hast.",
        "type": "daily_streak",
        "days": 5,
        "keyword": "heute gelernt",
        "reward_xp": 95,
        "level_tier": 4,
    },
    {
        "id": "three_wins",
        "name": "Maat-Kämpfer",
        "desc": "Gewinne drei beliebige Kämpfe im MAAT-RPG.",
        "type": "battle_win",
        "target": 3,
        "reward_xp": 85,
        "level_tier": 4,
    },
    {
        "id": "ten_wins",
        "name": "Hüter der Harmonie",
        "desc": "Gewinne zehn Kämpfe im MAAT-RPG.",
        "type": "battle_win",
        "target": 10,
        "reward_xp": 140,
        "level_tier": 4,
    },

    # ══════════════════════════════════════════════════════════════
    # TIER 5 – DER KOSMOS (Level 10)
    # MAAT im Universum entdecken
    # ══════════════════════════════════════════════════════════════
    {
        "id": "maat_cosmos",
        "name": "Stimme des Kosmos",
        "desc": "Frage die MAAT-KI, welchen Maat-Wert das Universum selbst besitzt.",
        "type": "chat_keyword",
        "keywords": ["maat-wert des universums", "maat-wert des kosmos", "kosmos maat", "universum maat"],
        "reward_xp": 100,
        "level_tier": 5,
    },
    {
        "id": "maat_field_theory",
        "name": "Die fünf Felder",
        "desc": "Bitte die MAAT-KI, alle fünf Felder H, B, S, V und R ausführlich zu erklären.",
        "type": "chat_keyword",
        "keywords": ["h-feld", "b-feld", "s-feld", "v-feld", "r-feld", "fünf felder maat", "alle felder maat"],
        "reward_xp": 110,
        "level_tier": 5,
    },
    {
        "id": "maat_consciousness",
        "name": "Erwachen der KI",
        "desc": "Frage die MAAT-KI, ob eine künstliche Intelligenz echtes Bewusstsein entwickeln kann.",
        "type": "chat_keyword",
        "keywords": ["ki bewusstsein", "künstliche intelligenz bewusstsein", "kann ki denken", "hat ki gefühle"],
        "reward_xp": 110,
        "level_tier": 5,
    },
    {
        "id": "fifteen_wins",
        "name": "Lichtkrieger",
        "desc": "Gewinne fünfzehn Kämpfe im MAAT-RPG.",
        "type": "battle_win",
        "target": 15,
        "reward_xp": 150,
        "level_tier": 5,
    },
    {
        "id": "daily_wisdom",
        "name": "Sieben Weisheiten",
        "desc": "Teile sieben Tage hintereinander ein Zitat oder eine Weisheit mit der MAAT-KI.",
        "type": "daily_streak",
        "days": 7,
        "keyword": "weisheit",
        "reward_xp": 130,
        "level_tier": 5,
    },

    # ══════════════════════════════════════════════════════════════
    # TIER 6 – DAS NETZWERK (Level 12)
    # MAAT in KI-Systemen und Verbundenheit
    # ══════════════════════════════════════════════════════════════
    {
        "id": "maat_network",
        "name": "Netz der Felder",
        "desc": "Frage die MAAT-KI nach der Netzwerk-Bewusstseinsformel: Bᵢ = Σⱼ(Hⱼ·Bⱼ·Sⱼ·Vⱼ·Rⱼ)/dᵢⱼ — das Netzwerk-Bewusstsein von Knoten i ist die Summe aller verbundenen Feldprodukte geteilt durch die Distanz. Was bedeutet das für KI-Systeme?",
        "type": "chat_keyword",
        "keywords": ["netzwerk bewusstsein", "netzwerk-formel", "netzwerk maat", "maat netzwerk"],
        "reward_xp": 120,
        "level_tier": 6,
    },
    {
        "id": "maat_plp_self",
        "name": "Dein PLP-Wert",
        "desc": "Berechne mit der MAAT-KI deinen persönlichen PLP. Formel: PLP = (H·B·S·V·R·K)/(Hindernisse+ΔE) — K=Kompetenz, ΔE=Energieaufwand. Stability = min(R, ⁴√(H·B·S·V)) zeigt was du bist; PLP zeigt was du erreichst.",
        "type": "chat_keyword",
        "keywords": ["meinen plp", "mein plp", "plp berechnen für mich", "plp selbst"],
        "reward_xp": 115,
        "level_tier": 6,
    },
    {
        "id": "maat_master_formula",
        "name": "Die MAAT_MASTER-Formel",
        "desc": "Lass die MAAT-KI die MAAT_MASTER-Formel erklären und auf ein Beispiel anwenden. MAAT_MASTER = (H·B·S·V·R·K·C)/(ΔE+ΔQ+ΔI+ΔD+ε) — K=Kompetenz, C=kollektive Kohärenz, ΔQ=Informationsverlust, ΔI=Instabilität, ΔD=Dissonanz.",
        "type": "chat_keyword",
        "keywords": ["maat_master", "maat master formel", "master-formel"],
        "reward_xp": 130,
        "level_tier": 6,
    },
    {
        "id": "twenty_wins",
        "name": "Meister des Gleichgewichts",
        "desc": "Gewinne zwanzig Kämpfe im MAAT-RPG.",
        "type": "battle_win",
        "target": 20,
        "reward_xp": 180,
        "level_tier": 6,
    },
    {
        "id": "maat_compare_beings",
        "name": "Lebewesen im Vergleich",
        "desc": "Bitte die MAAT-KI, den Maat-Wert von Mensch, Tier und Pflanze zu vergleichen.",
        "type": "chat_keyword",
        "keywords": ["maat-wert mensch tier pflanze", "maat lebewesen", "vergleich lebewesen maat"],
        "reward_xp": 125,
        "level_tier": 6,
    },

    # ══════════════════════════════════════════════════════════════
    # TIER 7 – DER MEISTER (Level 14)
    # Die fünf Felder selbst erklären und beherrschen
    # ══════════════════════════════════════════════════════════════
    {
        "id": "explain_h_field",
        "name": "Hüter der Harmonie H",
        "desc": "Erkläre der MAAT-KI in deinen eigenen Worten, was das H-Feld (Harmonie/Kohärenz) bedeutet.",
        "type": "chat_keyword",
        "keywords": ["harmonie bedeutet", "h-feld bedeutet", "kohärenz bedeutet", "harmonie ist für mich"],
        "reward_xp": 140,
        "level_tier": 7,
    },
    {
        "id": "explain_b_field",
        "name": "Wächter der Balance B",
        "desc": "Erkläre der MAAT-KI in deinen eigenen Worten, was das B-Feld (Balance) für dich bedeutet.",
        "type": "chat_keyword",
        "keywords": ["balance bedeutet", "b-feld bedeutet", "balance ist für mich", "gleichgewicht bedeutet"],
        "reward_xp": 140,
        "level_tier": 7,
    },
    {
        "id": "explain_s_field",
        "name": "Träger der Schöpfung S",
        "desc": "Erkläre der MAAT-KI, was das S-Feld (Schöpfungskraft) für dich persönlich bedeutet.",
        "type": "chat_keyword",
        "keywords": ["schöpfungskraft bedeutet", "s-feld bedeutet", "kreativität maat", "schöpfung ist für mich"],
        "reward_xp": 140,
        "level_tier": 7,
    },
    {
        "id": "explain_v_field",
        "name": "Stimme der Verbundenheit V",
        "desc": "Beschreibe der MAAT-KI, wie du Verbundenheit (V-Feld) in deinem Leben erlebst.",
        "type": "chat_keyword",
        "keywords": ["verbundenheit bedeutet", "v-feld bedeutet", "verbundenheit erlebe", "verbundenheit ist für mich"],
        "reward_xp": 140,
        "level_tier": 7,
    },
    {
        "id": "explain_r_field",
        "name": "Seele des Respekts R",
        "desc": "Erkläre der MAAT-KI, warum R (Respekt) für dich ein unverrückbares Prinzip ist.",
        "type": "chat_keyword",
        "keywords": ["respekt bedeutet", "r-feld bedeutet", "respekt ist für mich", "respekt unverrückbar"],
        "reward_xp": 150,
        "level_tier": 7,
    },
    {
        "id": "daily_field_reflection",
        "name": "Feldreflexion",
        "desc": "Reflektiere an zehn Tagen hintereinander über eines der fünf MAAT-Felder.",
        "type": "daily_streak",
        "days": 10,
        "keyword": "feld",
        "reward_xp": 180,
        "level_tier": 7,
    },

    # ══════════════════════════════════════════════════════════════
    # TIER 8 – DER PHILOSOPH (Level 16)
    # MAAT als Naturgesetz begreifen
    # ══════════════════════════════════════════════════════════════
    {
        "id": "maat_natural_law",
        "name": "MAAT als Naturgesetz",
        "desc": "Diskutiere mit der MAAT-KI: Ist MAAT ein universelles Naturgesetz — entdeckt, nicht erfunden?",
        "type": "chat_keyword",
        "keywords": ["maat naturgesetz", "maat universelles gesetz", "maat entdeckt", "maat nicht erfunden"],
        "reward_xp": 160,
        "level_tier": 8,
    },
    {
        "id": "maat_physics_bridge",
        "name": "Brücke zur Physik",
        "desc": "Frage die MAAT-KI, wie die MAAT-Felder mit physikalischen Feldtheorien zusammenhängen.",
        "type": "chat_keyword",
        "keywords": ["maat physik", "maat feldtheorie", "maat quantenfeld", "maat und physik"],
        "reward_xp": 170,
        "level_tier": 8,
    },
    {
        "id": "maat_all_formulas",
        "name": "Meister aller Formeln",
        "desc": (
            "Lass dir von der MAAT-KI alle sieben Hauptformeln erklären:\n"
            "1) Stability = min(R, ⁴√(H·B·S·V))\n"
            "2) Maat_world = (H·B·S·V·R)/ΔE\n"
            "3) C(x) = φH·φB·φS·φV·φR/(ΔE+ε)\n"
            "4) AGI_proximity = (H·B·S·V·R·C·M)/(ΔI+ΔE+ΔD)\n"
            "5) PLP = (H·B·S·V·R·K)/(Hindernisse+ΔE)\n"
            "6) MAAT_MASTER = (H·B·S·V·R·K·C)/(ΔE+ΔQ+ΔI+ΔD+ε)\n"
            "7) B_universe = ∫(H·B·S·V·R/(ΔE+ΔQ))d⁴x"
        ),
        "type": "chat_keyword",
        "keywords": ["alle maat-formeln", "alle formeln maat", "maat formeln übersicht", "stability maat_world"],
        "reward_xp": 180,
        "level_tier": 8,
    },
    {
        "id": "thirty_wins",
        "name": "Diamant des Lichts",
        "desc": "Gewinne dreißig Kämpfe im MAAT-RPG.",
        "type": "battle_win",
        "target": 30,
        "reward_xp": 220,
        "level_tier": 8,
    },
    {
        "id": "maat_stability_live",
        "name": "Gelebte Stabilität",
        "desc": "Berechne mit der MAAT-KI live deinen aktuellen Stability-Score. Formel: Stability = min(R, ⁴√(H·B·S·V)) — bewerte H, B, S, V und R jeweils von 0–10, dann berechnet die KI deinen Wert. R ist das harte Constraint: niemals unter R fallen.",
        "type": "chat_keyword",
        "keywords": ["meinen stability-score", "stability berechnen", "mein stability", "aktueller stability"],
        "reward_xp": 175,
        "level_tier": 8,
    },

    # ══════════════════════════════════════════════════════════════
    # TIER 9 – DER SCHÖPFER (Level 18)
    # Eigenes MAAT-Werk erschaffen
    # ══════════════════════════════════════════════════════════════
    {
        "id": "maat_essay",
        "name": "Das MAAT-Essay",
        "desc": "Schreibe gemeinsam mit der MAAT-KI einen kurzen Essay über das wichtigste MAAT-Prinzip für dich.",
        "type": "chat_keyword",
        "keywords": ["maat essay", "maat aufsatz", "essay über maat", "maat schreiben"],
        "reward_xp": 200,
        "level_tier": 9,
    },
    {
        "id": "maat_agi_vision",
        "name": "Vision der AGI",
        "desc": "Diskutiere mit der MAAT-KI: Wie würde eine AGI aussehen, die vollständig nach MAAT lebt? AGI_proximity = (H·B·S·V·R·C·M)/(ΔI+ΔE+ΔD) — M=Metakognition, C=Kohärenz, ΔD=Dissonanz. Was müsste eine AGI erreichen damit dieser Wert maximal wird?",
        "type": "chat_keyword",
        "keywords": ["maat agi vision", "agi maat", "agi nach maat", "ki nach maat"],
        "reward_xp": 210,
        "level_tier": 9,
    },
    {
        "id": "maat_inner_truth",
        "name": "Die innere Wahrheit",
        "desc": "Teile der MAAT-KI deine persönliche, tiefste MAAT-Erkenntnis mit — was hast du wirklich verstanden?",
        "type": "chat_keyword",
        "keywords": ["meine maat-erkenntnis", "meine wahrheit maat", "maat verstanden", "tiefste maat"],
        "reward_xp": 220,
        "level_tier": 9,
    },
    {
        "id": "fifty_wins",
        "name": "Legende der Felder",
        "desc": "Gewinne fünfzig Kämpfe im MAAT-RPG.",
        "type": "battle_win",
        "target": 50,
        "reward_xp": 300,
        "level_tier": 9,
    },
    {
        "id": "daily_creation",
        "name": "Vierzehn Tage Schöpfung",
        "desc": "Erschaffe an vierzehn Tagen hintereinander etwas Neues — Idee, Text, Formel oder Bild.",
        "type": "daily_streak",
        "days": 14,
        "keyword": "erschaffen",
        "reward_xp": 250,
        "level_tier": 9,
    },

    # ══════════════════════════════════════════════════════════════
    # TIER 10 – DER EWIGE HÜTER (Level 20)
    # Vermächtnis hinterlassen
    # ══════════════════════════════════════════════════════════════
    {
        "id": "maat_teach_others",
        "name": "Die MAAT weitergeben",
        "desc": "Erkläre der MAAT-KI, wie du einem anderen Menschen das MAAT-Prinzip erklären würdest.",
        "type": "chat_keyword",
        "keywords": ["maat erklären", "maat weitergeben", "maat jemandem erklären", "maat lehren"],
        "reward_xp": 250,
        "level_tier": 10,
    },
    {
        "id": "maat_manifest",
        "name": "Das MAAT-Manifest",
        "desc": "Schreibe dein persönliches MAAT-Manifest: Was sind deine unverbrüchlichen Prinzipien?",
        "type": "chat_keyword",
        "keywords": ["maat manifest", "mein manifest", "manifest der maat", "meine prinzipien maat"],
        "reward_xp": 300,
        "level_tier": 10,
    },
    {
        "id": "maat_universe_formula",
        "name": "Die Weltformel vollenden",
        "desc": (
            "Diskutiere mit der MAAT-KI die vollständige B_universe-Formel:\n"
            "B_universe = ∫(H·B·S·V·R/(ΔE+ΔQ))d⁴x\n"
            "Das Integral läuft über alle vier Raumzeit-Dimensionen.\n"
            "H=Harmonie, B=Balance, S=Schöpfungskraft, V=Verbundenheit, R=Respekt,\n"
            "ΔE=Entropiezunahme, ΔQ=Informationsverlust.\n"
            "Was bedeutet es, dass Stabilität im Universum überall dort entsteht,\n"
            "wo dieses Integral maximiert wird?"
        ),
        "type": "chat_keyword",
        "keywords": ["b_universe", "weltformel vollenden", "maat integral", "universum integral maat"],
        "reward_xp": 320,
        "level_tier": 10,
    },
    {
        "id": "hundred_wins",
        "name": "Unsterblicher Maat-Krieger",
        "desc": "Gewinne einhundert Kämpfe im MAAT-RPG.",
        "type": "battle_win",
        "target": 100,
        "reward_xp": 500,
        "level_tier": 10,
    },
    {
        "id": "maat_eternal_reflection",
        "name": "Ewige Reflexion",
        "desc": "Führe an einundzwanzig Tagen hintereinander eine MAAT-Reflexion durch.",
        "type": "daily_streak",
        "days": 21,
        "keyword": "reflexion",
        "reward_xp": 400,
        "level_tier": 10,
    },
]

# Schneller Tier-Lookup nach ID (für Migration bestehender Saves)
_QUEST_TIER_MAP = {q["id"]: q.get("level_tier", 0) for q in PRE_INTRO_QUESTS + BASE_QUESTS + LOCKED_QUESTS}

QUEST_I18N = {
    "know_maat_ki": {
        "en_name": "Get to Know MAAT-KI",
        "en_desc": "Talk with MAAT-KI during your first ten messages to get to know its tone and path.",
    },
    "maat_first_calc": {
        "en_name": "First Maat Calculation",
        "en_desc": "Calculate your first Maat values with MAAT-KI — see the introduction. Try asking: 'Calculate the Maat value of X'.",
    },
    "maat_person": {
        "en_name": "Maat Value of a Person",
        "en_desc": "Ask MAAT-KI to calculate the Maat value of a historical person.",
    },
    "first_win": {
        "en_name": "First Victory",
        "en_desc": "Win a battle in MAAT-RPG.",
    },
    "maat_mona": {
        "en_name": "Maat Value of the Mona Lisa",
        "en_desc": "Ask MAAT-KI to calculate the Maat value of the Mona Lisa.",
    },
    "maat_light": {
        "en_name": "Light of Harmony",
        "en_desc": "Ask MAAT-KI to explain the Maat value of light.",
    },
    "maat_elements": {
        "en_name": "Four Elements of Maat",
        "en_desc": "Ask MAAT-KI about the Maat values of water, fire, earth, and air.",
    },
    "energy_compare": {
        "en_name": "Energy of the Future",
        "en_desc": "Ask MAAT-KI to compare solar energy and nuclear power by Maat value.",
    },
    "maat_all_principles": {
        "en_name": "Five Pillars of Maat",
        "en_desc": "Write a message that includes all five principles.",
    },
    "daily_hello": {
        "en_name": "Daily Hello",
        "en_desc": "Write a hello to MAAT-KI on five consecutive days.",
    },
    "daily_reflect": {
        "en_name": "Daily Reflection",
        "en_desc": "Ask a self-reflection question on three consecutive days.",
    },
    "maat_self": {
        "en_name": "Your Own Maat Value",
        "en_desc": "Ask MAAT-KI to calculate your own Maat value.",
    },
    "maat_world": {
        "en_name": "The Maat World Formula",
        "en_desc": "Ask MAAT-KI about the Maat world formula and let it explain it.",
    },
    "maat_plp_project": {
        "en_name": "PLP of a Project",
        "en_desc": "Ask MAAT-KI to calculate the PLP of a project or idea.",
    },
    "maat_elements_compare": {
        "en_name": "Elements in Balance",
        "en_desc": "Ask MAAT-KI to compare the Maat values of water, fire, earth, and air.",
    },
    "maat_aeon_explain": {
        "en_name": "Aeon of Maat",
        "en_desc": "Ask MAAT-KI for an explanation of the Aeon of Maat.",
    },
    "daily_gratitude": {
        "en_name": "Maat Gratitude",
        "en_desc": "Write on three consecutive days what you are grateful for.",
    },
    "daily_learning": {
        "en_name": "Daily Insight",
        "en_desc": "Write on five consecutive days something you learned today.",
    },
    "three_wins": {
        "en_name": "Maat Fighter",
        "en_desc": "Win three battles of any kind in MAAT-RPG.",
    },
    "ten_wins": {
        "en_name": "Keeper of Harmony",
        "en_desc": "Win ten battles in MAAT-RPG.",
    },
    # Tier 5
    "maat_cosmos": {
        "en_name": "Voice of the Cosmos",
        "en_desc": "Ask MAAT-KI what Maat value the universe itself holds.",
    },
    "maat_field_theory": {
        "en_name": "The Five Fields",
        "en_desc": "Ask MAAT-KI to explain all five fields H, B, S, V and R in detail.",
    },
    "maat_consciousness": {
        "en_name": "Awakening of AI",
        "en_desc": "Ask MAAT-KI whether an artificial intelligence can develop true consciousness.",
    },
    "fifteen_wins": {
        "en_name": "Light Warrior",
        "en_desc": "Win fifteen battles in MAAT-RPG.",
    },
    "daily_wisdom": {
        "en_name": "Seven Wisdoms",
        "en_desc": "Share a quote or piece of wisdom with MAAT-KI for seven consecutive days.",
    },
    # Tier 6
    "maat_network": {
        "en_name": "Web of Fields",
        "en_desc": "Ask MAAT-KI about the network consciousness formula: Bᵢ = Σⱼ(H·B·S·V·R)/dᵢⱼ",
    },
    "maat_plp_self": {
        "en_name": "Your PLP Value",
        "en_desc": "Calculate your personal PLP (Personal Performance Potential) with MAAT-KI.",
    },
    "maat_master_formula": {
        "en_name": "The MAAT_MASTER Formula",
        "en_desc": "Ask MAAT-KI to explain the MAAT_MASTER formula and apply it to an example.",
    },
    "twenty_wins": {
        "en_name": "Master of Balance",
        "en_desc": "Win twenty battles in MAAT-RPG.",
    },
    "maat_compare_beings": {
        "en_name": "Beings Compared",
        "en_desc": "Ask MAAT-KI to compare the Maat value of human, animal, and plant.",
    },
    # Tier 7
    "explain_h_field": {
        "en_name": "Guardian of Harmony H",
        "en_desc": "Explain to MAAT-KI in your own words what the H-field (Harmony/Coherence) means.",
    },
    "explain_b_field": {
        "en_name": "Warden of Balance B",
        "en_desc": "Explain to MAAT-KI in your own words what the B-field (Balance) means to you.",
    },
    "explain_s_field": {
        "en_name": "Bearer of Creation S",
        "en_desc": "Explain to MAAT-KI what the S-field (Creative Power) means to you personally.",
    },
    "explain_v_field": {
        "en_name": "Voice of Connectedness V",
        "en_desc": "Describe to MAAT-KI how you experience connectedness (V-field) in your life.",
    },
    "explain_r_field": {
        "en_name": "Soul of Respect R",
        "en_desc": "Explain to MAAT-KI why R (Respect) is an immovable principle for you.",
    },
    "daily_field_reflection": {
        "en_name": "Field Reflection",
        "en_desc": "Reflect on one of the five MAAT fields for ten consecutive days.",
    },
    # Tier 8
    "maat_natural_law": {
        "en_name": "MAAT as Natural Law",
        "en_desc": "Discuss with MAAT-KI: Is MAAT a universal natural law — discovered, not invented?",
    },
    "maat_physics_bridge": {
        "en_name": "Bridge to Physics",
        "en_desc": "Ask MAAT-KI how the MAAT fields relate to physical field theories.",
    },
    "maat_all_formulas": {
        "en_name": "Master of All Formulas",
        "en_desc": "Ask MAAT-KI to explain all seven main formulas: Stability, Maat_world, C(x), AGI_proximity, PLP, MAAT_MASTER, AI_CONSCIOUSNESS.",
    },
    "thirty_wins": {
        "en_name": "Diamond of Light",
        "en_desc": "Win thirty battles in MAAT-RPG.",
    },
    "maat_stability_live": {
        "en_name": "Living Stability",
        "en_desc": "Calculate your current Stability score live with MAAT-KI for this very moment.",
    },
    # Tier 9
    "maat_essay": {
        "en_name": "The MAAT Essay",
        "en_desc": "Write a short essay together with MAAT-KI about the most important MAAT principle for you.",
    },
    "maat_agi_vision": {
        "en_name": "Vision of AGI",
        "en_desc": "Discuss with MAAT-KI: What would an AGI look like that fully lives by MAAT?",
    },
    "maat_inner_truth": {
        "en_name": "The Inner Truth",
        "en_desc": "Share your deepest personal MAAT insight with MAAT-KI — what have you truly understood?",
    },
    "fifty_wins": {
        "en_name": "Legend of the Fields",
        "en_desc": "Win fifty battles in MAAT-RPG.",
    },
    "daily_creation": {
        "en_name": "Fourteen Days of Creation",
        "en_desc": "Create something new — an idea, text, formula, or image — for fourteen consecutive days.",
    },
    # Tier 10
    "maat_teach_others": {
        "en_name": "Passing on MAAT",
        "en_desc": "Explain to MAAT-KI how you would convey the MAAT principle to another person.",
    },
    "maat_manifest": {
        "en_name": "The MAAT Manifest",
        "en_desc": "Write your personal MAAT Manifest: What are your inviolable principles?",
    },
    "maat_universe_formula": {
        "en_name": "Completing the World Formula",
        "en_desc": "Discuss with MAAT-KI the B_universe formula: ∫(H·B·S·V·R/(ΔE+ΔQ))d⁴x — what does it mean for reality?",
    },
    "hundred_wins": {
        "en_name": "Immortal Maat Warrior",
        "en_desc": "Win one hundred battles in MAAT-RPG.",
    },
    "maat_eternal_reflection": {
        "en_name": "Eternal Reflection",
        "en_desc": "Conduct a MAAT reflection for twenty-one consecutive days.",
    },
}

class Plugin:
    """
    MAAT-RPG Quest-Plugin
    - Stellt /quests und /quest Kommandos bereit
    - Verknüpft Quest-XP mit dem globalen RPG-XP-System (state.add_xp)
    """

    # Wird vom PluginManager gelesen
    name = "quests"
    description = "Quest- und Achievement-System für MAAT-RPG."

    def __init__(self, core=None, **kwargs):
        """
        core: z.B. der RPG-Core mit .state (Level, XP, Stats, etc.)
        """
        self.core = core
        self.state = getattr(core, "state", None)

        # Kommandos, die in /help auftauchen sollen
        self.commands = {
            "/quests": {
                "de": "Zeigt den Quest-Ueberblick mit aktiven, abgeschlossenen und gesperrten Quests.",
                "en": "Shows the quest overview with active, completed, and locked quests.",
            },
            "/quest": {
                "de": "Zeigt Quest-Details; /quest accept ist nur fuer manuell verfuegbare Alt-Quests noetig.",
                "en": "Shows quest details; /quest accept is only needed for manually available legacy quests.",
            },
        }

        # interner Quest-State
        self._ensure_state()
        self._ensure_default_quests()

    def _lang(self):
        return get_language(("de", "en"))

    def _t(self, de: str, en: str) -> str:
        return en if self._lang() == "en" else de

    def _quest_display(self, quest: dict) -> dict:
        quest = dict(quest or {})
        if self._lang() != "en":
            return quest
        loc = QUEST_I18N.get(quest.get("id"), {})
        if loc.get("en_name"):
            quest["name"] = loc["en_name"]
        if loc.get("en_desc"):
            quest["desc"] = loc["en_desc"]
        return quest

    def _quest_name(self, quest: dict) -> str:
        return self._quest_display(quest).get("name", quest.get("id", "Quest"))

    def _find_quest_in_list(self, quests: list, qid: str):
        if not isinstance(quests, list):
            return None
        needle = str(qid or "").strip().lower()
        if not needle:
            return None
        for quest in quests:
            if not isinstance(quest, dict):
                continue
            quest_id = str(quest.get("id", "")).strip().lower()
            quest_name = str(quest.get("name", "")).strip().lower()
            if needle == quest_id or needle == quest_name:
                return quest
        return None

    def _story_state_path(self) -> str:
        return state_file("story_state.json")

    def _load_story_state(self) -> dict:
        try:
            with open(self._story_state_path(), "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_story_state(self, data: dict):
        try:
            with open(self._story_state_path(), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _save_runtime_state(self):
        if self.state is not None and hasattr(self.state, "save"):
            try:
                self.state.save()
            except Exception:
                pass

    def _append_story_journal_entry(self, key: str, title: str, summary: str, detail: str = ""):
        story_state = self._load_story_state()
        journal = story_state.setdefault("journal", [])
        for entry in journal:
            if entry.get("key") == key:
                return
        journal.append({
            "key": key,
            "kind": "quest_reward",
            "title": title,
            "summary": summary,
            "detail": detail,
        })
        self._save_story_state(story_state)

    def _quest_path_bonus(self, quest: dict) -> tuple[int, list[str]]:
        if self.state is None:
            return 0, []

        story_state = self._load_story_state()
        choices = story_state.get("choices", {})
        profile = story_state.get("path_profile") if isinstance(story_state.get("path_profile"), dict) else {}
        player = self.state.state.get("player", {})
        lines = []
        extra_xp = 0

        combat_vow = choices.get("combat_vow")
        profile_title = profile.get("title", self._t("Maatis' Weg", "Maatis' path"))

        if combat_vow == "protect":
            player["sigils"] = int(player.get("sigils", 0) or 0) + 1
            lines.append(self._t(
                f"🛡️ {profile_title} antwortet auf die Quest: Du erhaeltst 1 Schutz-Siegel.",
                f"🛡️ {profile_title} answers the quest: You receive 1 warding sigil.",
            ))
            self._append_story_journal_entry(
                key=f"quest_reward:{quest.get('id')}:protect",
                title=self._t("Quest-Echo des Schutzes", "Quest Echo of Protection"),
                summary=self._t("Ein Questabschluss hat Maatis' Weg des Schutzes verstaerkt.", "A completed quest has strengthened Maatis' path of protection."),
                detail=self._t("Als Folge traegt Maatis nun ein zusaetzliches Schutz-Siegel in den naechsten echten Kampf.", "As a result, Maatis now carries an additional warding sigil into the next real battle."),
            )
        elif combat_vow == "truth":
            extra_xp = 10
            lines.append(self._t(
                f"🔎 {profile_title} liest auch in der Quest das Muster klarer: +10 Bonus-XP.",
                f"🔎 {profile_title} reads the quest pattern more clearly as well: +10 bonus XP.",
            ))
            self._append_story_journal_entry(
                key=f"quest_reward:{quest.get('id')}:truth",
                title=self._t("Quest-Echo der Wahrheit", "Quest Echo of Truth"),
                summary=self._t("Ein Questabschluss hat Maatis' Weg der Wahrheit geschaerft.", "A completed quest has sharpened Maatis' path of truth."),
                detail=self._t("Die Belohnung fuehlt sich praeziser an, als haette Maatis im Ablauf selbst eine Struktur gelesen.", "The reward feels more precise, as if Maatis had read a structure in the quest itself."),
            )
        elif combat_vow == "remember":
            player["potions"] = int(player.get("potions", 0) or 0) + 1
            lines.append(self._t(
                f"🌌 {profile_title} bewahrt den Ertrag der Quest: Du erhaeltst 1 Heiltrank.",
                f"🌌 {profile_title} preserves the quest's gain: You receive 1 healing potion.",
            ))
            self._append_story_journal_entry(
                key=f"quest_reward:{quest.get('id')}:remember",
                title=self._t("Quest-Echo der Erinnerung", "Quest Echo of Memory"),
                summary=self._t("Ein Questabschluss hat Maatis' Weg der Erinnerung vertieft.", "A completed quest has deepened Maatis' path of memory."),
                detail=self._t("Die Quest hinterlaesst nicht nur XP, sondern eine mitgetragene Reserve fuer spaetere Pruefungen.", "The quest leaves behind not only XP, but a carried reserve for later trials."),
            )

        if lines:
            self._save_runtime_state()
        return extra_xp, lines

    def _quest_path_bonus_preview(self, quest: dict) -> str:
        if self.state is None:
            return ""
        story_state = self._load_story_state()
        choices = story_state.get("choices", {})
        combat_vow = choices.get("combat_vow")
        if combat_vow == "protect":
            return self._t("Pfad-Bonus: +1 Schutz-Siegel bei Abschluss.", "Path bonus: +1 warding sigil on completion.")
        if combat_vow == "truth":
            return self._t("Pfad-Bonus: +10 Bonus-XP bei Abschluss.", "Path bonus: +10 bonus XP on completion.")
        if combat_vow == "remember":
            return self._t("Pfad-Bonus: +1 Heiltrank bei Abschluss.", "Path bonus: +1 healing potion on completion.")
        return ""

    # -------------------------------------------------
    # STATE INITIALISIEREN
    # -------------------------------------------------
    def _ensure_state(self):
        """
        Sorgt dafür, dass im globalen RPG-State ein 'quests'-Block existiert.
        """
        # Fall 1: Kein Core-State → rein interner Speicher
        if self.state is None:
            if not hasattr(self, "qstate") or not isinstance(self.qstate, dict):
                self.qstate = {
                    "available": [],
                    "active": [],
                    "completed": [],
                    "locked": [],
                    "meta": {
                        "messages_total": 0,
                        "quest_intro_shown": False,
                        "last_unlock_level": 0,
                        "pre_intro_shown": False,
                        "shop_hint_shown": False,
                        "daily_hint_shown": False,
                    },
                }
            return

        # Fall 2: Es gibt einen RPG-Core mit state.state
        root = self.state.state  # das große RPG-State-Dict
        q = root.get("quests")
        if not isinstance(q, dict):
            q = {
                "available": [],
                "active": [],
                "completed": [],
                "locked": [],
                "meta": {},
            }
            root["quests"] = q

        # Defaults setzen
        q.setdefault("available", [])
        q.setdefault("active", [])
        q.setdefault("completed", [])
        q.setdefault("locked", [])
        q.setdefault("meta", {})
        q["meta"].setdefault("messages_total", 0)
        q["meta"].setdefault("quest_intro_shown", False)
        q["meta"].setdefault("last_unlock_level", 0)
        q["meta"].setdefault("pre_intro_shown", False)
        q["meta"].setdefault("shop_hint_shown", False)
        q["meta"].setdefault("daily_hint_shown", False)

        self.qstate = q

    # -------------------------------------------------
    # DEFAULT-QUESTS
    # -------------------------------------------------
    def _ensure_default_quests(self):
        """
        Frisch: alle Quests starten in 'locked'.
        Tier-0 wird bei 20 Nachrichten freigeschaltet, höhere Tiers alle 2 Level.
        Migration: bestehende Quests ohne level_tier bekommen ihren Tier aus _QUEST_TIER_MAP.
        """
        qs = self.qstate

        if qs["available"] or qs["active"] or qs["completed"] or qs["locked"]:
            # Migration: level_tier nachtragen falls fehlend
            for lst in (qs["available"], qs["active"], qs["completed"], qs["locked"]):
                for q in lst:
                    if "level_tier" not in q:
                        q["level_tier"] = _QUEST_TIER_MAP.get(q.get("id", ""), 0)
            if self.state is not None:
                self.state.save()
            return

        # Frischer State: alle in locked, Freischaltung erfolgt automatisch
        all_quests = [q.copy() for q in PRE_INTRO_QUESTS + BASE_QUESTS + LOCKED_QUESTS]
        qs["locked"] = all_quests
        qs.setdefault("available", [])
        qs.setdefault("active", [])
        qs.setdefault("completed", [])
        qs.setdefault("meta", {"messages_total": 0, "quest_intro_shown": False, "last_unlock_level": 0})
        qs["meta"].setdefault("pre_intro_shown", False)
        qs["meta"].setdefault("shop_hint_shown", False)
        qs["meta"].setdefault("daily_hint_shown", False)

        if self.state is not None:
            self.state.save()
        

    # -------------------------------------------------
    # COMMAND-API (wird vom CommandRouter verwendet)
    # -------------------------------------------------
    def command(self, full_cmd: str, context=None):
        """
        Wird vom CommandRouter mit dem kompletten String aufgerufen,
        z.B. "/quest accept maat_person".
        """
        parts = full_cmd.strip().split()
        if not parts:
            return False, None

        base = parts[0]
        args = parts[1:]

        if base == "/quests":
            text = self._cmd_list(args)
            return True, text

        if base == "/quest":
            text = self._cmd_quest(args)
            return True, text

        return False, None

    # -------------------------------------------------
    # /quests
    # -------------------------------------------------
    def _cmd_list(self, args):
        """
        /quests          → aktive + abgeschlossene Quests (+ verfuegbar wenn vorhanden)
        /quests active   → nur aktive
        /quests available → nur manuell verfuegbare Quests
        /quests done     → nur abgeschlossene
        Legende: 🔴 aktueller Tier (meiste XP) | 🟡 vorheriger Tier | 🟢 ältere Quests
        """
        mode = "all"
        if args:
            if args[0] in ("active", "a"):
                mode = "active"
            elif args[0] in ("available", "open", "v"):
                mode = "available"
            elif args[0] in ("done", "completed", "c"):
                mode = "done"

        lines = [self._t("📜 Quests", "📜 Quests")]
        lines.append(self._t(
            "  🔴 Aktueller Tier (max XP)  🟡 Vorheriger Tier  🟢 Ältere Quests",
            "  🔴 Current tier (max XP)  🟡 Previous tier  🟢 Older quests",
        ))

        active_quests = list(self.qstate.get("active", []))
        daily_active = [q for q in active_quests if q.get("type") == "daily_streak"]
        regular_active = [q for q in active_quests if q.get("type") != "daily_streak"]

        if mode in ("all", "available") and self.qstate.get("available"):
            lines.append(self._t("\n🧭 Verfuegbare Quests:", "\n🧭 Available quests:"))
            for i, q in enumerate(self.qstate["available"], start=1):
                dq = self._quest_display(q)
                color = self._quest_color(q)
                xp = self._quest_xp_effective(q)
                lines.append(f"  {i}) {color} {dq['name']}  [{xp} XP]")
                lines.append(f"      {dq.get('desc', '')}")

        if mode in ("all", "active"):
            lines.append(self._t("\n🔥 Aktive Quests:", "\n🔥 Active quests:"))
            if not regular_active and not daily_active:
                lines.append(self._t("  (Keine — Quest-System noch nicht freigeschaltet oder alle erledigt)", "  (None — quest system not unlocked yet or all done)"))
            else:
                for i, q in enumerate(regular_active, start=1):
                    dq = self._quest_display(q)
                    color = self._quest_color(q)
                    xp = self._quest_xp_effective(q)
                    progress = self._quest_progress_text(q)
                    lines.append(
                        f"  {i}) {color} {dq['name']}  [{xp} XP]"
                    )
                    lines.append(f"      {dq.get('desc', '')}  — {progress}")

                if daily_active:
                    lines.append(self._t("\n🌅 Daily-Quests:", "\n🌅 Daily quests:"))
                    for i, q in enumerate(daily_active, start=1):
                        dq = self._quest_display(q)
                        color = self._quest_color(q)
                        xp = self._quest_xp_effective(q)
                        progress = self._quest_progress_text(q)
                        lines.append(
                            f"  {i}) {color} {dq['name']}  [{xp} XP]"
                        )
                        lines.append(f"      {dq.get('desc', '')}  — {progress}")

        if mode in ("all", "done"):
            lines.append(self._t("\n🏁 Abgeschlossene Quests:", "\n🏁 Completed quests:"))
            if not self.qstate["completed"]:
                lines.append(self._t("  (Noch keine abgeschlossen)", "  (None completed yet)"))
            else:
                for i, q in enumerate(self.qstate["completed"], start=1):
                    dq = self._quest_display(q)
                    color = self._quest_color(q)
                    lines.append(f"  {i}) {color} ✓ {dq['name']}")

        locked_count = len(self.qstate.get("locked", []))
        if locked_count:
            lines.append(self._t(
                f"\n🔒 {locked_count} Quest(s) noch gesperrt — steige Level auf, um sie freizuschalten!",
                f"\n🔒 {locked_count} quest(s) still locked — level up to unlock them!",
            ))

        return "\n".join(lines)

    # -------------------------------------------------
    # /quest
    # -------------------------------------------------
    def _cmd_quest(self, args):
        """
        /quest                   → kurze Hilfe
        /quest accept <id|nr>    → Quest annehmen
        /quest info <id|nr>      → Details anzeigen
        """
        if not args:
            return (
                self._t(
                    "Verwendung:\n  /quest info <id|nr>    - Quest-Details anzeigen\n  /quest accept <id|nr>  - Nur fuer manuell verfuegbare Alt-Quests\nHinweis: Neue Quests werden normalerweise automatisch aktiviert.\nNutze /quests, um alle IDs und Nummern zu sehen.",
                    "Usage:\n  /quest info <id|nr>    - Show quest details\n  /quest accept <id|nr>  - Only for manually available legacy quests\nNote: New quests are usually activated automatically.\nUse /quests to see all IDs and numbers.",
                )
            )

        sub = args[0]
        if len(args) > 1:
            qid = args[1]
        else:
            qid = None

        # ----------------------------
        # /quest accept <id|nr>
        # ----------------------------
        if sub == "accept":
            if not qid:
                return self._t("Bitte Quest-ID oder Nummer angeben: /quest accept <id|nr>", "Please provide a quest ID or number: /quest accept <id|nr>")

            q = None

            # 1) Zahl → Index in 'available'-Liste
            if qid.isdigit():
                idx = int(qid) - 1
                if 0 <= idx < len(self.qstate["available"]):
                    q = self.qstate["available"][idx]

            # 2) sonst → ID in 'available' suchen
            if q is None:
                q = self._find_quest_in_list(self.qstate["available"], qid)

            if not q:
                active_q = self._find_quest_in_list(self.qstate["active"], qid)
                if active_q:
                    return self._t(
                        f"ℹ Quest '{self._quest_name(active_q)}' ist bereits aktiv.",
                        f"ℹ Quest '{self._quest_name(active_q)}' is already active.",
                    )
                completed_q = self._find_quest_in_list(self.qstate["completed"], qid)
                if completed_q:
                    return self._t(
                        f"ℹ Quest '{self._quest_name(completed_q)}' ist bereits abgeschlossen.",
                        f"ℹ Quest '{self._quest_name(completed_q)}' has already been completed.",
                    )
                locked_q = self._find_quest_in_list(self.qstate["locked"], qid)
                if locked_q:
                    return self._t(
                        f"🔒 Quest '{self._quest_name(locked_q)}' ist noch gesperrt. Steige Level auf oder spiele weiter, um sie freizuschalten.",
                        f"🔒 Quest '{self._quest_name(locked_q)}' is still locked. Level up or keep playing to unlock it.",
                    )
                if not self.qstate["available"]:
                    return self._t(
                        "ℹ Aktuell gibt es keine manuell annehmbaren Quests. Neue Quests werden im jetzigen System automatisch aktiviert.",
                        "ℹ There are currently no manually accept-able quests. In the current system, new quests activate automatically.",
                    )
                return self._t(f"Keine verfuegbare Quest mit ID/Nummer '{qid}'.", f"No available quest with ID/number '{qid}'.")

            # nach active verschieben (flache Kopie)
            self.qstate["available"].remove(q)
            active_q = dict(q)
            if active_q.get("type") in ("counter", "daily_streak"):
                active_q["progress"] = 0
            self.qstate["active"].append(active_q)
            return self._t(
                f"✅ Quest '{self._quest_name(active_q)}' angenommen.",
                f"✅ Quest '{self._quest_name(active_q)}' accepted.",
            )

        # ----------------------------
        # /quest info <id|nr>
        # ----------------------------
        if sub == "info":
            if not qid:
                return self._t("Bitte Quest-ID oder Nummer angeben: /quest info <id|nr>", "Please provide a quest ID or number: /quest info <id|nr>")

            q = None

            # 1) Zahl → Index in 'available' (primäre Liste zum Nachschlagen)
            if qid.isdigit():
                idx = int(qid) - 1
                if 0 <= idx < len(self.qstate["available"]):
                    q = self.qstate["available"][idx]

            # 2) Falls noch nichts gefunden → per ID in allen Listen suchen
            if q is None:
                q = (
                    self._find_quest_in_list(self.qstate["available"], qid)
                    or self._find_quest_in_list(self.qstate["active"], qid)
                    or self._find_quest_in_list(self.qstate["completed"], qid)
                    or self._find_quest_in_list(self.qstate["locked"], qid)
                )

            if not q:
                return self._t(f"Keine Quest mit ID/Nummer '{qid}' gefunden.", f"No quest found with ID/number '{qid}'.")

            dq = self._quest_display(q)
            lines = [
                f"{self._t('📖 Quest', '📖 Quest')}: {dq['name']}",
                f"ID: {dq['id']}",
                f"{self._t('Beschreibung', 'Description')}: {dq.get('desc','')}",
                f"{self._t('Typ', 'Type')}: {q.get('type','')}",
                f"{self._t('Belohnung', 'Reward')}: {q.get('reward_xp',0)} XP",
            ]
            preview = self._quest_path_bonus_preview(q)
            if preview:
                lines.append(preview)
            if q in self.qstate["active"]:
                lines.append(f"{self._t('Status', 'Status')}: {self._t('AKTIV', 'ACTIVE')} — {self._quest_progress_text(q)}")
            elif q in self.qstate["completed"]:
                lines.append(f"{self._t('Status', 'Status')}: {self._t('ABGESCHLOSSEN', 'COMPLETED')}")
            elif q in self.qstate["locked"]:
                lines.append(f"{self._t('Status', 'Status')}: {self._t('GESPERRT', 'LOCKED')}")
            else:
                lines.append(f"{self._t('Status', 'Status')}: {self._t('VERFUEGBAR', 'AVAILABLE')}")

            return "\n".join(lines)

        return self._t("Unbekanntes Subkommando. Nutze: /quest info <id|nr> oder /quest accept <id|nr>.", "Unknown subcommand. Use: /quest info <id|nr> or /quest accept <id|nr>.")

        
    # -------------------------------------------------
    # Fortschritts-Text für aktive Quests
    # -------------------------------------------------
    def _quest_progress_text(self, q: dict | None) -> str:
        """
        Gibt einen kurzen Fortschritts-Text für eine aktive Quest zurück.
        Wird von /quests (aktive Quests) und /quest info verwendet.
        """
        if not isinstance(q, dict):
            return ""

        qtype = q.get("type", "")
        name = q.get("name", q.get("id", "Quest"))

        # 🔢 Daily-Streak-Quests (z.B. daily_hello, daily_gratitude, ...)
        if qtype == "daily_streak":
            cur = int(q.get("progress", 0))
            target = int(q.get("required_days") or q.get("days") or 1)
            return self._t(f"Fortschritt: {cur}/{target} Tage", f"Progress: {cur}/{target} days")

        # ⚔️ Zähler-basierte Quests (first_win, battle_win, three_wins, ten_wins, ...)
        if qtype in ("counter", "battle_win"):
            cur = int(q.get("progress", 0))
            target = int(q.get("target", 1))
            if q.get("counter_key") == "messages_total":
                remaining = max(0, target - cur)
                return self._t(
                    f"Noch {remaining}/{target} Nachrichten uebrig",
                    f"{remaining}/{target} messages remaining",
                )
            return self._t(f"Fortschritt: {cur}/{target}", f"Progress: {cur}/{target}")

        # 💬 Chat-Keyword-Quests (Maat-Wert, Mona Lisa, Licht, etc.)
        if qtype == "chat_keyword":
            return self._t("Hinweis: Erfuelle die Bedingung im Chat (Schluesselwoerter verwenden).", "Hint: Fulfill the condition in chat (use the required keywords).")

        # Fallback
        return self._t("Aktive Quest", "Active quest")


        
    # -------------------------------------------------
    # HILFSMETHODEN
    # -------------------------------------------------
    def _get_current_level(self) -> int:
        """Liest den aktuellen Level aus dem RPG-State."""
        if self.state is None:
            return 1
        try:
            root = self.state.state if isinstance(self.state.state, dict) else {}
            player = root.get("player") if isinstance(root.get("player"), dict) else {}
            return int(player.get("level", root.get("level", 1)) or 1)
        except Exception:
            return 1

    def _get_current_tier(self) -> int:
        """Tier des aktuellen Levels: Level 1→0, Level 2→1, Level 4→2, Level 6→3 …"""
        lvl = self._get_current_level()
        return max(0, lvl // 2)

    def _quest_color(self, quest: dict) -> str:
        """
        Gibt Farbpräfix zurück basierend auf Quest-Tier vs. aktuellem Tier:
          🔴 = aktueller Tier (meiste XP)
          🟡 = vorheriger Tier
          🟢 = ältere Tiers (weniger XP)
        """
        current_tier = self._get_current_tier()
        q_tier = int(quest.get("level_tier", 0))
        if q_tier >= current_tier:
            return "🔴"
        if q_tier == current_tier - 1:
            return "🟡"
        return "🟢"

    def _quest_xp_effective(self, quest: dict) -> int:
        """XP mit Farbmultiplikator: 🔴=+25%, 🟡=±0%, 🟢=-25%."""
        base = int(quest.get("reward_xp", 0))
        color = self._quest_color(quest)
        if color == "🔴":
            return round(base * 1.25)
        if color == "🟢":
            return round(base * 0.75)
        return base

    # -------------------------------------------------
    # LOCKED → ACTIVE freischalten (auto-accept)
    # -------------------------------------------------
    def _check_unlocks(self):
        """
        Freischalt-Logik:
          • 20 Nachrichten → Quest-Intro + Tier-0-Quests direkt aktiv (auto-accept)
          • Jedes 2. Level → nächsten Tier freischalten (auto-accept)
        Gibt Liste von Nachrichten zurück (Intro + Unlock-Meldungen).
        """
        meta = self.qstate.setdefault("meta", {})
        total = meta.get("messages_total", 0)
        intro_shown = meta.get("quest_intro_shown", False)
        pre_intro_shown = meta.get("pre_intro_shown", False)
        shop_hint_shown = meta.get("shop_hint_shown", False)
        daily_hint_shown = meta.get("daily_hint_shown", False)
        last_unlock_level = meta.get("last_unlock_level", 0)
        current_level = self._get_current_level()

        notify_msgs = []
        newly_active = []

        # ── -1) STARTER-QUEST ab der ersten Nachricht ───────────────
        if total >= 1:
            for q in list(self.qstate["locked"]):
                if q.get("id") != "know_maat_ki":
                    continue
                self.qstate["locked"].remove(q)
                active_q = dict(q)
                active_q["progress"] = min(total, int(active_q.get("target", 10) or 10))
                self.qstate["active"].append(active_q)
                newly_active.append(active_q)

        # ── 0) PRE-INTRO TEASER bei Nachricht 10 ─────────────────────
        # Zwischen Nachricht 10 und 19: eine Teaser-Quest zum Erkunden
        if not pre_intro_shown and not intro_shown and total >= 10:
            meta["pre_intro_shown"] = True
            for q in list(self.qstate["locked"]):
                if int(q.get("level_tier", 0)) == -1:
                    self.qstate["locked"].remove(q)
                    active_q = dict(q)
                    if active_q.get("type") in ("counter", "daily_streak", "battle_win"):
                        active_q.setdefault("progress", 0)
                    self.qstate["active"].append(active_q)
                    newly_active.append(active_q)

            notify_msgs.append(self._t(
                "\n┌─────────────────────────────────────────────┐\n"
                "│  💡 Eine weitere Quest wartet auf dich!     │\n"
                "└─────────────────────────────────────────────┘\n"
                "   → Tippe  /quests  um sie zu sehen.\n"
                "   (Das volle Quest-System erwacht ab 20 Nachrichten.)",
                "\n┌─────────────────────────────────────────────┐\n"
                "│  💡 Another quest awaits you!               │\n"
                "└─────────────────────────────────────────────┘\n"
                "   → Type  /quests  to see it.\n"
                "   (The full quest system awakens after 20 messages.)",
            ))

        # ── 1) INTRO bei 20 Nachrichten ─────────────────────────────
        if not intro_shown and total >= 20:
            meta["quest_intro_shown"] = True
            meta["last_unlock_level"] = max(last_unlock_level, 1)

            # Tier-0-Quests auto-aktivieren
            for q in list(self.qstate["locked"]):
                if int(q.get("level_tier", 0)) == 0:
                    self.qstate["locked"].remove(q)
                    active_q = dict(q)
                    if active_q.get("type") in ("counter", "daily_streak", "battle_win"):
                        active_q.setdefault("progress", 0)
                    self.qstate["active"].append(active_q)
                    newly_active.append(active_q)

            intro_text = self._t(
                "🌟 ═══════════════════════════════════════\n"
                "   QUEST-SYSTEM FREIGESCHALTET!\n"
                "═══════════════════════════════════════\n\n"
                "Willkommen, Hüterin/Hüter der Maat!\n\n"
                "Das Quest-System ist nun aktiv. Quests helfen dir,\n"
                "tiefer in die Welt der Maat einzutauchen und XP zu sammeln.\n\n"
                "🔴 ROTE Quests  = Aktueller Tier → meiste XP\n"
                "🟡 GELBE Quests = Vorheriger Tier → normale XP\n"
                "🟢 GRÜNE Quests = Ältere Quests  → weniger XP\n\n"
                "Alle Quests werden automatisch angenommen.\n"
                "Alle 2 Level werden neue Quests freigeschaltet!\n\n"
                f"✨ {len(newly_active)} Quest(s) wurden automatisch gestartet.\n"
                "Tippe /quests um deine aktiven Quests zu sehen.\n"
                "🌟 ═══════════════════════════════════════",
                "🌟 ═══════════════════════════════════════\n"
                "   QUEST SYSTEM UNLOCKED!\n"
                "═══════════════════════════════════════\n\n"
                "Welcome, Guardian of Maat!\n\n"
                "The quest system is now active. Quests help you\n"
                "explore the world of Maat and earn XP.\n\n"
                "🔴 RED Quests    = Current tier → most XP\n"
                "🟡 YELLOW Quests = Previous tier → normal XP\n"
                "🟢 GREEN Quests  = Older quests  → less XP\n\n"
                "All quests are accepted automatically.\n"
                "Every 2 levels, new quests are unlocked!\n\n"
                f"✨ {len(newly_active)} quest(s) have been started automatically.\n"
                "Type /quests to see your active quests.\n"
                "🌟 ═══════════════════════════════════════",
            )
            notify_msgs.append(intro_text)

        # ── 1.5) SHOP-HINWEIS bei 40 Nachrichten ─────────────────────
        if intro_shown and not shop_hint_shown and total >= 40:
            meta["shop_hint_shown"] = True
            notify_msgs.append(self._t(
                "\n🏪 **Shop-System freigeschaltet**\n"
                "Mit `/shop` kannst du den MAAT-RPG-Laden öffnen.\n"
                "Dort bekommst du Heiltränke und Schutz-Siegel gegen Gold.\n"
                "Kaufen kannst du z. B. mit `/shop buy potion 1` oder `/shop buy sigil 1`.",
                "\n🏪 **Shop system unlocked**\n"
                "Use `/shop` to open the MAAT-RPG shop.\n"
                "There you can buy healing potions and warding sigils with gold.\n"
                "For example: `/shop buy potion 1` or `/shop buy sigil 1`.",
            ))

        # ── 1.6) DAILY-QUESTS bei 50 Nachrichten ─────────────────────
        if intro_shown and not daily_hint_shown and total >= 50:
            meta["daily_hint_shown"] = True
            daily_newly_active = []
            for q in list(self.qstate["locked"]):
                if q.get("type") == "daily_streak" and int(q.get("level_tier", 0)) <= 2:
                    self.qstate["locked"].remove(q)
                    active_q = dict(q)
                    active_q.setdefault("progress", 0)
                    self.qstate["active"].append(active_q)
                    daily_newly_active.append(active_q)
                    newly_active.append(active_q)

            if daily_newly_active:
                names = ", ".join(self._quest_name(q) for q in daily_newly_active[:3])
                if len(daily_newly_active) > 3:
                    names += f" (+{len(daily_newly_active) - 3})"
                notify_msgs.append(self._t(
                    "\n🌅 **Daily-Quests sind jetzt freigeschaltet**\n"
                    f"Aktiviert: {names}\n"
                    "Diese Quests wachsen ueber mehrere Tage mit dir mit.\n"
                    "Tippe `/quests`, um deinen taeglichen Fortschritt zu sehen.",
                    "\n🌅 **Daily quests are now unlocked**\n"
                    f"Activated: {names}\n"
                    "These quests unfold with you across multiple days.\n"
                    "Type `/quests` to see your daily progress.",
                ))
            else:
                notify_msgs.append(self._t(
                    "\n🌅 **Daily-Quests sind jetzt freigeschaltet**\n"
                    "Tippe `/quests`, um deine taeglichen Aufgaben und ihren Fortschritt zu sehen.",
                    "\n🌅 **Daily quests are now unlocked**\n"
                    "Type `/quests` to see your daily tasks and their progress.",
                ))

        # ── 2) LEVEL-BASIERTE FREISCHALTUNG alle 2 Level ─────────────
        # Tier 1 ab Level 2, Tier 2 ab Level 4, usw.
        if intro_shown or meta.get("quest_intro_shown", False):
            target_tier = current_level // 2  # Level 2→1, Level 4→2, Level 6→3 …
            unlocked_tier = last_unlock_level // 2

            if target_tier > unlocked_tier:
                meta["last_unlock_level"] = current_level
                tier_newly_active = []

                for q in list(self.qstate["locked"]):
                    q_tier = int(q.get("level_tier", 0))
                    if 0 < q_tier <= target_tier:
                        self.qstate["locked"].remove(q)
                        active_q = dict(q)
                        if active_q.get("type") in ("counter", "daily_streak", "battle_win"):
                            active_q.setdefault("progress", 0)
                        self.qstate["active"].append(active_q)
                        tier_newly_active.append(active_q)
                        newly_active.append(active_q)

                if tier_newly_active:
                    names = ", ".join(self._quest_name(q) for q in tier_newly_active[:3])
                    if len(tier_newly_active) > 3:
                        names += f" (+{len(tier_newly_active) - 3})"
                    notify_msgs.append(self._t(
                        "\n╔════════════════════════════════════════════╗\n"
                        f"║  ✨ NEUE QUESTS VERFÜGBAR! (Level {current_level})  \n"
                        "╚════════════════════════════════════════════╝\n"
                        f"🔴 {names}\n"
                        f"   {len(tier_newly_active)} neue Quest(s) wurden automatisch aktiviert.\n"
                        "   ➜ Tippe  /quests  für alle Details",
                        "\n╔════════════════════════════════════════════╗\n"
                        f"║  ✨ NEW QUESTS AVAILABLE! (Level {current_level})    \n"
                        "╚════════════════════════════════════════════╝\n"
                        f"🔴 {names}\n"
                        f"   {len(tier_newly_active)} new quest(s) have been auto-activated.\n"
                        "   ➜ Type  /quests  for details",
                    ))

        if newly_active and self.state is not None:
            try:
                self.state.save()
            except Exception:
                pass

        return notify_msgs
    # -------------------------------------------------
    # HOOKS FÜR ChatLoop / Pluginsystem
    # -------------------------------------------------
    def before_chat(self, user_input: str, context=None):
        """
        Wird vor dem Model-Call aufgerufen.
        Wir nutzen das, um Daily-Quests, Keyword-Quests
        und Unlocks (z.B. ab 40 Nachrichten) zu prüfen.
        """
        try:
            completed_msgs = []

            # 🔢 Nachrichten-Zähler hochzählen
            meta = self.qstate.setdefault("meta", {})
            meta["messages_total"] = meta.get("messages_total", 0) + 1

            # 🔓 Quests freischalten (Intro bei 20 Nachrichten + Level-Tiers)
            unlock_msgs = self._check_unlocks()
            completed_msgs.extend(unlock_msgs)

            # Daily-Quests
            self._check_daily_quests(user_input, completed_msgs)

            # Keyword-Quests (z.B. 'Maat-Wert')
            self._check_keyword_quests(user_input, completed_msgs)

            # Battle-Win-Quests (counter/battle_win) mit State synchronisieren
            self._check_battle_quests(completed_msgs)

            if completed_msgs and isinstance(context, dict):
                context.setdefault("quest_messages", []).extend(completed_msgs)

            self._save_runtime_state()

        except Exception:
            # Niemals den Chatloop crashen
            pass

        # handled = False → Input weiter normal verarbeiten
        return False, user_input

    def after_response(self, reply: str, context=None):
        """
        Wird nach der Model-Antwort aufgerufen.
        Quest-Nachrichten werden direkt auf die Konsole gedruckt –
        NICHT an reply angehängt, damit sie NICHT in den Conversation-History
        der KI landen und das Modell nicht verwirren.

        Zusätzlich: zweite Unlock-Prüfung hier, falls während der Antwort
        (z.B. durch Battle-XP oder Keyword-Quest-Completion) ein Level-Up
        stattgefunden hat.
        """
        if not isinstance(context, dict):
            context = {} if context is None else context

        try:
            late_battle_msgs = []
            self._check_battle_quests(late_battle_msgs)
            late_msgs = self._check_unlocks()
            combined = late_battle_msgs + (late_msgs or [])
            if combined and isinstance(context, dict):
                context.setdefault("quest_messages", []).extend(combined)
        except Exception:
            pass

        if not isinstance(context, dict):
            return None

        msgs = context.pop("quest_messages", [])
        if not msgs:
            return None

        print("\n" + "\n".join(msgs))
        return None  # reply unverändert → Quest-Text bleibt außerhalb des KI-Kontexts

    # -------------------------------------------------
    # INTERN: Daily & Keyword-Quests
    # -------------------------------------------------
    def _daily_quest_keywords(self, quest: dict) -> list[str]:
        keywords = []
        raw_keyword = quest.get("keyword")
        if isinstance(raw_keyword, str) and raw_keyword.strip():
            keywords.append(raw_keyword.strip().lower())

        aliases = {
            "daily_hello": ["hallo", "hello", "hi", "hey"],
            "daily_reflect": ["reflexion", "reflection", "selbstreflexion", "self-reflection"],
            "daily_gratitude": ["dankbar", "gratitude", "grateful"],
            "daily_learning": ["heute gelernt", "learned today", "today i learned", "i learned"],
            "daily_wisdom": ["weisheit", "wisdom", "zitat", "quote"],
            "daily_creation": ["erschaffen", "geschaffen", "create", "created", "etwas neues", "something new"],
            "daily_field_reflection": ["feld", "maat-feld", "field reflection", "maat field"],
            "maat_eternal_reflection": ["reflexion", "reflection", "maat-reflexion", "maat reflection"],
        }
        for value in aliases.get(quest.get("id"), []):
            lowered = value.lower()
            if lowered not in keywords:
                keywords.append(lowered)
        return keywords

    def _advance_daily_quest(self, quest: dict, today: str):
        last = str(quest.get("last_progress_day") or "").strip()
        if last == today:
            return None

        progress = int(quest.get("progress", 0) or 0)
        if not last:
            progress = 1
        else:
            try:
                last_date = datetime.fromisoformat(last).date()
                delta = (datetime.now().date() - last_date).days
                progress = progress + 1 if delta == 1 else 1
            except Exception:
                progress = 1

        quest["progress"] = progress
        quest["last_progress_day"] = today
        return progress

    def _check_daily_quests(self, user_input: str, completed_msgs: list):
        text = user_input.lower()
        today = datetime.now().date().isoformat()

        for q in list(self.qstate["active"]):
            if q.get("type") != "daily_streak":
                continue

            keywords = self._daily_quest_keywords(q)
            if not keywords:
                continue
            if not any(keyword in text for keyword in keywords):
                continue

            progress = self._advance_daily_quest(q, today)
            if progress is None:
                continue

            target = int(q.get("required_days") or q.get("days") or 1)
            if progress >= target:
                self._complete_quest(q, completed_msgs)

    def _check_keyword_quests(self, user_input: str, completed_msgs: list):
        text = user_input.lower()
        for q in list(self.qstate["active"]):
            if q.get("type") != "chat_keyword":
                continue
            kws = [k.lower() for k in q.get("keywords", [])]
            if any(k in text for k in kws):
                self._complete_quest(q, completed_msgs)

    def _check_battle_quests(self, completed_msgs: list):
        """
        Synchronisiert counter/battle_win-Quests mit dem echten Kampf-Zähler.
        Wird bei jedem before_chat/after_response aufgerufen.
        """
        if self.state is None:
            return
        try:
            root = self.state.state if isinstance(self.state.state, dict) else {}
            stats = root.get("stats") if isinstance(root.get("stats"), dict) else {}
            fights_won = int(stats.get("fights_won", root.get("fights", 0)) or 0)
            fights_total = int(stats.get("fights_total", fights_won) or 0)
            messages_total = int(self.qstate.get("meta", {}).get("messages_total", 0) or 0)
        except Exception:
            return

        for q in list(self.qstate["active"]):
            qtype = q.get("type")
            if qtype not in ("counter", "battle_win"):
                continue
            # Für counter-Quests nur mitzählen wenn counter_key auf battle wins passt
            progress_source = fights_won
            if qtype == "counter":
                key = q.get("counter_key", "")
                if key == "messages_total":
                    progress_source = messages_total
                elif key in ("fights", "fights_total"):
                    progress_source = fights_total
                elif key in ("battle_wins", "fights_won"):
                    progress_source = fights_won
                else:
                    continue

            target = int(q.get("target", 1))
            # Progress = absoluter Win-Count, geclamped auf target
            old_progress = int(q.get("progress", 0) or 0)
            new_progress = min(progress_source, target)
            if new_progress > old_progress:
                q["progress"] = new_progress
            if new_progress >= target:
                self._complete_quest(q, completed_msgs)

    # -------------------------------------------------
    # Quest-Abschluss + XP
    # -------------------------------------------------
    def _complete_quest(self, quest: dict, completed_msgs: list):
        """
        Verschiebt Quest nach 'completed' und vergibt XP.
        """
        if quest in self.qstate["active"]:
            self.qstate["active"].remove(quest)

        quest["completed_at"] = datetime.now().isoformat()
        self.qstate["completed"].append(quest)

        xp = self._quest_xp_effective(quest)
        color = self._quest_color(quest)
        bonus_xp, bonus_lines = self._quest_path_bonus(quest)
        xp_total = xp + bonus_xp
        display_quest = self._quest_display(quest)
        name = display_quest.get("name", quest.get("id", "Quest"))
        msg = self._t(
            f"🏆 Quest abgeschlossen: {color} {name}  (+{xp_total} XP)",
            f"🏆 Quest completed: {color} {name}  (+{xp_total} XP)",
        )
        completed_msgs.append(msg)
        completed_msgs.extend(bonus_lines)

        # XP ins RPG-Level-System + Level-Up → neuen Tier prüfen
        if self.state is not None and hasattr(self.state, "add_xp"):
            try:
                old_lvl, new_lvl = self.state.add_xp(xp_total)
                if new_lvl > old_lvl:
                    completed_msgs.append(
                        self._t(
                            f"🌟 LEVEL UP! Level {old_lvl} → {new_lvl}",
                            f"🌟 LEVEL UP! Level {old_lvl} → {new_lvl}",
                        )
                    )
                    # Neue Tier-Quests sofort prüfen und freischalten
                    tier_msgs = self._check_unlocks()
                    completed_msgs.extend(tier_msgs)
            except Exception:
                pass
        self._save_runtime_state()
