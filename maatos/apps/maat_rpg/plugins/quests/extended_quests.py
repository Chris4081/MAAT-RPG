"""The road beyond level 20: four authored quests every two levels through 50."""
# Level, chapter, first discussion, second discussion, daily journal topic.
CHAPTERS = [
    (22, 'Die Sternenkarte', 'Sternenpfade', 'Wie würdest du aus widersprüchlichen Sternenkarten einen sicheren Weg durch Terra bestimmen?', 'Verlorene Wegzeichen', 'Welche Hinweise würdest du bewahren, damit andere Reisende denselben Weg finden können?', 'Sternenchronik'),
    (24, 'Die Stadt der Echos', 'Stadt der Echos', 'In einer verlassenen Stadt wiederholt jede Straße eine andere Erinnerung. Wie unterscheidest du Zeugnis und Täuschung?', 'Stimmen im Brunnen', 'Zwei Stimmen bitten um Hilfe und widersprechen einander. Welche Fragen stellst du, bevor du Partei ergreifst?', 'Echochronik'),
    (26, 'Der gläserne Garten', 'Gläserner Garten', 'Der Garten wächst nur, wenn Besucher etwas zurücklassen. Welche Gabe wäre hilfreich, ohne jemandem zu schaden?', 'Samen des Wandels', 'Entwirf einen kleinen Versuch, mit dem Maatis herausfinden kann, was die fremden Pflanzen wirklich brauchen.', 'Gartenchronik'),
    (28, 'Die Brücke der Namen', 'Brücke der Namen', 'Eine Brücke verlangt den Namen eines vergessenen Menschen. Wie könnte Maatis helfen, ohne eine Geschichte zu erfinden?', 'Zwei Ufer', 'Zwei Gemeinschaften misstrauen einander. Entwirf einen ersten gemeinsamen Schritt, dessen Ergebnis beide prüfen können.', 'Brückenchronik'),
    (30, 'Das Archiv der Zeit', 'Archiv der Zeit', 'Maatis findet zwei unvereinbare Berichte über denselben Tag. Wie dokumentiert er die Unsicherheit?', 'Geliehene Zukunft', 'Ein Artefakt zeigt eine mögliche Zukunft. Welche Entscheidungen sollte Maatis trotzdem selbst verantworten?', 'Zeitchronik'),
    (32, 'Die schweigende Oase', 'Schweigende Oase', 'Eine Oase verliert Wasser, während ihr Hüter schweigt. Welche Beobachtungen sammelt ihr zuerst?', 'Wasser für alle', 'Entwirf eine faire Wasserverteilung für Reisende, Bewohner und Pflanzen, wenn die Vorräte knapp sind.', 'Oasenchronik'),
    (34, 'Das Herz der Schmiede', 'Resonanzschmiede', 'Eine neue Waffe könnte Terra schützen und zugleich verwüsten. Welche Grenzen sollten ihrer Nutzung gesetzt werden?', 'Werkzeug des Friedens', 'Entwirf aus denselben Materialien ein Werkzeug, das Konflikte entschärft, und erkläre seinen Nachteil.', 'Schmiedechronik'),
    (36, 'Das Meer aus Sand', 'Meer aus Sand', 'Ein Sandsturm trennt die Gruppe. Wie würdest du Suche, Schutz und knappe Kräfte organisieren?', 'Leuchtturm der Wüste', 'Entwirf ein Signal, das auch Menschen verstehen, die eure Sprache nicht kennen.', 'Wüstenchronik'),
    (38, 'Der Rat der Masken', 'Rat der Masken', 'Jede Maske im Rat behauptet, die Wahrheit zu vertreten. Welche überprüfbare Frage würdest du allen stellen?', 'Macht ohne Zwang', 'Wie könnte ein Rat verbindlich entscheiden und zugleich Widerspruch und Minderheiten schützen?', 'Maskenchronik'),
    (40, 'Die Wurzeln von Terra', 'Wurzeln von Terra', 'Eine Stadt lebt von einem Wald, den sie langsam zerstört. Entwickle einen schrittweisen Plan für ihr Zusammenleben.', 'Unsichtbare Nachbarn', 'Welche Folgen könnte eine scheinbar kleine Veränderung für unbekannte Lebewesen haben?', 'Wurzelchronik'),
    (42, 'Die Bibliothek des Lichts', 'Bibliothek des Lichts', 'Wissen ist hier nur gegen eine Erinnerung erhältlich. Welche Grenze sollte Maatis bei diesem Handel ziehen?', 'Wissen teilen', 'Entwirf eine Möglichkeit, wichtiges Wissen zugänglich zu machen, ohne private Erinnerungen offenzulegen.', 'Lichtchronik'),
    (44, 'Der zerbrochene Spiegel', 'Zerbrochener Spiegel', 'Maatis begegnet einem Abbild seiner früheren Fehler. Wie kann er Verantwortung übernehmen, ohne sich darauf zu reduzieren?', 'Versprechen erneuern', 'Formuliere ein konkretes Versprechen, das Maatis überprüfen und bei einem Fehler nachbessern kann.', 'Spiegelchronik'),
    (46, 'Die fünf Horizonte', 'Fünf Horizonte', 'Harmonie, Balance, Schöpfungskraft, Verbundenheit und Respekt weisen unterschiedliche Wege. Wie wägt ihr sie ab?', 'Eine tragfähige Grenze', 'Wann wäre es richtig, eine verlockende Abkürzung abzulehnen, obwohl die Reise dadurch schwerer wird?', 'Horizontchronik'),
    (48, 'Das Tor der Heimkehr', 'Tor der Heimkehr', 'Nach langer Reise erkennt Maatis seine Heimat kaum wieder. Welche Fragen stellt er, bevor er Veränderungen bewertet?', 'Heimkehr ohne Herrschaft', 'Wie kann Maatis seine Erfahrung anbieten, ohne den Menschen seiner Heimat ihre Entscheidungen abzunehmen?', 'Heimkehrchronik'),
    (50, 'Hüter einer lebendigen Welt', 'Lebendige Welt', 'Entwirf mit der KI einen Plan, wie Terra auch ohne einen einzelnen allmächtigen Hüter stabil bleiben kann.', 'Vermächtnis von Maatis', 'Welche drei überprüfbaren Lehren soll Maatis weitergeben, und welche offene Frage soll erhalten bleiben?', 'Vermächtnischronik'),
]

EXPANDED_QUESTS = []
for level, chapter, topic_a, question_a, topic_b, question_b, journal in CHAPTERS:
    tier = level // 2
    prefix = f'journey_{level}'
    for suffix,topic,question in [('insight',topic_a,question_a),('choice',topic_b,question_b)]:
        EXPANDED_QUESTS.append(dict(
            id=f'{prefix}_{suffix}', name=topic,
            desc=f'{chapter}: {question}\nSprich darüber mit der KI und nenne dabei „{topic}“.',
            type='chat_keyword', keywords=[topic], reward_xp=260+level*6, level_tier=tier,
        ))
    target=120+(level-22)*10
    EXPANDED_QUESTS.append(dict(
        id=f'{prefix}_guardian', name=f'Bewahrer · {chapter}',
        desc=f'Erreiche insgesamt {target} gewonnene Kämpfe. Arena- und Zufallssiege sowie reguläre Boss-Siege zählen über den gemeinsamen Siegzähler; Testdemos nicht.',
        type='battle_win', target=target, reward_xp=380+level*8, level_tier=tier,
    ))
    days=3+(level-22)//8
    EXPANDED_QUESTS.append(dict(
        id=f'{prefix}_journal', name=journal,
        desc=f'Führe an {days} aufeinanderfolgenden Kalendertagen im Chat deine „{journal}“ weiter. Erzähle jeweils, was Maatis gelernt hat und welche Frage offen bleibt. Nenne dabei „{journal}“.',
        type='daily_streak', days=days, keyword=journal, reward_xp=320+level*7, level_tier=tier,
    ))
