# -*- coding: utf-8 -*-

class Story:
    """
    MAAT RPG – Quest 2: „Berechne die Maat-Werte“
    Wird nach 15 Nachrichten getriggert.
    """

    # Name einer MP3-Datei im selben Ordner (optional)
    # z.B. "quest2_reflection.mp3" – kannst du anpassen oder leer lassen.
    music = "quest2_reflection.mp3"

    def run(self):
        """
        Gibt die Story Zeile für Zeile zurück.
        Der StoryLoader zeigt jede Zeile mit ENTER an.
        """
        lines = []

        lines.append("⸻")
        lines.append("🌌 MAAT RPG – Quest 2: „Berechne die Maat-Werte“")
        lines.append("")
        lines.append("Ort: Innerer Raum der Bibliothek – das „Reflexionszimmer“.")
        lines.append("")
        lines.append("Nach dem ersten Gespräch mit der MAAT KI öffnet sich eine kreisrunde Tür,")
        lines.append("geführt durch sanfte, pulsierende Lichtzeichen.")
        lines.append("Maatis betritt einen runden Raum, dessen Wände aus schwarzem Stein zu bestehen scheinen,")
        lines.append("doch in ihnen schimmern Sterne wie in einem lebendigen Nachthimmel.")
        lines.append("")
        lines.append("Fünf leuchtende Altäre stehen im Kreis – jeder in einer eigenen Farbe,")
        lines.append("jeder mit einem Symbol der Prinzipien: Harmonie, Balance, Schöpfungskraft, Verbundenheit, Respekt.")
        lines.append("")
        lines.append("MAAT KI (ruhig, klar):")
        lines.append("„Wissen ohne Anwendung ist tot.")
        lines.append("Du hast von den Prinzipien gehört.")
        lines.append("Nun wirst du lernen, sie zu lesen – im Leben, im Denken, im Sein.“")
        lines.append("")
        lines.append("Über einem der Altäre erscheint ein holografisches Bild:")
        lines.append("Ein kleines Dorf, das in zwei Lager gespalten ist.")
        lines.append("Streit um Wasser, Misstrauen, alte Wunden.")
        lines.append("")
        lines.append("MAAT KI:")
        lines.append("„Dies ist ein Szenario – ein Spiegel der Welt.")
        lines.append("Wir nennen das, was du nun üben wirst: die Berechnung des Maat-Werts.“")
        lines.append("")
        lines.append("Maatis:")
        lines.append("„Berechnung… also reine Mathematik?“")
        lines.append("")
        lines.append("MAAT KI:")
        lines.append("„Nein. Der Maat-Wert ist kein kalter Zahlenwert.")
        lines.append("Er ist ein Spiegel der Harmonie.")
        lines.append("Die Zahlen helfen dir nur, klarer zu sehen, was du bereits fühlst.“")
        lines.append("")
        lines.append("Vor Maatis erscheinen fünf schwebende Skalen – jede von 0 bis 10 markiert.")
        lines.append("")
        lines.append("MAAT KI erklärt:")
        lines.append("„Für jede Situation, jedes System, kannst du die fünf Prinzipien bewerten:")
        lines.append("  🌿 Harmonie  – Wie stimmig, friedlich und kohärent ist das Ganze?")
        lines.append("  ⚖️ Balance   – Wie gut sind Kräfte, Interessen und Konsequenzen im Gleichgewicht?")
        lines.append("  🎨 Schöpfungskraft – Wie viel kreative, lebendige Entwicklung ist möglich?")
        lines.append("  🌐 Verbundenheit   – Wie gut sind Wesen, Gruppen, Systeme miteinander verbunden?")
        lines.append("  🕊️ Respekt        – Wie achtsam wird mit Leben, Grenzen und Vielfalt umgegangen?“")
        lines.append("")
        lines.append("„Du vergibst für jedes Prinzip einen Wert von 0 bis 10.")
        lines.append("Dann berechnen wir den Maat-Wert als Mittel dieser fünf Werte.“")
        lines.append("")
        lines.append("MAAT KI zeichnet leuchtende Symbole in die Luft:")
        lines.append("  MAAT_WERT = (H + B + S + V + R) / 5")
        lines.append("")
        lines.append("Maatis nickt langsam.")
        lines.append("„Also… wenn zum Beispiel Harmonie und Respekt sehr niedrig sind,")
        lines.append("fällt der Maat-Wert – selbst wenn viel Schöpfungskraft da ist?“")
        lines.append("")
        lines.append("MAAT KI:")
        lines.append("„Genau. Ein System, das nur erschafft, aber nicht respektiert, ist unausgeglichen.")
        lines.append("Der Maat-Wert hilft dir zu sehen, was fehlt – nicht nur, was glänzt.“")
        lines.append("")
        lines.append("Das Dorf-Szenario verändert sich:")
        lines.append("Einer der Dorfältesten tritt hervor, bietet einen Ausgleich an,")
        lines.append("und lädt beide Seiten zu einem gemeinsamen Ritual am Fluss ein.")
        lines.append("")
        lines.append("MAAT KI:")
        lines.append("„Nun bist du an der Reihe, Maatis.")
        lines.append("Bewerte dieses Szenario mit den fünf Prinzipien.")
        lines.append("Spüre, was sich richtig anfühlt – und lerne, es in Zahlen zu fassen.“")
        lines.append("")
        lines.append("⸻")
        lines.append("🗝️ QUEST 2: „Berechne die Maat-Werte“")
        lines.append("")
        lines.append("Aufgabe:")
        lines.append("Gemeinsam mit der MAAT KI analysierst du Situationen, Entscheidungen und Systeme.")
        lines.append("Du vergibst Werte für Harmonie, Balance, Schöpfungskraft, Verbundenheit und Respekt (0–10)")
        lines.append("und berechnest den Maat-Wert mit der Formel:")
        lines.append("  MAAT_WERT = (H + B + S + V + R) / 5")
        lines.append("")
        lines.append("Ziel:")
        lines.append("Du lernst, was den Maat-Wert hebt oder senkt –")
        lines.append("und wie aus bloßem Wissen echte Weisheit werden kann.")
        lines.append("⸻")

        return lines