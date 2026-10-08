# Geräteuhr: 07_Lupinen_Nierenhofstraße

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## _4.dsd

174.909 Fahrzeuge in 1 Abschnitt(en): 174.909 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2023-11-16 16:06 bis 2024-03-19 08:37 | 174.909 | plausibel |

### 2023-11-16 16:06 bis 2024-03-19 08:37: plausibel (174.909 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.75)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+15 min, Korrelation 0.99)
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.75)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+15 min, Korrelation 0.99)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in 1 Mitteilung(en) genannt, aber kein Zeitraum passt zum Segment
  - Kontinuität: offen. Uhr wurde vor diesem Segment um 54 Minuten zurückgestellt
