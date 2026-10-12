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

Jeder Abschnitt wird wie die ganze Datei ausgewertet (Kennzahlen je Tageszeit, Histogramm, Gefährdung, Lärm, Gruppen); der Rauschboden und der
Regenanteil sind aus der Anpassung über die ganze Datei herausgerechnet, die Gruppen je Abschnitt neu angepasst. Die YAML enthält unter
`abschnitte` die Liste `liste` mit `beginn` (Bruch, Wahrscheinlichkeit, Merkmale vorher und nachher, Verschiebung in Streuungen, Lücke in Tagen,
Begründung) und den Kennzahlen; `summary.csv` enthält die Zahl der Abschnitte und Brüche je Datei.

## Begründung auf den Detailseiten

Je Bruch nennt die Seite: den Unterschied der Verteilungen, die Verschiebung von mittlerem Tempo, 85. und 15. Perzentil und Fahrzeugzahl,
eine Lücke ohne vollständige Aufzeichnung vor dem Bruch, den Erfassungszeitraum der Verwaltung, wenn eine seiner Grenzen höchstens 3 Tage
neben dem Bruch liegt, und **Brüche an anderen Standorten am selben Tag (±1 Tag)**.

## Befund (Stand Oktober 2026)

Von 109 Dateien lassen sich 95 prüfen (die übrigen haben weniger als 14 vollständige Tage). In **38 Dateien** gibt es 44 Brüche: 33 Dateien haben
zwei Abschnitte, vier haben drei, eine vier. Der Unterschied der Verteilungen liegt im Median bei 30 % (kleinster 16 %, größter 80 %).

Die Brüche sind über die Kalendertage nicht gleichmäßig verteilt: **23 von 44 liegen in sieben Häufungen**, in denen an mindestens drei
verschiedenen Standorten innerhalb von zwei Tagen ein Bruch auftritt:

| Tage | Brüche an verschiedenen Standorten |
|------|-----------------------------------|
| 13./14.05.2023 | 3 |
| 06.–08.09.2023 | 3 |
| 04.09.2024 | 3 |
| 14./15.04.2025 | 5 |
| 17./18.07.2025 | 3 |
| 28./29.11.2025 | 3 |
| 14./15.04.2026 | 3 |

Das passt dazu, dass Geräte an gemeinsamen Terminen umgehängt wurden und die Dateien über den Wechsel hinweg weiterliefen. Belegt ist es nicht:
Nur bei drei Brüchen fehlen vorher Tage; bei keinem liegt der Bruch nahe einer Grenze der Erfassungszeiträume in den Mitteilungen der Verwaltung
(die Mitteilungen betreffen vor allem andere Zeiträume). 21 Brüche liegen ohne Häufung. Ein Beispiel für den Wert der Trennung: In
`47_Bonner Straße` springt das mittlere Tempo am 14.09.2023 nach einer Lücke von 8 Tagen von 50,6 auf 38,8 km/h, die Fahrzeugzahl ab 25 km/h sinkt
auf 37 %. Im ersten Abschnitt liegt die V85 bei 56 km/h, im zweiten bei 41 km/h; die Gesamtverteilung gibt keinen der beiden Orte wieder.

## Grenzen

- **Auflösung ein Tag.** Ein Wechsel mitten am Tag fällt auf den Tag selbst; Tage mit unvollständiger Aufzeichnung (erster und letzter Tag eines
  Uhr-Abschnitts) zählen nicht. Die Fahrzeuge an Lücken oder Teiltagen gehören zum Abschnitt davor.
- **Nicht jede Veränderung ist ein Umhängen.** Baustellen, Straßensperrungen, geänderte Verkehrsregeln und lange Ferien können ebenso wirken. Eine
  Antwort der Verwaltung, wann welches Gerät wo hing, wäre der Beleg.
- **Mehrere kleine Brüche** (unter 15 %) und Brüche in Dateien mit weniger als 14 Tagen bleiben unerkannt. Die Wahrscheinlichkeit setzt unabhängige
  Tageswerte nach der Aufblähung voraus; sie ist keine Häufigkeit.
- **Rauschboden und Regenanteil** sind für die ganze Datei geschätzt und gelten damit auch für Abschnitte, in denen ein anderer Ort anderes Rauschen
  haben kann.
- **Gruppen je Abschnitt** haben weniger Fahrzeuge; unter 5.000 Fahrzeugen werden sie nicht zerlegt ([gruppen.md](gruppen.md)).

## Ausblick

Gruppen sind bisher nur durch die Form der Geschwindigkeitsverteilung definiert, und das ist zirkulär: Eine Kurve, die zur Verteilung passt, ist noch
kein Phänomen. Die Abschnitte erlauben einen unabhängigen Test: Taucht eine Gruppe in getrennten Abschnitten desselben Standorts oder in Abschnitten
verschiedener Standorte mit ähnlichen Eigenschaften wieder auf (ähnliche Lage, ähnlicher Tagesgang, gleiche Reaktion auf Licht und Wetter), ist sie
mehr als eine Anpassung. Vorarbeiten stehen in `exploration/verhalten/` (nicht im Repository; erprobt an sieben Messreihen, vor der Trennung nach Abschnitten): Die Verteilung lässt sich besser als Mischung fester
Profile mit wechselnden Gewichten beschreiben als als verschobene Verteilung, die Profile sind zwischen geraden und ungeraden Wochen stabil, und
die Gewichte reagieren auf Dunkelheit, Regen, Temperatur und Schnee (mit Placebo-Test gegen verschobene Wetterreihen).

## Erzeugen

`bruch.py` läuft in `dsd2csv.py` mit; es braucht nur die Standardbibliothek. Test: `test_bruch.py`.
