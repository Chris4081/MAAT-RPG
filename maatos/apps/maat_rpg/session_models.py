# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class PlayerSnapshot:
    hp: int = 120
    max_hp: int = 120
    level: int = 3
    xp: int = 605
    next_xp: int = 925
    gold: int = 17
    potions: int = 1
    boss_victories: int = 0
    final_victories: int = 0
    principles_restored: int = 0
    path_profile: str = "Tone Seeker of Memory"
    rank: str = "Awakening"
    motive: str = "Memory continues to resonate as order."


@dataclass(slots=True)
class BattleSnapshot:
    round_number: int = 0
    fight_type: str | None = None
    enemy_level: int | None = None
    combat_source: str | None = None
    arena_difficulty: str | None = None
    active: bool = False
    enemy_name: str = ""
    enemy_visual: dict = field(default_factory=dict)
    enemy_hp: int = 0
    enemy_max_hp: int = 0
    resonance: int = 0
    weakness: str = "-"
    aura: str = "-"
    phase: str = "-"
    charge: int = 0
    charge_max: int = 3
    last_log: str = ""


@dataclass(slots=True)
class ChoiceRequest:
    prompt: str
    options: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SystemEvent:
    kind: str
    message: str


@dataclass(slots=True)
class UiSnapshot:
    language: str = "en"
    profile_name: str = "Standard Profile"
    profile_labels: list[str] = field(default_factory=list)
    app_title: str = "MAAT-RPG Desktop Alpha"
    model_status: str = "Local model bridge ready"
    status_text: str = "Idle"
    thinking_enabled: bool = False
    rpg_context_enabled: bool = False
    hallu_mode: bool = False
    music_enabled: bool = False
    voice_enabled: bool = True
    player: PlayerSnapshot = field(default_factory=PlayerSnapshot)
    battle: BattleSnapshot = field(default_factory=BattleSnapshot)
