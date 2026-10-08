# Geräteuhr: 14_2024_Salzstraße

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## DSD17385 Tempo30_4.dsd

117.136 Fahrzeuge in 2 Abschnitt(en): 117.136 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2024-07-24 07:16 bis 2024-09-04 15:30 | 56.797 | plausibel |
| 2024-09-12 10:37 bis 2024-12-04 10:16 | 60.339 | plausibel |

### 2024-07-24 07:16 bis 2024-09-04 15:30: plausibel (56.797 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 1.00)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (-15 min, Korrelation 0.98)
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 1.00)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (-15 min, Korrelation 0.98)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge

### 2024-09-12 10:37 bis 2024-12-04 10:16: plausibel (60.339 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.96)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 0.98)
- Begründung: zeitumstellung: Sprung im Verkehrsgang liegt am amtlichen Umstellungstag 2024-10-27 (Abweichung +1 Tage, 100% der Tage passen): Datum auf den Tag genau verankert; Tagesgang passt über 1 Zeitumstellung(en) nach der Korrektur
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.96)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 0.98)
  - Zeitumstellung: bestätigt. Sprung im Verkehrsgang liegt am amtlichen Umstellungstag 2024-10-27 (Abweichung +1 Tage, 100% der Tage passen): Datum auf den Tag genau verankert; Tagesgang passt über 1 Zeitumstellung(en) nach der Korrektur
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
