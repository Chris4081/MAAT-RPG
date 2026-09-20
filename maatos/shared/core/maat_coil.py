"""Deterministic Star Covenant: a fixed light trail, shrines and timed rifts.

The trail never grows and is safe to cross. A circuit requires five different
shrines followed by the central sanctuary. Replay remains the reward authority.
"""
import random


class StarCoil:
    width = height = 17
    center = (8, 8)
    shrines = ((8, 1), (14, 6), (12, 13), (4, 13), (2, 6))
    actions = {'L', 'R', 'U', 'D'}
    target = 3
    endless = False
    trail_length = 7
    round_budget = 190

    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.body = [self.center]
        self.direction = 'U'
        self.moves = []
        self.score = 0
        self.over = False
        self.shields = 3
        self.charged = set()
        self.remaining = self.round_budget
        self.ticks = 0
        self.invulnerable = 0
        self.pulse_age = 0
        self.rift_axis = self.rng.randrange(4)
        self.rift_offset = self.rng.randint(-3, 3)
        self.reason = ''

    @classmethod
    def inside(cls, cell):
        x, y = cell
        return (x - 8) ** 2 + (y - 8) ** 2 <= 58

    @classmethod
    def sanctuary(cls, cell):
        return any(abs(cell[0] - x) + abs(cell[1] - y) <= 1
                   for x, y in (cls.center, *cls.shrines))

    @property
    def pulse_period(self):
        return max(30, 54 - self.score * 3)

    @property
    def warning(self):
        return self.pulse_age >= self.pulse_period - 14

    @property
    def dangerous(self):
        return self.pulse_age >= self.pulse_period - 4

    def in_rift(self, cell):
        if self.sanctuary(cell):
            return False
        x, y = cell[0] - 8, cell[1] - 8
        return (x, y, x - y, x + y)[self.rift_axis] == self.rift_offset

    def hurt(self, reason):
        if self.invulnerable:
            return
        self.shields -= 1
        self.invulnerable = 12
        if self.shields <= 0:
            self.over = True
            self.reason = reason

    def step(self, action):
        if self.over:
            return
        if action not in self.actions:
            raise ValueError('Invalid Star Covenant action')
        self.moves.append(action)
        self.direction = action
        self.ticks += 1
        self.invulnerable = max(0, self.invulnerable - 1)
        self.remaining -= 1
        self.pulse_age += 1
        if self.pulse_age >= self.pulse_period:
            self.pulse_age = 0
            self.rift_axis = self.rng.randrange(4)
            self.rift_offset = self.rng.randint(-3, 3)
        dx, dy = {'L': (-1, 0), 'R': (1, 0), 'U': (0, -1), 'D': (0, 1)}[action]
        x, y = self.body[0]
        head = (x + dx, y + dy)
        if self.inside(head):
            self.body.insert(0, head)
            del self.body[self.trail_length:]
        head = self.body[0]
        for index, shrine in enumerate(self.shrines):
            if head == shrine:
                self.charged.add(index)
        if self.dangerous and self.in_rift(head):
            self.hurt('rift')
        if self.over:
            return
        if len(self.charged) == 5 and head == self.center:
            self.score += 1
            self.charged.clear()
            self.remaining = max(100, self.round_budget - self.score * 5)
            if self.score >= self.target and not self.endless:
                self.over = True
                self.reason = 'complete'
                return
        if self.remaining <= 0:
            # Timing pressure cannot be avoided by resting in a safe sanctuary.
            self.invulnerable = 0
            self.hurt('time')
            self.charged.clear()
            self.remaining = max(100, self.round_budget - self.score * 5)
        if not self.endless and self.ticks >= 40000:
            self.over = True
            self.reason = 'limit'


def migrate_classic_snake(state):
    """Keep discoveries/earned wins; archive incomparable fruit highscores.

    Outstanding tickets are invalidated, never refunded. Repeated calls do not
    duplicate progress. No user files are accessed by this migration.
    """
    data = state.get('minigames', {})
    if 'snake' in data.get('discovered', []):
        data['discovered'] = list(dict.fromkeys(
            'maat_coil' if k == 'snake' else k for k in data['discovered']))
    wins = data.get('wins', {})
    if 'snake' in wins:
        wins['maat_coil'] = int(wins.get('maat_coil', 0)) + int(wins.pop('snake'))
    scores = data.get('highscores', {})
    if 'snake' in scores:
        data.setdefault('legacy_highscores', {})['snake'] = scores.pop('snake')
    pending = data.get('pending')
    if pending and pending.get('game') == 'snake':
        pending['game'] = 'maat_coil'
        pending.pop('ticket', None)
    practice = data.get('practice')
    if practice and practice.get('game') == 'snake':
        data.pop('practice', None)
