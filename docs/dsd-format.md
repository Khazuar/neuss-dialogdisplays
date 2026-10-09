# DSD-Dateiformat

> Eigene Analyse; Fehler in der Beschreibung und in der Auswertung können nicht ausgeschlossen werden (ohne Gewähr).

Das Format der `.dsd`-Dateien (Dialogdisplay / Geschwindigkeitsanzeigetafel) ist nicht offiziell
dokumentiert. Die folgende Beschreibung wurde durch Analyse der Dateien ermittelt und mit den
Kennzahlen aus DataCollect-Auswertungen gegengeprüft (Tempolimit, V85). Sie kann unvollständig sein.
Die Referenzimplementierung ist `dsd2csv.py` (Funktion `parse`).

## Aufbau

| Teil    | Inhalt |
|---------|--------|
| Kopf    | 6 Byte `004DSD` |
| Konfig  | Folge von Key/Value-Records: `[Typ 1B][0x00][Wertlänge 1B][Namenslänge 1B][Name][Wert][2 Byte Prüfsumme]`. Ein `0xFF`-Byte trennt Blöcke (Konfiguration, Aktiv-Flags, Signatur). |
| Daten   | Folge von Records, jeweils mit CRC-8/MAXIM (Poly 0x31 reflektiert, Init 0) über alle Bytes davor als letztem Byte. |

### Datenrecords

| Typ    | Länge | Aufbau | Bedeutung |
|--------|-------|--------|-----------|
| `0x0F` | 9 Byte  | `0F v YY MM DD hh mm ss crc` | Fahrzeug, `v` = Geschwindigkeit in km/h |
| `0x33` | 9 Byte  | `33 YY MM DD hh mm ss x crc` | Status |
| `0x20` | 10 Byte | `20 YY MM DD hh mm ss x1 x2 crc` | Status (ältere Firmware) |

Jahr = 2000 + YY. Records mit falscher CRC werden übersprungen (Byte für Byte weitersuchen).
Die Bedeutung der Statuswerte ist unbekannt; `--status` schreibt sie roh als Hex.

## Tempolimit

Die Anzeige schaltet Smiley/Frowny anhand des Konfigurationswerts **`safety_speed`**. Das ist eine
**Anzeige-Schwelle** des Geräts. Sie stimmt bei den meisten Messungen mit dem vorgeschriebenen Tempolimit überein (20, 30,
40, 50 km/h), aber nicht immer. Gegen die Mitteilungen der Verwaltung ([metadaten.md](metadaten.md)) weichen sechs
Dateien ab:

| Messung | `safety_speed` | Mitteilung | Beobachtung |
|---|---|---|---|
| `15_2024_Martinusstraße` | 10 | 30 | Profil „325er“ für verkehrsberuhigte Bereiche, gemessen wurde vor dem Beginn des Bereichs |
| `46_Matthiasstraße` | 50 | 30 | Gerät ohne Namen, kein PDF der Stadt zum Vergleich |
| `Stationär_Villestraße/FR GV/L 142 FR Speck20_3` | 20 | 50 | Im Gerät steht „verdeckte Messung“, die Mitteilung nennt für die Villestraße eine verdeckte Messung |
| `Stationär_Villestraße/FR Norf/Ville Norf 30` | 30 | 50 | wie oben |
| `36_Lanzerather Buschweg` | 10 | 12 | verkehrsberuhigter Bereich, kleine Abweichung |
| `60_Mühlenstraße` | 10 | „deutlich unter 20“ | verkehrsberuhigter Bereich |

Alle vier Messungen mit dem Gerätenamen „325er“ (Martinusstraße, Lanzerather Buschweg, zweimal Mühlenstraße) haben 10 km/h
und liegen in verkehrsberuhigten Bereichen; dazu passt, dass die PDFs der Stadt dort ebenfalls 10 km/h als „Vmax StVO“ führen.
Die beiden Villestraße-Dateien sind die einzigen mit `hidden_measurement_on = 01`. `dsd2csv.py` verwendet für die
Kennzahlen deshalb das Limit der Mitteilung, wo es mindestens 5 km/h abweicht und die Zuordnung belastbar ist
(`belege/korrekturen.json`, vier Dateien); bei den verkehrsberuhigten Bereichen bleibt es bei der DSD-Konfiguration.

Fallstrick: Einbyte-Werte werden vom Parser als Text gelesen, wenn das Byte druckbar ist. Das Limit
50 km/h (Byte `0x32`) erscheint daher als Zeichen `2`, 30 km/h (`0x1e`) als Hex `1e`.
`byte_wert()` in `dsd2csv.py` löst beide Fälle auf.

Weitere nützliche Konfigurationswerte: `name` (Messstellenname, oft mit Tempolimit), `capture_min_speed`
(Erfassung ab km/h), `configuration_number` (Gerät).

## Geräteuhr, Zeitumstellung und Tageszeit-Auswertung

Für Auswertungen nach Tageszeit (Tags, Nachts, Schulweg) muss bekannt sein, welche Ortszeit ein
Zeitstempel bedeutet. Die Rohdaten tragen keine Zeitzone. Das hier beschriebene Zeitmodell stammt aus
einer Analyse der Dateien, nicht aus Herstellerangaben.

**Heartbeat.** Records vom Typ `0x33` erscheinen bei laufendem Gerät im exakten 10-Minuten-Takt
(`hh:00`, `hh:10`, …). Sie zeigen Uhrsprünge und Aufzeichnungslücken, auch wenn kein Fahrzeug vorbeikommt.
Records vom Typ `0x20` (ältere Firmware) haben diesen Takt nicht und werden dafür nicht verwendet.

**Keine Sommerzeitumstellung.** Die Geräte stellen ihre Uhr nicht um, auch nicht mit der Einstellung
`dst_on=01` und den hinterlegten Umstelldaten (`dst_time_reach_*`). Belege:

- Im Heartbeat zeigt sich bei keiner der 27 geprüften Umstellungen (25 Messungen, 6 davon mit `dst_on=01`)
  der Sprung von +70 bzw. −50 Minuten, den eine Umstellung hinterlassen würde. Zwei Unregelmäßigkeiten im
  Zeitfenster sind eine nächtliche Stromlücke und eine Lücke von 20 Minuten, keine Stundensprünge.
- Der Tagesgang des Verkehrs (Werktage, 35 Tage vor und nach dem Stichtag, 15-Minuten-Auflösung) verschiebt
  sich in Gerätezeit bei allen 28 geprüften Umstellungen in 26 Messungen um etwa eine Stunde (45 bis 105
  Minuten, im Frühjahr früher, im Herbst später). Der Berufsverkehr bleibt in Ortszeit zur selben Zeit,
  die Geräteuhr läuft weiter. Das gilt auch für Geräte mit `dst_on=01`.

**Modell.** Die Uhr wird bei der Inbetriebnahme auf die gültige Ortszeit gestellt und läuft dann
durch. Die Ortszeit eines Fahrzeugs ist die Gerätezeit plus der Unterschied zwischen dem Versatz zu UTC
am Fahrzeugzeitpunkt (MEZ 1 h, MESZ 2 h, Regel: letzter Sonntag im März/Oktober, 01:00 UTC) und dem Versatz
beim Stellen der Uhr. Eine im Sommer gestellte Uhr geht im Winter eine Stunde vor, eine im Winter gestellte
im Sommer eine Stunde nach. Siehe `geraet_zu_ortszeit()`.

**Prüfung des Modells.** Nach der Umrechnung liegt der Versatz des Tagesgangs vor und nach der Umstellung
bei 0 Minuten (13 von 16 prüfbaren Umstellungen), 15 Minuten (2) bzw. einmal bei 105 Minuten. Der letzte
Fall (`08_Kruppstraße`) liegt in den Herbstferien, die den Tagesgang verändern. Die Prüfung läuft pro
Auswertung mit und steht in der YAML unter `uhr.segmente[].zeitumstellung_abweichung_min`.

**Uhr-Segmente.** Eine Aufzeichnung wird in Abschnitte mit zusammenhängender Uhr zerlegt:

- ein Rückwärtssprung um mehr als 2 Minuten oder eine Lücke von mehr als 3 Tagen beginnt ein neues Segment;
- einzelne Zeitstempel, die mehr als einen Tag vom gleitenden Median ihrer 100 Nachbarn abweichen
  (Ausreißer wie das Jahr 2255), bilden kein Segment;
- nach einem Rückwärtssprung (Uhr nachgestellt) gilt die Uhr als neu gestellt. Nach einer reinen Lücke
  läuft sie mit dem alten Versatz weiter. Die Uhr behält also über eine Lücke hinweg ihre Sommer- oder
  Winterzeit.

Ein Segment ist **nicht nutzbar**, wenn

- es mit dem Standarddatum `2020-01-01 12:00` beginnt (Uhr nach Stromausfall zurückgesetzt und nicht neu
  gestellt; die Fahrzeuge sind echt, ihre Uhrzeit ist unbekannt),
- sein Beginn außerhalb von 2020 bis 2030 liegt oder mehr als einen Tag vor dem vorigen Segment (versprungenes
  Datum mitten in der Aufzeichnung),
- mehr als 15 % seiner Fahrzeuge in Ortszeit zwischen 0 und 5 Uhr liegen (Median über alle Segmente: 3,6 %).
  Das zeigt eine um Stunden verstellte Uhr, etwa bei `Stationär_Villestraße/FR GV/…_5` (Tagesgang um
  etwa 8 Stunden gegenüber den Nachbarmessungen verschoben). Diese Uhren werden nicht korrigiert, weil der
  Fehler nicht belegbar ist.

Die Bewertung je Datei (`uhr.bewertung`) ist `plausibel` (mindestens 99 % der Fahrzeuge nutzbar, kein
Hinweis auf eine verrutschte Uhr), `eingeschraenkt` oder `unbrauchbar` (unter 50 % nutzbar).

**Teilzeiträume.** `teilzeitraeume` und `bereinigt` in der YAML verwenden nur Fahrzeuge aus nutzbaren
Segmenten, umgerechnet auf Ortszeit:

| Zeitraum | Definition |
|----------|------------|
| `tags` | 06:00 bis 18:00 Uhr, alle Tage |
| `nachts` | 18:00 bis 06:00 Uhr, alle Tage |
| `schulweg` | 07:00 bis 08:00 Uhr, Montag bis Freitag |

Schulferien und Feiertage sind nicht herausgerechnet. `bereinigt` umfasst alle Tageszeiten.
Die Gesamtwerte (oberste Ebene der YAML) enthalten weiterhin alle Fahrzeuge der Datei ab 5 km/h
(siehe unten).

## Auswertung ab 5 km/h

`dsd2csv.py` nimmt Fahrzeuge unter 5 km/h aus der Auswertung (`--min-kmh`, Standard 5; `0` nimmt alle). Bis dahin war der
Parameter nie gesetzt, weder in den Workflows (`pages.yml`, `release.yml`) noch im Skript, es wurden also alle Fahrzeuge
gezählt. Die CSV-Dateien enthalten weiterhin jeden Messwert. In der YAML stehen `auswertung_ab_kmh` und
`fahrzeuge_unter_auswertung_ab`, die Detailseiten nennen beides.

Warum: Wir nehmen an, dass sich kein Fahrzeug im Sinne der StVO regelmäßig langsamer als 5 km/h an der Anzeige vorbei
bewegt. Solche Werte stammen vermutlich von Fußgängern, Tieren, Echos oder Störungen. Belegt ist das nicht, es ist eine
Festlegung für diese Auswertung. Die Geräte erfassen je nach Konfiguration ab 3, 7, 9 oder 10 km/h (`capture_min_speed`;
24, 19, 58 bzw. 8 Dateien). Werte unter 5 km/h stehen in 22 der 24 Dateien mit Erfassung ab 3 km/h, aber auch in 12 der 58
Dateien mit Erfassung ab 9 km/h und in einer mit 7 km/h. Die Geräte speichern also teils Werte unterhalb der eingestellten
Erfassungsgrenze.

Wirkung: Von etwa 12,0 Millionen Fahrzeugen fallen 0,46 Millionen (3,8 %) heraus, in 35 der 109 Dateien. Bei drei Messstellen
sind es über 40 % (Bauerbahn, Feldstraße, Alte Uferstraße). Die Einhaltungsquoten sinken dadurch oder bleiben gleich, bei
einzelnen Messungen um bis zu 6,5 Prozentpunkte (qualifizierte Quote, Median über alle Messungen: 0), das mittlere Tempo
steigt (Median 0, höchstens +4,9 km/h). Die drei Dateien mit Tempolimit 10 km/h (verkehrsberuhigter Bereich) enthalten
keine Werte unter 5 km/h und ändern sich nicht.

Vergleich mit den Mitteilungen der Verwaltung (31 Messungen, Zuordnung über Straßenname und Zeitraum, Fahrzeuge im
Erfassungszeitraum; Median der Abweichung DSD − Mitteilung):

| Größe | alle Fahrzeuge | ab 5 km/h | ab 10 km/h |
|---|---|---|---|
| mittleres Tempo | −1,29 km/h | −0,80 km/h | −0,03 km/h |
| V85 | 0 km/h | 0 km/h | 0 km/h |
| Anteil unter dem genannten Tempo (24 Messungen) | −0,9 Prozentpunkte | −0,9 Prozentpunkte | −1,3 Prozentpunkte |
| Fahrzeuge je Tag (15 Messungen) | −1 % | −5 % | −9 % |

Das mittlere Tempo der Mitteilungen passt am besten zu einer Grenze von 10 bis 12 km/h, der Anteil unter dem genannten
Tempo und die Fahrzeuge je Tag passen dagegen mit allen Fahrzeugen am besten. Die Mitteilungen rechnen also offenbar nicht
für alle Größen mit derselben Menge an Fahrzeugen; wie genau, geht aus den Daten nicht hervor. Die Grenze von 5 km/h ist
ein Kompromiss, den wir mit der Annahme zu Fahrzeugen im Sinne der StVO begründen, nicht mit diesem Vergleich.

**Grenzen.** Die Plausibilitätsprüfung erkennt zurückgesetzte, versprungene und um Stunden verstellte
Uhren. Eine Abweichung um wenige Minuten oder um genau eine Stunde, die bereits beim Stellen entstand,
ist mit dem Verkehrsgang allein nicht belegbar. Ob die Uhr beim Stellen richtig ging, ist eine
Annahme, die der Test an den Zeitumstellungen nur relativ bestätigt.

## Bekannte Datenprobleme

- **Fehlerhafte Zeitstempel:** Einzelne Records haben eine gültige CRC, aber ein unmögliches Datum
  (Monat/Tag außerhalb des Bereichs, Jahre bis 2255). Bei manchen Dateien beginnen die Daten außerdem
  viele Jahre vor der eigentlichen Messung (Geräteuhr nicht gestellt oder Altdaten im Speicher),
  siehe oben.
- **Ausreißer:** Vereinzelte Fahrzeugwerte weit über 150 km/h (bis 254 km/h), vermutlich Messfehler.
- **Abweichung zu DataCollect:** Die Überschreitungsquote (`Vexc %`) in den DataCollect-Auswertungen
  ist bei vielen Messungen höher als die aus den DSD-Rohdaten berechnete. Die Zahl der Überschreiter
  stimmt überein, im Nenner fehlen dort offenbar langsame Fahrzeuge. Das Verfahren ist noch nicht
  geklärt.
