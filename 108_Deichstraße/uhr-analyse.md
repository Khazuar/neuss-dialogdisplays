# Geräteuhr: 108_Deichstraße

Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## DSD16734 Tempo30_7.dsd

27.561 Fahrzeuge in 1 Abschnitt(en): 27.561 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2025-12-03 09:47 bis 2026-03-29 09:08 | 27.561 | plausibel |

### 2025-12-03 09:47 bis 2026-03-29 09:08: plausibel (27.561 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.99)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (-30 min, Korrelation 0.97)
- Begründung: ris: Mitteilung 69/0466/2026 (Bezirksausschuss VII - Uedesheim, 2026-06-25) nennt den Ort und den Zeitraum 2025-10-26 bis 2026-03-29; Ende des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.99)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (-30 min, Korrelation 0.97)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/0466/2026 (Bezirksausschuss VII - Uedesheim, 2026-06-25) nennt den Ort und den Zeitraum 2025-10-26 bis 2026-03-29; Ende des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=246544&type=do>
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
