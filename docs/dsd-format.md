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

## Bekannte Datenprobleme

- **Fehlerhafte Zeitstempel:** Einzelne Records haben eine gültige CRC, aber ein unmögliches Datum
  (Monat/Tag außerhalb des Bereichs, Jahre bis 2255). Bei manchen Dateien beginnen die Daten außerdem
  viele Jahre vor der eigentlichen Messung (Geräteuhr nicht gestellt oder Altdaten im Speicher).
- **Ausreißer:** Vereinzelte Fahrzeugwerte weit über 150 km/h (bis 254 km/h), vermutlich Messfehler.
- **Abweichung zu DataCollect:** Die Überschreitungsquote (`Vexc %`) in den DataCollect-Auswertungen
  ist bei vielen Messungen höher als die aus den DSD-Rohdaten berechnete. Die Zahl der Überschreiter
  stimmt überein, im Nenner fehlen dort offenbar langsame Fahrzeuge. Das Verfahren ist noch nicht
  geklärt.
