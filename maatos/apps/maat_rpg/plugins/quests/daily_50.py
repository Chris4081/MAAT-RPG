"""Repeatable endgame dailies: one reward per local calendar day."""
DAILY_TOPICS = [
    ('harmony', 'Frieden im Kleinen', 'Friedensimpuls', 'Beschreibe einen kleinen Konflikt in Terra und einen friedlichen ersten Schritt.', 120),
    ('balance', 'Die Waage des Tages', 'Tageswaage', 'Wäge zwei konkurrierende Bedürfnisse ab und erkläre deinen Kompromiss.', 120),
    ('creation', 'Eine Idee für Terra', 'Terras Werkstatt', 'Entwirf etwas Nützliches für eine Siedlung und nenne eine Grenze deiner Idee.', 150),
    ('connection', 'Brücken bauen', 'Brückenimpuls', 'Überlege mit der KI, wie zwei fremde Gruppen Vertrauen aufbauen könnten.', 140),
    ('respect', 'Eine Grenze achten', 'Respektwache', 'Nenne eine Grenze, die Maatis heute achten sollte, und begründe sie.', 120),
    ('evidence', 'Spurensuche', 'Tagesbeleg', 'Trenne an einem Beispiel aus der Reise eine Beobachtung von einer Vermutung.', 160),
    ('memory', 'Ein kostbarer Moment', 'Erinnerungsfunke', 'Halte eine Erinnerung aus Maatis’ Reise fest, die anderen helfen könnte.', 100),
    ('tactics', 'Plan vor dem Schwert', 'Taktikrat', 'Besprich einen Kampfplan samt Rückzugsbedingung, bevor Maatis die Arena betritt.', 160),
    ('care', 'Fürsorge auf dem Weg', 'Fürsorgeimpuls', 'Entwirf eine konkrete Hilfe für einen erschöpften Reisenden.', 120),
    ('doubt', 'Eine gute Gegenfrage', 'Zweifelsprobe', 'Formuliere eine Gegenfrage zu einer überzeugenden Behauptung und sage, was sie klären soll.', 180),
    ('gratitude', 'Dank an die Welt', 'Terras Dank', 'Erzähle, wem Maatis heute danken könnte und wofür.', 100),
    ('legacy', 'Ein Satz für morgen', 'Morgenvermächtnis', 'Formuliere eine Lehre für kommende Reisende und eine Frage, die offenbleiben darf.', 150),
]
DAILY_50_QUESTS = [dict(
    id='daily50_'+key, name='Täglich · '+name,
    desc=f'{task}\nSprich darüber im Chat und nenne „{keyword}“. Einmal pro Kalendertag belohnbar; am nächsten Tag wieder verfügbar.',
    type='daily_streak', days=1, keyword=keyword, level_tier=25,
    reward_xp=xp, repeatable=True, daily_reset=True,
) for key,name,keyword,task,xp in DAILY_TOPICS]
