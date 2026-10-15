# Raten statt Anteile: Wie viele zu schnelle Fahrzeuge pro Stunde?

> Eigene Einschätzung nach festen Regeln, nicht amtlich. Fehler im Verfahren und in der Auswertung können nicht
> ausgeschlossen werden (ohne Gewähr).

V85, Durchschnitt und Einhaltungsquote (die Kennzahlen der Verwaltung) sind **Anteile oder Lagewerte je Fahrzeug**. Sie
beantworten: „Wie fährt ein typischer Fahrer hier?“ Das ist die richtige Frage, um Verhalten zu vergleichen oder zu prüfen, ob
ein Display wirkt. Sie beantwortet aber nicht, **wie viel zusätzliche Gefahr oder Belastung jemanden trifft, der sich an der
Straße aufhält** (zu Fuß, mit dem Rad, im Auto, in der Wohnung). Dafür sind sie ungeeignet, weil sie schnelle Fahrzeuge durch
langsame ausgleichen lassen: 10 Raser unter 100 Fahrzeugen sind 10 %, 10 Raser unter 1000 Fahrzeugen 1 %, und die zweite Straße
sieht „besser“ aus, obwohl dort genauso viele zu schnell fahren.

## Der Gedanke

Wer an der Straße ist, setzt sich dem Risiko und der Belastung (Lärm, Abgase) durch Fahrzeuge aus. Jedes Fahrzeug trägt dazu
bei. Als hinzunehmend gilt aber, was mit genau dem erlaubten Tempo fährt; das Maß, um das der eigene Nachteil darüber hinaus
wächst, entsteht allein durch Fahrzeuge, die **schneller als erlaubt** sind. Diese wirken **absolut** (je Zeit), nicht relativ
zur Menge der übrigen Fahrzeuge. Wer eine Stunde an einer Straße steht, begegnet eben den Rasern dieser Stunde, nicht dem
Anteil.

Das sind **Raten je Stunde**: Fahrzeuge über dem Limit und das Zusatzrisiko.

## Die Kennzahlen (Block `raten`, Spalten in `kennzahlen.csv`)

Gezählt werden nur Fahrzeuge aus **vollständig aufgezeichneten Stunden** (gleiche Menge wie die Zellen der Detailseiten).
Stunden ohne Fahrzeug zählen mit, Lücken in der Aufzeichnung nicht.

| Feld | Bedeutung |
|---|---|
| `stunden` | vollständig aufgezeichnete Stunden der Auswahl |
| `fahrzeuge_je_stunde` | Fahrzeuge je Stunde (Fahrzeuge ÷ Stunden) |
| `ueber_limit_je_stunde` | Fahrzeuge über dem Tempolimit je Stunde |
| `ueber_limit_plus_toleranz_je_stunde` | Fahrzeuge über Limit plus Messtoleranz (3 km/h, ab 100 km/h 3 %) je Stunde; die vorsichtigere Zahl |
| `zusatzrisiko_je_stunde` | Summe von max(0, (v / Tempolimit)⁴ − 1) über alle Fahrzeuge, geteilt durch die Stunden |

**Alle Raten gelten je Stunde der Auswahl.** Das ist für Teilzeiträume (Nacht, Abend, Schulweg) unmittelbar vergleichbar, weil jede
Auswahl auf dieselbe Einheit bezogen ist: Wer in der Nacht eine Stunde an der Straße steht, begegnet so vielen zu schnellen Fahrzeugen,
wie die Nachtzeile angibt, und am Abend so vielen, wie die Abendzeile angibt. Eine Zahl je Tag ließe sich nicht vergleichen, weil sie vom
Zeitfenster abhängt (acht Nachtstunden gegen drei Abendstunden). Für eine Tagesrate ganztägig genügt die Multiplikation mit 24.

**Zusatzrisiko:** Nach dem Potenzmodell von Nilsson wächst die Unfallschwere (Getötete) mit der 4. Potenz der Geschwindigkeit.
Ein Fahrzeug mit dem Tempolimit zählt 0 (hinzunehmendes Maß), eines mit 40 km/h bei Tempo 30 zählt 2,2, eines mit 50 km/h
bei Tempo 30 6,7, eines mit dem doppelten Limit 15. Gelesen: Ein Zusatzrisiko von 15 je Stunde ist so viel Mehrgefahr, wie ein Fahrzeug
mit dem doppelten Tempolimit in dieser Stunde brächte; 30 wäre das Doppelte davon. Das Potenzmodell beschreibt streng genommen die
mittlere Geschwindigkeit; es hier auf einzelne Fahrzeuge anzuwenden, ist eine Vereinfachung.

**Aufprall** (`gefaehrdung`): Fahrzeuge je Stunde, die im Szenario mit mehr als 30 bzw. 50 km/h auftreffen
(`aufprall_ueber_30_kmh_je_stunde`, `aufprall_ueber_50_kmh_je_stunde`); Beschreibung des Szenarios in [gefaehrdung.md](gefaehrdung.md).
Die Zahl der Fahrzeuge, die überhaupt noch auftreffen, gibt es nicht gesondert: Im Szenario trifft auf, wer über dem Limit fährt, das ist
`ueber_limit_je_stunde`. **Lärm** (`laerm`): Vorbeifahrten je Stunde, die mindestens 3 bzw. 6 dB lauter sind als ein Fahrzeug mit dem
Tempolimit (`mind_3_db_lauter_je_stunde`, `mind_6_db_lauter_je_stunde`).

## Was weggefallen ist und warum

Die früheren Kennzahlen teilten durch die Fahrzeugzahl und hatten den beschriebenen Fehler doppelt: Fahrzeuge unter dem Limit
senkten den Wert.

- **Risikoindex** (Mittel von (v / Limit)⁴ über alle Fahrzeuge): ersetzt durch das Zusatzrisiko je Stunde.
- **Anteil der Fahrzeuge, die auftreffen**, **mittlere Aufprallgeschwindigkeit über alle Fahrzeuge**, **Anteile über 30 und 50
  km/h**: ersetzt durch Fahrzeuge je Stunde. Geblieben sind Kennwerte, die die schnellen Fahrzeuge selbst beschreiben (mittlerer
  Aufprall der Auftreffenden, Aufprall bei V95 und V99).
- **Mittelungspegel** (energetisches Mittel aller Fahrzeuge): ersatzlos weggefallen. Eine absolute Summe wäre kein guter Lärmwert,
  weil sich der Dauerpegel mit der Masse der Fahrzeuge ändert; der **Zusatzpegel** durch Überschreitungen (Schallenergie aller Fahrzeuge gegenüber der mit auf das Limit gekappten schnellen Fahrzeugen)
  liegt im Median bei nur 0,23 dB (höchstens 1,38 dB über 95 Messungen,
  `tools/absolut_vergleich.py`), und würde die Belastung durch einzelne schnelle Fahrten kleinreden. Für einzelne laute Vorbeifahrten
  (Aufwachen, Erschrecken) zählt die Zahl je Stunde.
- Geblieben sind V85, Durchschnitt, V95, V99 und Einhaltung als Beschreibung des Fahrverhaltens und für den Vergleich mit der
  Verwaltung.

## Wie stark ändert das die Reihenfolge?

`tools/absolut_vergleich.py` vergleicht je Messung (95 Messungen mit mindestens 14 Tagen und 2.000 Fahrzeugen in vollständig
aufgezeichneten Stunden). Die Rangfolge ändert sich im Großen und Ganzen wenig: Rangkorrelation (Spearman) zwischen V85 über Limit
und Zusatzrisiko je Stunde 0,88, zwischen Einhaltung und Zusatzrisiko 0,91, zwischen V85 über Limit und Überschreitungen je Stunde 0,81.
Einzelne Messungen verschieben sich um 30 bis 35 Ränge von 95: Am Reckberg (Tempo 50) steht beim V85 über Limit auf Rang 4
(+14), beim Zusatzrisiko je Stunde auf Rang 38, weil dort nur 772 Fahrzeuge am Tag fahren; am Berghäuschensweg (Tempo 50) geht es von
Rang 63 (V85 +2) auf Rang 30, weil dort 2.300 Fahrzeuge am Tag fahren und 254 zu schnell sind.

## Grenzen

- **Verkehrsmenge zählt mit.** Eine Hauptstraße mit guter Einhaltung kann vor einer Wohnstraße mit schlechter Einhaltung stehen.
  Das ist gewollt, die Raten messen, wo die meiste Überschreitung stattfindet, nicht, wo die Fahrer am schlechtesten fahren. Beides
  gehört zusammen: die Übersicht zeigt „Zu schnell pro Stunde“ neben V85 und Einhaltung.
- **Die Vollständigkeit der Zählung geht direkt ein.** Bei Anteilen kürzen sich verpasste Fahrzeuge weitgehend heraus, bei Raten nicht.
  Die Geräte verpassen etwa 3 % der Fahrzeuge (Gerätesperre, [totzeit.md](totzeit.md)), bei Regen mehr. Die Raten sind also
  Untergrenzen; wo bei Regen mehr Fahrzeuge fehlen, liegt die Rate dort am stärksten darunter (Auswahl „nur trockene Stunden“
  auf den Detailseiten).
- **Eine Fahrtrichtung oder beide?** Messungen mit nur einer Fahrtrichtung unterschätzen die Rate an der Straße. Ob beide Richtungen
  erfasst sind, ist bei vielen Dateien nicht belegt (`beidseitige_messung` in `messungen.csv`).
- **Tageszeit:** Die Rate über alle Stunden mischt Nacht und Tag. Für Anwohner zählt die Nacht, für den Schulweg 7–8 Uhr; beide Zeitfenster
  stehen einzeln in `kennzahlen.csv` und auf den Detailseiten.
- **Wie viele Menschen sich dort aufhalten, weiß niemand.** Die Rate gilt für eine Person, die da ist, nicht für die Straße insgesamt.
- **Die Stundenzahl ist die der vollständig aufgezeichneten Stunden.** Bei Dateien mit viel Ausfall ist sie klein, die Rate bleibt gültig,
  aber unsicherer.
- **Messtoleranz:** `ueber_limit_je_stunde` zählt jede Überschreitung, `ueber_limit_plus_toleranz_je_stunde` nur die mit Sicherheitsabstand;
  die Übersicht zeigt die vorsichtigere Zahl.

## Beispiel: Düsseldorfer Straße (Tempo 50)

Aus `106_Düsseldorfer Straße/DSD17400 Tempo50_2.yaml`, ganze Messung (Zeiträume und Abschnitte unterscheiden sich stark, siehe
[abschnitte.md](abschnitte.md)): 76,8 Fahrzeuge je Stunde, davon 21,4 über Limit plus Toleranz (28 %), Zusatzrisiko 32,2 je Stunde.
Je Stunde nachts (22–6 Uhr) sind es 52,3 Fahrzeuge, davon 17,5 zu schnell; abends (19–22 Uhr) 91,3 Fahrzeuge und 27,5 zu schnelle. Im
ersten Abschnitt der Datei (vor dem erkannten Bruch) waren es 0,4 Überschreitungen je Stunde bei 75,7 Fahrzeugen: Eine Zahl für die
ganze Datei bildet die Abschnitte also nicht ab.

## Reproduktion

```sh
python3 -I dsd2csv.py .                                  # schreibt den Block raten in jede YAML
python3 -I tools/absolut_vergleich.py _vorschau/daten   # Rangvergleich Anteile gegen Raten
```

Tests: `test_dsd2csv.py` (Gefaehrdung: Raten, Zusatzrisiko, Toleranz, vollständige Stunden), `test_seiten.py`.
