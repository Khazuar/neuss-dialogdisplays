# Geräteuhr: 88_Pomona (Eingang)

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## _17.dsd

52.496 Fahrzeuge in 1 Abschnitt(en): 52.496 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2025-03-19 15:13 bis 2025-07-06 07:50 | 52.496 | plausibel |

### 2025-03-19 15:13 bis 2025-07-06 07:50: plausibel (52.496 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.99)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+45 min, Korrelation 0.97)
- Begründung: ris: Mitteilung 69/0459/2026 (Bezirksausschuss I - Innenstadt, 2026-06-17) nennt den Ort und den Zeitraum 2025-03-19 bis 2025-07-06; Beginn und Ende des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.99)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+45 min, Korrelation 0.97)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/0459/2026 (Bezirksausschuss I - Innenstadt, 2026-06-17) nennt den Ort und den Zeitraum 2025-03-19 bis 2025-07-06; Beginn und Ende des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=245735&type=do>
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
