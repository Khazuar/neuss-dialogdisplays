# Geräteuhr: 95_Reuschenberger Straße

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## DSD17385 Tempo30_6.dsd

171.843 Fahrzeuge in 1 Abschnitt(en): 171.843 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2025-04-17 13:32 bis 2025-07-06 09:38 | 171.843 | plausibel |

### 2025-04-17 13:32 bis 2025-07-06 09:38: plausibel (171.843 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.98)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (-30 min, Korrelation 0.98)
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.98)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (-30 min, Korrelation 0.98)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
