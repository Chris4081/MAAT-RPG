"""Small ASCII-only animation frames for combat, independent of game rules."""
SUPPORT_FRAMES = {
    'focus': (' . ', ' (.) ', ' (+) ', ' ((+)) ', ' (+) ', ' . ', '   '),
    'heal': (' . ', ' + ', ' + + ', ' +++ ', ' + + ', ' + ', '   '),
}
FRAMES = {
    'slash': (' . ', ' -- ', ' ---> ', ' ==/=> ', ' * / * ', '  +  ', ' . '),
    'claw': (' . ', ' / / ', ' /// ', ' ///> ', ' *X* ', ' + + ', ' . '),
    'wave': (' . ', ' ~ ', ' ~~~ ', ' ~~~> ', ' ( * ) ', ' ~ ~ ', ' . '),
    'spark': (' . ', ' + ', ' /Z/ ', ' /Z/> ', ' *+* ', ' + + ', ' . '),
    'sand': (' . ', ' .: ', ' .::: ', ' .:::> ', ' :*:*: ', ' : . ', ' . '),
    'balance': (' . ', ' = ', ' =|= ', ' =|=> ', ' [*] ', ' - - ', ' . '),
    'creation': (' . ', ' + ', ' +*+ ', ' +*+> ', ' **+** ', ' * * ', ' . '),
    'connection': (' . ', ' o ', ' o-o ', ' o-o-> ', ' (o*o) ', ' o o ', ' . '),
    'respect': (' . ', ' [] ', ' [|] ', ' [|]=> ', ' [*] ', ' [ ] ', ' . '),
    'impulse': (' . ', ' (*) ', ' ((+)) ', ' ==(*)== ', ' **+** ', ' * + * ', ' . '),
}


def effect_kind(event, archetype):
    if event.get('attack') == 'special':
        return 'impulse'
    if event.get('attacker') == 'player':
        attack = event.get('attack', '').lower()
        if attack in {'h', 'b', 's', 'v', 'r'}:
            return dict(h='wave', b='balance', s='creation', v='connection', r='respect')[attack]
        if attack in ('focus', 'heal', 'potion'):
            return 'heal' if attack == 'potion' else attack
        for word, kind in [('harmony','wave'),('creation','creation'),('connectedness','connection'),('connection','connection'),('respect','respect'),('harmonie','wave'),('balance','balance'),('schöpfung','creation'),
                           ('verbundenheit','connection'),('respekt','respect'),('skill','spark'),('impulse','impulse')]:
            if word in attack:
                return kind
        return 'slash'
    from shared.core.monster_catalog import ENEMY_EFFECTS
    return ENEMY_EFFECTS.get(archetype, 'slash')


def directional_frame(text, attacker):
    if attacker != 'enemy':
        return text
    return text[::-1].translate(str.maketrans('></\\()[]', '<>\\/)(]['))
