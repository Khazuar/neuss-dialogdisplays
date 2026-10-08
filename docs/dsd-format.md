# DSD-Dateiformat

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

Die Anzeige schaltet Smiley/Frowny anhand des Konfigurationswerts **`safety_speed`**. Er entspricht
in allen geprüften Dateien dem Tempolimit der Messstelle (20, 30, 40, 50 km/h).

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
Die Gesamtwerte (oberste Ebene der YAML) enthalten weiterhin alle Fahrzeuge der Datei.

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
