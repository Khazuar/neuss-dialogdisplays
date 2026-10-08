# Geräteuhr: 109_Ruhrstraße

Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## _10.dsd

103.155 Fahrzeuge in 4 Abschnitt(en): 103.085 plausibel, 3 eingeschraenkt, 67 unbrauchbar.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2025-10-26 08:52 bis 2026-03-23 13:35 | 98.576 | plausibel |
| 2255-11-30 02:41 bis 2255-11-30 04:30 | 67 | unbrauchbar |
| 2026-03-23 15:34 bis 2026-03-29 09:25 | 4.509 | plausibel |
| 1 weitere Abschnitte | 3 | eingeschraenkt |

### 2025-10-26 08:52 bis 2026-03-23 13:35: plausibel (98.576 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.94)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 0.99)
- Begründung: ris: Mitteilung 69/0464/2026 (Bezirksausschuss V - Norf, 2026-07-02) nennt den Ort und den Zeitraum 2025-10-26 bis 2026-03-29; Beginn des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.94)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 0.99)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/0464/2026 (Bezirksausschuss V - Norf, 2026-07-02) nennt den Ort und den Zeitraum 2025-10-26 bis 2026-03-29; Beginn des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=246992&type=do>
  - Kontinuität: offen. Uhr wurde vor diesem Segment um 54 Minuten zurückgestellt

### 2255-11-30 02:41 bis 2255-11-30 04:30: unbrauchbar (67 Fahrzeuge)

- Begründung: Zeitstempel im Jahr 2255
- Belege:
  - Datum: widerspricht. Zeitstempel im Jahr 2255
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (0 volle Tage, nötig 21)
  - Tagesgang: offen. zu wenige Fahrzeuge oder Werktage für den Tagesgang
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Datum der Uhr nicht verwertbar
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge

### 2026-03-23 15:34 bis 2026-03-29 09:25: plausibel (4.509 Fahrzeuge)

- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 0.94)
- Begründung: ris: Mitteilung 69/0464/2026 (Bezirksausschuss V - Norf, 2026-07-02) nennt den Ort und den Zeitraum 2025-10-26 bis 2026-03-29; Ende des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (5 volle Tage, nötig 21)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 0.94)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/0464/2026 (Bezirksausschuss V - Norf, 2026-07-02) nennt den Ort und den Zeitraum 2025-10-26 bis 2026-03-29; Ende des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=246992&type=do>
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
