# Geräteuhr: 46_Matthiasstraße

Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## _13.dsd

76.620 Fahrzeuge in 3 Abschnitt(en): 65.336 plausibel, 11.284 eingeschraenkt.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2023-11-16 15:54 bis 2023-11-16 16:12 | 50 | eingeschraenkt |
| 2023-11-16 15:14 bis 2023-12-15 09:50 | 65.336 | plausibel |
| 2023-12-18 16:40 bis 2024-03-19 10:00 | 11.234 | eingeschraenkt |

### 2023-11-16 15:54 bis 2023-11-16 16:12: eingeschraenkt, unzureichend belegt (50 Fahrzeuge)

- Begründung: nur 1 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Begründung: ris: Mitteilung 69/280/2024 (Bezirksausschuss VII - Uedesheim, 2024-06-18) nennt den Ort und den Zeitraum 2023-11-16 bis 2024-03-19; Beginn des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (0 volle Tage, nötig 21)
  - Tagesgang: offen. zu wenige Fahrzeuge oder Werktage für den Tagesgang
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/280/2024 (Bezirksausschuss VII - Uedesheim, 2024-06-18) nennt den Ort und den Zeitraum 2023-11-16 bis 2024-03-19; Beginn des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=209026&type=do>
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge

### 2023-11-16 15:14 bis 2023-12-15 09:50: plausibel (65.336 Fahrzeuge)

- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (-15 min, Korrelation 0.95)
- Begründung: ris: Mitteilung 69/280/2024 (Bezirksausschuss VII - Uedesheim, 2024-06-18) nennt den Ort und den Zeitraum 2023-11-16 bis 2024-03-19; Beginn des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. Wochenmuster nicht eindeutig (beste Korrelation 0.61, Abstand 0.10)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (-15 min, Korrelation 0.95)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/280/2024 (Bezirksausschuss VII - Uedesheim, 2024-06-18) nennt den Ort und den Zeitraum 2023-11-16 bis 2024-03-19; Beginn des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=209026&type=do>
  - Kontinuität: offen. Uhr wurde vor diesem Segment um 57 Minuten zurückgestellt

### 2023-12-18 16:40 bis 2024-03-19 10:00: eingeschraenkt, unzureichend belegt (11.234 Fahrzeuge)

- Begründung: nur 1 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Begründung: ris: Mitteilung 69/280/2024 (Bezirksausschuss VII - Uedesheim, 2024-06-18) nennt den Ort und den Zeitraum 2023-11-16 bis 2024-03-19; Ende des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. Wochenmuster nicht eindeutig (beste Korrelation 0.57, Abstand 0.04)
  - Tagesgang: offen. Tagesgang weicht etwas ab (+0 min, Korrelation 0.90)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/280/2024 (Bezirksausschuss VII - Uedesheim, 2024-06-18) nennt den Ort und den Zeitraum 2023-11-16 bis 2024-03-19; Ende des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=209026&type=do>
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
- Schätzung, nicht angewendet: Tageszeit +0 Minuten (positiv: Uhr geht vor)
