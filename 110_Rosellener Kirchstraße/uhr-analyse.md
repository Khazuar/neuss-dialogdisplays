# Geräteuhr: 110_Rosellener Kirchstraße

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## DSD17350 Tempo30_6.dsd

134.771 Fahrzeuge in 1 Abschnitt(en): 134.771 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2025-12-03 09:20 bis 2026-03-29 08:43 | 134.771 | plausibel |

### 2025-12-03 09:20 bis 2026-03-29 08:43: plausibel (134.771 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.99)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 1.00)
- Begründung: ris: Mitteilung 69/0462/2026 (Bezirksausschuss VIII - Rosellen, 2026-07-07) nennt den Ort und den Zeitraum 2025-10-26 bis 2026-03-29; Ende des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.99)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 1.00)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/0462/2026 (Bezirksausschuss VIII - Rosellen, 2026-07-07) nennt den Ort und den Zeitraum 2025-10-26 bis 2026-03-29; Ende des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=246955&type=do>
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
