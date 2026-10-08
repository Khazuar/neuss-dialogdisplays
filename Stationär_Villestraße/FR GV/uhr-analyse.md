# Geräteuhr: Stationär_Villestraße/FR GV

Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## 0000000000000000_2.dsd

35.337 Fahrzeuge in 2 Abschnitt(en): 35.337 eingeschraenkt.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2023-03-01 13:27 bis 2023-03-03 02:00 | 3.584 | eingeschraenkt |
| 2023-03-03 01:00 bis 2023-03-15 11:40 | 31.753 | eingeschraenkt |

### 2023-03-01 13:27 bis 2023-03-03 02:00: eingeschraenkt, unzureichend belegt (3.584 Fahrzeuge)

- Begründung: nur 0 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (1 volle Tage, nötig 21)
  - Tagesgang: offen. zu wenige Fahrzeuge oder Werktage für den Tagesgang
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in 2 Mitteilung(en) genannt, aber kein Zeitraum passt zum Segment
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge

### 2023-03-03 01:00 bis 2023-03-15 11:40: eingeschraenkt, unzureichend belegt (31.753 Fahrzeuge)

- Begründung: nur 1 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 0.92)
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (11 volle Tage, nötig 21)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 0.92)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in 2 Mitteilung(en) genannt, aber kein Zeitraum passt zum Segment
  - Kontinuität: offen. Uhr wurde vor diesem Segment um 60 Minuten zurückgestellt

## 0000000000000000_3.dsd

759.906 Fahrzeuge in 2 Abschnitt(en): 756.017 plausibel, 3.889 eingeschraenkt.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2023-03-15 11:40 bis 2023-03-17 02:00 | 3.889 | eingeschraenkt |
| 2023-03-17 01:07 bis 2024-01-11 16:31 | 756.017 | plausibel |

### 2023-03-15 11:40 bis 2023-03-17 02:00: eingeschraenkt, unzureichend belegt (3.889 Fahrzeuge)

- Begründung: nur 1 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Begründung: ris: Mitteilung 69/288/2024 (Bezirksausschuss III - Selikum, Reuschenberg, Weckhoven, Hoisten, 2024-06-27) nennt den Ort und den Zeitraum 2023-03-15 bis 2024-01-11; Beginn des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (1 volle Tage, nötig 21)
  - Tagesgang: offen. zu wenige Fahrzeuge oder Werktage für den Tagesgang
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/288/2024 (Bezirksausschuss III - Selikum, Reuschenberg, Weckhoven, Hoisten, 2024-06-27) nennt den Ort und den Zeitraum 2023-03-15 bis 2024-01-11; Beginn des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=209702&type=do>
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge

### 2023-03-17 01:07 bis 2024-01-11 16:31: plausibel (756.017 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.99)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 0.98)
- Begründung: zeitumstellung: Sprung im Verkehrsgang liegt am amtlichen Umstellungstag 2023-10-29 (Abweichung -1 Tage, 87% der Tage passen): Datum auf den Tag genau verankert; Tagesgang passt über 1 Zeitumstellung(en) nach der Korrektur
- Begründung: ris: Mitteilung 69/288/2024 (Bezirksausschuss III - Selikum, Reuschenberg, Weckhoven, Hoisten, 2024-06-27) nennt den Ort und den Zeitraum 2023-03-15 bis 2024-01-11; Ende des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.99)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 0.98)
  - Zeitumstellung: bestätigt. Sprung im Verkehrsgang liegt am amtlichen Umstellungstag 2023-10-29 (Abweichung -1 Tage, 87% der Tage passen): Datum auf den Tag genau verankert; Tagesgang passt über 1 Zeitumstellung(en) nach der Korrektur
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/288/2024 (Bezirksausschuss III - Selikum, Reuschenberg, Weckhoven, Hoisten, 2024-06-27) nennt den Ort und den Zeitraum 2023-03-15 bis 2024-01-11; Ende des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=209702&type=do>
  - Kontinuität: offen. Uhr wurde vor diesem Segment um 52 Minuten zurückgestellt

## 0000000000000000_4.dsd

163.490 Fahrzeuge in 3 Abschnitt(en): 160.202 plausibel, 3.288 eingeschraenkt.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2024-01-11 16:32 bis 2024-01-11 17:03 | 82 | eingeschraenkt |
| 2024-01-11 17:00 bis 2024-01-13 02:00 | 3.206 | eingeschraenkt |
| 2024-01-13 01:03 bis 2024-03-19 09:28 | 160.202 | plausibel |

### 2024-01-11 16:32 bis 2024-01-11 17:03: eingeschraenkt, unzureichend belegt (82 Fahrzeuge)

- Begründung: nur 1 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Begründung: ris: Mitteilung 69/288/2024 (Bezirksausschuss III - Selikum, Reuschenberg, Weckhoven, Hoisten, 2024-06-27) nennt den Ort und den Zeitraum 2023-03-15 bis 2024-01-11; Ende des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (0 volle Tage, nötig 21)
  - Tagesgang: offen. zu wenige Fahrzeuge oder Werktage für den Tagesgang
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/288/2024 (Bezirksausschuss III - Selikum, Reuschenberg, Weckhoven, Hoisten, 2024-06-27) nennt den Ort und den Zeitraum 2023-03-15 bis 2024-01-11; Ende des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=209702&type=do>
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge

### 2024-01-11 17:00 bis 2024-01-13 02:00: eingeschraenkt, unzureichend belegt (3.206 Fahrzeuge)

- Begründung: nur 1 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Begründung: ris: Mitteilung 69/288/2024 (Bezirksausschuss III - Selikum, Reuschenberg, Weckhoven, Hoisten, 2024-06-27) nennt den Ort und den Zeitraum 2024-01-11 bis 2024-03-19; Beginn des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (1 volle Tage, nötig 21)
  - Tagesgang: offen. zu wenige Fahrzeuge oder Werktage für den Tagesgang
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/288/2024 (Bezirksausschuss III - Selikum, Reuschenberg, Weckhoven, Hoisten, 2024-06-27) nennt den Ort und den Zeitraum 2024-01-11 bis 2024-03-19; Beginn des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=209702&type=do>
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge

### 2024-01-13 01:03 bis 2024-03-19 09:28: plausibel (160.202 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.90)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (-15 min, Korrelation 0.98)
- Begründung: ris: Mitteilung 69/288/2024 (Bezirksausschuss III - Selikum, Reuschenberg, Weckhoven, Hoisten, 2024-06-27) nennt den Ort und den Zeitraum 2024-01-11 bis 2024-03-19; Ende des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.90)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (-15 min, Korrelation 0.98)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/288/2024 (Bezirksausschuss III - Selikum, Reuschenberg, Weckhoven, Hoisten, 2024-06-27) nennt den Ort und den Zeitraum 2024-01-11 bis 2024-03-19; Ende des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=209702&type=do>
  - Kontinuität: offen. Uhr wurde vor diesem Segment um 56 Minuten zurückgestellt

## 0000000000000000_5.dsd

403.508 Fahrzeuge in 5 Abschnitt(en): 403.508 eingeschraenkt.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2025-08-08 07:18 bis 2025-08-11 08:00 | 2.068 | eingeschraenkt |
| 2025-11-28 09:41 bis 2025-11-30 01:59 | 5.246 | eingeschraenkt |
| 2025-11-29 17:54 bis 2025-12-15 22:20 | 50.748 | eingeschraenkt |
| 2025-12-15 22:06 bis 2026-04-09 06:32 | 345.445 | eingeschraenkt |
| 1 weitere Abschnitte | 1 | eingeschraenkt |

### 2025-08-08 07:18 bis 2025-08-11 08:00: eingeschraenkt, unzureichend belegt (2.068 Fahrzeuge)

- Begründung: nur 0 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (2 volle Tage, nötig 21)
  - Tagesgang: offen. zu wenige Fahrzeuge oder Werktage für den Tagesgang
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in 2 Mitteilung(en) genannt, aber kein Zeitraum passt zum Segment
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge

### 2025-11-28 09:41 bis 2025-11-30 01:59: eingeschraenkt, unzureichend belegt (5.246 Fahrzeuge)

- Begründung: nur 0 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (1 volle Tage, nötig 21)
  - Tagesgang: offen. zu wenige Fahrzeuge oder Werktage für den Tagesgang
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in 2 Mitteilung(en) genannt, aber kein Zeitraum passt zum Segment
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge

### 2025-11-29 17:54 bis 2025-12-15 22:20: eingeschraenkt, widerspruch (50.748 Fahrzeuge)

- Begründung: tagesgang: Tagesgang um -450 Minuten gegenüber dem typischen Verlauf verschoben
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (15 volle Tage, nötig 21)
  - Tagesgang: widerspricht. Tagesgang um -450 Minuten gegenüber dem typischen Verlauf verschoben
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in 2 Mitteilung(en) genannt, aber kein Zeitraum passt zum Segment
  - Kontinuität: offen. Uhr wurde vor diesem Segment um 485 Minuten zurückgestellt
- Schätzung, nicht angewendet: Tageszeit -450 Minuten (positiv: Uhr geht vor)

### 2025-12-15 22:06 bis 2026-04-09 06:32: eingeschraenkt, widerspruch (345.445 Fahrzeuge)

- Begründung: tagesgang: Tagesgang um -465 Minuten gegenüber dem typischen Verlauf verschoben
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.92)
  - Tagesgang: widerspricht. Tagesgang um -465 Minuten gegenüber dem typischen Verlauf verschoben
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in 2 Mitteilung(en) genannt, aber kein Zeitraum passt zum Segment
  - Kontinuität: offen. Uhr wurde vor diesem Segment um 13 Minuten zurückgestellt
- Schätzung, nicht angewendet: Tageszeit -465 Minuten (positiv: Uhr geht vor)

## L 142 FR Speck20_3.dsd

223.344 Fahrzeuge in 1 Abschnitt(en): 223.344 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2024-04-25 11:21 bis 2024-07-24 08:59 | 223.344 | plausibel |

### 2024-04-25 11:21 bis 2024-07-24 08:59: plausibel (223.344 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.83)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+60 min, Korrelation 0.98)
- Begründung: ris: Mitteilung (Ergebnisse von Verkehrsmessungen durch Dialog Displays) (Bezirksausschuss III - Selikum, Reuschenberg, Weckhoven, Hoisten, 2024-11-14) nennt den Ort und den Zeitraum 2024-03-27 bis 2024-07-24; Ende des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.83)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+60 min, Korrelation 0.98)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung (Ergebnisse von Verkehrsmessungen durch Dialog Displays) (Bezirksausschuss III - Selikum, Reuschenberg, Weckhoven, Hoisten, 2024-11-14) nennt den Ort und den Zeitraum 2024-03-27 bis 2024-07-24; Ende des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=216549&type=do>
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge

## L 142 FR Speck_4.dsd

2 Fahrzeuge in 2 Abschnitt(en): 2 eingeschraenkt.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2 weitere Abschnitte | 2 | eingeschraenkt |
