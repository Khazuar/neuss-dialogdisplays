# Geräteuhr: 94_Ruhrstraße

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## DSD17350 Tempo30_4.dsd

90.290 Fahrzeuge in 1 Abschnitt(en): 90.290 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2025-04-17 14:02 bis 2025-07-06 10:04 | 90.290 | plausibel |

### 2025-04-17 14:02 bis 2025-07-06 10:04: plausibel (90.290 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.89)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+30 min, Korrelation 0.99)
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.89)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+30 min, Korrelation 0.99)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in 1 Mitteilung(en) genannt, aber kein Zeitraum passt zum Segment
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
