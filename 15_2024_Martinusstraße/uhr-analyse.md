# Geräteuhr: 15_2024_Martinusstraße

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## DSD 14178 325er_2.dsd

21.063 Fahrzeuge in 1 Abschnitt(en): 21.063 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2024-07-24 07:28 bis 2024-11-22 13:29 | 21.063 | plausibel |

### 2024-07-24 07:28 bis 2024-11-22 13:29: plausibel (21.063 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.96)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+30 min, Korrelation 0.95)
- Begründung: zeitumstellung: Sprung im Verkehrsgang liegt am amtlichen Umstellungstag 2024-10-27 (Abweichung +1 Tage, 100% der Tage passen): Datum auf den Tag genau verankert; Tagesgang passt über 1 Zeitumstellung(en) nach der Korrektur
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.96)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+30 min, Korrelation 0.95)
  - Zeitumstellung: bestätigt. Sprung im Verkehrsgang liegt am amtlichen Umstellungstag 2024-10-27 (Abweichung +1 Tage, 100% der Tage passen): Datum auf den Tag genau verankert; Tagesgang passt über 1 Zeitumstellung(en) nach der Korrektur
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
