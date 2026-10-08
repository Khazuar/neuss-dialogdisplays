# Geräteuhr: Stationär_Villestraße/FR Norf

Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## 0000000000000000_4.dsd

Die Datei enthält keine Fahrzeugdaten.

## Ville Norf 30.dsd

399.149 Fahrzeuge in 3 Abschnitt(en): 399.147 plausibel, 2 eingeschraenkt.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2024-03-27 06:36 bis 2024-06-04 10:08 | 229.590 | plausibel |
| 2024-06-04 10:01 bis 2024-07-24 07:37 | 169.557 | plausibel |
| 1 weitere Abschnitte | 2 | eingeschraenkt |

### 2024-03-27 06:36 bis 2024-06-04 10:08: plausibel (229.590 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.93)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+15 min, Korrelation 0.98)
- Begründung: ris: Mitteilung (Ergebnisse von Verkehrsmessungen durch Dialog Displays) (Bezirksausschuss III - Selikum, Reuschenberg, Weckhoven, Hoisten, 2024-11-14) nennt den Ort und den Zeitraum 2024-03-27 bis 2024-07-24; Beginn des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.93)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+15 min, Korrelation 0.98)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung (Ergebnisse von Verkehrsmessungen durch Dialog Displays) (Bezirksausschuss III - Selikum, Reuschenberg, Weckhoven, Hoisten, 2024-11-14) nennt den Ort und den Zeitraum 2024-03-27 bis 2024-07-24; Beginn des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=216549&type=do>
  - Kontinuität: offen. Uhr wurde vor diesem Segment um 53 Minuten zurückgestellt

### 2024-06-04 10:01 bis 2024-07-24 07:37: plausibel (169.557 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.96)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (-60 min, Korrelation 0.97)
- Begründung: ris: Mitteilung (Ergebnisse von Verkehrsmessungen durch Dialog Displays) (Bezirksausschuss III - Selikum, Reuschenberg, Weckhoven, Hoisten, 2024-11-14) nennt den Ort und den Zeitraum 2024-03-27 bis 2024-07-24; Ende des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.96)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (-60 min, Korrelation 0.97)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung (Ergebnisse von Verkehrsmessungen durch Dialog Displays) (Bezirksausschuss III - Selikum, Reuschenberg, Weckhoven, Hoisten, 2024-11-14) nennt den Ort und den Zeitraum 2024-03-27 bis 2024-07-24; Ende des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=216549&type=do>
  - Kontinuität: offen. Uhr wurde vor diesem Segment um 7 Minuten zurückgestellt

## Ville Norf_12.dsd

339.652 Fahrzeuge in 1 Abschnitt(en): 339.652 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2024-11-29 09:32 bis 2025-03-18 15:15 | 339.652 | plausibel |

### 2024-11-29 09:32 bis 2025-03-18 15:15: plausibel (339.652 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.86)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 0.99)
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.86)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 0.99)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in 2 Mitteilung(en) genannt, aber kein Zeitraum passt zum Segment
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge

## Ville Norf_2.dsd

49.173 Fahrzeuge in 1 Abschnitt(en): 49.173 eingeschraenkt.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2023-03-01 17:38 bis 2023-03-15 12:28 | 49.173 | eingeschraenkt |

### 2023-03-01 17:38 bis 2023-03-15 12:28: eingeschraenkt, unzureichend belegt (49.173 Fahrzeuge)

- Begründung: nur 1 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (-15 min, Korrelation 0.94)
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (13 volle Tage, nötig 21)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (-15 min, Korrelation 0.94)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in 2 Mitteilung(en) genannt, aber kein Zeitraum passt zum Segment
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge

## Ville Norf_3.dsd

984.030 Fahrzeuge in 3 Abschnitt(en): 978.831 plausibel, 5.199 eingeschraenkt.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2023-03-15 11:36 bis 2023-03-17 02:00 | 5.193 | eingeschraenkt |
| 2023-03-17 01:10 bis 2024-01-11 17:05 | 978.831 | plausibel |
| 1 weitere Abschnitte | 6 | eingeschraenkt |

### 2023-03-15 11:36 bis 2023-03-17 02:00: eingeschraenkt, unzureichend belegt (5.193 Fahrzeuge)

- Begründung: nur 1 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Begründung: ris: Mitteilung 69/288/2024 (Bezirksausschuss III - Selikum, Reuschenberg, Weckhoven, Hoisten, 2024-06-27) nennt den Ort und den Zeitraum 2023-03-15 bis 2024-01-11; Beginn des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (1 volle Tage, nötig 21)
  - Tagesgang: offen. zu wenige Fahrzeuge oder Werktage für den Tagesgang
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/288/2024 (Bezirksausschuss III - Selikum, Reuschenberg, Weckhoven, Hoisten, 2024-06-27) nennt den Ort und den Zeitraum 2023-03-15 bis 2024-01-11; Beginn des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=209702&type=do>
  - Kontinuität: offen. Uhr wurde vor diesem Segment um 53 Minuten zurückgestellt

### 2023-03-17 01:10 bis 2024-01-11 17:05: plausibel (978.831 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.99)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (-45 min, Korrelation 0.98)
- Begründung: zeitumstellung: Sprung im Verkehrsgang liegt am amtlichen Umstellungstag 2023-10-29 (Abweichung -1 Tage, 93% der Tage passen): Datum auf den Tag genau verankert; Tagesgang passt über 1 Zeitumstellung(en) nach der Korrektur
- Begründung: ris: Mitteilung 69/288/2024 (Bezirksausschuss III - Selikum, Reuschenberg, Weckhoven, Hoisten, 2024-06-27) nennt den Ort und den Zeitraum 2023-03-15 bis 2024-01-11; Ende des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.99)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (-45 min, Korrelation 0.98)
  - Zeitumstellung: bestätigt. Sprung im Verkehrsgang liegt am amtlichen Umstellungstag 2023-10-29 (Abweichung -1 Tage, 93% der Tage passen): Datum auf den Tag genau verankert; Tagesgang passt über 1 Zeitumstellung(en) nach der Korrektur
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/288/2024 (Bezirksausschuss III - Selikum, Reuschenberg, Weckhoven, Hoisten, 2024-06-27) nennt den Ort und den Zeitraum 2023-03-15 bis 2024-01-11; Ende des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=209702&type=do>
  - Kontinuität: offen. Uhr wurde vor diesem Segment um 50 Minuten zurückgestellt

## Ville Norf_4.dsd

218.044 Fahrzeuge in 2 Abschnitt(en): 214.151 plausibel, 3.893 eingeschraenkt.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2024-01-11 17:06 bis 2024-01-13 02:00 | 3.893 | eingeschraenkt |
| 2024-01-13 01:02 bis 2024-03-19 09:40 | 214.151 | plausibel |

### 2024-01-11 17:06 bis 2024-01-13 02:00: eingeschraenkt, unzureichend belegt (3.893 Fahrzeuge)

- Begründung: nur 1 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Begründung: ris: Mitteilung 69/288/2024 (Bezirksausschuss III - Selikum, Reuschenberg, Weckhoven, Hoisten, 2024-06-27) nennt den Ort und den Zeitraum 2024-01-11 bis 2024-03-19; Beginn des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (1 volle Tage, nötig 21)
  - Tagesgang: offen. zu wenige Fahrzeuge oder Werktage für den Tagesgang
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/288/2024 (Bezirksausschuss III - Selikum, Reuschenberg, Weckhoven, Hoisten, 2024-06-27) nennt den Ort und den Zeitraum 2024-01-11 bis 2024-03-19; Beginn des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=209702&type=do>
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge

### 2024-01-13 01:02 bis 2024-03-19 09:40: plausibel (214.151 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.91)
- Begründung: ris: Mitteilung 69/288/2024 (Bezirksausschuss III - Selikum, Reuschenberg, Weckhoven, Hoisten, 2024-06-27) nennt den Ort und den Zeitraum 2024-01-11 bis 2024-03-19; Ende des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.91)
  - Tagesgang: offen. Tagesgang weicht etwas ab (-75 min, Korrelation 0.97)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/288/2024 (Bezirksausschuss III - Selikum, Reuschenberg, Weckhoven, Hoisten, 2024-06-27) nennt den Ort und den Zeitraum 2024-01-11 bis 2024-03-19; Ende des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=209702&type=do>
  - Kontinuität: offen. Uhr wurde vor diesem Segment um 57 Minuten zurückgestellt
- Schätzung, nicht angewendet: Tageszeit -75 Minuten (positiv: Uhr geht vor)
