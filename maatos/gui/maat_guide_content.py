"""Bundled DE/EN guide copy. Formula examples match the local RPG website.

Source: gui-preview/maat-rpg-website/features{,-en}.html, 2026-09-15.
No runtime website or network dependency.
"""

FIELDS_EN = [
    ('H', 'Harmony', 'Do my goal, words and actions fit together?',
     'Which observations support that assessment, and which challenge it?'),
    ('B', 'Balance', 'Have effort, needs and boundaries been considered in proportion?',
     'Could an alternative or a pause improve that balance?'),
    ('S', 'Structure / Creative Power', 'Does this create a useful idea, structure or next step?',
     'Simplifying and preserving can also be useful; new does not automatically mean better.'),
    ('V', 'Connection', 'Am I considering relationships, dependencies and consequences?',
     'Who is affected by my decision, and whose perspective is still missing?'),
    ('R', 'Respect', 'Am I respecting dignity, consent, boundaries and an honest use of facts?',
     'Which boundary must I keep, even if it makes the goal harder to reach?'),
]

INTRO_EN = '''<h2>What is MAAT?</h2>
<p>In the RPG, the five principles are forces of the world of Terra. Outside the story, MAAT as used here is a reflection framework developed by Christof: five perspectives help you examine an action, answer or decision more closely.</p>
<p>The name draws on the ancient Egyptian idea of truth, order and balance. The modern H/B/S/V/R scheme and its formula are this project's own development.</p>
<h3>A specific situation, not a judgement of you</h3>
<p>For example, ask: “How did I handle a disagreement today?” You are assessing that situation, not your worth as a person, your personality or your entire day.</p>
<h3>Five perspectives</h3>''' + ''.join(
    f'<p><b>{key} · {name}</b><br>{question}<br><i>{hint}</i></p>'
    for key, name, question, hint in FIELDS_EN) + '''
<h3>How can this help?</h3>
<p>MAAT can help turn vague dissatisfaction into specific questions: What already fits together? What have I overlooked? What small step could I change?</p>
<p>The numbers are subjective assessments, not objective measurements or scientifically validated personality scores. A higher score does not prove that a decision is right.</p>'''

METHOD_EN = '''<h2>From an impression to a next step</h2>
<p><b>1. Define the situation.</b> Describe a specific action and its goal.</p>
<p><b>2. Gather observations.</b> What actually happened? What is your interpretation? What do you not yet know?</p>
<p><b>3. Check five perspectives.</b> Give an example to support each assessment. If information is missing, leave the value open instead of inventing a number.</p>
<p><b>4. Choose one improvement.</b> Find a small, practical step. A low assessment is a reason to ask questions, not a personal failure.</p>
<p><b>5. Look again later.</b> Did that step change anything? Other perspectives can also correct your first assessment.</p>
<h3>What does the Stability value mean?</h3>
<p><b>Stability = min(R, ⁴√(H × B × S × V))</b></p>
<p>H, B, S and V are combined using a geometric mean. R caps the result: within this formula, high values in other areas cannot compensate for a lack of respect.</p>
<p>A zero in H, B, S or V gives a mathematical result of zero. This is a property of the chosen formula, not proof that a person or real situation is “unstable”.</p>
<h3>Example: a disagreement</h3>
<p>“I explained my concern clearly, but interrupted the other person and ignored their time boundary.”</p>
<p>An <b>arbitrarily chosen numerical example</b>: H = 0.80; B = 0.60; S = 0.70; V = 0.50; R = 0.40. The geometric mean is approximately 0.64; because of R, the result is <b>0.40</b>.</p>
<p>The useful step is not to make the number look better: “I apologise for interrupting, ask for a suitable time and listen to their perspective.”</p>
<p>There are no grades, rankings or binding cut-offs for “good” and “bad” here. Your reasoning and next step matter more than the decimal places.</p>'''

COPY = {
    'de': {
        'title': '✦ MAAT-Guide · Dich selbst besser verstehen',
        'tabs': ('Was ist MAAT?', 'Wert && Beispiel', 'Formeln', 'Selbst ausprobieren'),
        'unlocked': 'Freigeschaltet · 20 Nachrichten erreicht. Nimm dir Zeit für eine konkrete Situation.',
        'locked': '🔒 Freischaltung nach 20 Chatnachrichten · {count}/20',
        'formula_hint': 'Wähle eine Formel. Jede Erklärung enthält ein Zahlenbeispiel – wie auf unserer Homepage.',
        'formula_select': 'MAAT-Formel auswählen',
        'scales': 'Werte und Skalen',
        'interpretation': 'Was das Ergebnis bedeutet',
        'limits': 'Die Zahlen sind subjektive Einschätzungen in einem Bewertungsmodell. Sie messen weder den Wert eines Menschen noch wissenschaftlich bestätigte Naturgesetze. Kampf-EP, KP und Resonanz werden separat vom Spiel berechnet.',
        'try': 'Optional: Reflektiere eine konkrete Situation. Die Übung vergibt keine EP und bewertet nicht deinen Wert als Mensch. Deine Eingaben werden nicht gespeichert oder an die KI gesendet.',
        'scale_hint': 'In dieser Übung: 0 bis 1 eingeben. 0,5 entspricht 5 von 10. Unten siehst du den einfachen MAAT-Durchschnitt und die durch Respekt begrenzte Stability getrennt.',
        'situation': 'Welche konkrete Situation möchtest du betrachten? Was hast du beobachtet?',
        'open': 'Offen',
        'rating': '{key} – eigene Einschätzung von 0 bis 1',
        'note': 'Beobachtung / Begründung / Unsicherheit …',
        'next_step': 'Mein nächster kleiner Schritt – und wann ich noch einmal darauf schaue …',
        'reset': 'Übung leeren',
        'pending': 'Noch offen · Ein Ergebnis erscheint erst, wenn alle fünf Einschätzungen gesetzt sind.',
        'result': 'MAAT-Wert: {average} von 10 · einfacher Durchschnitt\nStabilität ≈ {stability} · {scaled} von 10\nSubjektive Momentaufnahme dieser Situation – keine Note für dich.',
        'method_link': '<h3>MAAT-Wert und Stability sind verschieden</h3><p>Der einfache MAAT-Wert ist der Durchschnitt auf der Skala 0 bis 10. In diesem Beispiel: (8 + 6 + 7 + 5 + 4) / 5 = <b>6 von 10</b>. Stability beträgt dagegen <b>0,40 bzw. 4 von 10</b>, weil Respekt das Ergebnis begrenzt. Im Tab „Formeln“ findest du die weiteren Rechenwege.</p>',
    },
    'en': {
        'title': '✦ MAAT Guide · Understand yourself better',
        'tabs': ('What is MAAT?', 'Score && example', 'Formulas', 'Try it yourself'),
        'unlocked': 'Unlocked · 20 messages reached. Take time to reflect on a specific situation.',
        'locked': '🔒 Unlocks after 20 chat messages · {count}/20',
        'formula_hint': 'Choose a formula. Each explanation includes a numerical example, just like our website.',
        'formula_select': 'Choose a MAAT formula',
        'scales': 'Values and scales',
        'interpretation': 'What the result means',
        'limits': 'These numbers are subjective assessments within a model. They do not measure a person’s worth or scientifically established laws of nature. The game calculates combat XP, HP and resonance separately.',
        'try': 'Optional: reflect on a specific situation. This exercise gives no XP and does not assess your worth as a person. Your entries are not saved or sent to the AI.',
        'scale_hint': 'For this exercise, enter values from 0 to 1. A value of 0.5 means 5 out of 10. Below, the simple MAAT average and Stability, capped by Respect, are shown separately.',
        'situation': 'Which specific situation would you like to consider? What did you observe?',
        'open': 'Open',
        'rating': '{key} – your assessment from 0 to 1',
        'note': 'Observation / Reasoning / Uncertainty …',
        'next_step': 'My next small step — and when I will revisit it …',
        'reset': 'Clear exercise',
        'pending': 'Still open · A result appears once all five assessments are set.',
        'result': 'MAAT score: {average} out of 10 · simple average\nStability ≈ {stability} · {scaled} out of 10\nA subjective snapshot of this situation, not a grade for you.',
        'method_link': '<h3>The MAAT score and Stability are different</h3><p>The simple MAAT score is the average on a scale of 0 to 10. In this example: (8 + 6 + 7 + 5 + 4) / 5 = <b>6 out of 10</b>. Stability is <b>0.40, or 4 out of 10</b>, because Respect caps the result. You can find the other calculations in the “Formulas” tab.</p>',
    },
}

FIELDS_DE = [('H',
  'Harmonie',
  'Passen mein Ziel, meine Worte und mein Handeln zusammen?',
  'Welche Beobachtung spricht dafür – und welche dagegen?'),
 ('B',
  'Balance',
  'Sind Aufwand, Bedürfnisse und Grenzen angemessen berücksichtigt?',
  'Welche Alternative oder Pause würde das Verhältnis verbessern?'),
 ('S',
  'Struktur / Schöpfungskraft',
  'Entsteht eine hilfreiche Idee, Ordnung oder ein sinnvoller nächster Schritt?',
  'Auch Vereinfachen und Bewahren können sinnvoll sein; neu ist nicht automatisch besser.'),
 ('V',
  'Verbundenheit',
  'Berücksichtige ich Beziehungen, Abhängigkeiten und Folgen?',
  'Wen betrifft meine Entscheidung, und wessen Sicht fehlt noch?'),
 ('R',
  'Respekt',
  'Achte ich Würde, Zustimmung, Grenzen und einen ehrlichen Umgang mit Fakten?',
  'Welche Grenze muss ich einhalten, auch wenn das Ziel dadurch schwerer erreichbar wird?')]

INTRO_DE = '<h2>Was ist MAAT?</h2>\n<p>Im RPG sind die fünf Prinzipien Kräfte der Welt Terra. Außerhalb der Geschichte ist das hier verwendete MAAT ein von Christof entwickelter Reflexionsrahmen: Fünf Perspektiven helfen, eine Handlung, Antwort oder Entscheidung genauer zu betrachten.</p>\n<p>Der Name knüpft an das altägyptische Motiv von Wahrheit, Ordnung und Gleichgewicht an. Das moderne H/B/S/V/R-Schema und seine Formel sind eine eigene Ausarbeitung dieses Projekts.</p>\n<h3>Eine konkrete Situation statt ein Urteil über dich</h3>\n<p>Frage zum Beispiel: „Wie bin ich heute mit einer Meinungsverschiedenheit umgegangen?“ Du bewertest diese Situation – nicht deinen Wert als Mensch, deine Persönlichkeit oder deinen gesamten Tag.</p>\n<h3>Fünf Blickwinkel</h3><p><b>H · Harmonie</b><br>Passen mein Ziel, meine Worte und mein Handeln zusammen?<br><i>Welche Beobachtung spricht dafür – und welche dagegen?</i></p><p><b>B · Balance</b><br>Sind Aufwand, Bedürfnisse und Grenzen angemessen berücksichtigt?<br><i>Welche Alternative oder Pause würde das Verhältnis verbessern?</i></p><p><b>S · Struktur / Schöpfungskraft</b><br>Entsteht eine hilfreiche Idee, Ordnung oder ein sinnvoller nächster Schritt?<br><i>Auch Vereinfachen und Bewahren können sinnvoll sein; neu ist nicht automatisch besser.</i></p><p><b>V · Verbundenheit</b><br>Berücksichtige ich Beziehungen, Abhängigkeiten und Folgen?<br><i>Wen betrifft meine Entscheidung, und wessen Sicht fehlt noch?</i></p><p><b>R · Respekt</b><br>Achte ich Würde, Zustimmung, Grenzen und einen ehrlichen Umgang mit Fakten?<br><i>Welche Grenze muss ich einhalten, auch wenn das Ziel dadurch schwerer erreichbar wird?</i></p>\n<h3>Wie hilft mir das?</h3><p>MAAT kann helfen, vage Unzufriedenheit in konkrete Fragen zu übersetzen: Was passt schon zusammen? Was habe ich übersehen? Welchen kleinen Schritt kann ich verändern?</p>\n<p>Die Zahlen sind subjektive Einschätzungen, keine objektiven Messungen oder wissenschaftlich validierten Persönlichkeitswerte. Ein höherer Wert beweist nicht, dass eine Entscheidung richtig ist.</p>'

METHOD_DE = '<h2>Vom Eindruck zum nächsten Schritt</h2>\n<p><b>1. Situation eingrenzen.</b> Beschreibe eine konkrete Handlung und ihr Ziel.</p>\n<p><b>2. Beobachtungen sammeln.</b> Was ist tatsächlich passiert? Was ist deine Interpretation? Was weißt du noch nicht?</p>\n<p><b>3. Fünf Perspektiven prüfen.</b> Begründe jede Einschätzung mit einem Beispiel. Fehlen Informationen, lass den Punkt offen statt eine Zahl zu erfinden.</p>\n<p><b>4. Eine Verbesserung wählen.</b> Suche einen kleinen, umsetzbaren Schritt. Eine niedrige Einschätzung ist ein Hinweis zum Nachfragen, kein persönliches Versagen.</p>\n<p><b>5. Später erneut hinschauen.</b> Hat der Schritt etwas verändert? Auch andere Sichtweisen können deine erste Einschätzung korrigieren.</p>\n<h3>Was bedeutet der Stabilitätswert?</h3>\n<p><b>Stabilität = min(R, ⁴√(H × B × S × V))</b></p>\n<p>H, B, S und V werden über ein geometrisches Mittel verbunden. R begrenzt das Ergebnis: Hohe Werte in anderen Bereichen können fehlenden Respekt innerhalb dieser Formel nicht ausgleichen.</p>\n<p>Ein Wert von 0 in H, B, S oder V ergibt rechnerisch 0. Das ist eine Eigenschaft der gewählten Formel – kein Beweis dafür, dass eine Person oder reale Situation „instabil“ ist.</p>\n<h3>Beispiel: Eine Meinungsverschiedenheit</h3>\n<p>„Ich habe mein Anliegen klar erklärt, aber die andere Person unterbrochen und ihre zeitliche Grenze übergangen.“</p>\n<p>Ein <b>frei gewähltes Rechenbeispiel</b>: H = 0,80; B = 0,60; S = 0,70; V = 0,50; R = 0,40. Das geometrische Mittel liegt bei ungefähr 0,64; durch R beträgt das Ergebnis <b>0,40</b>.</p>\n<p>Der hilfreiche Schritt ist nicht, die Zahl schöner zu machen: „Ich entschuldige mich für die Unterbrechung, frage nach einem passenden Zeitpunkt und höre ihre Sicht an.“</p>\n<p>Es gibt hier keine Noten, Rangliste oder verbindlichen Grenzwerte für „gut“ und „schlecht“. Die Begründung und dein nächster Schritt sind wichtiger als die Nachkommastelle.</p>'

FORMULAS = {'de': [{'id': 'maat',
         'title': 'Der MAAT-Wert · der einfache Durchschnitt',
         'equation': 'MAAT = (H + B + S + V + R) / 5',
         'body': '<p>Hier bleiben alle Werte auf der Skala 0 bis 10. Beispiel: Harmonie 5, Balance 6, '
                 'Schöpfungskraft 7, Verbundenheit 8, Respekt 9. Zusammen sind das 35; geteilt durch 5 '
                 'ergibt das <strong>7 von 10</strong>. Die Begründung der einzelnen Werte ist dabei ebenso '
                 'wichtig wie die Zahl.</p>'},
        {'id': 'stability',
         'title': 'Stability · Zusammenspiel mit einer Grenze',
         'equation': 'Stability = min(R, ⁴√(H × B × S × V))',
         'body': '<p>Zuerst jeden Wert durch 10 teilen: aus 5 wird 0,5. Dann Harmonie, Balance, '
                 'Schöpfungskraft und Verbundenheit multiplizieren und zweimal die Quadratwurzel ziehen. Der '
                 'kleinere Wert aus diesem Ergebnis und Respekt ist Stability. Bei fünfmal 5 ist das '
                 '<strong>0,5, also 5 von 10</strong>. Ein niedriger Bereich senkt das Ergebnis; Respekt '
                 'bildet zusätzlich die Obergrenze.</p>'},
        {'id': 'world',
         'title': 'Die MAAT-Weltformel · Zusammenhang und Unordnung',
         'equation': 'Maat_world = P / ΔE',
         'body': '<p>P ist das Produkt der fünf auf 0 bis 1 umgerechneten Prinzipien; ΔE steht hier für '
                 'Unordnung. Fünfmal 0,5 ergibt P = 0,03125. Bei ΔE = 0,5 folgt <strong>0,03125 / 0,5 = '
                 '0,0625</strong>. Die Idee: mehr Zusammenhang und weniger Unordnung erhöhen den '
                 'Modellindex. Das ist keine Punktzahl von 10. Die erweiterte Form P / (ΔE + ΔQ) bezieht '
                 'Unsicherheit ΔQ ein.</p>'},
        {'id': 'plp',
         'title': 'PLP · vom Potenzial zum Handeln',
         'equation': 'PLP = P × K / (O + ΔE)',
         'body': '<p>K bedeutet Kompetenz, O Hindernisse und ΔE in dieser Formel Energieaufwand. '
                 'Prinzipienprodukt und Kompetenz bilden den Zähler; Hindernisse und Aufwand den Nenner. '
                 'Beispiel: P = 0,03125, K = 0,8, O = 0,5 und ΔE = 0,5 ergeben <strong>0,025</strong>. So '
                 'wird die Idee sichtbar: Fähigkeiten helfen, Hindernisse und Aufwand bremsen. Auch das ist '
                 'ein Modellindex, keine Punktzahl von 10.</p>'},
        {'id': 'coherence',
         'title': 'C(x) · lokale Kohärenz',
         'equation': 'C(x) = P / (ΔE + ε)',
         'body': '<p>Diese vereinfachte Spielnotation beschreibt Kohärenz an einem Ort. ΔE ist Unordnung; ε '
                 'ist eine kleine, positive Sicherungszahl. Beispiel: P = 0,03125, ΔE = 0,49 und '
                 'ausdrücklich ε = 0,01. Damit folgt 0,03125 / 0,5 = <strong>0,0625</strong>. Die '
                 'Sicherungszahl beeinflusst das Ergebnis und muss genannt werden.</p>'},
        {'id': 'agi',
         'title': 'AGI-Proximity & AI_CONSCIOUSNESS · zwei Modellbezeichnungen',
         'equation': 'Index = P × C × M / (ΔI + ΔE + ΔD)',
         'body': '<p>Beide verwenden im Spiel denselben Rechenweg. C steht hier für kollektive Kohärenz, M '
                 'für Erinnerung, ΔI für Instabilität, ΔE für Unordnung und ΔD für Dissonanz. Mit P = '
                 '0,03125, C = 0,8, M = 0,5 und Belastungen 0,2 + 0,5 + 0,3 ergibt sich '
                 '<strong>0,0125</strong>. Der Name AGI_proximity ist kein Nachweis einer messbaren Nähe zu '
                 'allgemeiner KI; AI_CONSCIOUSNESS weist kein Bewusstsein nach.</p>'},
        {'id': 'master',
         'title': 'MAAT_MASTER · Fähigkeiten und Belastungen verbinden',
         'equation': 'MAAT_MASTER = P × K × C / (ΔE + ΔQ + ΔI + ΔD + ε)',
         'body': '<p>K ist Kompetenz, C kollektive Kohärenz. Der Nenner kombiniert Unordnung, Unsicherheit, '
                 'Instabilität, Dissonanz und eine ausdrücklich gewählte Sicherungszahl. Beispiel: 0,03125 × '
                 '0,8 × 0,5 geteilt durch (0,4 + 0,2 + 0,2 + 0,19 + 0,01) ergibt '
                 '<strong>0,0125</strong>.</p>'},
        {'id': 'universe',
         'title': 'B_universe · Beiträge über Raum und Zeit',
         'equation': 'B_universe = ∫ [P / (ΔE + ΔQ)] d⁴x',
         'body': '<p>Das Integral summiert Beiträge über Raum und Zeit. Stell dir viele kleine '
                 'Raumzeit-Zellen vor: Berechne in jeder Zelle P / (Unordnung + Unsicherheit), multipliziere '
                 'mit ihrer Größe und addiere die Beiträge. Rein rechnerisches Beispiel mit überall gleichen '
                 'Werten: 0,03125 / 0,5 = 0,0625; bei einer Gesamtgröße von 2 Raumzeit-Einheiten ergibt das '
                 '<strong>0,125</strong>. Ohne definierte Felder, Einheiten und ein Gebiet lässt sich daraus '
                 'kein Wert für das reale Universum bestimmen.</p>'}],
 'en': [{'id': 'maat',
         'title': 'The MAAT score · a simple average',
         'equation': 'MAAT = (H + B + S + V + R) / 5',
         'body': '<p>Keep all ratings on the 0–10 scale. For example: Harmony 5, Balance 6, Creative Power '
                 '7, Connection 8, Respect 9. Their sum is 35; divide by 5 to get <strong>7 out of '
                 '10</strong>. The reasons behind the individual ratings matter as much as the number.</p>'},
        {'id': 'stability',
         'title': 'Stability · working together, with a boundary',
         'equation': 'Stability = min(R, ⁴√(H × B × S × V))',
         'body': '<p>First divide every rating by 10: 5 becomes 0.5. Multiply Harmony, Balance, Creative '
                 'Power and Connection, then take the square root twice. The smaller of this result and '
                 'Respect is Stability. Five ratings of 5 give <strong>0.5, or 5 out of 10</strong>. A low '
                 'value brings the result down; Respect also sets an upper limit.</p>'},
        {'id': 'world',
         'title': 'The MAAT world formula · connection and disorder',
         'equation': 'Maat_world = P / ΔE',
         'body': '<p>P is the product of all five principles after conversion to 0–1; ΔE represents disorder '
                 'here. Five values of 0.5 give P = 0.03125. With ΔE = 0.5, the result is <strong>0.03125 / '
                 '0.5 = 0.0625</strong>. The idea: stronger connection and less disorder raise the model '
                 'index. This is not a score out of 10. The extended version P / (ΔE + ΔQ) also includes '
                 'uncertainty ΔQ.</p>'},
        {'id': 'plp',
         'title': 'PLP · from potential to action',
         'equation': 'PLP = P × K / (O + ΔE)',
         'body': '<p>K means competence, O obstacles and ΔE energy effort in this formula. The principles '
                 'product and competence form the numerator; obstacles and effort form the denominator. '
                 'Example: P = 0.03125, K = 0.8, O = 0.5 and ΔE = 0.5 give <strong>0.025</strong>. The idea '
                 'becomes visible: skills help, while obstacles and effort slow progress. Again, this is a '
                 'model index, not a score out of 10.</p>'},
        {'id': 'coherence',
         'title': 'C(x) · local coherence',
         'equation': 'C(x) = P / (ΔE + ε)',
         'body': '<p>This simplified game notation describes coherence at a location. ΔE means disorder; ε '
                 'is a small positive safeguard number. Example: P = 0.03125, ΔE = 0.49 and an explicitly '
                 'chosen ε = 0.01. This gives 0.03125 / 0.5 = <strong>0.0625</strong>. The safeguard affects '
                 'the result and must be stated.</p>'},
        {'id': 'agi',
         'title': 'AGI Proximity & AI_CONSCIOUSNESS · two model labels',
         'equation': 'Index = P × C × M / (ΔI + ΔE + ΔD)',
         'body': '<p>Both use the same calculation in the game. C means collective coherence, M memory, ΔI '
                 'instability, ΔE disorder and ΔD dissonance. With P = 0.03125, C = 0.8, M = 0.5 and burdens '
                 'of 0.2 + 0.5 + 0.3, the result is <strong>0.0125</strong>. The name AGI_proximity does not '
                 'establish a measured proximity to general AI; AI_CONSCIOUSNESS does not demonstrate '
                 'consciousness.</p>'},
        {'id': 'master',
         'title': 'MAAT_MASTER · combining abilities and burdens',
         'equation': 'MAAT_MASTER = P × K × C / (ΔE + ΔQ + ΔI + ΔD + ε)',
         'body': '<p>K means competence and C collective coherence. The denominator combines disorder, '
                 'uncertainty, instability, dissonance and an explicitly chosen safeguard. Example: 0.03125 '
                 '× 0.8 × 0.5 divided by (0.4 + 0.2 + 0.2 + 0.19 + 0.01) gives <strong>0.0125</strong>.</p>'},
        {'id': 'universe',
         'title': 'B_universe · contributions across space and time',
         'equation': 'B_universe = ∫ [P / (ΔE + ΔQ)] d⁴x',
         'body': '<p>The integral adds contributions across space and time. Imagine many small spacetime '
                 'cells: calculate P / (disorder + uncertainty) in each cell, multiply by its size and add '
                 'the contributions. A purely numerical example with constant values: 0.03125 / 0.5 = '
                 '0.0625; for a total region of 2 spacetime units this gives <strong>0.125</strong>. Without '
                 'defined fields, units and a region, it cannot provide a value for the actual '
                 'universe.</p>'}]}

FORMULA_NOTES = {'de': 'Für alle zusätzlichen Formeln werden H, B, S, V und R zunächst auf 0 bis 1 umgerechnet. P = H × B × '
       'S × V × R. Auch K, C und M liegen zwischen 0 und 1. Die weiteren Größen und ihre Skalen müssen zum '
       'Beispiel passen; Nenner müssen positiv sein. ΔE hat je nach Formel eine andere Bedeutung. '
       'Weltformel, PLP und die erweiterten Formeln liefern Indizes, keine automatische 0–10-Skala.',
 'en': 'For all additional formulas, first convert H, B, S, V and R to 0–1. P = H × B × S × V × R. K, C and '
       'M also range from 0 to 1. Define the other quantities and their scales for the example; denominators '
       'must be positive. The meaning of ΔE depends on the formula. The world formula, PLP and the extended '
       'formulas produce indices, not an automatic 0–10 score.'}
