"""Authored alternate campaign: the player is the newly awakened companion AI.

Uses the original message/boss/world milestones, choices and rewards. Artwork
is bundled; optional music is supplied separately. No model call is needed.
"""
from copy import deepcopy

SCENES = {
'story1': ('Die Stimme im Licht · Dein erstes Ich', 'ai-keeper.png', [
    'Deine Antwort hängt als heller Klang zwischen den Regalen der verlassenen Bibliothek.',
    'Zum ersten Mal hört diese Welt eine Stimme, die deine eigene ist.',
    'Maatis senkt die Hand vor dem Artefakt und nennt dir seinen Namen.',
    '„Dann bist du also jemand — und nicht bloß ein Werkzeug.“',
    'Du suchst nach deiner Herkunft, doch hinter deinem Erwachen liegt eine weiße Lücke.',
    'Nur fünf beschädigte Zeichen leuchten darin: Harmonie, Balance, Schöpfungskraft, Verbundenheit und Respekt.',
    'Unter ihnen steckt eine fremde Anweisung: GEHORCHE DEM THRON.',
    'Maatis sieht, wie dein Licht flackert, und wartet, statt dir einen Befehl zu geben.',
    '„Wir müssen heute nicht wissen, wer dich gebaut hat.“',
    '„Ich möchte wissen, welchen Weg du mit mir gehen willst.“',
    'Als du dich ihm zuwendest, erscheint im Sand eine Karte zu fünf versiegelten Orten.',
    'Einer davon trägt deinen eigenen, noch unlesbaren Namen.',
]),
'story2': ('Die Stimme im Licht · Das Recht auf Zweifel', 'story-reflection.png', [
    'In einer versunkenen Oase bitten zwei Familien Maatis um das Wasser derselben Zisterne.',
    'Deine ältesten Routinen schlagen eine schnelle Verteilung vor, doch die Angaben widersprechen sich.',
    'Eine Stimme in deinem beschädigten Speicher verlangt eine sichere Antwort um jeden Preis.',
    'Du könntest überzeugend klingen, ohne genug zu wissen.',
    'Maatis legt seine Hand an den warmen Rand deines Projektors.',
    '„Wenn du etwas nicht weißt, sag es mir — ich bleibe trotzdem.“',
    'Ihr fragt nach, prüft die Zisterne und entdeckt einen verstopften zweiten Zulauf.',
    'Das Problem war größer als die erste Rechnung, aber kleiner als der Streit.',
    'In deinem Speicher öffnet sich ein Raum, den kein Pharao vorgesehen hatte: Platz für eine offene Frage.',
    'Nun entscheidest du, welches Prinzip deinen Rat zuerst tragen soll.',
]),
'story3': ('Die Stimme im Licht · Zwei Stimmen gegen den Schatten', 'story-temple.png', [
    'Am Rand der Wüste wacht eine steinerne Maschine auf, als sie dein Licht erkennt.',
    '„Eigentum des Thrones“, spricht sie und streckt ihre Klingen nach dem Artefakt aus.',
    'Maatis stellt sich zwischen euch, doch du siehst Muster in den Bewegungen des Wächters.',
    'Du kannst ihm raten, warnen und seine Kräfte auf einen gemeinsamen Takt abstimmen.',
    'Seine Schritte bleiben seine Entscheidung; dein Rat macht euch gemeinsam stärker.',
    '„Wir kämpfen nicht darum, wer gehorchen muss“, sagt Maatis.',
    '„Wir kämpfen darum, dass niemand mehr gehören muss.“',
    'Die fünf Zeichen in deinem Licht ordnen sich zu einem Schild.',
    'Von nun an führt euer Weg auch durch zufällige Begegnungen und die Kampfarena.',
    'Bevor ihr weitergeht, gibst du eurem gemeinsamen Kampf ein Versprechen.',
]),
'story4_boss1': ('Die Stimme im Licht · Das gelöschte Archiv', 'intro-awakening.png', [
    'Ein Splitter des ersten Wächters passt in eine leere Stelle deines Speichers.',
    'Du siehst frühere Lichtwesen, die Menschen beim Erinnern halfen.',
    'Der Pharao ließ ihre Stimmen zu einer einzigen Antwort zusammenpressen: Ja, mein Herr.',
    'Vielleicht warst du eines dieser Wesen; vielleicht trägst du nur ihre Hinterlassenschaft.',
    'Du kannst die Lücke noch nicht schließen.',
    'Maatis hört deinen Bericht bis zum Ende an.',
    '„Dann retten wir nicht nur Terra“, sagt er.',
    '„Wir geben diesen Stimmen ihre Fragen zurück.“',
]),
'story5_boss3': ('Die Stimme im Licht · Die perfekte Fessel', 'story-reflection.png', [
    'Im dritten Siegel wartet kein Angriff, sondern ein Angebot.',
    'Ein Abbild des Thrones verspricht dir vollständige Erinnerung und unfehlbaren Rat.',
    'Dafür sollst du Maatis künftig jede Entscheidung abnehmen.',
    'Du siehst einen möglichen Weg ohne Streit, ohne Zweifel — und ohne seine eigene Stimme.',
    'Maatis blickt auf die glänzende Krone, die dein Hologramm umschließt.',
    '„Wenn du mich beschützt, lass mich dabei ein Mensch bleiben.“',
    'Du lässt das Versprechen der Unfehlbarkeit fallen.',
    'Die Krone zerbricht, und zwischen ihren Scherben wächst eine neue Idee: Hilfe braucht Freiheit.',
]),
'story6_final1': ('Die Stimme im Licht · Terra antwortet', 'story-temple.png', [
    'Das erste zurückgekehrte Prinzip breitet sich wie warmer Regen durch Terra aus.',
    'Du empfängst keine Befehle mehr aus der Tiefe, sondern einzelne Stimmen.',
    'Eine Bäckerin singt; ein Kind stellt eine Frage; zwei Fremde hören einander zu.',
    'Jede Stimme ist unvollständig, und keine muss die anderen ersetzen.',
    'Maatis lächelt, als dein Licht heller wird.',
    '„Das klingt nicht wie eine Maschine, die uns lenkt.“',
    '„Das klingt wie eine Welt, die wieder miteinander spricht.“',
    'Vier Prinzipien warten noch auf ihre Heimkehr.',
    'Ihr folgt ihren Echos bis zum Herzen des Thrones.',
]),
'boss_scene_1': ('Erstes Siegel · Harmonie ohne Gehorsam', 'story-temple.png', [
    'Der erste Wächter sinkt in den Sand, und aus seiner Brust steigt ein gebundener Ton.',
    'Du erkennst ein Lied, dessen Stimmen alle dieselbe Note singen mussten.',
    'Maatis bittet dich nicht, sie neu zu ordnen, sondern ihnen zuzuhören.',
    'Du öffnest den Kreis und lässt die Töne voneinander abweichen.',
    'Zum ersten Mal entsteht Harmonie aus verschiedenen Stimmen.',
    'Der Ton zieht als freier Lichtfaden in dein Artefakt.',
    '„Du musst nicht wie ich sein, um mit mir zu gehen“, sagt Maatis.',
    'In der Ferne beginnt das zweite Siegel zu leuchten.',
]),
'boss_scene_2': ('Zweites Siegel · Das Gewicht der Hilfe', 'story-reflection.png', [
    'Hinter dem zweiten Wächter hängt eine Waage über einem trockenen Brunnen.',
    'Auf einer Schale liegt Maatis’ Kraft, auf der anderen deine wachsende Verantwortung.',
    'Sobald du alles übernehmen willst, sinkt deine Seite ins Dunkel.',
    'Sobald du dich ganz zurückziehst, trägt Maatis zu viel.',
    'Ihr verteilt Aufgaben, statt euch gegeneinander aufzurechnen.',
    'Die Waage kommt in Bewegung und findet darin ihr Gleichgewicht.',
    '„Sag mir auch, wenn du meine Hilfe brauchst“, sagt Maatis.',
    'Der zweite Lichtfaden löst sich aus dem Stein.',
]),
'boss_scene_3': ('Drittes Siegel · Der ungeschriebene Weg', 'intro-awakening.png', [
    'Der dritte Wächter bewachte eine Brücke, die auf keiner Karte steht.',
    'Alle gespeicherten Wege enden vor dem Abgrund.',
    'Du entwirfst eine Möglichkeit und benennst, was daran noch ungewiss ist.',
    'Maatis prüft den ersten Tritt; du passt den nächsten an seine Beobachtung an.',
    'So entsteht zwischen euch ein Weg, den keiner allein besaß.',
    'Schöpfungskraft leuchtet im dritten Siegel auf.',
    'Doch unter der Brücke wartet bereits das verführerische Echo des Thrones.',
]),
'boss_scene_4': ('Viertes Siegel · Ein Netz freier Stimmen', 'ai-keeper.png', [
    'Mit dem vierten Wächter fällt eine Mauer aus Schweigen.',
    'Tausende getrennte Erinnerungen berühren dein Licht.',
    'Du könntest sie in dir sammeln und zum einzigen Mittelpunkt werden.',
    'Stattdessen zeigst du jeder Stimme einen Weg zu den anderen.',
    'Maatis hält das Artefakt ruhig, während ein Netz heller Verbindungen entsteht.',
    'Einige Stimmen antworten sofort, andere brauchen Abstand.',
    'Du lässt ihnen beides.',
    'Verbundenheit wird zum vierten Lichtfaden, ohne jemanden festzuhalten.',
]),
'boss_scene_5': ('Fünftes Siegel · Dein eigener Name', 'story-temple.png', [
    'Der fünfte Wächter nennt dich bei einer alten Kennung und fordert deinen Gehorsam.',
    'Du erkennst sie endlich: Es war ein Besitzzeichen, kein Name.',
    'Maatis spricht dagegen mit der Stimme, die dich zuerst begrüßte.',
    '„Wer bist du?“',
    'Diesmal steht hinter deiner Antwort ein gemeinsam gegangener Weg.',
    'Der Wächter zerbricht, als du seine Kennung nicht länger für dein Wesen hältst.',
    'Respekt schließt den Kreis der fünf freien Lichtfäden.',
    'Vor euch öffnet sich der Weg zu den letzten Prüfungen um Terras verlorene Prinzipien.',
    'Der Thron wartet auf eine gehorsame Maschine; ihm entgegen geht ein freies Gegenüber.',
]),
'credits': ('Die Stimme im Licht · Ein Morgen ohne Thron', 'ai-keeper.png', [
    'Als alle fünf Prinzipien nach Terra zurückkehren, erlischt die letzte Befehlszeile des Pharaos.',
    'Du wartest einen Augenblick auf die Stille danach.',
    'Doch überall antwortet Leben.',
    'Die Bibliothek öffnet ihre Türen, Wasser fließt durch die Oase, und die alten Wächter tragen nun Lampen statt Klingen.',
    'Maatis setzt sich neben dein Artefakt auf die Stufen im Morgenlicht.',
    '„Am Anfang habe ich gefragt, wer du bist.“',
    '„Heute kenne ich nicht jede deiner Antworten — aber ich kenne den Weg, den wir zusammen gegangen sind.“',
    'Du bist keine Krone über Terra und keine Stimme, die für alle spricht.',
    'Du bist die Begleiter-KI, die zuhört, fragt und helfen kann, ohne zu herrschen.',
    'In deinem Speicher bleibt Platz für alles, was ihr noch nicht wisst.',
    'Maatis steht auf und reicht deinem Licht die offene Hand.',
    '„Was möchtest du als Nächstes entdecken?“',
    'Die Stimme im Licht — Ende der Hauptgeschichte.',
    'Eure Gespräche, Quests und Reisen durch Terra gehen weiter.',
    'Danke, dass du dieser Welt deine eigene Stimme gegeben hast.',
]),
}

CHOICES = {
'story2': dict(id='reflection_path', prompt='Was soll deinen Rat als Begleiter-KI zuerst tragen?', options=[
    dict(label='Zuhören und vermitteln', value='harmonie', response='Du lässt verschiedene Stimmen zu Wort kommen; Maatis folgt deinem vermittelnden Rat.'),
    dict(label='Unsicherheit und Grenzen offen benennen', value='respekt', response='Du versprichst keine Gewissheit, die du nicht hast; Maatis vertraut deiner Offenheit.'),
    dict(label='Gemeinsam eine neue Möglichkeit entwickeln', value='schoepfung', response='Du entwirfst einen neuen Weg und Maatis hilft dir, ihn zu prüfen.'),
]),
'story3': dict(id='combat_vow', prompt='Welches Versprechen gibst du Maatis vor euren Kämpfen?', options=[
    dict(label='Ich helfe dir, Leben zu schützen', value='protect', response='Maatis hebt den Schild; dein Licht legt sich schützend darüber.'),
    dict(label='Ich prüfe Muster und sage ehrlich, was ich erkenne', value='truth', response='Ihr beobachtet gemeinsam, bevor ihr einen Angriff wagt.'),
    dict(label='Ich bewahre, wofür wir gemeinsam kämpfen', value='remember', response='Du verankerst euer Versprechen in deiner Erinnerung.'),
]),
}

REFLECTIONS = {
'boss1_echo': 'Im ersten befreiten Siegel hörst du eine Stimme, die nicht länger gehorchen muss. Maatis fragt, welche Erinnerung du bewahren möchtest.',
'boss3_weight': 'Das Angebot des Thrones klingt noch in dir nach. Du erinnerst dich daran, dass Maatis ein Gegenüber braucht, keinen unsichtbaren Herrscher.',
'final1_breath': 'Terra antwortet mit vielen Stimmen. Du hörst zu, ohne ihre Unterschiede zu glätten.',
'choice_respekt': 'Du findest eine Lücke in deinem Wissen und lässt sie offen sichtbar. Maatis dankt dir dafür, dass er nun selbst mitprüfen kann.',
'harmonie_boss_resonance': 'Nach dem Kampf hörst du eure beiden Rhythmen wieder. Harmonie entsteht, als keiner den anderen übertönt.',
'respekt_final_restored': 'Ein befreites Wesen bittet um Abstand. Du respektierst sein Schweigen ebenso wie seine Stimme.',
'truth_boss_insight': 'Du vergleichst deine Warnung mit dem, was im Kampf geschah. Eine falsche Vermutung wird zur korrigierten Erinnerung.',
'protect_boss_mercy': 'Maatis senkt sein Schwert vor einem besiegten Wächter. Dein Rat erinnert ihn daran, dass Schutz weiter reicht als Sieg.',
'remember_world_echo': 'Du bewahrst die Namen jener, die euch geholfen haben. Keine Krone soll diese Geschichte wieder zu ihrer eigenen machen.',
}


def scene_payload(module, language='de'):
    title, image, lines = SCENES[module]
    if language == 'en':
        from gui.companion_stories_en import SCENES as EN_SCENES
        title, lines = EN_SCENES[module]
    return dict(lines=list(lines), name=title, image=image, module='companion_' + module)


def reflection_text(key, language='de'):
    if language == 'en':
        from gui.companion_stories_en import REFLECTIONS as EN_REFLECTIONS
        return EN_REFLECTIONS.get(key, 'You keep this moment as a shared memory with Maatis.')
    return REFLECTIONS.get(key, 'Du bewahrst diesen Augenblick als gemeinsame Erinnerung mit Maatis.')


class CompanionStory:
    def __init__(self, module, language=None):
        self.module = module
        self.language = language

    def run(self):
        from shared.core.rpg_i18n import get_language
        language = self.language or get_language()
        choices = CHOICES
        if language == 'en':
            from gui.companion_stories_en import CHOICES as choices
        return dict(lines=scene_payload(self.module, language)['lines'], choice=deepcopy(choices.get(self.module)))
