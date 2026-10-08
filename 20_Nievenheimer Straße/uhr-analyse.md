# Geräteuhr: 20_Nievenheimer Straße

Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## 0000000000000000_12.dsd

48.291 Fahrzeuge in 1 Abschnitt(en): 48.291 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2023-09-29 13:10 bis 2023-10-26 05:03 | 48.291 | plausibel |

### 2023-09-29 13:10 bis 2023-10-26 05:03: plausibel (48.291 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.93)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+30 min, Korrelation 0.99)
- Begründung: ris: Mitteilung 69/251/2024 (Bezirksausschuss V - Norf, 2024-02-27) nennt den Ort und den Zeitraum 2023-09-11 bis 2023-10-26; Ende des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.93)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+30 min, Korrelation 0.99)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/251/2024 (Bezirksausschuss V - Norf, 2024-02-27) nennt den Ort und den Zeitraum 2023-09-11 bis 2023-10-26; Ende des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=202481&type=do>
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
