# Brüche und Abschnitte einer Messreihe

> Eigene Berechnung, ohne Gewähr. Ein erkannter Bruch ist eine statistische Aussage über die Daten („das Verhalten des Verkehrs ändert sich
> hier plötzlich und bleibt anders“). Was dabei geschah, sagen die Daten nicht.

Die Geräte werden umgehängt oder neu eingestellt. Eine DSD-Datei kann dabei mehrere Einsätze enthalten, an verschiedenen Stellen und mit
verschiedenem Verkehr. Mischt man sie, beschreibt die Verteilung einen Ort, den es nicht gibt. `bruch.py` sucht deshalb in jeder Datei nach
Stellen, an denen sich die Geschwindigkeitszusammensetzung dauerhaft ändert, und zerlegt die Messreihe dort in **Abschnitte**. Die
Gesamtauswertung über alle Daten bleibt (sie lässt sich mit den Angaben der Verwaltung vergleichen); zusätzlich wird jeder Abschnitt einzeln
ausgewertet, mit Begründung und Wahrscheinlichkeit.

## Verfahren

1. **Tagesmerkmale.** Für jeden vollständig aufgezeichneten Tag (24 Stunden mit nutzbarer Uhr, mindestens 50 Fahrzeuge ab der halben
   Höchstgeschwindigkeit, mindestens 10 km/h) werden fünf Werte gebildet: mittleres Tempo, 15. und 85. Perzentil, Anteil über dem Tempolimit und
   der Logarithmus der Fahrzeugzahl. Der Unterschied zwischen Werktagen, Samstagen und Sonntagen (Median je Tagtyp) wird abgezogen.
   **Schulferien und Feiertage in NRW zählen nicht** (`kalender.py`): Der Verkehr ist dort anders, kehrt danach aber zurück. Ohne diese
   Ausnahme hielt das Verfahren etwa das Ende der Osterferien 2026 an der Breiten Straße für einen Bruch. Ein Bruch, vor dem Ferien liegen,
   nennt sie in der Begründung; ob die Änderung in oder nach den Ferien geschah, bleibt offen. In der Auswertung der Abschnitte zählen die
   Ferientage wieder mit (sie gehören zum Abschnitt davor); für die Analyse des Verhaltens sind Ferien und Feiertage eigene Merkmale.
2. **Streuung von Tag zu Tag und von Woche zu Woche.** Die Streuung je Merkmal schätzt man robust aus den Unterschieden aufeinanderfolgender Tage.
   Wetter, Ferien und Feiertage machen die Tage einander ähnlich; deshalb wird sie um das Verhältnis aufgebläht, um das der Unterschied zwischen
   benachbarten Sieben-Tage-Fenstern größer ist, als reines Tagesrauschen erwarten ließe (Median-Abweichung, unempfindlich gegen Brüche).
3. **Zerlegung.** Die Tage werden optimal in Abschnitte von mindestens 7 Tagen zerlegt (dynamische Programmierung: Summe der quadrierten
   Abweichungen vom Abschnittsmittel in Einheiten der Streuung, Strafe je Bruch nach dem BIC).
4. **Wahrscheinlichkeit je Bruch.** BIC-Vergleich „ein Abschnitt“ gegen „zwei Abschnitte“ für die beiden angrenzenden Abschnitte,
   p = 1 / (1 + exp(−ΔBIC / 2)) bei gleicher Vorabwahrscheinlichkeit. Getrennt wird ab p ≥ 90 %; Brüche zwischen 50 und 90 % stehen als
   `moegliche_brueche` in der YAML. p gilt unter den Annahmen des Modells (normalverteilte Tageswerte, aufgeblähte Streuung); sie ist ein Maß für die
   Stärke des Befunds. Bei Brüchen mit sehr großem Unterschied ist sie praktisch 100 %.
5. **Ausschläge sind keine Brüche.** Ein Abschnitt von höchstens 21 Tagen, nach dem der Verkehr zum früheren Niveau zurückkehrt (Netto-Verschiebung
   höchstens halb so groß wie der Ausschlag), wird nicht getrennt (Osterwoche, Weihnachten, Unwetter). Sie stehen als `ausschlaege`.
6. **Der Unterschied muss groß sein.** Bei mehreren Tausend Fahrzeugen je Tag ist schon eine Verschiebung um 0,3 km/h statistisch sicher. Getrennt
   wird deshalb nur, wenn sich die Verteilungen der Geschwindigkeiten (ganze km/h) vor und nach dem Bruch um mindestens **15 %** unterscheiden
   (totale Variation, halbe Summe der Anteilsunterschiede; 0 = gleich, 1 = nichts gemeinsam). Die Schwelle ist von Hand gewählt und nicht an
   bekannten Umhängeterminen geeicht. Wer sie ändert (`MIN_UNTERSCHIED`), ändert die Zahl der Abschnitte.

Jeder Abschnitt wird wie die ganze Datei ausgewertet (Kennzahlen je Tageszeit, Histogramm, Gefährdung, Lärm, Verhaltensgruppen); der Rauschboden und der
Regenanteil sind aus der Anpassung über die ganze Datei herausgerechnet. Die YAML enthält unter
`abschnitte` die Liste `liste` mit `beginn` (Bruch, Wahrscheinlichkeit, Merkmale vorher und nachher, Verschiebung in Streuungen, Lücke in Tagen,
Begründung) und den Kennzahlen; `summary.csv` enthält die Zahl der Abschnitte und Brüche je Datei.

## Begründung auf den Detailseiten

Je Bruch nennt die Seite: den Unterschied der Verteilungen, die Verschiebung von mittlerem Tempo, 85. und 15. Perzentil und Fahrzeugzahl,
eine Lücke ohne vollständige Aufzeichnung vor dem Bruch, den Erfassungszeitraum der Verwaltung, wenn eine seiner Grenzen höchstens 3 Tage
neben dem Bruch liegt, und **Brüche an anderen Standorten am selben Tag (±1 Tag)**.

## Befund (Stand Oktober 2026)

Von 109 Dateien lassen sich 92 prüfen (die übrigen haben ohne Ferien und Feiertage weniger als 14 vollständige Tage). In **34 Dateien** gibt es je
einen Bruch. Der Unterschied der Verteilungen liegt im Median bei 35 % (kleinster 15 %, größter 79 %).

Bevor Ferien und Feiertage ausgenommen waren, fand das Verfahren 44 Brüche in 38 Dateien; ein Teil davon waren Ferienanfang oder Ferienende
(etwa an der Breiten Straße das Ende der Osterferien 2026). Diese Fälle sind jetzt keine Brüche mehr.

14 der 34 Brüche liegen in vier Häufungen, in denen an mindestens drei verschiedenen Standorten innerhalb von zwei Tagen ein Bruch auftritt:

| Tage | Brüche an verschiedenen Standorten |
|------|-----------------------------------|
| 13./14.05.2023 | 3 |
| 06.–08.09.2023 | 3 |
| 04.09.2024 | 3 |
| 27.04.2025 (erster Tag nach den Osterferien) | 5 |

Bei den fünf Brüchen am 27.04.2025 unterscheidet sich der Verkehr nach den Osterferien dauerhaft von dem davor (Pomona, Viersener Straße,
Krokusstraße, Am Reckberg, Föhrenstraße). Das passt dazu, dass die Geräte in den Ferien umgehängt wurden und die Dateien weiterliefen; belegt ist
es nicht. Ebenso liegen die Brüche an der Preußen- und der Münchener Straße am ersten Tag nach den Sommerferien 2025. Nur bei drei Brüchen fehlen
vorher Tage ohne Aufzeichnung; bei keinem liegt der Bruch nahe einer Grenze der Erfassungszeiträume in den Mitteilungen der Verwaltung (die
Mitteilungen betreffen vor allem andere Zeiträume). Ein Beispiel für den Wert der Trennung: In `47_Bonner Straße` springt das mittlere Tempo am
14.09.2023 nach einer Lücke von 8 Tagen von 50,6 auf 38,8 km/h, die Fahrzeugzahl ab 25 km/h sinkt auf 37 %. Im ersten Abschnitt liegt die V85 bei
56 km/h, im zweiten bei 41 km/h; die Gesamtverteilung gibt keinen der beiden Orte wieder.
## Grenzen

- **Auflösung ein Tag.** Ein Wechsel mitten am Tag fällt auf den Tag selbst; Tage mit unvollständiger Aufzeichnung (erster und letzter Tag eines
  Uhr-Abschnitts) zählen nicht. Die Fahrzeuge an Lücken oder Teiltagen gehören zum Abschnitt davor.
- **Nicht jede Veränderung ist ein Umhängen.** Baustellen, Straßensperrungen, geänderte Verkehrsregeln und lange Ferien können ebenso wirken. Eine
  Antwort der Verwaltung, wann welches Gerät wo hing, wäre der Beleg.
- **Mehrere kleine Brüche** (unter 15 %) und Brüche in Dateien mit weniger als 14 Tagen bleiben unerkannt. Die Wahrscheinlichkeit setzt unabhängige
  Tageswerte nach der Aufblähung voraus; sie ist keine Häufigkeit.
- **Rauschboden und Regenanteil** sind für die ganze Datei geschätzt und gelten damit auch für Abschnitte, in denen ein anderer Ort anderes Rauschen
  haben kann.
- **Verhaltensgruppen je Abschnitt** brauchen mindestens 14 Tage und 5.000 Fahrzeuge ([verhalten.md](verhalten.md)); kürzere Abschnitte
  werden nur mit den Vorlagen der Stadtebene geprüft.

## Ausblick

Die früheren Formgruppen ([gruppen.md](gruppen.md)) waren nur durch die Form der Geschwindigkeitsverteilung definiert, und das ist zirkulär: Eine Kurve, die zur Verteilung passt, ist noch
kein Phänomen. Die Abschnitte erlauben einen unabhängigen Test: Taucht eine Gruppe in getrennten Abschnitten desselben Standorts oder in Abschnitten
verschiedener Standorte mit ähnlichen Eigenschaften wieder auf (ähnliche Lage, ähnlicher Tagesgang, gleiche Reaktion auf Licht und Wetter), ist sie
mehr als eine Anpassung. Der Stand dazu steht in [verhalten.md](verhalten.md). Erste Vorarbeiten (an sieben Messreihen, vor der Trennung nach Abschnitten): Die Verteilung lässt sich besser als Mischung fester
Profile mit wechselnden Gewichten beschreiben als als verschobene Verteilung, die Profile sind zwischen geraden und ungeraden Wochen stabil, und
die Gewichte reagieren auf Dunkelheit, Regen, Temperatur und Schnee (mit Placebo-Test gegen verschobene Wetterreihen).

## Erzeugen

`bruch.py` läuft in `dsd2csv.py` mit; es braucht nur die Standardbibliothek. Test: `test_bruch.py`.
