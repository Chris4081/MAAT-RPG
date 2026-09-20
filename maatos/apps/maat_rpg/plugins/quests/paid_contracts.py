"""25 one-time endgame contracts. Progress starts at purchase, never retroactively."""
TOPICS = [
 ('Die Karawane der Morgenröte','Begleite eine Karawane durch die Dünen.', 'wins'),
 ('Karten für die Oase','Besprich sichere Wege zwischen den Oasen.', 'chat'),
 ('Wache am Sternentor','Sichere die Wege zum Sternentor.', 'wins'),
 ('Stimmen im Sand','Sammle im Gespräch Erinnerungen an die Wüste.', 'chat'),
 ('Die verlorene Laterne','Halte Schatten von den Laternenpfaden fern.', 'wins'),
 ('Das Wasser der Nachbarn','Entwickle mit deinem Gegenüber Ideen für gerechte Wasserverteilung.', 'chat'),
 ('Schutz für die Boten','Mache die Botenwege wieder sicher.', 'wins'),
 ('Das offene Archiv','Besprich, wie Wissen für alle zugänglich bleiben kann.', 'chat'),
 ('Die letzte Nachtwache','Unterstütze die Nachtwachen von Terra.', 'wins'),
 ('Ein Garten aus Fragen','Erkunde im Gespräch neue Möglichkeiten für die Oase.', 'chat'),
 ('Prüfung der fünf Tore','Bewähre dich auf dem Weg zwischen den fünf Toren.', 'wins'),
 ('Die Waage der Städte','Erörtere Konflikte zwischen Terras Städten.', 'chat'),
 ('Die zerbrochene Eskorte','Sichere einen langen Versorgungspfad.', 'wins'),
 ('Bibliothek ohne Mauern','Entwickle im Gespräch eine reisende Bibliothek.', 'chat'),
 ('Wächter der Flussquellen','Verteidige die Wege zu Terras Quellen.', 'wins'),
 ('Der Rat der Fremden','Besprich, wie fremde Gruppen gemeinsame Regeln finden können.', 'chat'),
 ('Das Tal der Echos','Stelle dich den Schatten auf den Talwegen.', 'wins'),
 ('Eine Grenze aus Licht','Untersuche im Dialog Hilfe, Freiheit und persönliche Grenzen.', 'chat'),
 ('Siegel der Heimkehr','Sichere die Rückwege versprengter Reisender.', 'wins'),
 ('Die unvollständige Chronik','Sammle im Gespräch Perspektiven für eine ehrliche Chronik.', 'chat'),
 ('Expedition zum ersten Horizont','Führe eine lange Expedition durch Terras Schattengebiete.', 'wins'),
 ('Das Vermächtnis der Stimmen','Entwickle im Dialog ein Vermächtnis für kommende Generationen.', 'chat'),
 ('Die Wacht jenseits des Thrones','Bewahre die freien Wege nach dem Fall des Thrones.', 'wins'),
 ('Der lebendige Weltatlas','Erkunde im Gespräch, wie Terra sich weiterentwickeln könnte.', 'chat'),
 ('Hüter des neuen Morgens','Bewähre dich auf einer langen Reise durch das befreite Terra.', 'wins'),
]
TITLES=['Horizontwächter','Bewahrer der Stimmen','Wächter ohne Thron','Chronist des lebendigen Terra','Hüter des neuen Morgens']
PAID_CONTRACTS=[]
for index,(name,story,kind) in enumerate(TOPICS):
    tier=0 if index<10 else 1 if index<20 else 2
    price=(500,1000,2000)[tier]
    target=((5,12,30) if kind=='wins' else (10,25,50))[tier]
    xp=(800,1800,4000)[tier]
    rewards=({'potions':1},{'potions':2,'sigils':1},{'potions':3,'sigils':2})[tier]
    title=TITLES[index-20] if tier==2 else None
    objective=f'Gewinne {target} echte Kämpfe nach dem Kauf; Arena und Zufallskämpfe zählen.' if kind=='wins' else f'Sende nach dem Kauf {target} normale Chatnachrichten. Beide Spielperspektiven zählen; Befehle zählen nicht. Die Erzählidee ist frei, der Zähler prüft keine inhaltliche Qualität.'
    reward=f'{xp} Basis-EP, '+', '.join(f'{n} '+('Heiltrank' if k=='potions' and n==1 else 'Heiltränke' if k=='potions' else 'Schutz-Siegel') for k,n in rewards.items())
    if title:reward+=f' und Sammeltitel „{title}“'
    PAID_CONTRACTS.append(dict(id=f'contract50_{index+1:02}',name=name,desc=f'{story}\nZiel: {objective}\nBelohnung: {reward}.',
        type='battle_win' if kind=='wins' else 'counter',counter_key='battle_wins' if kind=='wins' else 'messages_total',
        target=target,level_tier=25,reward_xp=xp,purchase_price=price,reward_items=dict(rewards),reward_title=title,
        repeatable=False,contract_category=('Expedition','Prüfung','Großer Auftrag')[tier]))
