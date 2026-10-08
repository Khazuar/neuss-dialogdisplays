# Geräteuhr: 118_Ruhrstraße

Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## _11.dsd

174.297 Fahrzeuge in 3 Abschnitt(en): 155.814 plausibel, 17.979 eingeschraenkt, 504 unbrauchbar.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2026-03-29 09:30 bis 2026-07-20 13:42 | 155.814 | plausibel |
| 2255-11-30 00:07 bis 2255-11-30 04:29 | 504 | unbrauchbar |
| 2026-07-20 18:08 bis 2026-08-02 10:43 | 17.979 | eingeschraenkt |

### 2026-03-29 09:30 bis 2026-07-20 13:42: plausibel (155.814 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.92)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+30 min, Korrelation 0.99)
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.92)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+30 min, Korrelation 0.99)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in 1 Mitteilung(en) genannt, aber kein Zeitraum passt zum Segment
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge

### 2255-11-30 00:07 bis 2255-11-30 04:29: unbrauchbar (504 Fahrzeuge)

- Begründung: Zeitstempel im Jahr 2255
- Belege:
  - Datum: widerspricht. Zeitstempel im Jahr 2255
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (0 volle Tage, nötig 21)
  - Tagesgang: offen. zu wenige Fahrzeuge oder Werktage für den Tagesgang
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Datum der Uhr nicht verwertbar
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge

### 2026-07-20 18:08 bis 2026-08-02 10:43: eingeschraenkt, unzureichend belegt (17.979 Fahrzeuge)

- Begründung: nur 1 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+30 min, Korrelation 0.99)
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (12 volle Tage, nötig 21)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+30 min, Korrelation 0.99)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in 1 Mitteilung(en) genannt, aber kein Zeitraum passt zum Segment
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
