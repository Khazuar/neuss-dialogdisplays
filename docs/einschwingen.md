# Einschwingen nach Montage und Brüchen, Art der Änderung

> Eigene Auswertung, nicht amtlich. Fehler im Verfahren und in der Auswertung können nicht ausgeschlossen werden (ohne Gewähr).

## Worum es geht

Jeder Einsatz eines Displays beginnt mit einer Montage, und manche Einsätze haben Brüche: Danach fährt der Verkehr anders, etwa weil ein neues
Schild hängt oder das Gerät anders ausgerichtet wurde ([einsaetze.md](einsaetze.md)). Zwei Fragen:

1. **Einschwingen:** Ändert sich der Verkehr nach dem Beginn eines Einsatz-Abschnitts noch eine Weile, bis er einen stabilen Stand erreicht
   (Gewöhnung an das Display oder an das neue Schild)? Wie lange dauert das?
2. **Art der Änderung:** Was hat sich an der Grenze geändert: der Standort, der genaue Ort oder die Ausrichtung des Geräts, die Fahrtrichtung
   oder die Straße selbst?

Vor einer Montage gibt es an diesem Ort keine Daten. Messbar ist darum nur, ob sich der Verkehr **nach** dem Beginn noch ändert, nicht, wie er
ohne Display wäre. Die Wirkung des Displays selbst lässt sich so nicht messen, wohl aber, ob sie in den ersten Wochen nachlässt.

Code: `einschwingen.py` (aufgerufen von `einsaetze.py`), Ergebnis je Einsatz-Abschnitt in `einsaetze.json` und in
[`einschwingen.csv`, `einschwingen-schritte.csv`](../DATEN.md), auf den Detailseiten im Reiter „Einschwingen“.

## Einschwingen

**Beginn.** Bei einer Montage das erste Fahrzeug nach der Transportlücke (bei einer Inbetriebnahme nach Pause: montiert spätestens dann), bei
einem Bruch der verfeinerte Zeitpunkt ([einsaetze.md](einsaetze.md), „Brüche in den Aufenthalten“), sonst das erste Fahrzeug des Abschnitts
(Datenbeginn, ungeprüfte Dateigrenze; dann ist der Zeitpunkt nur ungefähr). Gerechnet wird ab der ersten vollen Stunde danach.

**Schritte.** Fenster gleicher Länge ab dem Beginn, je ein ganzes Vielfaches von 24 Stunden, damit jede Tageszeit gleich oft vorkommt. Die
Länge ist die kürzeste von 1, 2, 3, 4 oder 7 Tagen, bei der ein Schritt im Mittel mindestens 1.000 Fahrzeuge hat. Dann ist der V95 auf etwa
0,5 km/h genau; ruhige Straßen bekommen längere Schritte. Gerechnet wird bis 63 Tage nach dem Beginn oder bis zum Ende des Abschnitts, aus den
bereinigten Fahrzeugen des Einsatzes (Rauschboden und Regenanteil abgezogen, nur vollständig aufgezeichnete Stunden). Schritte mit weniger als
der Hälfte aufgezeichneter Stunden fallen weg.

**Werktag und Wochenende.** An vielen Orten fährt man samstags und sonntags anders. Damit ein Schritt von einem Tag (nur Werktag oder nur
Sonntag) mit einem von sieben Tagen vergleichbar ist, wird jedes Fahrzeug um den Unterschied seines Tagtyps (Werktag, Samstag, Sonn- und
Feiertag) verschoben: mittleres Tempo dieses Tagtyps im stabilen Stand minus mittleres Tempo im stabilen Stand. V85 und V95 werden in der
km/h-Klasse interpoliert (jede Klasse gleichmäßig von v − 0,5 bis v + 0,5), damit sie nicht in ganzen km/h springen.

**Stabiler Stand.** Die Schritte ab Tag 21. Ihr Mittel ist der Stand, ihre Standardabweichung die übliche Schwankung (Wetter, Wochen,
Zufall). Ohne mindestens drei Schritte dort gibt es kein Urteil („zu kurz“).

**Einschwingen belegt?** Je Größe (Mittel, V85, V95) wird die Kurve Wert(t) = Stand + A · e^(−(t − t₁)/τ) an die Schritte angepasst und mit
einem gleichbleibenden Stand verglichen (BIC). τ ist höchstens 7 Tage: Nach 3τ = 21 Tagen sind 95 % der Anfangsabweichung abgebaut, und dort
beginnt der stabile Stand. Langsamere Veränderungen sind eher Drift (Jahreszeit) als Einschwingen. Belegt ist ein Einschwingen, wenn die Kurve
beim Mittel oder beim V85 um mindestens 6 BIC-Punkte besser passt. A ist dann die Abweichung zu Beginn (positiv: anfangs schneller), stabil ist
der Verkehr nach 3τ.

## Art der Änderung

Verglichen werden die Werktage ohne Feiertage bis 14 Tage vor und nach der Grenze, ohne den Tag der Grenze selbst, aus den Rohdaten des
Gesamtstroms (`bewegungen.py`). Wenn auf beiden Seiten mindestens drei Tage außerhalb der Ferien liegen, nur diese. Die Fenster enden an
der nächsten anderen Grenze.

| Merkmal | Bedeutung |
|---|---|
| Menge | ln(Fahrzeuge je Stunde danach / davor), über die Stunden des Tages, die auf beiden Seiten vorkommen |
| Tagesgang | Anteil der Fahrzeuge, die zu anderen Stunden fahren (Gesamtvariation der Tagesgänge) |
| Spitze | ln(Fahrzeuge 6–9 Uhr / 15–18 Uhr): Bei Pendlerverkehr kehrt eine andere Fahrtrichtung die Spitze um |
| Tempo | Änderung der Quantile q10 bis q90 (Fahrzeuge ab 15 km/h); passt ein gemeinsamer Faktor besser als ein gemeinsamer Abstand? |
| sofort | Anteil der Tempoänderung, der im ersten Schritt nach der Grenze schon da ist (gegen den stabilen Stand danach) |

Ein anderer Messwinkel wirkt wie ein Faktor: Das Radar misst v · cos(Winkel), alle Geschwindigkeiten werden um denselben Anteil kleiner oder
größer. Ein Display, ein Schild oder eine andere Stelle an der Straße verschieben dagegen eher alle gleich viel oder vor allem die Schnellen.

| Klasse | Regel |
|---|---|
| Standortwechsel | Montage zu Beginn eines Einsatzes, wenn der Aufenthalt davor zu einem anderen Standort gehört; oder eine Bewegung, nach der sich die Menge mehr als verdoppelt oder halbiert |
| andere Fahrtrichtung | Tagesgang anders (mindestens 20 %) und die Spitze kehrt sich um (Vorzeichen wechselt, Unterschied mindestens 0,5) |
| andere Ausrichtung (Messwinkel) | Tempo um mindestens 2 km/h anders, Menge (±30 %) und Tagesgang gleich, und ein gemeinsamer Faktor passt mindestens doppelt so gut wie ein gemeinsamer Abstand |
| Änderung an der Straße | Tempo um mindestens 2 km/h anders, aber im ersten Schritt erst weniger als 70 % davon (allmählich, etwa ein neues Schild); oder nur die Menge oder nur der Tagesgang anders (Baustelle, Umleitung) |
| genauer Ort oder Ausrichtung geändert | Tempo sofort um mindestens 2 km/h anders, Menge gleich; oder Tempo und Menge zugleich anders (anderer Mast) |
| keine deutliche Änderung | nichts davon |
| nicht bestimmbar | weniger als drei Werktage auf einer Seite, oder Ferien nur auf einer Seite ohne große Tempoänderung |

Liegen nur auf einer Seite Ferientage, zählen Menge und Tagesgang nicht (Ferien ändern beides), und das Tempo erst ab 4 km/h.

Die Klassen sind Hinweise, keine Beweise. Ein Display, das versetzt wird, und eine Baustelle in der Nähe können gleich aussehen.

## Ergebnis (Stand November 2026)

**Einschwingen nach der Montage.** 79 Einsatz-Abschnitte beginnen mit einer minutengenau bekannten Montage; 74 davon sind lang genug für ein
Urteil.

| Urteil | Abschnitte |
|---|---|
| kein Einschwingen messbar | 66 |
| Einschwingen belegt | 8 (4 anfangs langsamer, 4 anfangs schneller; stabil nach 3 bis 21 Tagen) |
| zu kurz | 5 |

Im Mittel über die 74 Montagen lag der erste Schritt **+0,1 ± 0,2 km/h** (mittleres Tempo) und **+0,3 ± 0,2 km/h** (V85) über dem späteren
Stand. Der Verkehr ist also vom ersten Tag an praktisch so schnell wie Wochen später. Weder werden die Fahrzeuge mit der Zeit schneller (die
Wirkung des Displays ließe nach), noch gibt es einen Neuheitseffekt (anfangs deutlich langsamer). Das passt zur früheren Auswertung über
Tageswerte (`exploration/gewoehnung/einschwingen.py`): in den ersten gut zwei Wochen +0,2 km/h, gegen eine Gegenprobe mit Schein-Ereignissen
30 Tage nach der Montage etwa 0,3 km/h.

Die acht belegten Fälle gehen in beide Richtungen. Anfangs langsamer: Am Alten Bach 12/2024 (−5,9 km/h, stabil nach 6 Tagen), Viersener
Straße 02/2025 (−5,8 km/h, nur der erste Tag), Ruhrstraße 04/2026 (−4,6 km/h) und Preußenstraße 07/2025 (−2,3 km/h). Anfangs schneller:
Hermannstraße 07/2023 (+5,6 km/h), Lüttenglehner Straße 01/2025 (V85 +4,6 km/h), Nievenheimer Straße 09/2023 (V85 +3,6 km/h) und
Cyriakusstraße 04/2024 (+1,0 km/h). Ein allgemeines Muster ergibt sich daraus nicht. Anfangs schneller kann auch heißen, dass die Montage in
die Ferien oder kurz vor eine Baustelle fiel.

**Brüche.** Von den 8 Brüchen in Einsätzen sind 6 lang genug; ein Einschwingen ist bei 3 belegt. Das deutlichste Beispiel ist die Viersener
Straße am 14.05.2025 um 07:18 (Tempo-30-Schild zum Schutz der Gänse): Das mittlere Tempo fiel im ersten Tag von 40,8 auf 37,4 km/h und dann
allmählich um weitere 2,6 km/h auf 34,7 km/h (τ = 5 Tage). Stabil war der Verkehr nach etwa zwei Wochen.

**Art der Änderung.**

| Grenze | Klasse | Anzahl |
|---|---|---|
| Montage zu Beginn eines Einsatzes, das Gerät kam von einem anderen Standort | Standortwechsel | 82 |
| Montage zu Beginn eines Einsatzes, das Gerät hing davor am selben Standort | keine deutliche Änderung 2, nicht bestimmbar 3 | 5 |
| Bewegung innerhalb eines Einsatzes | Standortwechsel 1, nicht bestimmbar 3 | 4 |
| Bruch im Aufenthalt | genauer Ort oder Ausrichtung 2, Änderung an der Straße 2, andere Ausrichtung 1, keine 1, nicht bestimmbar 2 | 8 |
| ungeprüfte Dateigrenze | keine 2, nicht bestimmbar 1 | 3 |

Eine Fahrtrichtung hat sich an keiner Grenze erkennbar geändert. Die Brüche Hermannstraße 06.09.2023 und Rosmarinstraße 16.01.2025 (Tempo
sofort 2,5 bis 4 km/h anders, Menge gleich) sehen nach einem Eingriff am Gerät aus, Ruhrstraße 09.07.2026 (alle Geschwindigkeiten um etwa
10 % kleiner) nach einem anderen Messwinkel. Die Liedberger Straße am 28.11.2025 ist ein Standortwechsel innerhalb einer Messung (Menge danach
ein Fünftel). Bei der Viersener Straße am 14.04.2025 wurde das Gerät 25 Minuten abgenommen und am selben Standort wieder montiert; davor
galt die Messung „Tempo 50“, danach „Tempo 30“. Weil danach Osterferien waren, ist die Art der Änderung nicht bestimmbar.

**Gegenprobe.** An 160 Schein-Grenzen mitten in Abschnitten von mindestens 42 Tagen (Tag 21 und 35) ergab die Klassifikation 137-mal keine
deutliche Änderung, 14-mal nicht bestimmbar, 7-mal eine Änderung an der Straße und 2-mal eine andere Fahrtrichtung. Rund 6 % der
beurteilbaren Schein-Grenzen werden also fälschlich als Änderung erkannt; einige davon sind vermutlich echte Änderungen ohne Bruch (etwa
Bauerbahn im Mai 2024: Menge −40 %, Tagesgang anders).

## Forschungsstand

- Klassische Geschwindigkeitsanzeigen (nur die Zahl) verlieren an Wirkung, wenn sie lange an einem Ort bleiben ([TRL PPR314](https://www.trl.co.uk/uploads/trl/documents/PPR314.pdf)).
- Für Dialog-Displays (Smiley, „Danke“/„Langsam“) fanden deutsche Untersuchungen keine nachlassende Wirkung über mehrere Wochen
  ([TRID 1119038](https://trid.trb.org/View/1119038), [GDV, TRID 1128391](https://trid.trb.org/View/1128391)).
- Nach einer Absenkung des Tempolimits fällt das Tempo meist sofort und bleibt niedriger
  ([AA Research Foundation, Neuseeland](https://www.aa.co.nz/about/aa-research-foundation/programmes/speed-limits/)); eine feste Zeitspanne bis
  zur „Annahme“ eines neuen Limits nennt die Literatur nicht.

## Grenzen

- Ohne Daten vor der Montage ist „anfangs schneller“ nicht von „anfangs andere Verkehrsteilnehmer“ (Ferienende, Baustelle in der Nähe) zu
  trennen.
- Der stabile Stand ab Tag 21 enthält Jahreszeit und Wetter dieser Wochen. Ein langer Abschnitt im Herbst kann langsamer werden, ohne dass
  das mit dem Display zu tun hat. Darum ist τ auf 7 Tage begrenzt.
- Die Schwellen der Klassen sind von Hand gesetzt und an Schein-Grenzen geprüft (siehe Ergebnis), nicht an bekannten Fällen geeicht: Von den
  Brüchen kennen wir die Ursache nur in Einzelfällen (Viersener Straße: Tempo-30-Schild ab Mai 2025).
