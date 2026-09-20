# Proportionale Kampfbalance / Proportional combat balance

Stand / Updated: 2026-09-16

## Deutsch

Normale **Zufalls- und Arenakämpfe** skalieren jetzt mit den regulären Werten
des Spielerlevels. Das Level vergrößert die Zahlen; die angestrebte relative
Schwierigkeit bleibt vergleichbar. Die Berechnung steht in
`shared/core/arena_difficulty.py` (`ENCOUNTER_TARGETS`).

- Grün: deutliche KP-Reserve bei vernünftiger Angriffswahl.
- Gelb: knapp ohne Heiltrank schaffbar, mit rechtzeitigem MAAT-Impuls.
- Rot: normalerweise einen Heiltrank einplanen; Taktik und Talente können helfen.

Die Gegner-KP orientieren sich an einem festen Referenzablauf aus Prinzipangriffen
und Impuls. Der Schaden folgt den regulären Level-KP (`100 + 10 × (Level − 1)`).
Beide Seiten haben bei normalen Kämpfen eine proportionale Schwankung von ±5 %
für Prinzipangriffe bzw. gewöhnliche Gegnertreffer. Kritische Treffer,
Schwachstellen, Fähigkeiten und Impuls behalten ihre vorhandenen Effekte.
Aktuelle KP, gekaufte Talente, Trankvorrat und persönliche MAAT-Buffs werden
**nicht** benutzt, um den Gegner nachträglich stärker zu machen.

Bosse, Finale, Dungeons, Tutorial und Titeldemo behalten ihre bisherige
Gegnerskalierung. Belohnungen, Freischaltungen und Kartenfortschritt bleiben
gleich; Arenasiege geben weiterhin die Hälfte der entsprechenden Zufallskampf-EP.
Der gemeinsame Heiltrankfehler ist behoben: Tränke heilen die tatsächlichen
aktuellen KP, verbrauchen ein Item und können ohne Inventar keine alten KP
wiederherstellen.

### Prüfung

Echte Kampfschleife, private Testsaves, kein Modell und kein Audio; Heilung durch
Belohnungen/Levelaufstiege ist für die Messung deaktiviert. Referenz: MAAT-Felder
je 0,8, volle reguläre KP, keine Talente/Skills/Storyboni, Schöpfungskraft als
Angriff, Impuls ab 100 Resonanz, erlaubter Trank unter 30 % KP. Je 100 Kämpfe mit
Seeds 3000–3099 pro Level und Variante; insgesamt 2.000 Kämpfe.

| Level | Grün: mittlere Rest-KP, ohne Trank | Gelb: mittlere Rest-KP, ohne Trank | Rot: Siege ohne Trank | Rot: Siege mit einem Trank |
| --- | ---: | ---: | ---: | ---: |
| 1 | 49,3 % | 19,1 % | 13/100 | 100/100 |
| 7 | 49,4 % | 19,0 % | 10/100 | 100/100 |
| 15 | 50,4 % | 20,0 % | 12/100 | 100/100 |
| 30 | 49,9 % | 20,6 % | 10/100 | 100/100 |
| 50 | 49,8 % | 20,7 % | 10/100 | 100/100 |

Das sind Ergebnisse dieser Strategie, keine Sieg-Garantie. Bereits verwundete
Figuren, andere Aktionen, Buffs und Talente verändern das Ergebnis. Das bestehende
Testprofil mit 99.999 KP bleibt absichtlich wesentlich stärker als reguläre Figuren.
Regressionen: `tests/test_encounter_scaling.py` prüft weitere feste Seeds,
Heiltrankverbrauch, gleiche Arena-/Zufallswerte und unveränderte Sonderkämpfe.

## English

Ordinary **random encounters and arena battles** now follow regular player-level
stats. Higher levels raise the numbers while keeping a similar relative challenge:
green leaves a comfortable margin, yellow is close without a potion when the
impulse is used well, and red normally calls for one healing potion.

Enemy HP is based on a fixed reference attack/impulse budget. Incoming damage
follows normal level HP, with ±5% variation for ordinary enemy hits and player
principle attacks. Current HP, talents, potion inventory and actual MAAT buffs
do not make enemies adapt to counter the player's build. Skills, critical hits,
weaknesses, rewards and progression retain their effects. Boss, finale, dungeon,
tutorial and title-demo enemy scaling is unchanged.

The shared potion bug is fixed: healing now uses current battle HP and consumes
an item; attempting to drink from an empty inventory cannot restore old HP.

The table above reports 2,000 real-loop simulations with full regular HP, MAAT
fields at 0.8, no talents/skills/story bonuses, Creation attacks, impulse at 100
resonance, and at most one potion below 30% HP. Music, models and reward healing
were disabled. These are reference-strategy results, not guaranteed outcomes for
every build or action sequence. The existing 99,999-HP test profile remains stronger
than a regular character.
