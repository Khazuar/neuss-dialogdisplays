# Gerätesperre (Totzeit): Wie viele Fahrzeuge die Geräte verpassen (Forschungsstand)

> Eigene Berechnung, ohne Gewähr. Noch nicht Teil der Auswertung: Keine Kennzahl ist um die Sperre korrigiert. Alle Zahlen stammen aus den
> Skripten `tools/totzeit_regen.py`, `tools/totzeit_eichung.py` und `tools/totzeit_doppelt.py` (Stand Oktober 2026, 109 Dateien, Ergebnis
> von `lokal_bauen.py` als Eingabe).

## Frage

Nach jedem Datensatz nimmt ein Gerät für einige Sekunden keinen neuen auf. In 100 von 106 Dateien kommt kein Abstand unter 2 bis 8 s vor,
bei 68 der geprüften Dateien sind es 5 s (passend zu `ar_timeout`/`dead_time` in der Gerätekonfiguration, [wetter.md](wetter.md)). Fahrzeuge
in dieser Zeit fehlen. Zwei Quellen:

- **Regenphantome** sperren das Gerät ebenfalls. Die echten Fahrzeuge in dieser Zeit fehlen, auch wenn die Phantome später herausgerechnet
  werden ([rauschen.md](rauschen.md)).
- **Dichter Verkehr:** Folgt ein Fahrzeug dem anderen innerhalb der Sperre, wird es nicht gemessen. Bei zufälligen (Poisson-)Ankünften und
  einer festen Sperre τ nach jedem Datensatz fehlt der Anteil m·τ (m: Datensätze je Sekunde), bei 200 Datensätzen je Stunde und 5 s also 28 %.

Wenn ein Teil fehlt und die Fehlenden den Gemessenen ähneln, stünde jeder Datensatz für etwas mehr als ein Fahrzeug, mit einem Faktor, der mit
der Dichte wächst. Im Histogramm wären das gebrochene Zuschläge je Stunde und Geschwindigkeit.

## Versuch 1: Verdecken Regenphantome Fahrzeuge?

Phantome kommen unabhängig vom Verkehr. Der Anteil der Zeit, den sie sperren (Phantome je Regenstunde mal τ), sagt deshalb den Anteil
verdeckter Fahrzeuge voraus, ohne Annahme darüber, wie die Fahrzeuge ankommen. Je Datei und Regenklasse: Fahrzeuge (Datensätze ab der
Verkehrsschwelle) in Regenstunden gegen die trockenen Stunden derselben Zelle (Tagtyp, Stunde); Phantome = langsame Datensätze über der
trockenen Erwartung. 97 Dateien, 290 Paare aus Datei und Regenklasse, 33.171 Regenstunden.

| Sperranteil durch Phantome | Regenstunden | Sperre im Mittel | Rückgang der Fahrzeuge |
| --- | --- | --- | --- |
| unter 0,2 % | 12.570 | 0,02 % | 0,5 % |
| 0,2 bis 1 % | 9.102 | 0,50 % | 1,5 % |
| 1 bis 3 % | 6.785 | 1,77 % | 3,7 % |
| 3 bis 10 % | 4.543 | 5,74 % | 11,7 % |
| über 10 % | 171 | 11,42 % | 30,6 % |

Gerade über alle Paare (gewichtet nach Regenstunden): **Rückgang = 0,4 % + 2,0 × Sperranteil** (95-%-Bereich der Steigung 1,2 bis 2,8,
Bootstrap über Dateien).

- **Der Rückgang des Verkehrs bei Regen ist fast ganz ein Messeffekt.** Wo keine Phantome sperren, fährt bei Regen kaum weniger Verkehr
  (0,5 %; dort sind alle drei Regenklassen gemischt). Der Rückgang wächst mit der Sperrzeit durch die Phantome und erreicht bei den stärksten Dateien 30 %.
  Damit ist der vermutete Mechanismus aus [wetter.md](wetter.md) (Rückgang um 10 bis 25 % bei starkem Regen) belegt.
- **Aber jede gesperrte Sekunde kostet etwa doppelt so viel Verkehr wie erwartet.** Erwartet war eine Steigung von 1. Geprüft und nicht bestätigt:
  - Langsame Ziele sperren länger (sie bleiben länger im Radarfeld)? Nein, siehe Versuch 4.
  - Echos unter der Erfassungsgrenze (9 bis 10 km/h), die nicht gespeichert werden, sperren mit? Dann müsste die Steigung bei Geräten mit
    niedriger Erfassungsgrenze kleiner sein. Bis 5 km/h: 1,79 (1,17 bis 2,87, 18 Dateien); 6 bis 9 km/h: 2,14 (0,83 bis 3,19, 71 Dateien).
    Kein Unterschied nachweisbar.
  - Offen: Ein nasses Gerät erfasst schlechter, die Sperre verlängert sich bei dichter Folge von Echos (die Phantome kommen in Schüben, siehe
    [rauschen.md](rauschen.md)), oder die Phantome sind mit der verwendeten Schätzung (langsame Datensätze über der trockenen Erwartung)
    untergezählt.
- Nach Gerätesperre getrennt: 1 bis 2 s 1,89 (1,18 bis 3,59), 5 s 1,72 (0,34 bis 2,63); die Geräte mit 8 s haben kaum Phantome.

**Folge:** Die Verkehrsmenge in Regenstunden ist zu niedrig, im Mittel um etwa das Doppelte des Sperranteils (Regenklasse 3: Sperre 3,5 %,
Rückgang 8,3 %). Für Tempo und Einhaltung spielt das kaum eine Rolle, solange die Verpassten so schnell fahren wie die Gemessenen; für Mengen
(Fahrzeuge je Tag) schon. Eine Korrektur wäre möglich (Faktor 1 + 2 × Sperranteil je Regenstunde), ist aber ohne Erklärung des Faktors 2
nicht belastbar.

## Versuch 2: Eichung an Geräten mit kurzer Sperre

18 Dateien haben eine Sperre von 1 oder 2 s (10 davon die stationären Messungen an der Villestraße, dazu Bauerbahn, Nierenhofstraße,
Kruppstraße, Weckhovener Straße, zweimal Berghäuschensweg, Matthiasstraße, Hochstadenstraße). Auf ihre Datensätze wurde eine feste Sperre
von 5 s (und 8 s) gelegt; das ergibt, was ein Gerät mit längerer Sperre verpasst hätte, nach Verkehrsdichte (Datensätze je Stunde, wie das
Gerät mit langer Sperre sie sähe):

| Datensätze je Stunde | verpasst bei 5 s | Poisson bei 5 s | verpasst bei 8 s | Poisson bei 8 s |
| --- | --- | --- | --- | --- |
| bis 25 | 2,0 % | 2,1 % | 3,5 % | 3,4 % |
| 25 bis 50 | 2,1 % | 5,2 % | 4,7 % | 8,4 % |
| 50 bis 100 | 2,5 % | 10,7 % | 6,7 % | 17,2 % |
| 100 bis 150 | 4,3 % | 17,6 % | 11,3 % | 27,6 % |
| 150 bis 200 | 4,3 % | 24,6 % | 16,3 % | 37,6 % |
| 200 bis 300 | 8,2 % | 31,2 % | 32,9 % | 51,6 % |
| über 300 | 20,1 % | 46,3 % | 42,2 % | 67,1 % |

- **Die Poisson-Rechnung überschätzt den Verlust stark.** Bei dünnem Verkehr stimmt sie, ab 50 Datensätzen je Stunde liegt der gemessene
  Verlust bei einem Viertel bis einem Fünftel. Die Fahrzeuge kommen also nicht zufällig: Knapp hinter einem gemessenen Fahrzeug folgen
  seltener weitere, als Poisson erwarten lässt.
- **Vorbehalt:** Auch die Geräte mit kurzer Sperre sind nicht die Wahrheit. Was sie selbst verpassen (dicht folgende Fahrzeuge, die das Radar
  nicht trennt), fehlt auch hier. Die Zahlen sind deshalb eine **Untergrenze**. Und 10 der 18 Dateien stammen von einer einzigen Straße
  (Villestraße, Landesstraße mit Tempo 50).

## Versuch 3: Fahren die Verpassten anders?

Verpasste gegen behaltene Fahrzeuge derselben Stunde (simulierte Sperre, 18 Dateien):

- Bei 5 s Sperre sind die Verpassten im Median 1,0 km/h langsamer (Spanne der Dateien −5,6 bis +17,0 km/h), bei 8 s 1,2 km/h. Dicht
  folgende Fahrzeuge fahren etwas langsamer, wohl weil dichter Verkehr langsamer ist.
- Folge für die Kennzahlen eines Geräts mit 5 s Sperre gegenüber dem mit kurzer: Mittel im Median +0,3 km/h, Einhaltung −0,7 Prozentpunkte
  (höchstens 1,5), V85 in 4 von 18 Dateien um 1 km/h höher. Bei 8 s: +0,7 km/h, −1,2 Prozentpunkte (höchstens 2,8), V85 in 6 von 18 um 1 höher.
- Die Sperre verschiebt die Kennzahlen also leicht in Richtung „schneller“. Der Effekt ist klein und reicht für keine andere Einstufung der
  Verwaltung, außer an der Grenze einer Stufe.

## Versuch 4: Sperrt das Gerät nach langsamen Zielen länger?

Je Datensatz: Anteil kurzer Abstände (unter τ + 5 s) danach gegen davor. Danach wirkt die Sperre dieses Datensatzes, davor die des Vorgängers
bei gleicher Verkehrslage. Bei fester Sperre ist das Verhältnis R von der Geschwindigkeit unabhängig.

| Geschwindigkeit des Datensatzes | 0–10 | 10–20 | 20–30 | 30–40 | 40–60 | ab 60 km/h |
| --- | --- | --- | --- | --- | --- | --- |
| R, Geräte mit 5 s Sperre (Median über Dateien) | 1,11 | 1,07 | 0,87 | 0,97 | 1,25 | 2,30 |
| R, Geräte mit 1 bis 2 s Sperre | 1,13 | 1,09 | 1,21 | 0,94 | 0,93 | 1,77 |

- Nach langsamen Datensätzen folgen nicht seltener kurze Abstände: **keine längere Sperre nach langsamen Zielen.** Damit erklärt das den
  Faktor 2 aus Versuch 1 nicht.
- Nach schnellen Datensätzen (ab 60 km/h) folgen **mehr als doppelt so oft** kurze Abstände wie davor. Das führte zu Versuch 6.

## Versuch 5: Wie viel fehlt insgesamt?

Die Eichkurve aus Versuch 2 auf die 68 Dateien mit 5 s Sperre angewandt (je Stunde nach Dichte): Faktor im Median **1,027**, 90 % der Dateien
unter 1,041, höchstens 1,042. Nach Poisson wären es im Median 1,105, höchstens 1,247. Die Geräte verpassen also im Median etwa 3 % der Fahrzeuge
durch die Sperre (Untergrenze, siehe Vorbehalt in Versuch 2), nicht 10 %. Regenstunden kommen hinzu (Versuch 1).

## Versuch 6: Doppelmessungen?

- **Schnelle Fahrzeuge:** Der Datensatz nach einem schnellen (ab 60 km/h) hat binnen 10 s nicht dieselbe, sondern eine deutlich kleinere
  Geschwindigkeit (Median −36 km/h; fast gleich schnell nur 2,9 % gegen 7,4 % bei unabhängigen Paaren). Keine Doppelmessung desselben
  Fahrzeugs. Ein schneller Wert mit einem um mindestens 15 km/h langsameren Nachfolger binnen 10 s kommt bei 4,3 % der schnellen Datensätze
  vor, gespiegelt (langsamerer Vorgänger) bei 2,1 %. Der Überschuss von **2,2 %** (Median je Datei 1,3 %, höchstens 7,1 % am Berghäuschensweg)
  könnte ein Fehlwert sein, den ein normales Fahrzeug auslöst, bevor es nach der Sperre richtig gemessen wird. Das betrifft V99 und die
  Nachtereignisse höchstens am Rand.
- **Langsame Objekte:** Nach Datensätzen unter 30 km/h ist der Nachfolger binnen 5 bis 10 s in 38,6 % der Fälle fast gleich schnell
  (höchstens 2 km/h Unterschied), bei Abständen von 30 bis 120 s nur in 22,3 %. Eine Wiedermessung desselben Objekts nach Ablauf der Sperre
  müsste sich bei genau 5 s häufen. Bei Paaren unter 20 km/h tut sie das nicht: Von den fast gleich schnellen Paaren mit 5 bis 9 s Abstand
  liegen 14 % bei 5 s, von den verschieden schnellen 10 %, sonst sind beide flach über 6 bis 9 s verteilt. Eher Gruppen (Kolonnen, Rad- oder
  Fußgängergruppen) als Doppelmessungen. Bisher also weiterhin kein Hinweis auf Doppelmessungen in nennenswertem Umfang.

## Was daraus folgt

**Umgesetzt (Oktober 2026):** Statt zu korrigieren, lassen sich Regenstunden weglassen. Die Auswahl „Wetter: nur trockene Stunden“ im Reiter
Analyse der Detailseiten und die Spalte `regenklasse` der Stundendaten ([DATEN.md](../DATEN.md)) beschränken auf Stunden ohne Regen (auch nicht
in den drei Stunden davor und der danach). Der Vergleich mit allen Stunden zeigt, wie stark Regen die Zahlen einer Messung bewegt.

Über alle Messungen (`tools/trocken_vergleich.py`; 94 Messungen mit mindestens 200 trockenen und 50 Regenstunden, Regenstunden im Median 17 %
der Stunden): Nur trockene Stunden haben im Median **0,6 % mehr Fahrzeuge je Stunde** als alle Stunden (10 % der Messungen unter −2,4 %,
10 % über +3,8 %, höchstens +10,7 % am Kuhweg). V85 bleibt in 83 von 94 Messungen gleich (je 5-mal ±1 km/h, einmal +2), die Einhaltung im Median
auch (größter Unterschied 2,2 Prozentpunkte). Vorbehalt: Trockene Stunden verteilen sich anders auf Tageszeiten und Jahreszeiten als alle
Stunden; ein Teil der Unterschiede, auch die negativen, kommt daher und nicht vom Regen.

- **Regenstunden:** Die Verkehrsmenge ist dort messbar zu niedrig, abhängig von der Zahl der Phantome. Für Mengen in Regenstunden (Stunden-
  und Tageswerte) wäre eine Korrektur sinnvoll; sie scheitert vorerst am unerklärten Faktor 2. Ein nächster Versuch: die Sperre je
  Regenstunde aus der beobachteten Folge der Datensätze statt aus der Zahl der Phantome schätzen.
- **Allgemeine Sperre:** Klein (im Median etwa 3 %, Untergrenze), in dichten Stunden mehr. Für Tempo und Einhaltung kaum wichtig, für Fahrzeuge
  je Tag spürbar, aber dieselbe Verzerrung haben die Zahlen der Verwaltung (gleiche Geräte).
- **Gewichte im Aggregat:** Eine gebrochene Gewichtung je Stunde wäre technisch einfach. Für die allgemeine Sperre ist die Eichung aber zu
  unsicher (Untergrenze, eine Straße dominiert), für den Regen fehlt die Erklärung des Faktors 2. Deshalb noch keine Korrektur in den Daten.
- **Eine bessere Wahrheit** wären unabhängige Zählungen (Zählstellen, Video) an einem Messort, oder zwei Geräte mit verschiedener Sperre am
  selben Ort zur selben Zeit.

## Nachrechnen

```sh
python3 -I lokal_bauen.py                    # _vorschau/auswertung.json
python3 -I tools/totzeit_regen.py            # Versuch 1
python3 -I tools/totzeit_eichung.py          # Versuche 2 bis 5
python3 -I tools/totzeit_doppelt.py          # Versuch 6
python3 -I tools/trocken_vergleich.py        # alle gegen nur trockene Stunden (braucht _vorschau/daten von lokal_bauen.py)
```
