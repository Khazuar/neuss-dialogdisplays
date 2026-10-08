# Geräteuhr: 13_2024_Neukirchener Straße

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## DSD17350 Tempo30_2.dsd

103.375 Fahrzeuge in 1 Abschnitt(en): 103.375 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2024-09-16 14:14 bis 2024-12-04 12:25 | 103.375 | plausibel |

### 2024-09-16 14:14 bis 2024-12-04 12:25: plausibel (103.375 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.96)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (-30 min, Korrelation 0.98)
- Begründung: zeitumstellung: Sprung im Verkehrsgang liegt am amtlichen Umstellungstag 2024-10-27 (Abweichung +0 Tage, 100% der Tage passen): Datum auf den Tag genau verankert; Tagesgang passt über 1 Zeitumstellung(en) nach der Korrektur
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.96)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (-30 min, Korrelation 0.98)
  - Zeitumstellung: bestätigt. Sprung im Verkehrsgang liegt am amtlichen Umstellungstag 2024-10-27 (Abweichung +0 Tage, 100% der Tage passen): Datum auf den Tag genau verankert; Tagesgang passt über 1 Zeitumstellung(en) nach der Korrektur
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
