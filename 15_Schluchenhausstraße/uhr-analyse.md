# Geräteuhr: 15_Schluchenhausstraße

Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## _7.dsd

11.401 Fahrzeuge in 1 Abschnitt(en): 11.401 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2023-01-31 13:00 bis 2023-03-15 11:46 | 11.401 | plausibel |

### 2023-01-31 13:00 bis 2023-03-15 11:46: plausibel (11.401 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.88)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+60 min, Korrelation 0.95)
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.88)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+60 min, Korrelation 0.95)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
