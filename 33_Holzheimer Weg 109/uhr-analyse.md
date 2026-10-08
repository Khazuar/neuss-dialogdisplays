# Geräteuhr: 33_Holzheimer Weg 109

Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## _7.dsd

18.217 Fahrzeuge in 10 Abschnitt(en): 17.408 eingeschraenkt, 809 unbrauchbar.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2023-05-04 16:35 bis 2023-05-08 07:25 | 2.923 | eingeschraenkt |
| 2020-01-01 12:00 bis 2020-01-01 22:41 | 96 | unbrauchbar |
| 2020-01-01 12:00 bis 2020-01-01 22:55 | 214 | unbrauchbar |
| 2020-01-01 12:00 bis 2020-01-01 22:20 | 349 | unbrauchbar |
| 2020-01-01 12:00 bis 2020-03-04 08:37 | 14.485 | eingeschraenkt |
| 5 weitere Abschnitte | 150 | unbrauchbar |

### 2023-05-04 16:35 bis 2023-05-08 07:25: eingeschraenkt, unzureichend belegt (2.923 Fahrzeuge)

- Begründung: nur 0 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (3 volle Tage, nötig 21)
  - Tagesgang: offen. zu wenige Fahrzeuge oder Werktage für den Tagesgang
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge

### 2020-01-01 12:00 bis 2020-01-01 22:41: unbrauchbar (96 Fahrzeuge)

- Begründung: Uhr nach einem Reset auf das Standarddatum 2020-01-01 12:00 nicht neu gestellt
- Begründung: nur 96 Fahrzeuge: Datum und Tageszeit nicht rekonstruierbar
- Belege:
  - Datum: widerspricht. Uhr nach einem Reset auf das Standarddatum 2020-01-01 12:00 nicht neu gestellt
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (0 volle Tage, nötig 21)
  - Tagesgang: offen. zu wenige Fahrzeuge oder Werktage für den Tagesgang
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Datum der Uhr nicht verwertbar
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge

### 2020-01-01 12:00 bis 2020-01-01 22:55: unbrauchbar (214 Fahrzeuge)

- Begründung: Uhr nach einem Reset auf das Standarddatum 2020-01-01 12:00 nicht neu gestellt
- Begründung: nur 214 Fahrzeuge: Datum und Tageszeit nicht rekonstruierbar
- Belege:
  - Datum: widerspricht. Uhr nach einem Reset auf das Standarddatum 2020-01-01 12:00 nicht neu gestellt
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (0 volle Tage, nötig 21)
  - Tagesgang: offen. zu wenige Fahrzeuge oder Werktage für den Tagesgang
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Datum der Uhr nicht verwertbar
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge

### 2020-01-01 12:00 bis 2020-01-01 22:20: unbrauchbar (349 Fahrzeuge)

- Begründung: Uhr nach einem Reset auf das Standarddatum 2020-01-01 12:00 nicht neu gestellt
- Begründung: nur 349 Fahrzeuge: Datum und Tageszeit nicht rekonstruierbar
- Belege:
  - Datum: widerspricht. Uhr nach einem Reset auf das Standarddatum 2020-01-01 12:00 nicht neu gestellt
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (0 volle Tage, nötig 21)
  - Tagesgang: offen. zu wenige Fahrzeuge oder Werktage für den Tagesgang
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Datum der Uhr nicht verwertbar
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge

### 2020-01-01 12:00 bis 2020-03-04 08:37: eingeschraenkt, zurueckgesetzt (14.485 Fahrzeuge)

- Begründung: Uhr nach einem Reset auf das Standarddatum 2020-01-01 12:00 nicht neu gestellt
- Begründung: Die Uhr lief nach dem Reset gleichmäßig weiter: relative Zeiten sind nutzbar, Datum, Wochentag und Uhrzeit müssen rekonstruiert werden
- Belege:
  - Datum: widerspricht. Uhr nach einem Reset auf das Standarddatum 2020-01-01 12:00 nicht neu gestellt
  - Wochenrhythmus: offen. Wochenmuster nicht eindeutig (beste Korrelation 0.67, Abstand 0.21)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (-30 min, Korrelation 0.92)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Datum der Uhr nicht verwertbar
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
