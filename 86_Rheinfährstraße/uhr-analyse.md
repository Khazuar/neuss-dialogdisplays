# Geräteuhr: 86_Rheinfährstraße

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## DSD17385 Tempo50_2.dsd

132.188 Fahrzeuge in 1 Abschnitt(en): 132.188 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2025-01-03 10:01 bis 2025-03-19 16:25 | 132.188 | plausibel |

### 2025-01-03 10:01 bis 2025-03-19 16:25: plausibel (132.188 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.99)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (-45 min, Korrelation 0.98)
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.99)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (-45 min, Korrelation 0.98)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
