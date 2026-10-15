# Gefährdung, Lärm und nächtliche Ereignisse

> **Wichtig:** Alles in diesem Dokument sind **Schätzungen** aus der Verteilung der gemessenen Geschwindigkeiten.
> Sie ersetzen weder eine Unfallanalyse noch eine Lärmmessung oder ein Gutachten. **Fehler in der Auswertung
> (Skripte, Annahmen, Zuordnung der Daten) können nicht ausgeschlossen werden.** Die Zahlen sind ohne Gewähr und nicht
> für Bußgeld-, Gerichts- oder Genehmigungsverfahren gedacht.

Die Kennzahlen stehen in jeder `<name>.yaml` (Blöcke `gefaehrdung`, `laerm`, `nacht_ereignisse`) und auf den
Detailseiten der Standorte. `gefaehrdung` und `laerm` gibt es für dieselben Zeiträume wie die übrigen Kennzahlen:
alle Fahrzeuge der Datei, Fahrzeuge mit nutzbarer Zeit, Nacht, Vormittag, Nachmittag, Abend, Schulweg. Ohne bekanntes Tempolimit entfallen
sie. Berechnet wird in `dsd2csv.py`, die Annahmen stehen dort als Konstanten (`GEFAEHRDUNG`, `NACHT`).

## Zusatzrisiko je Stunde (Potenzmodell nach Nilsson)

Nach dem Potenzmodell (Nilsson, Universität Lund; später von Elvik u. a. aktualisiert) wächst die Unfallschwere mit
einer Potenz der Geschwindigkeit: mit der 2. Potenz bei Unfällen mit Personenschaden, mit der 3. bei Schwerverletzten
und mit der 4. bei Getöteten. Verwendet wird die 4. Potenz, und zwar nur für den Teil über dem Tempolimit:

```
zusatzrisiko_je_stunde = Summe über alle Fahrzeuge von max(0, (v / Tempolimit)^4 − 1)  ÷  Stunden
```

Das ist eine **Rate**, kein Mittelwert (Begründung und Grenzen in [raten.md](raten.md)): Fahrzeuge bis zum Tempolimit zählen 0,
und langsame Fahrzeuge gleichen die schnellen nicht aus. Ein Fahrzeug mit dem doppelten Tempolimit zählt 15. Es ist kein
Absolutrisiko und sagt nichts über Unfallzahlen. Streng genommen beschreibt das Potenzmodell, wie sich die *mittlere*
Geschwindigkeit auf die Unfallschwere auswirkt; hier wird es auf einzelne Fahrzeuge angewendet, eine Vereinfachung. Der frühere
Risikoindex (Mittel über alle Fahrzeuge) ist weggefallen.

## Aufprallgeschwindigkeit: Mit wie viel km/h träfe jedes Fahrzeug auf?

Anschaulicher als der Index. Das Szenario: Ein Kind tritt genau dort auf die Fahrbahn, wo ein Auto mit dem erlaubten
Tempo gerade noch zum Stehen kommt (Anhaltestrecke bei Tempolimit). Jedes gemessene Fahrzeug hat dieselbe Reaktionszeit
und dieselbe Bremsverzögerung. Ein schnelleres Fahrzeug hat die Reaktionsstrecke schon verbraucht, bevor der Bremsweg
beginnt, und trifft entsprechend schneller auf.

```
Anhaltestrecke bei Tempolimit  d = L·t + L² / (2a)
Reststrecke zum Bremsen        r = d − v·t
Aufprallgeschwindigkeit        v_auf = sqrt(v² − 2·a·r)   (0, wenn das Fahrzeug vorher steht; v, wenn r ≤ 0)
```

Angenommen werden eine Reaktionszeit von **t = 1,0 s** und eine Verzögerung von **a = 7,0 m/s²** (trockene Fahrbahn).
Ausgegeben wird, **mit wie viel km/h die gemessenen Fahrzeuge auftreffen**:

- `aufprall_mittel_der_aufprallenden_kmh`: mittlere Aufprallgeschwindigkeit nur der Fahrzeuge, die auftreffen.
- `aufprall_p95_kmh`, `aufprall_p99_kmh`: Aufprallgeschwindigkeit des Fahrzeugs an der V95 bzw. V99, also was die
  schnellsten 5 % bzw. 1 % mindestens erreichten.
- `anhaltestrecke_bei_limit_m`: die Strecke, bei der das Auto mit dem Tempolimit gerade noch hält.
- zusätzlich `aufprall_ueber_30_kmh_je_stunde` und `aufprall_ueber_50_kmh_je_stunde`: Fahrzeuge je Stunde, die mit mehr als 30
  bzw. 50 km/h auftreffen (Orientierungswerte ohne Aussage über bestimmte Verletzungen; Raten aus vollständig aufgezeichneten Stunden,
  [raten.md](raten.md)). Wie viele Fahrzeuge überhaupt noch auftreffen, steht nicht gesondert da: Im Szenario trifft auf, wer über dem
  Limit fährt, das ist `ueber_limit_je_stunde` im Block `raten`.

So rechnet das Modell, gerundet (gemessenes Tempo: Tempolimit plus ... km/h):

| Tempolimit | Anhaltestrecke | +5 km/h | +10 km/h | +15 km/h | +20 km/h | +30 km/h |
|---|---|---|---|---|---|---|
| 20 km/h | 7,8 m | 22 | 30 | 35 | 40 | 50 |
| 30 km/h | 13,3 m | 24 | 35 | 43 | 50 | 60 |
| 40 km/h | 19,9 m | 26 | 37 | 47 | 55 | 69 |
| 50 km/h | 27,7 m | 28 | 40 | 50 | 58 | 74 |

Die Zahlen in den Zellen sind die Aufprallgeschwindigkeit in km/h. Ein Fahrzeug, das in einer 30er-Zone mit 35 km/h
unterwegs ist, trifft also mit 24 km/h auf, eines mit 40 km/h mit 35 km/h. Ab einer Geschwindigkeit, bei der schon die
Reaktionsstrecke länger ist als die Anhaltestrecke bei Tempolimit (30er-Zone: ab 48 km/h), wird gar nicht mehr
gebremst, das Fahrzeug trifft mit seiner vollen Geschwindigkeit auf.

Grenzen:

- Gemessen wird am Display, nicht am Ort des Konflikts. Beschleunigung, Gefälle, Nässe, Reifenzustand, unterschiedliche
  Reaktionszeiten und das Ausweichen sind nicht berücksichtigt.
- Empfindlichkeit gegenüber den Annahmen (nachgerechnet für Reaktionszeiten von 0,5 bis 1,5 s und Verzögerungen von 5 bis
  8 m/s²): Bei 45 km/h in der 30er-Zone liegt die Aufprallgeschwindigkeit je nach Annahme zwischen 37 und 45 km/h, bei
  70 km/h in der 50er-Zone zwischen 53 und 64 km/h. Die Größenordnung bleibt, die einzelne Zahl nicht.
- Die Messung hat eine Toleranz von mindestens 3 km/h. Die Werte werden nicht um die Toleranz bereinigt.
- Die Geräte erfassen auch Radfahrende. Deren Fahrten zählen mit, ändern die Raten über dem Limit aber nicht.
- Wie schwer die Folgen eines Aufpralls sind, hängt von Person, Fahrzeug und Aufprallsituation ab. Die
  Aufprallgeschwindigkeit ist keine Aussage über Verletzungen.

## Lärm (grobe Schätzung)

Der Lärm einer Straße hängt von der Verkehrsmenge, dem Anteil an Lkw und Motorrädern, dem Belag, dem Abstand und vielem
mehr ab, das die Messdaten nicht enthalten. Geschätzt wird deshalb nur der Anteil, der von der **Geschwindigkeit** der
Pkw abhängt, und zwar **relativ zu einem Fahrzeug, das das Tempolimit fährt**. Absolute Pegel in dB(A) werden nicht
angegeben. Als Geschwindigkeitsterm dient der Pkw-Anteil aus der RLS-90:

```
L(v) = 27,7 + 10·lg(1 + (0,02·v)³)  in dB(A),   Δ(v) = L(v) − L(Tempolimit)
```

Beispielhafte Unterschiede zu einem Fahrzeug mit 50 km/h: 70 km/h +2,7 dB, 100 km/h +6,5 dB, 120 km/h +8,7 dB.

- **Spitzenpegel** (`spitzenpegel_p99_gegenueber_limit_db`): Δ des Fahrzeugs bei der V99, also wie viel lauter die
  schnellsten Fahrten gegenüber einem Fahrzeug mit Tempolimit vorbeifahren. Das ist der aussagekräftigere Wert, weil
  einzelne laute Fahrten stören. Dazu die Zahl der Vorbeifahrten je Stunde, die mindestens 3 dB bzw. 6 dB lauter sind
  (`mind_3_db_lauter_je_stunde`, `mind_6_db_lauter_je_stunde`). Sie wirken je Fahrzeug (Aufwachen, Erschrecken), deshalb zählt die
  Zahl, nicht der Anteil.
- Einen **Mittelungspegel** gibt es nicht mehr (energetisches Mittel aller Fahrzeuge): Er hängt von der Masse der Fahrzeuge ab, und
  Radfahrende (kaum Motorgeräusch) und langsame Fahrzeuge senken ihn, auch wenn viele zu schnell sind ([raten.md](raten.md)).

Orientierung: 3 dB bedeuten die doppelte Schallenergie, etwa 10 dB nimmt man als doppelt so laut wahr.
Grenzen: Die RLS-90 wurde durch die RLS-19 abgelöst, die die Geschwindigkeitsabhängigkeit etwas anders beschreibt.
Lkw, Motorräder, Beschleunigung, Fahrbahnbelag und Abstand fehlen. Für Lärmgutachten ist das nicht geeignet.

## Ereignisse pro Nacht

Zählt, wie oft nachts ein Fahrzeug mit sehr hohem Tempo fährt. Eine Aussage wie „in 71 von 154 Nächten mindestens ein
Fahrzeug ab 100 km/h“ ist verständlicher als ein Perzentil.

- **Nacht:** 22:00 bis 06:00 Uhr Ortszeit. Die Nacht gehört zum Abend, an dem sie beginnt.
- **Gezählt werden nur vollständig aufgezeichnete Nächte** (Beginn und Ende innerhalb eines Abschnitts mit nutzbarer
  Zeit). Fiel das Gerät in einer Nacht aus, zählt sie als Nacht ohne Ereignis; der Anteil der Nächte ist dann eher zu
  niedrig.
- **Schwellen:** das doppelte Tempolimit sowie 100 und 120 km/h. Bei 50 km/h fallen doppeltes Tempo und 100 km/h
  zusammen.
- Je Schwelle: Nächte mit mindestens einer Fahrt, deren Anteil an allen Nächten, die Gesamtzahl der Fahrten und die
  Fahrten je Nacht.

Grenzen: Die Uhrzeit ist nur auf etwa eine Stunde belegt ([uhr-bewertung.md](uhr-bewertung.md)); Fahrten nahe 22:00 und
06:00 können der falschen Nacht zugeordnet sein. Einzelne sehr hohe Werte sind vermutlich Messfehler des Radarsensors
([dsd-format.md](dsd-format.md)); Schwellen von 100 und 120 km/h sind davon weniger betroffen als Spitzenwerte über
150 km/h. Ob ein Fahrzeug tatsächlich so schnell fuhr, lässt sich aus den Daten nicht belegen.

## Beispiel: Düsseldorfer Straße (Tempo 50, 26.10.2025 bis 29.03.2026)

Aus `106_Düsseldorfer Straße/DSD17400 Tempo50_2.yaml` (ganze Messung): Zusatzrisiko 32,2 je Stunde. Im beschriebenen Szenario kämen
21,4 Fahrzeuge je Stunde (über Limit plus Toleranz) nicht mehr rechtzeitig zum Stehen; sie träfen im Mittel mit 34 km/h auf.
Das Fahrzeug an der V95 träfe mit 52 km/h auf, das an der V99 mit 69 km/h. Das schnellste Prozent fährt
etwa 3,7 dB lauter als ein Fahrzeug mit 50 km/h vorbei. In 71 von 154 Nächten (46 %) fuhr mindestens ein Fahrzeug mit
100 km/h oder mehr, in 23 Nächten (15 %) eines mit 120 km/h oder mehr; im Schnitt sind es 0,84 Fahrten ab 100 km/h je
Nacht. Die Uhr dieser Messung ist nur „eingeschränkt“ belegt, die Tageszeiten sind also unsicher.

## Reproduktion

```sh
python3 -I dsd2csv.py .          # schreibt die Blöcke gefaehrdung, laerm und nacht_ereignisse in jede YAML
python3 -m unittest -v           # Tests (test_dsd2csv.py: Gefaehrdung, Laerm, NachtEreignisse)
```
