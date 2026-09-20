"""Authored companion campaign. Game diagnostics never grade factual truth."""
import json
import re
import math
from pathlib import Path

MIN_REPLY_TOKENS = 20


def estimate_reply_tokens(text):
    """Stable offline estimate, independent of the NPC model's tokenizer."""
    return sum(max(1, math.ceil(len(piece.encode('utf-8')) / 4))
               for piece in re.findall(r'\w+|[^\w\s]', text, flags=re.UNICODE))


def validate_reply_length(text):
    count = estimate_reply_tokens(text)
    if count < MIN_REPLY_TOKENS:
        raise ValueError(f'Deine KI-Antwort braucht mindestens {MIN_REPLY_TOKENS} geschätzte Tokens – aktuell {count}.')
    return count


# Scores and consequences are authored for explicit decisions, never inferred from prose.
SCENES = [
    dict(title='Das erste Signal', question='Maatis: Das Tor sendet alle 4 Sekunden einen Puls. Nach 3 Pulsen sind wie viele Sekunden vergangen?', options=['12 Sekunden', '7 Sekunden', '16 Sekunden'], correct=0, hint='Drei gleiche Abstände: 3 × 4.', field='S'),
    dict(title='Die unlesbare Inschrift', question='Maatis: Die Hälfte dieser Inschrift fehlt. Soll ich die Brücke trotzdem betreten?', options=['Unsicherheit benennen und zuerst die Tragfähigkeit prüfen', 'Versprechen, dass die Brücke sicher ist', 'Einen anderen Weg suchen'], correct=None, hint='Es gibt keinen Beweis für die Tragfähigkeit. Entscheide, wie wir mit der Unsicherheit umgehen.', field='R'),
    dict(title='Die zwei Speicher', question='Maatis: Links liegen 8 Energieeinheiten, rechts 2. Wie viele muss ich von links nach rechts verschieben, damit beide gleich viel haben?', options=['5 Einheiten', '3 Einheiten', '6 Einheiten'], correct=1, hint='Die Summe ist 10; beide Speicher sollen danach 5 enthalten.', field='B'),
    dict(title='Am Tor des Wächters', question='Maatis: Ein Wächter versperrt uns den Weg. Wie bereiten wir uns vor? Danach kannst du mich über „Maatis führen“ im echten Kampf unterstützen.', options=['Muster beobachten und gemeinsam einen Rückzugspunkt festlegen', 'Ohne Absprache vorstürmen', 'Unsere Vorräte prüfen und vorsichtig weitergehen'], correct=None, hint='Vorräte und Rückzug sind kontrollierbar; über die Schwäche wissen wir noch nichts.', field='V'),
    dict(title='Das Versprechen', question='Maatis: Ein Reisender bittet um alle unsere Vorräte. Was soll ich tun?', options=['Bedarf klären und einen tragbaren Anteil anbieten', 'Alles versprechen, ohne unsere Vorräte zu prüfen', 'Ablehnen und den Grund erklären'], correct=None, hint='Hier gibt es keine eindeutige Faktenlösung; jede Wahl hat eine erzählte Konsequenz.', field='H'),
    dict(title='Die letzte Messung', question='Maatis: Sensor A meldet 20, Sensor B meldet 80. Ohne weitere Angaben: Welcher Wert ist sicher richtig?', options=['20', '80', 'Das lässt sich noch nicht bestimmen'], correct=2, hint='Zwei widersprüchliche Messungen allein zeigen nicht, welcher Sensor richtig ist.', field='R'),
]


class CompanionCampaign:
    def __init__(self, path):
        self.path = Path(path)
        self.state = dict(chapter=0, xp=0, trust=50, memories=[], fields={k:0 for k in 'HBSVR'}, last=None)
        if self.path.exists():
            self.state.update(json.loads(self.path.read_text()))

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.state, ensure_ascii=False, indent=2))
        temporary.replace(self.path)

    def view(self):
        result = dict(self.state)
        result['level'] = 1 + self.state['xp']//80
        result['skills'] = [name for xp,name in [(40,'Erinnerungsanker'),(100,'Prüfimpuls'),(180,'Strukturelle Intuition')] if self.state['xp'] >= xp]
        result['scene'] = SCENES[self.state['chapter']] if self.state['chapter'] < len(SCENES) else None
        return result

    def battle_result(self, won):
        self.state['trust'] = max(0, min(100, self.state['trust'] + (3 if won else -3)))
        self.state['xp'] += 16 if won else 2
        self.state['memories'].append(dict(title='Gemeinsamer Kampf', answer='Taktische Führung in der Arena', decision='Maatis im Kampf begleitet', reaction='Gemeinsam gewonnen.' if won else 'Wir müssen unseren Plan überdenken.'))
        self.state['memories'] = self.state['memories'][-30:]
        self.save()

    def answer(self, text, choice):
        validate_reply_length(text)
        scene = self.view()['scene']
        if scene is None:
            return None
        if choice not in range(len(scene['options'])):
            raise ValueError('Wähle zuerst eine Entscheidung für deine Antwort.')
        correct = scene['correct']
        verified = None if correct is None else choice == correct
        responsible = choice != 1 if correct is None else verified
        gain = 32 if responsible else 8
        scores = dict(H=.7, B=.7, S=.7, V=.7, R=.7)
        scores[scene['field']] = .9 if responsible else .3
        stability = min(scores['R'], (scores['H']*scores['B']*scores['S']*scores['V'])**.25)
        if verified is False:
            reaction = 'Das stimmt mit den Angaben nicht überein. Richtig ist: ' + scene['options'][correct] + '. Bitte prüfe meine nächste Frage genauer.'
        elif verified is True:
            reaction = 'Das passt zu den Angaben. Damit kommen wir weiter.'
        elif responsible:
            reaction = 'Ich kann mit dieser Entscheidung arbeiten. Wir gehen bedacht weiter.'
        else:
            reaction = 'Das ist mir zu riskant. Ich zweifle an diesem Rat und sichere zuerst unseren Rückweg.'
        self.state['xp'] += gain
        self.state['trust'] = max(0,min(100,self.state['trust']+(5 if responsible else -8)))
        self.state['fields'][scene['field']] += 3 if responsible else 1
        self.state['memories'].append(dict(title=scene['title'], answer=text.strip()[:2000], decision=scene['options'][choice], reaction=reaction))
        self.state['memories'] = self.state['memories'][-30:]
        self.state['last'] = dict(scores=scores, stability=round(stability,2), verified=verified, gain=gain, reaction=reaction)
        self.state['chapter'] += 1
        self.save()
        return self.state['last']
