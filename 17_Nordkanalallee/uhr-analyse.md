# Geräteuhr: 17_Nordkanalallee

Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## DSD14178 Tempo30_2.dsd

46.503 Fahrzeuge in 1 Abschnitt(en): 46.503 eingeschraenkt.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2022-03-30 11:21 bis 2022-05-02 12:35 | 46.503 | eingeschraenkt |

### 2022-03-30 11:21 bis 2022-05-02 12:35: eingeschraenkt, unzureichend belegt (46.503 Fahrzeuge)

- Begründung: nur 1 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+45 min, Korrelation 0.96)
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. Wochenmuster nicht eindeutig (beste Korrelation 0.71, Abstand 0.12)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+45 min, Korrelation 0.96)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in 1 Mitteilung(en) genannt, aber kein Zeitraum passt zum Segment
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge

## DSD17400 Tempo30_3.dsd

233.029 Fahrzeuge in 1 Abschnitt(en): 233.029 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2024-04-23 10:57 bis 2024-07-23 08:53 | 233.029 | plausibel |

### 2024-04-23 10:57 bis 2024-07-23 08:53: plausibel (233.029 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.96)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (-30 min, Korrelation 0.96)
- Begründung: ris: Mitteilung 69/313/2024 (Bezirksausschuss I - Innenstadt, 2024-12-04) nennt den Ort und den Zeitraum 2024-04-23 bis 2024-07-23; Beginn und Ende des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.96)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (-30 min, Korrelation 0.96)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/313/2024 (Bezirksausschuss I - Innenstadt, 2024-12-04) nennt den Ort und den Zeitraum 2024-04-23 bis 2024-07-23; Beginn und Ende des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=217893&type=do>
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
