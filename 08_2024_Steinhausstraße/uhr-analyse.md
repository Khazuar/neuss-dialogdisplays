# Geräteuhr: 08_2024_Steinhausstraße

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## DSD17386 Tempo30_3.dsd

117.092 Fahrzeuge in 1 Abschnitt(en): 117.092 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2024-07-24 08:35 bis 2024-12-04 09:56 | 117.092 | plausibel |

### 2024-07-24 08:35 bis 2024-12-04 09:56: plausibel (117.092 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.94)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (-15 min, Korrelation 0.98)
- Begründung: zeitumstellung: Sprung im Verkehrsgang liegt am amtlichen Umstellungstag 2024-10-27 (Abweichung +0 Tage, 100% der Tage passen): Datum auf den Tag genau verankert; Tagesgang passt über 1 Zeitumstellung(en) nach der Korrektur
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.94)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (-15 min, Korrelation 0.98)
  - Zeitumstellung: bestätigt. Sprung im Verkehrsgang liegt am amtlichen Umstellungstag 2024-10-27 (Abweichung +0 Tage, 100% der Tage passen): Datum auf den Tag genau verankert; Tagesgang passt über 1 Zeitumstellung(en) nach der Korrektur
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
