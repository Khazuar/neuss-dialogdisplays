# Geräteuhr: 59_Nierenhofstraße

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## _8.dsd

83.902 Fahrzeuge in 1 Abschnitt(en): 83.902 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2023-07-19 09:37 bis 2023-11-16 14:55 | 83.902 | plausibel |

### 2023-07-19 09:37 bis 2023-11-16 14:55: plausibel (83.902 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.95)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 0.99)
- Begründung: zeitumstellung: Tagesgang passt über 1 Zeitumstellung(en) nach der Korrektur
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.95)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 0.99)
  - Zeitumstellung: bestätigt. Tagesgang passt über 1 Zeitumstellung(en) nach der Korrektur
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
