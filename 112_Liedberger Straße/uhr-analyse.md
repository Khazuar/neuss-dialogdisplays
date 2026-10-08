# Geräteuhr: 112_Liedberger Straße

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## DSD14178 Tempo30_5.dsd

32.072 Fahrzeuge in 1 Abschnitt(en): 32.072 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2025-10-26 09:10 bis 2026-01-17 09:05 | 32.072 | plausibel |

### 2025-10-26 09:10 bis 2026-01-17 09:05: plausibel (32.072 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.96)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+15 min, Korrelation 0.97)
- Begründung: ris: Mitteilung 69/0463/2026 (Bezirksausschuss IV - Holzheim, 2026-06-16) nennt den Ort und den Zeitraum 2025-10-26 bis 2026-03-29; Beginn des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.96)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+15 min, Korrelation 0.97)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/0463/2026 (Bezirksausschuss IV - Holzheim, 2026-06-16) nennt den Ort und den Zeitraum 2025-10-26 bis 2026-03-29; Beginn des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=245761&type=do>
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
