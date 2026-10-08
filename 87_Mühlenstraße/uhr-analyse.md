# Geräteuhr: 87_Mühlenstraße

Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## DSD 14178 325er_3.dsd

34.038 Fahrzeuge in 1 Abschnitt(en): 34.038 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2024-12-04 11:20 bis 2025-02-21 09:32 | 34.038 | plausibel |

### 2024-12-04 11:20 bis 2025-02-21 09:32: plausibel (34.038 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.93)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+15 min, Korrelation 0.95)
- Begründung: ris: Mitteilung 69/0459/2026 (Bezirksausschuss I - Innenstadt, 2026-06-17) nennt den Ort und den Zeitraum 2024-12-04 bis 2025-03-19; Beginn des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.93)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+15 min, Korrelation 0.95)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/0459/2026 (Bezirksausschuss I - Innenstadt, 2026-06-17) nennt den Ort und den Zeitraum 2024-12-04 bis 2025-03-19; Beginn des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=245735&type=do>
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
