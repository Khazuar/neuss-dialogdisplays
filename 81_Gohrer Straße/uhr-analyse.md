# Geräteuhr: 81_Gohrer Straße

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## DSD17400 Tempo30_5.dsd

64.807 Fahrzeuge in 4 Abschnitt(en): 64.584 plausibel, 2 eingeschraenkt, 221 unbrauchbar.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2024-12-04 10:24 bis 2025-01-24 10:31 | 28.852 | plausibel |
| 2000-11-30 00:00 bis 2000-11-30 04:30 | 221 | unbrauchbar |
| 2025-01-24 14:49 bis 2025-03-19 15:27 | 35.732 | plausibel |
| 1 weitere Abschnitte | 2 | eingeschraenkt |

### 2024-12-04 10:24 bis 2025-01-24 10:31: plausibel (28.852 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.91)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+15 min, Korrelation 0.96)
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.91)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+15 min, Korrelation 0.96)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: offen. Uhr wurde vor diesem Segment um 55 Minuten zurückgestellt

### 2000-11-30 00:00 bis 2000-11-30 04:30: unbrauchbar (221 Fahrzeuge)

- Begründung: Zeitstempel im Jahr 2000
- Belege:
  - Datum: widerspricht. Zeitstempel im Jahr 2000
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (0 volle Tage, nötig 21)
  - Tagesgang: offen. zu wenige Fahrzeuge oder Werktage für den Tagesgang
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Datum der Uhr nicht verwertbar
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge

### 2025-01-24 14:49 bis 2025-03-19 15:27: plausibel (35.732 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.93)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 0.97)
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.93)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 0.97)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
