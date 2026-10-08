# Geräteuhr: 18_Neuenberger Straße

Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## 23_05_04_Neuenberger Straße.dsd

46.340 Fahrzeuge in 1 Abschnitt(en): 46.340 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2023-03-15 11:36 bis 2023-04-19 19:16 | 46.340 | plausibel |

### 2023-03-15 11:36 bis 2023-04-19 19:16: plausibel (46.340 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.85)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+30 min, Korrelation 0.99)
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.85)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+30 min, Korrelation 0.99)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
