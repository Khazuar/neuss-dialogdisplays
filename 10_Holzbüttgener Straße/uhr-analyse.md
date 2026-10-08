# Geräteuhr: 10_Holzbüttgener Straße

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## _6.dsd

59.857 Fahrzeuge in 1 Abschnitt(en): 59.857 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2023-07-19 09:20 bis 2023-11-16 17:24 | 59.857 | plausibel |

### 2023-07-19 09:20 bis 2023-11-16 17:24: plausibel (59.857 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.97)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 0.99)
- Begründung: zeitumstellung: Tagesgang passt über 1 Zeitumstellung(en) nach der Korrektur
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.97)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 0.99)
  - Zeitumstellung: bestätigt. Tagesgang passt über 1 Zeitumstellung(en) nach der Korrektur
  - Mitteilungen der Verwaltung: offen. Ort in 1 Mitteilung(en) genannt, aber kein Zeitraum passt zum Segment
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
