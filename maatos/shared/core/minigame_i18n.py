"""Minigame presentation only; game IDs, rules and rewards stay canonical."""
from .minigames import CATALOG

EN_GAMES = {
    'maat_coil': ('✦ MAAT-Snake · Star Covenant', '3 covenants: activate five shrines and return to the center'),
    'breakout': ('🧱 Seal Breaker', 'Break 40 seals with 3 lives'),
    'temple_circles': ('◎ MAAT · Temple Circles', '10 temple seals: align and activate three rune rings'),
    'memory': ('🃏 Rune Pairs', 'Find 8 pairs in no more than 16 pair attempts'),
    'mines': ('💎 Treasure Seeker', 'Reveal all safe tiles · 5 traps'),
    'lights': ('💡 Starlights', 'Turn off all lights in no more than 30 moves'),
    'slide': ('🔢 Temple Puzzle', 'Arrange numbers 1–8 in no more than 100 moves'),
    'maze': ('🧭 Desert Maze', 'Reach the golden gate'),
    'sokoban': ('📦 Seal Transport', 'Push both crates onto the golden targets'),
    'four': ('🔴 Connect Four', 'Connect four of your pieces · against the warden'),
    'three': ('⭕ Rune Duel', 'Connect three of your runes · against the warden'),
    'reflex': ('⚡ Star Catcher', 'Catch 15 stars before their time runs out'),
    'wheel': ('🎡 Wheel of Fortune', 'Spin the wheel · the gold star wins'),
    'snake_walls': ('🐍 Temple Wall Snake', 'Collect 15 fruits between the temple walls'),
    'maat_snake': ('✦ MAAT Snake', 'Collect 15 runes in the order H → B → S → V → R'),
    'maat_echo': ('🔔 Echo of the Principles', 'Remember five sequences of 3 to 7 runes'),
    'maat_balance': ('⚖ Scales of Truth', 'Balance three scales using the right weights'),
    'maat_creation': ('🎨 Creation Mosaic', 'Create the target pattern in no more than 45 clicks'),
    'maat_connection': ('✦ Path of Connection', 'Connect H → B → S → V → R without retracing your steps'),
    'maat_respect': ('🛡 Guardian of Respect', 'Choose the permitted rune twelve times · at most 2 mistakes'),
    'maat_numbers': ('📐 Resonance Arithmetic', 'Solve twelve resonance calculations · at most 2 mistakes'),
    'maat_towers': ('🏛 Towers of Terra', 'Move four discs to the right · no more than 30 moves'),
    'maat_rings': ('☀ Five Sun Rings', 'Set all five rings to 0 · no more than 35 clicks'),
}

EN = {
    '🎮 Minispiele freigeschaltet!': '🎮 Minigames unlocked!',
    '🎮 Minispiel · {name}': '🎮 Minigame · {name}',
    '{goal} · {xp} EP + {gold} Gold · Einmalige Belohnung': '{goal} · {xp} XP + {gold} Gold · One-time reward',
    'Spielen · {remaining}/2 Versuche übrig': 'Play · {remaining}/2 attempts left',
    'Weiterreisen': 'Continue journey',
    'Spielen': 'Play',
    '🔒 Noch nicht entdeckt': '🔒 Not discovered yet',
    '✦ DIE SPIELHALLE ✦': '✦ THE ARCADE ✦',
    '{count} / {total} Spiele entdeckt\nFinde Spiele zufällig im Chat, um sie hier dauerhaft freizuschalten.\nFreies Spielen zählt für Erfolge, ohne EP/Gold. Belohnungen gibt es bei Chat-Herausforderungen.': '{count} / {total} games discovered\nDiscover games randomly in chat to unlock them here permanently.\nFree play counts toward achievements, without XP/Gold. Chat challenges award rewards.',
    'Endlos · spiele bis zur Niederlage oder bis du zurückkehrst.': 'Endless · play until you lose or return.',
    'mehr ist besser': 'higher is better',
    'gesammelte Gewinne': 'total wins',
    'weniger ist besser · nur Siege': 'lower is better · wins only',
    'Noch kein Eintrag': 'No record yet',
    '🏆 Bestleistung: {value}\n{rule}': '🏆 Personal best: {value}\n{rule}',
    'Früchte': 'fruits', 'Siegel': 'seals', 'Reihen': 'rows', 'Sterne': 'stars',
    'Paarversuche': 'pair attempts', 'Klicks': 'clicks', 'Züge': 'moves',
    'Schritte': 'steps', 'Glückstreffer': 'lucky wins', 'Runen': 'runes',
    'Bünde': 'covenants', 'Tempelsiegel': 'temple seals',
    'Spielhalle · Freies Spielen · ohne EP/Gold': 'Arcade · Free play · no XP/gold',
    'Chat-Herausforderung · Versuch {attempts}/2': 'Chat challenge · Attempt {attempts}/2',
    'Zurück zur Spielhalle': 'Back to arcade',
    'Zurück zum Chat': 'Back to chat',
    'Leertaste: Pause · Esc: Spiel verlassen': 'Space: Pause · Esc: Leave game',
}
for kind, (name, goal) in EN_GAMES.items():
    EN[CATALOG[kind][0]] = name
    EN[CATALOG[kind][1]] = goal


def tr(text, language='de', **values):
    text = EN.get(text, text) if language == 'en' else text
    return text.format(**values) if values else text


def game_info(kind, language='de'):
    name, goal, xp, gold = CATALOG[kind]
    if language == 'en':
        name, goal = EN_GAMES[kind]
    return name, goal, xp, gold
