# Geräteuhr: 05_Quinheimer Straße

Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## _5.dsd

108.883 Fahrzeuge in 1 Abschnitt(en): 108.883 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2024-03-19 08:38 bis 2024-07-24 07:51 | 108.883 | plausibel |

### 2024-03-19 08:38 bis 2024-07-24 07:51: plausibel (108.883 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.92)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+15 min, Korrelation 0.99)
- Begründung: ris: Mitteilung 69/311/2024 (Bezirksausschuss VI - Gnadental, Grimlinghausen, Erfttal, 2024-11-28) nennt den Ort und den Zeitraum 2024-03-19 bis 2024-07-24; Beginn und Ende des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.92)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+15 min, Korrelation 0.99)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/311/2024 (Bezirksausschuss VI - Gnadental, Grimlinghausen, Erfttal, 2024-11-28) nennt den Ort und den Zeitraum 2024-03-19 bis 2024-07-24; Beginn und Ende des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=217330&type=do>
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
