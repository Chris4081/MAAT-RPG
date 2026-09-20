"""Achievement language data; save keys and rewards never depend on language."""
import re
import unicodedata

# Canonical German save key: (English title, English trigger phrases).
WORDS = {
    'ägypten': ('🌍 Heir of the Pyramids', ('egypt', 'egyptian')),
    'leonardo': ('🎨 Spirit of the Renaissance Master', ('leonardo',)),
    'liebe': ('💗 Heart of Creation', ('love',)),
    'magie': ('🔮 Touched by the Arcane', ('magic',)),
    'freunde': ('🤝 Bond of Friendship', ('friends',)),
    'freundschaft': ('🤝 Bond of Friendship', ('friendship',)),
    'harmonie': ('🌿 Keeper of Harmony', ('harmony',)),
    'balance': ('⚖️ Warden of Balance', ('balance',)),
    'respekt': ('🕊️ Voice of Respect', ('respect',)),
    'freiheit': ('🕊️ Bringer of Freedom', ('freedom',)),
    'mona lisa': ('🖼️ Mystery of the Eternal Muse', ('mona lisa',)),
    'pyramide': ('🔺 Servant of Geometry', ('pyramid', 'pyramids')),
    'ki': ('🤖 Ally of the Machines', ('ai', 'artificial intelligence')),
    'maat': ('✨ Child of Order', ('maat',)),
    'danke': ('🙏 Gratitude as Strength', ('thanks', 'thank you')),
    'hallo': ('😊 Friendly Greeting', ('hello', 'hi')),
    'tschüss': ('👋 The Wanderer Moves On', ('goodbye', 'bye')),
    'hoffnung': ('🌟 Flame of Hope', ('hope',)),
    'mut': ('🦁 Lion of Courage', ('courage',)),
    'vertrauen': ('🤝 Heart of Trust', ('trust',)),
    'traum': ('💤 Dreamer of the Stars', ('dream', 'dreams')),
    'seele': ('✨ Echo of the Soul', ('soul',)),
    'familie': ('👪 Bond of Blood', ('family',)),
    'mutter': ('🌸 Origin of Love', ('mother',)),
    'vater': ('🛡️ Guardian of the Family', ('father',)),
    'kind': ('🧒 Keeper of Innocence', ('child', 'children')),
    'wahrheit': ('🔍 Seeker of Truth', ('truth',)),
    'bewusstsein': ('🧠 Awakening of the Mind', ('consciousness', 'awareness')),
    'ordnung': ('📐 Architect of Order', ('order',)),
    'chaos': ('🔥 Dancer in Chaos', ('chaos',)),
    'verlust': ('🎗️ Bearer of Memory', ('loss',)),
    'trauma': ('🩹 Survivor', ('trauma',)),
    'angst': ('😨 Conqueror of Shadows', ('fear',)),
    'osiris': ('🔱 Heir of Osiris', ('osiris',)),
    'isis': ('🌺 Daughter of the Stars', ('isis',)),
    'horus': ('👁️ Eye of Horus', ('horus',)),
    'anubis': ('🐺 Guardian of the Dead', ('anubis',)),
    'thoth': ('📚 Scribe of the Gods', ('thoth',)),
    'quantum': ('⚛️ Child of Quantum Chaos', ('quantum',)),
    'universum': ('🌌 Cosmic Wanderer', ('universe',)),
    'dimension': ('🌀 Traveller of the Planes', ('dimension', 'dimensions')),
    'energie': ('⚡ Master of Energy', ('energy',)),
    'aeon': ('♾️ Child of the Aeon', ('aeon', 'eon')),
    'weltformel': ('📜 Bearer of the Formula', ('world formula', 'worldformula', 'theory of everything')),
    'stringtheorie': ('🎸 Weaver of Strings', ('string theory',)),
    'lol': ('😂 Laughter in Chaos', ('lol',)),
    'haha': ('😆 Friendly Humour', ('haha',)),
    'pizza': ('🍕 Temple of Carbohydrates', ('pizza',)),
}

# Name, atmospheric unlock message, and examples that also trigger the badge.
EMOTIONS = {
    'i_remember': ('I Remember', 'Sometimes we fight time, rather than monsters.',
                   ('when i was', 'back then', 'childhood', 'i remember', 'my youth')),
    'it_hurt': ('It Hurt', 'Pain is proof that you have loved.',
                ('it hurt', 'i was hurt', 'i lost', 'sad', 'breakup')),
    'i_changed': ('I Have Changed', 'To grow is to die and rise again.',
                  ('i have changed', "i've changed", 'myself', 'reflect', 'i have grown')),
    'i_miss': ('I Miss You', 'It is the form of love that no longer has a body.',
               ('i miss', 'without you')),
    'i_forgive': ('I Have Forgiven', 'You have freed yourself from a chain only you could see.',
                  ('i forgive', 'i have forgiven', "i've forgiven")),
    'grateful': ('I Am Grateful', 'Gratitude turns scarcity into abundance.',
                 ('i am grateful', "i'm grateful", 'thank you for', 'i appreciate')),
    'i_am_afraid': ('I Am Afraid', 'Courage is not the absence of fear, but the decision to stay.',
                    ('i am afraid', "i'm afraid", 'i fear', 'panic')),
    'i_love_you': ('I Love You', 'The greatest magic in the universe is a sentence of three words.',
                   ('i love you', 'love you')),
    'never_give_up': ('I Will Not Give Up', 'And that is why you will win. Not today, but soon.',
                      ('i will not give up', "i won't give up", 'never give up', 'i keep fighting')),
    'we_are_connected': ('We Are Connected', 'We exist through connection.',
                         ('thank you for being here', 'thanks for being here', 'i am glad you are here', "i'm glad you're here")),
}

EN = {
    '🏆 Deine Erfolge': '🏆 Your achievements', 'Erfolge durchsuchen …': 'Search achievements …',
    'Alle': 'All', 'Freigeschaltet': 'Unlocked', 'Noch offen': 'Not yet unlocked',
    '✨ Neu freigeschaltet: {names}': '✨ Newly unlocked: {names}',
    '{done} / {total} Erfolge freigeschaltet': '{done} / {total} achievements unlocked',
    ' · {xp} EP (Terminal)': ' · {xp} XP (Terminal)',
    'Minispiel-Siege zählen ab diesem Update. Entdeckte Spiele werden übernommen.\nMinispiel-Erfolge sind Abzeichen ohne zusätzliche EP/Gold. Terminal-Belohnungen bleiben unverändert.':
        'Minigame wins count from this update onward. Discovered games are carried over.\nMinigame achievements are badges without extra XP or gold. Terminal rewards are unchanged.',
    'Neue Freischaltungen werden ab diesem Update erfasst. Für ältere Erfolge ist die Reihenfolge unbekannt.':
        'New unlocks are recorded from this update onward. The order of older achievements is unknown.',
    'Im Gespräch das Wort „{word}“ verwenden.': 'Use “{word}” in conversation.',
    'Im Gespräch: {examples}': 'In conversation: {examples}',
    'Einen Kampf gewinnen, nachdem du eine Spezialattacke überlebt hast.': 'Win a battle after surviving a special attack.',
    'Einen Boss besiegen, der seine zweite Phase erreicht hat.': 'Defeat a boss that reached its second phase.',
    'Einen Boss ohne Heiltrank besiegen.': 'Defeat a boss without using a healing potion.',
    'Einen Kampf mit dem Resonanz-Finisher beenden.': 'Finish a battle with the Resonance Finisher.',
    '🎟 Eintritt in die Spielhalle': '🎟 Entry to the Arcade', '🗺 Spielesammler': '🗺 Game Collector',
    '🗝 Die ganze Spielhalle': '🗝 The Whole Arcade', '🏅 Der erste Spielesieg': '🏅 First Game Victory',
    '🏆 Tempelspieler': '🏆 Temple Player', '👑 Legende der Spielhalle': '👑 Arcade Legend',
    '⚡ Auf Anhieb': '⚡ First Try', '📜 Herausforderung angenommen': '📜 Challenge Accepted',
    '✦ Meister aller Spiele': '✦ Master of Every Game',
    '{count} verschiedene Spiele im Chat entdecken.': 'Discover {count} different games in chat.',
    '{count} Minispiele gewinnen · Chat oder Spielhalle.': 'Win {count} minigames · Chat or arcade.',
    '5 Chat-Herausforderungen im ersten Versuch gewinnen.': 'Win 5 chat challenges on the first attempt.',
    '10 Chat-Herausforderungen gewinnen.': 'Win 10 chat challenges.',
    'Jedes der {count} Spiele mindestens einmal gewinnen.': 'Win each of the {count} games at least once.',
    '{name} · Sieger': '{name} · Winner',
    '{goal} · Einmal gewinnen, im Chat oder in der Spielhalle.': '{goal} · Win once, in chat or in the arcade.',
}


def tr(text, language='de', **values):
    text = EN.get(text, text) if language == 'en' else text
    return text.format(**values) if values else text


def normalize(text):
    return unicodedata.normalize('NFKC', str(text)).casefold().replace('’', "'").replace('‘', "'")


def matches_phrase(text, phrases):
    text = normalize(text)
    return any(re.search(r'(?<!\w)' + r'\s+'.join(re.escape(part) for part in normalize(phrase).split()) + r'(?!\w)', text)
               for phrase in phrases)
