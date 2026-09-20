"""Stable visual identities for the 25 campaign bosses; combat rules stay separate."""
BOSS_ART = {1: 'pharaoh', 2: 'broken_harmony', 3: 'archon', 4: 'time', 5: 'sun'}
# Boss number, asset, German motif, English motif, normal-attack visual.
EGYPTIAN_BOSSES = (
    (6, 'boss06_scarab_regent', 'Skarabäus-Regent', 'Scarab Regent', 'sand'),
    (7, 'boss07_lotus_keeper', 'Hüterin des Lotus', 'Lotus Keeper', 'wave'),
    (8, 'boss08_anubis', 'Wächter des Anubis', 'Guardian of Anubis', 'wave'),
    (9, 'boss09_thoth', 'Schreiber des Thot', 'Scribe of Thoth', 'connection'),
    (10, 'boss10_horus', 'Schwingen des Horus', 'Wings of Horus', 'impulse'),
    (11, 'boss11_sobek', 'Koloss des Sobek', 'Colossus of Sobek', 'claw'),
    (12, 'boss12_hathor', 'Sistrum der Hathor', 'Sistrum of Hathor', 'wave'),
    (13, 'boss13_sekhmet', 'Zorn der Sachmet', 'Wrath of Sekhmet', 'creation'),
    (14, 'boss14_osiris', 'Djed-Hüter des Osiris', 'Djed Keeper of Osiris', 'connection'),
    (15, 'boss15_khepri', 'Sonnenkäfer des Chepri', 'Sun Scarab of Khepri', 'spark'),
    (16, 'boss16_uraeus', 'Uräus der Schattenkrone', 'Uraeus of the Shadow Crown', 'sand'),
    (17, 'boss17_bennu', 'Bennu der Morgenröte', 'Bennu of the Dawn', 'wave'),
    (18, 'boss18_ammit', 'Ammit an der Seelenwaage', 'Ammit at the Soul Scales', 'claw'),
    (19, 'boss19_khonsu', 'Mondwanderer des Chons', 'Moon Walker of Khonsu', 'connection'),
    (20, 'boss20_apep', 'Apophis der Sonnenfinsternis', 'Apep of the Eclipse', 'impulse'),
    (21, 'boss21_golden_pharaoh', 'Pharao der Goldenen Maske', 'Pharaoh of the Golden Mask', 'sand'),
    (22, 'boss22_maat_wings', 'Gefieder der MAAT', 'Wings of MAAT', 'balance'),
    (23, 'boss23_seth', 'Sturmherr des Seth', 'Storm Lord of Set', 'spark'),
    (24, 'boss24_duat_obelisk', 'Zeitobelisk der Duat', 'Time Obelisk of the Duat', 'connection'),
    (25, 'boss25_ra', 'Sonnenrichter des Re', 'Sun Judge of Ra', 'impulse'),
)
BOSS_ART.update({number: art for number, art, *_ in EGYPTIAN_BOSSES})
BOSS_MOTIFS = {number: (de, en) for number, _, de, en, _ in EGYPTIAN_BOSSES}
BOSS_EFFECTS = {art: effect for _, art, _, _, effect in EGYPTIAN_BOSSES}
CAMPAIGN_BOSS_COUNT = len(BOSS_ART)
