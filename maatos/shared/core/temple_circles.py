"""Deterministic rune-ring puzzle; no falling pieces or rectangular well."""
import random


class TempleCircles:
    target = 10
    endless = False
    actions = {'0L', '0R', '1L', '1R', '2L', '2R', 'seal'}

    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.moves = []
        self.score = 0
        self.focus = 3
        self.over = False
        self.reason = ''
        self.order = []
        self.new_pattern()

    @property
    def budget(self):
        return 7 if self.score >= 10 else 8

    @property
    def gate(self):
        return self.score % 5

    @property
    def rune(self):
        return self.order[self.gate]

    @property
    def aligned(self):
        return all(ring[self.gate] == self.rune for ring in self.rings)

    def new_pattern(self):
        if self.gate == 0:
            self.order = list('HBSVR')
            self.rng.shuffle(self.order)
        self.rings = []
        for _ in range(3):
            ring = list('HBSVR')
            self.rng.shuffle(ring)
            self.rings.append(ring)
        # Every pattern needs at least one rotation. Any target can be reached
        # with at most 2 rotations per ring + 1 seal action = 7 moves.
        if self.aligned:
            self.rings[0] = self.rings[0][-1:] + self.rings[0][:-1]
        self.remaining = self.budget

    def fail(self, reason):
        self.focus -= 1
        self.reason = reason
        if self.focus == 0:
            self.over = True
        else:
            self.new_pattern()

    def step(self, action):
        if self.over:
            return
        if action not in self.actions:
            raise ValueError('Invalid Temple Circles action')
        self.moves.append(action)
        self.remaining -= 1
        self.reason = ''
        if action == 'seal':
            if not self.aligned:
                self.fail('alignment')
            else:
                self.score += 1
                if self.score >= self.target and not self.endless:
                    self.over = True
                    self.reason = 'complete'
                else:
                    self.new_pattern()
        else:
            index = int(action[0])
            ring = self.rings[index]
            self.rings[index] = ring[-1:] + ring[:-1] if action[1] == 'R' else ring[1:] + ring[:1]
            if self.remaining == 0:
                self.fail('moves')


def migrate_temple_blocks(state):
    """Preserve earned progress, but don't mix cleared rows with temple seals."""
    data = state.get('minigames', {})
    if 'tetris' in data.get('discovered', []):
        data['discovered'] = list(dict.fromkeys(
            'temple_circles' if kind == 'tetris' else kind for kind in data['discovered']))
    wins = data.get('wins', {})
    if 'tetris' in wins:
        wins['temple_circles'] = int(wins.get('temple_circles', 0)) + int(wins.pop('tetris'))
    records = data.get('highscores', {})
    if 'tetris' in records:
        data.setdefault('legacy_highscores', {})['tetris'] = records.pop('tetris')
    pending = data.get('pending')
    if pending and pending.get('game') == 'tetris':
        pending['game'] = 'temple_circles'
        pending.pop('ticket', None)
    practice = data.get('practice')
    if practice and practice.get('game') == 'tetris':
        data.pop('practice', None)
