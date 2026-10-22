# Einsätze: Brüche erklären und Messungen neu abgrenzen

> Eigene Auswertung, nicht amtlich. Fehler im Verfahren und in der Auswertung können nicht ausgeschlossen werden (ohne Gewähr). Keine der
> Zuordnungen ist von der Verwaltung bestätigt, solange das nicht ausdrücklich dasteht.

## Worum es geht

Die Verwaltung liefert je Messung eine Datei: Standort, Fahrtrichtung, Zeitraum. In vielen Dateien gibt es einen **Bruch**
([abschnitte.md](abschnitte.md)): Ab einem Tag ändert sich der Verkehr dauerhaft. Ein Teil dieser Brüche hat eine einfache Ursache. Das Gerät
wurde ausgelesen (neue Datei, neuer Standort laut Verwaltung), hing aber noch einige Wochen am alten Ort und wurde erst später umgehängt. Dann
beschreibt der Abschnitt vor dem Bruch noch den alten Standort. Kopien alter Datensätze sind es nicht: Kein Abschnitt hat Stunden, die in einer
anderen Datei genauso vorkommen (Prüfung im Bericht, der zu diesem Verfahren geführt hat).

Darum unterscheidet die Auswertung:

| Begriff | Bedeutung |
|---|---|
| **Standort** | physischer Ort (dieselbe Straße, ungefähr derselbe Streckenabschnitt; eine Detailseite) |
| **Messung** | Datei der Verwaltung: Standort, Fahrtrichtung und Zeitraum, wie geliefert |
| **Abschnitt** | zeitlicher Bereich einer Messung mit ähnlichen Daten |
| **Bruch** | Grenze zwischen zwei Abschnitten (Tagesauflösung) |
| **Zusammengesetzter Abschnitt** | Abschnitte verschiedener Messungen desselben Geräts, unmittelbar nacheinander, die zusammengehören |
| **Einsatz** | der Zeitraum, in dem ein Gerät tatsächlich an einem Standort in eine Fahrtrichtung gemessen hat |

Meist ist ein Einsatz gleich einer Messung. Zu jeder Messung gibt es einen Einsatz am selben Standort, jeder Einsatz und jede Messung hat
mindestens einen Abschnitt, und jedes Fahrzeug liegt genau in einem Einsatz oder an einem ausgenommenen Umhängtag (`test_einsaetze.py`).

Die **Hauptauswertung folgt den Einsätzen** (Ansicht „Einsätze“ der Übersicht, erste Wahl auf den Detailseiten). Die **Sicht der Verwaltung**
(die Messungen, wie geliefert) bleibt vollständig erhalten. Mit ihr vergleichen wir die Mitteilungen.

## Ablauf der Auswertung

1. **Je Messung** (`dsd2csv.py`): Parsen, Uhr, dann die Brüche auf den unkorrigierten Fahrzeugen. Rauschboden und Regenanteil hängen vom Ort
   ab; ein Ortswechsel erzeugt aber auch ohne Korrektur einen Bruch, und die Bruchsuche zählt ohnehin erst ab der halben Höchstgeschwindigkeit.
   Für die Ansicht „Messung“ werden Rauschboden und Regenanteil danach **je Abschnitt** geschätzt und abgezogen (ein Bruch kann ein
   Ortswechsel sein), daraus Kennzahlen, Filter und Aggregat der Messung. Daneben entsteht ein **Rohaggregat** (Stunde × km/h vor jedem Abzug).
   Verhaltensgruppen gibt es je Messung nicht mehr.
2. **Zuordnung** (`einsaetze.py`): Brüche erklären und Einsätze bilden, aus dem Rohaggregat (ab 15 km/h, also unabhängig von den Abzügen).
3. **Je Einsatz** (`einsaetze.py`): Ein Einsatz wird an den Brüchen geteilt, die in ihm bleiben (unerklärt, Ferien); Teile, die über eine
   Dateigrenze aneinanderstoßen, gehören laut Zuordnung zum selben Ort und bleiben zusammen. Je **Einsatz-Abschnitt** werden Rauschboden und
   Regenanteil neu geschätzt, mit der Wetterstation des Einsatzstandorts. Ist der Einsatz gleich der Messung, ist das dieselbe Schätzung wie in
   Schritt 1 (zum Vergleich steht sie dabei). Dann Kennzahlen, Gefährdung, Lärm, Nächte, Zellen der Auswahl (mit Rauschboden) und die
   **Verhaltensgruppen je Einsatz-Abschnitt**; Zwischenspeicher je Einsatz (Ebene „einsatz“).
4. `stadtgruppen.py` bildet Standort- und Stadtgruppen aus den Gruppen der Einsätze; `daten_bauen.py` schreibt die Stundendaten beider Sichten
   (`stunden.csv.gz` je Messung, `einsaetze-stunden.csv.gz` je Einsatz).

Wie stark der Abzug je Abschnitt die Messungen verändert (`tools/abzug_je_abschnitt.py`, 34 Messungen mit mehreren Abschnitten): Die V85 ändert
sich in 2 Messungen (Konradstraße −7 km/h, Schluchenhausstraße −1 km/h), die Einhaltung im Median um +0,01 Prozentpunkte, höchstens um 7,1. Bei der
Konradstraße war ein großer Rauschboden für die ganze Datei belegt, je Abschnitt in einem Abschnitt nicht mehr; dort bleiben rund 7.400 langsame
Fahrten mehr in den Kennzahlen.

## Zuordnung eines Bruchs

In dieser Rangfolge:

1. **Angabe der Verwaltung** (`belege/brueche-verwaltung.json`): bestätigt. Sie hat Vorrang. Bei einem bestätigten Umhängen gelten die
   bestätigten Tage.
2. **Umhängen, belegt:** Der Abschnitt vor dem Bruch gleicht dem letzten Abschnitt der vorigen Messung desselben Geräts an einem anderen
   Standort. Spiegelbildlich ist auch möglich, dass der Abschnitt nach dem letzten Bruch dem ersten Abschnitt der folgenden Messung gleicht.
   Alle Kriterien unten müssen erfüllt sein.
3. **Ereignis, plausibel:** Der Bruch liegt auf dem ersten Schultag nach Ferien oder dem ersten Ferientag (±1 Tag, `kalender.py`) oder auf
   Beginn oder Ende eines länger dauernden Ereignisses (`belege/ereignisse.json`). Kurze Ereignisse wie das Schützenfest werden nur als
   zeitliche Nähe genannt: Ein Bruch braucht auf beiden Seiten mindestens 7 Tage. Ein Fest von fünf Tagen erklärt ihn nicht.
4. **Umhängen, möglich:** schwächere Kriterien. Auch sie bilden einen Einsatz, gekennzeichnet als „unsicher“.
5. **Unerklärt:** Diese Brüche sind Fragen an die Verwaltung.

Belegte, mögliche und bestätigte Zuordnungen verändern die Einsätze, jeweils nur zwischen unmittelbar aufeinanderfolgenden Messungen desselben
Geräts. Der Bruchtag und der Tag davor gehören dann zu keinem Einsatz, denn dort wurde umgehängt, transportiert und montiert. Die Kennzeichnung
lautet „abgeleitet, nicht bestätigt“ (belegt), „unsicher“ (möglich) oder „bestätigt“ (Angabe der Verwaltung).

### Kriterien für „Umhängen, belegt“ (`einsaetze.py`)

Grundlage ist das Rohaggregat (vor Rauschboden- und Regenabzug, vollständig aufgezeichnete Stunden, 15 bis 99 km/h).

- **Score ≤ 1,15:** Die Geschwindigkeitsverteilung und der Tagesgang (Stunde × Werktag/Wochenende) beider Abschnitte unterscheiden sich kaum
  mehr als die geraden von den ungeraden Tagen desselben Abschnitts.
  - Score = Mittel aus totaler Variation der Verteilungen / Rauschen und totaler Variation der Tagesgänge / Rauschen.
  - Rauschen ist das größere beider Abschnitte, mindestens 0,015 bzw. 0,02.
- **Fahrzeuge je Stunde** im Verhältnis 0,7 bis 1,4.
- **Nulltest, p ≤ 0,05:** Kaum ein Abschnitt eines anderen Standorts mit gleichem Tempolimit gleicht dem Vergleichsabschnitt so gut
  (p = (1 + Treffer) / (1 + Vergleichsabschnitte); bei weniger als 20 mit gleichem Limit alle Limits). Bei rund 85 Vergleichsabschnitten ist
  p = 0,012 der kleinstmögliche Wert („keiner ähnlicher“).
- **Gegenprobe > 3:** Der Abschnitt auf der anderen Seite des Bruchs gleicht dem Vergleichsabschnitt nicht.
- **Bruch sicher:** Wahrscheinlichkeit ≥ 0,9.
- **Naht stetig:** Die letzten 7 Tage der vorigen Messung und die ersten 7 Tage des Abschnitts passen zusammen (Score ≤ 2 am Rauschen der
  Fenster, Fahrzeuge je Stunde 0,7 bis 1,4). Am Auslesetag selbst hat sich dann nichts geändert.
- **Möglich:** Score ≤ 1,5, Verhältnis passt, p ≤ 0,10.
- **Richtung:** Taucht dasselbe Abschnittspaar in beiden Richtungen auf, zeigt es nur, dass beide zusammengehören. Die Lesart „das Gerät hing
  nach dem Auslesen noch am alten Ort“ hat dann Vorrang, die Gegenlesung wird „zurückgestellt“. Beispiel: Abschnitt 2 der Einsteinstraße
  gleicht Abschnitt 1 der Rosmarinstraße. Nach der Vorgänger-Lesart gehört Abschnitt 1 der Rosmarinstraße zur Einsteinstraße.

Alle Schwellen sind Festlegungen, kein Befund. Sie stehen als Konstanten in `einsaetze.py`.

## Ergebnis (Stand Oktober 2026)

Von 34 Brüchen sind:

- **9 Umhängen, belegt:**
  - Quinheimer Straße (19.04.2024);
  - Einsteinstraße, Steinhausstraße, Martinusstraße (alle 04.09.2024);
  - Rosmarinstraße (13.12.2024);
  - Düsseldorfer Straße, Ruhrstraße (beide 28.11.2025);
  - Weckhovener Straße (02.12.2025);
  - Martinstraße (21.04.2026).

  Daraus entstehen 9 zusammengesetzte Einsätze, etwa Daimlerstraße bis 02.09.2024 statt bis zum Auslesen am 24.07.2024.
  Die Einsteinstraße gibt Abschnitt 1 an die Daimlerstraße ab und bekommt Abschnitt 1 der Rosmarinstraße.
- **3 Umhängen, möglich:**
  - Konrad-Adenauer-Ring 14.05.2023;
  - Matthiasstraße 19.12.2023;
  - Hoistener Schulstraße 13.09.2024. Hier gleicht Abschnitt 1 der Nordkanalallee, aber an der Naht ändert sich der Anteil der Fahrten unter
    15 km/h stark (am Ende der Nordkanalallee etwa die Hälfte, danach kaum noch). Am Auslesetag hat sich also etwas geändert.

  Auch sie bilden Einsätze, gekennzeichnet als „unsicher“. Insgesamt: 9 Einsätze abgeleitet, 3 unsicher, 11 gekürzt, 86 gleich der Messung.
- **7 Ereignis, plausibel:** fünf Brüche am 27.04.2025 (erster Schultag nach den Osterferien: Pomona, Viersener Straße, Krokusstraße,
  Am Reckberg, Föhrenstraße) und zwei am 27.08.2025 (nach den Sommerferien: Preußenstraße, Münchener Straße). Ein Umhängen zeigt sich dort nicht.
  Die Bruchsuche lässt Ferientage aus; ein Bruch am ersten Schultag heißt also, dass sich der Verkehr über die Ferien geändert hat (neues
  Schuljahr, Baustelle in den Ferien oder Umhängen in den Ferien an einen Ort, der keiner vorigen Messung gleicht). Dass fünf Geräte am selben
  Tag brechen, spricht eher für eine Umhängaktion in den Osterferien. Die Erklärung „Ferien“ ist deshalb nur plausibel, nicht belegt.
- **15 unerklärt.** Darunter sind zwei Paare am selben Tag: Holzheimer Weg und Alte Uferstraße am 13.05.2023, Holzbüttgener Straße und
  Nierenhofstraße am 08.09.2023. Das spricht ebenfalls für Umhängaktionen, aber ohne passende vorige Messung (dort hatten mehrere Geräte keine
  nutzbare Uhr).

Die Liste mit allen Belegen steht auf der Seite „Brüche“ (`brueche.html`) und in `daten/brueche.csv`.

## Grenzen und Gegenhypothesen

- **Ähnlichkeit ist kein Beweis.** Straßen gleichen Typs und Limits sehen sich ähnlich. Der Nulltest vergleicht deshalb mit allen Abschnitten
  gleichen Limits, nicht mit Zufallspaaren. Eine Baustelle oder Sperrung mitten im Einsatz am selben Ort wäre eine andere Erklärung für einen
  Bruch. Dann aber gliche der Abschnitt davor nicht so genau dem Ende der vorigen Messung an einem anderen Ort.
- **Nur unmittelbar aufeinander folgende Messungen desselben Geräts** werden verglichen (Ende der vorigen höchstens 3 Tage neben dem Beginn).
  Geräte mit nicht nutzbarer Uhr bleiben außen vor.
- **Tagesauflösung:** Der Umhängtag ist der Bruchtag. Der Tag davor wird mit ausgenommen, weil die Bruchsuche einen Wechsel mitten am Tag dem
  Tag selbst zuschlägt.
- **Ferien als Erklärung** sind schwach (siehe oben). Eine Prüfung der Richtung, etwa „mehr Verkehr nach den Ferien“, ist nicht möglich, weil
  die Bruchsuche Ferientage auslässt.
- **Kennzahlen eines Einsatzes** stammen aus dem Rohaggregat (Stundenauflösung). Für Kennzahlen, Rauschboden und Verhaltensgruppen reicht das;
  Fahrten innerhalb einer Stunde lassen sich nicht weiter ordnen.
- **Die Messungen sind die Gegenprobe:** Sie bleiben ohne Zusammensetzen und zeigen, was die Verwaltung geliefert hat. Ein Fehler in der
  Zuordnung zeigt sich als Unterschied zwischen Einsatz und Messung.
- **Die YAML je Datei** bleibt die Sicht der Verwaltung. Einsätze und Zuordnungen stehen in `einsaetze.json`, `daten/einsaetze.csv` und
  `daten/brueche.csv`.

## Reproduktion

```sh
python3 -I einsaetze.py --auswertung _vorschau/auswertung.json --aggregat _vorschau-aggregat --cache .zwischenspeicher --jobs 8
python3 -I tools/abzug_je_abschnitt.py   # Abzug je Abschnitt gegen je Datei (Messungen)
```

`lokal_bauen.py` und der Workflow rufen es nach `dsd2csv.py` auf. Tests: `test_einsaetze.py`.
