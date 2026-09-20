"""Shared arena and random-encounter tiers for combat stats, rewards and presentation."""
TIERS = {
    'easy': {'label': 'Leicht', 'color': '#79d69b', 'hp': .75, 'damage': .80, 'xp': .75},
    'normal': {'label': 'Normal', 'color': '#f2cf66', 'hp': 1., 'damage': 1., 'xp': 1.},
    'hard': {'label': 'Schwer', 'color': '#f08080', 'hp': 1.35, 'damage': 1.25, 'xp': 1.50},
}

# Ordinary arena/random fights use action budgets, rather than increasing
# difficulty every level. The legacy multipliers above still serve demos and
# special fights; labels, colors and XP rewards are shared by both systems.
# (reference principle hits, reference impulses, incoming share of level HP)
ENCOUNTER_TARGETS = {
    'easy': (3.5, 0, .21),
    'normal': (4.0, 1, .28),
    'hard': (5.4, 1, .29),
}


def combat_tier(context):
    if not isinstance(context, dict) or context.get('combat_source') not in ('arena', 'random', 'demo'):
        return None
    return TIERS.get(context.get('arena_difficulty'), TIERS['normal'])


def normal_encounter_stats(hp, damage, level, fight_type, context):
    """Return ordinary fight stats including the tier, or None for other fights.

    Reference build: untrained Creation + impulse, MAAT fields at .8 (the
    normal combat unlock after 30 messages), no talents/items/story bonuses.
    Enemy HP follows this build's damage; incoming damage follows regular
    level HP. Thus levels raise the numbers, not the intended difficulty.
    The player's current HP, actual buffs, talents and inventory never enter
    the calculation: healing, build choices and upgrades retain their value.
    """
    context = context or {}
    if (fight_type != 'normal' or context.get('combat_source') not in ('arena', 'random')
            or context.get('guide_mode') or context.get('title_demo_mode') or context.get('editor_mode')):
        return None
    level = max(1, int(level))
    attacks, impulses, hit_share = ENCOUNTER_TARGETS.get(
        context.get('arena_difficulty'), ENCOUNTER_TARGETS['normal'])
    # Mean base roll + Creation buff + approximate weakness/critical average.
    reference_attack = (12 + 2 * level + .5) * 1.24 * 1.08
    reference_impulse = 32 + 5 * level + 7
    level_hp = 100 + (level - 1) * 10
    target_hp = attacks * reference_attack + impulses * reference_impulse
    target_damage = level_hp * hit_share
    # Preserve custom base-stat overrides; standard enemy stats cancel out.
    return (max(1, round(target_hp * hp / (40 + level * 8))),
            max(1, round(target_damage * damage / (5 + level * 2))))
