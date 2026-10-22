# Rauschboden

> Eigene Einschätzung nach festen Regeln, nicht amtlich. Fehler im Verfahren und in der Auswertung können nicht
> ausgeschlossen werden (ohne Gewähr).

Die Geräte zeichnen auch sehr langsame Messwerte auf, die kaum von Fahrzeugen stammen dürften: Fußgänger, Tiere, Echos,
Störungen. Was es ist, sagen die Daten nicht. Statt einer festen Mindestgeschwindigkeit schätzt `rauschen.py` für jede
Datei, welcher Teil der Messwerte **nicht vom Verkehr abhängt**, und rechnet ihn aus allen Kennzahlen heraus. Die CSV-Dateien
bleiben vollständig. Es gibt zwei Teile: den **trockenen Rauschboden** (gleichmäßig über den Tag) und den **Regenanteil**
(zusätzliche langsame Datensätze, die Regen im Radar erzeugt, [wetter.md](wetter.md)).

## Warum keine Mindestgeschwindigkeit

Früher nahmen wir Werte unter 5 km/h heraus (`--min-kmh`). Das war eine Annahme („kein Fahrzeug im Sinne der StVO bewegt sich
regelmäßig so langsam“). Die Daten tragen mehr: Bei vielen Messstellen fällt die Zahl der Fahrten nachts auf 3 bis 20 % der
Tagesrate, bei den sehr langsamen Werten aber nicht. In der Föhrenstraße liegt das Verhältnis Nacht zu Tag bei 0,5 bis 0,7
bis etwa 8 km/h und fällt erst bei 9 bis 12 km/h auf das Niveau des Verkehrs (etwa 0,03 bis 0,1). Nachts zwischen 0 und 5 Uhr
bestehen dort 45 % der aufgezeichneten „Fahrzeuge“ aus Werten unter 10 km/h. Die Grenze liegt je Messstelle verschieden, und
bei Geräten, die erst ab 9 oder 10 km/h erfassen, ist nur der Auslauf sichtbar.

## Modell

Je Zelle aus **Tagtyp** (Werktag, Samstag, Sonn- und Feiertag in NRW) und **Stunde** gilt für die Fahrten je Stunde mit der
Geschwindigkeit v

    y(v, Zelle) = a(v) + b(v) · Verkehr(Zelle)

- `Verkehr(Zelle)` sind die Fahrten je Stunde ab der Verkehrsschwelle (70 % des Tempolimits, mindestens 15 km/h).
- `a(v)` ist die **verkehrsunabhängige** Rate, der Rauschboden. `b(v)` ist der Teil, der mit dem Verkehr geht. Zu `b(v)`
  gehören auch die echten langsamen Fahrer (Radfahrer, Abbieger …): Sie nehmen nachts im selben Maß ab wie der Verkehr.
- Es zählt nur der Zeitverlauf, keine Annahme über die Form der Verteilung. Die Schätzung nutzt gewichtete kleinste Quadrate
  mit Poisson-Gewichten und einem Ausgleich für Überstreuung; `a` und `b` sind nicht negativ.
- `a(v)` zählt nur, wenn es mindestens **3 Standardfehler** über 0 liegt (`SIGMA`).
- Geschätzt wird nur unterhalb der Verkehrsschwelle und nur aus Zeiten mit nutzbarer Uhr und aus Stunden, die ein Abschnitt
  vollständig abdeckt. Zellen mit weniger als 3 Tagen bleiben draußen.
- Mit Wetterdaten (`belege/wetter.json`) werden `a(v)` und `b(v)` **nur aus trockenen Stunden** geschätzt: Stunden mit Regen,
  im Vor- und Nachlauf des Regens (eine Stunde danach, drei davor) und ohne Wetterwert bleiben draußen. Vorher gingen die Regenstunden in
  den Mittelwert ein, und der angebliche „Rauschboden“ war bei 27 Dateien im Kern Regenstörung.

## Regenanteil

Regen erzeugt langsame Datensätze, die nicht von Fahrzeugen stammen und nicht gleichmäßig über den Tag verteilt sind. Wirkung, Zahlen
und Quelle der Wetterdaten: [wetter.md](wetter.md). Das Modell ergänzt für jede Regenklasse k einen **Regenanteil** c_k(v), der nicht vom
Verkehr abhängt:

    y(v, Zelle, Regenklasse k) = a(v) + b(v) · Verkehr(Zelle) + c_k(v)

- **Regenklassen** nach der Intensität der Stunde: Niederschlag der Stunde plus je die Hälfte der beiden Nachbarstunden (mm):
  Klasse 1 von 0,1 bis 0,5, Klasse 2 von 0,5 bis 2, Klasse 3 ab 2 mm. Sie erklärt die Schwankung der langsamen Datensätze etwas besser
  als der Niederschlag der Stunde allein (Anteil der erklärten Varianz 0,252 gegen 0,245; die Unterschiede zwischen den getesteten Definitionen
  sind klein). Trocken ist eine Stunde, wenn sie, ihre Nachbarn und die drei Stunden davor unter 0,1 mm haben. Stunden im Vor- und Nachlauf des
  Regens und ohne Wert („unklar“) gehen nicht in die Schätzung ein; von ihnen wird nur a(v) abgezogen.
- **Schätzung:** c_k(v) sind die Datensätze je Regenstunde, die in Stunden der Klasse k über a(v) + b(v) · Verkehr hinausgehen, mit dem Verkehr
  der Regenstunden. Es gilt nur dort, wo die Datensätze mindestens 1,5-mal so häufig sind wie ohne Regen erwartet (Fahrzeuge sind kleine
  Abweichungen vom Modell, das Störsignal ein Vielfaches), mindestens 1 Standardfehler über 0 liegen und einen **zusammenhängenden Lauf** von
  mindestens drei Geschwindigkeiten (Lücken bis 1 km/h) bilden, dessen Summe mindestens **3 Standardfehler** über 0 liegt. Je Geschwindigkeit
  sind die Zählwerte klein, über den Lauf nicht; einzelne Ausreißer bei vielen Tests (Klassen mal Geschwindigkeiten) sind Zufall. Klassen mit
  weniger als 12 Stunden übernehmen die Schätzung der nächsten Klasse. Anders als a(v) wird c_k(v) auch bei Geschwindigkeiten geschätzt, die
  bei Trockenheit nie vorkommen (der Regen erzeugt Werte bei 0 bis 6 km/h).
- **Belegt** (und abgezogen), wenn mindestens 12 Regenstunden vorliegen, ein Regenanteil nachweisbar ist, 95 % davon unter **15 km/h**
  liegen und er in beiden Hälften der Messtage auftritt (die eine Hälfte hat nicht unter einem Fünftel der anderen). Lockerer als beim
  trockenen Rauschboden, weil die Stärke der Störung von der tatsächlichen Regenmenge innerhalb einer Klasse abhängt und die Hälften der Tage
  zufällig unterschiedlich viel starken Regen enthalten (Klasse 3 reicht von 2 mm bis weit darüber): Mit der strengeren Prüfung (Unterschied
  höchstens die Hälfte des größeren Werts, wie beim trockenen Rauschboden) fielen 18 Dateien durch, bei mehreren davon war das Tempo in
  Regenstunden um 5 bis 18 km/h verzerrt.
- Bei den jetzigen Dateien: Regenanteil **belegt bei 64** von 99 geprüften Dateien (bei 13 davon auch der trockene Rauschboden), bei 22 nicht
  nachweisbar, bei 11 mit Obergrenze über 15 km/h (bis 34 km/h, nicht von langsamem Verkehr zu trennen), bei 2 nicht stabil.

## Wann der Abzug gilt

Eine Datei braucht mindestens 3000 Fahrzeuge mit nutzbarer Zeit und ein bekanntes Tempolimit. Der Rauschboden gilt als **belegt**
und wird abgezogen, wenn

1. a(v) überhaupt nachweisbar ist,
2. 95 % der Rauschmasse unter **15 km/h** liegen (reicht das „Rauschen“ weiter, ist es nicht von langsamem Verkehr zu trennen),
3. der Anteil in den Hälften der Messtage (gerade und ungerade Tage) **stabil** ist: Unterschied höchstens 1,5 Prozentpunkte
   oder höchstens die Hälfte des größeren Werts.

Sonst steht in der YAML unter `rauschen.grund`, warum nicht, und es wird **nichts** herausgerechnet. Bei den jetzigen Dateien (trockener
Rauschboden, mit Wetterdaten geschätzt): 14 belegt, 78 ohne nachweisbaren Rauschboden, 2 nicht stabil, 5 mit Obergrenze über 15 km/h, 10 zu klein.
Ohne Wetterdaten waren es 41 belegt, 34 ohne nachweisbaren Rauschboden, 17 nicht stabil, 7 mit Obergrenze über 15 km/h, 10 zu klein: Bei den
meisten der 41 war ein Teil davon Regen.

## Abzug

**Je Abschnitt bzw. Einsatz-Abschnitt** (seit 22.10.2026, [einsaetze.md](einsaetze.md)): Der Rauschboden hängt vom Ort ab (Bäume, Gebäude,
Echos). Er wird deshalb nicht mehr für eine ganze Datei geschätzt, die Daten mehrerer Orte enthalten kann, sondern für die Ansicht „Messung“ je
Abschnitt und für die Einsätze je Einsatz-Abschnitt, mit der Wetterstation des Einsatzstandorts.

Jedes Fahrzeug zählt anteilig als Rauschen: Die erwartete Zahl je Zelle und km/h ist `a(v) · Stunden`, höchstens die dort
gemessene Zahl (nachts liegt die Rate des Rauschens oft unter dem Mittel). Entfernt werden ganze Fahrzeuge, gleichmäßig
über die Zeit verteilt, Rundungsreste laufen in die nächste Zelle. So bleibt jede weitere Auswertung (V85, Einhaltung,
Gefährdung, Lärm, Nächte, Histogramme) unverändert aufgebaut. Für Fahrten ohne nutzbare Uhr (Gesamtwerte) gilt derselbe Anteil
je Geschwindigkeit, aber nur für den trockenen Rauschboden: Ohne Uhrzeit ist nicht bekannt, ob es regnete, die Gesamtwerte aller
Fahrzeuge enthalten das Regenrauschen deshalb weiter.

Der **Regenanteil** wird dagegen nicht je Zelle abgezogen, sondern **je Regenklasse und Geschwindigkeit über alle Zellen der Klasse**:
erwartet `c_k(v) · Stunden der Klasse` (in den Zellen, die in den betrachteten Fahrten vorkommen). Ein Abzug je Zelle (Tagesart mal Stunde)
mit dem Klassenmittel ließ 26 % des Überschusses stehen: Wo die Störung unter dem Klassenmittel liegt, wird gekappt (es kann nicht mehr entfernt
werden, als da ist), wo sie darüber liegt, bleibt Rest. Mit dem Abzug je Klasse stimmen geschätzter und tatsächlich entfernter Anteil überein
(533 513 entfernt gegen 529 666 geschätzt und 538 456 beobachteten Überschuss, 60 Dateien).

In der YAML steht unter `rauschen`: `belegt`, `abgezogen_fahrzeuge`, `anteil_prozent` (Schätzung des Modells),
`abgezogen_anteil_prozent` (tatsächlich entfernt), `mittel_kmh`, `obergrenze_kmh` (95 %), `stabil`, die Anteile der Hälften
und `spektrum` (Fahrten je 1000 Stunden: `rausch` und `alle`), dazu unter `regen`: `belegt`, `regenstunden`, `stunden_je_klasse`,
`zusatz_je_regenstunde` (Datensätze je Regenstunde, die zusätzlich auftreten), `zusatz_je_klasse`, `mittel_kmh`, `obergrenze_kmh`, `stabil`,
`grund` (wenn nicht belegt) und `abgezogen_fahrzeuge`. `fahrzeuge_in_datei` ist die Zahl vor dem Abzug,
`anzahl_fahrzeuge` danach. Die Detailseiten zeigen das Spektrum und den Regenanteil.

**Wirkung** (Regenstunden gegen trockene Stunden, gleiche Tagesart, Tageszeit und gleicher Monat, 91 Dateien): Der Tempo-Unterschied der
bereinigten Fahrzeuge sinkt im Median von −3,13 auf −0,24 km/h (nach Regentag: von −1,06 auf −0,29 km/h); bei den Fahrzeugen ab dem halben
Limit bleibt er bei 0 (−0,01 km/h), die Menge ab halbem Limit unverändert (0,965). Bei den Dateien mit belegtem Regenanteil sind die Verhältnisse
der Datensätze je Stunde (Regenstunde gegen trocken) nach dem Abzug bei 0 bis 12 km/h bei 0,8 bis 1,1 (vorher bis 24-fach). Bei den
Dateien ohne belegten Regenanteil (35 von 99) bleibt die Verzerrung: im Median klein (−0,03 km/h), bei etwa einem Drittel aber über 1 km/h.

## Grenzen

- Das Modell nimmt für den trockenen Rauschboden eine **konstante** Rate an. Nachts liegt sie oft niedriger. Der tatsächlich entfernte
  Anteil ist deshalb etwas kleiner als der geschätzte. Der Regen ist modelliert (Klassen nach der Stunde), Wind und Temperatur nicht. Der
  Regenanteil hängt nur von der Klasse ab, nicht von Stunde oder Tagesart; innerhalb einer Klasse streut die Stärke der Störung (bis zum
  Faktor 5 zwischen den Hälften der Tage), im Mittel stimmt die Menge.
- Der Regen kommt aus einer Station (Neuss seit August 2024, davor Düsseldorf, 12 km) und gilt für die Stunde, nicht für den Ort der Messstelle:
  In einer Neusser Regenstunde regnet es in Düsseldorf nur in 70 % der Fälle ([wetter.md](wetter.md)). Die Einteilung nach Regenstunden ist
  dadurch verrauscht, der Effekt eher unterschätzt.
- Der Regen erzeugt Datensätze bei 13 bis 20 km/h und mehr (bei 11 Dateien reicht der Regenanteil über 15 km/h): Sie sind von langsamem
  Verkehr nicht zu trennen und bleiben stehen.
- Jeder Stördatensatz sperrt das Gerät für einige Sekunden und kann Fahrzeuge verdecken: In Regenstunden bleibt die Verkehrsmenge unsicher,
  auch wenn die Störung herausgerechnet ist ([wetter.md](wetter.md)).
- Eine Ground Truth gibt es nicht. Überprüft ist nur, dass der Anteil nicht von der gewählten Verkehrsschwelle abhängt (Median
  der Änderung bei 50 % und 90 % statt 70 % des Limits: 0,03 Prozentpunkte) und dass er sich in Hälften der Messtage
  bei den meisten Dateien wiederholt.
- Der Abzug ist ein statistischer Anteil. Er sagt nicht, welches einzelne Fahrzeug Rauschen ist.
- Bei verkehrsberuhigten Bereichen (Tempolimit 10 km/h) und bei Geräten, die erst ab 9 oder 10 km/h erfassen, ist oft nichts
  nachweisbar. Dort bleibt alles in der Auswertung.
- Wie das Rauschen von echten langsamen Fahrern (Radfahrer, Abbieger, langsame Autos) und von der Hauptmenge zu trennen ist,
  ist ein eigener Schritt (Gruppenerkennung) und noch nicht Teil der Kennzahlen.

## Verteilung des Regenabzugs auf Stunden

Der Regenanteil c_k(v) sind Datensätze je Regenstunde der Klasse k und Geschwindigkeit v. Wie sie auf einzelne Stunden verteilt werden, ist
nicht festgelegt, und `dsd2csv.py` rechnet bisher zwei Wege: Die Kennzahlen der ganzen Datei, die Abschnitte, die Tage, die Auswahl auf den
Seiten und das Aggregat ([DATEN.md](../DATEN.md)) kommen aus dem Abzug für die **ganze Datei** (A). Die feste Zeitraumtabelle (Nacht,
Vormittag, Nachmittag, Abend) in YAML und noscript-Block dünnt jede Tageszeit-Liste **einzeln** aus (B). Ein dritter Weg (C) zieht
die c_k(v) je Regenstunde ab, weil das nahe am Modell liegt, wurde aber nicht übernommen. `tools/regen_abzug_vergleich.py` vergleicht
die drei an den 65 Dateien mit belegtem Regenanteil. Prüfmaß: Nach dem Abzug sollen die langsamen Fahrten je Stunde dem Erwartungswert
des Modells folgen (b(v) mal Verkehr), in Regenstunden so gut wie in trockenen.

| | Abgezogen gegen Modell | Mittlere Abweichung je Regenstunde | Streuung Regen zu trocken |
| --- | --- | --- | --- |
| A ganze Datei | 1,00 | +0,01 | 1,23 |
| B je Zeitraum | 0,92 | +0,99 | 1,77 |
| C je Regenstunde | 0,56 | +4,77 | 3,39 |

(Mediane über 65 Dateien; A hat in 64 von 65 Dateien die kleinere Streuung als B, in allen 65 als C.)

- **C scheitert**, weil die Störungen in Schüben kommen: Einzelne Regenstunden haben viel mehr Datensätze, als der Durchschnitt c erwarten lässt.
  Ein fester Abzug je Stunde lässt dort viel stehen und kann in ruhigen Stunden nicht alles abziehen (56 % der Rechnung).
- **A trifft die Stunden am besten**, weil er die Fahrten nach ihrer Häufigkeit in der Gruppe (Klasse, Geschwindigkeit) entfernt, also
  dort, wo die Störungen sind.
- **B weicht ab:** Er zieht in Regenstunden zu wenig ab (92 % der Rechnung, Rest +1 Datensatz je Regenstunde) und verteilt auf die
  Tageszeiten anders. Folge: Die Fahrzeugzahl der Zeiträume weicht von der Auswahl und vom Aggregat ab (Nacht im Median 2,3 %, bis 68 %;
  V85 in 21 von 65 Dateien, bis 5 km/h).
- Konsequenz (umgesetzt, Oktober 2026): Die Zeiträume werden aus der bereinigten Liste für die ganze Datei abgeleitet (`dsd2csv.py`,
  `rechnen`). Seitdem stimmen Zeitraumtabelle, Auswahl, Tage, Abschnitte und Aggregat überein (alle 424 Zeiträume der 109 Messungen exakt,
  `test_aggregat.py`). Die Zeitraumzahlen bei Dateien mit Regenanteil haben sich dadurch geändert: Die Tabelle oben und die Zahlen zu B gelten für den Stand davor.

## Reproduktion

```sh
python3 -I dsd2csv.py .          # rauschen.py wird eingebunden; Ergebnis steht unter "rauschen" in jeder YAML
python3 -m unittest -v test_rauschen
python3 -I tools/regen_abzug_vergleich.py   # Verteilung des Regenabzugs auf Stunden (braucht _vorschau/auswertung.json von lokal_bauen.py)
```

Alle Schwellen stehen oben in `rauschen.py` (`SIGMA`, `MIN_TAGE`, `MIN_FAHRZEUGE`, `OBERGRENZE_KMH`, `INSTABIL_PP`, `INSTABIL_REL`, für den
Regen `REGEN_KLASSEN`, `MIN_REGENSTUNDEN`, `REGEN_REL`, `REGEN_LAUF`, `REGEN_EINZEL_SIGMA`, `INSTABIL_REGEN`, `INSTABIL_REGEN_REL`).
