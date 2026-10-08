# Geräteuhr: 12_Berghäuschensweg

Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## DSD_16735_7.dsd

38.760 Fahrzeuge in 2 Abschnitt(en): 38.760 eingeschraenkt.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2023-01-31 12:27 bis 2023-02-01 12:18 | 2.437 | eingeschraenkt |
| 2023-02-01 11:37 bis 2023-02-17 08:15 | 36.323 | eingeschraenkt |

### 2023-01-31 12:27 bis 2023-02-01 12:18: eingeschraenkt, unzureichend belegt (2.437 Fahrzeuge)

- Begründung: nur 0 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (0 volle Tage, nötig 21)
  - Tagesgang: offen. zu wenige Fahrzeuge oder Werktage für den Tagesgang
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge

### 2023-02-01 11:37 bis 2023-02-17 08:15: eingeschraenkt, unzureichend belegt (36.323 Fahrzeuge)

- Begründung: nur 1 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+30 min, Korrelation 0.99)
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (15 volle Tage, nötig 21)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+30 min, Korrelation 0.99)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: offen. Uhr wurde vor diesem Segment um 41 Minuten zurückgestellt

## _8.dsd

98.409 Fahrzeuge in 2 Abschnitt(en): 95.972 plausibel, 2.437 eingeschraenkt.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2023-01-31 12:27 bis 2023-02-01 12:18 | 2.437 | eingeschraenkt |
| 2023-02-01 11:37 bis 2023-03-15 10:27 | 95.972 | plausibel |

### 2023-01-31 12:27 bis 2023-02-01 12:18: eingeschraenkt, unzureichend belegt (2.437 Fahrzeuge)

- Begründung: nur 0 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (0 volle Tage, nötig 21)
  - Tagesgang: offen. zu wenige Fahrzeuge oder Werktage für den Tagesgang
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge

### 2023-02-01 11:37 bis 2023-03-15 10:27: plausibel (95.972 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.97)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+30 min, Korrelation 0.99)
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.97)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+30 min, Korrelation 0.99)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: offen. Uhr wurde vor diesem Segment um 41 Minuten zurückgestellt
