# Geräteuhr: 113_Am Leuchtenhof

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## DSD14178 Tempo30_6.dsd

20.698 Fahrzeuge in 1 Abschnitt(en): 20.698 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2026-03-29 11:26 bis 2026-07-29 22:52 | 20.698 | plausibel |

### 2026-03-29 11:26 bis 2026-07-29 22:52: plausibel (20.698 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.90)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 0.96)
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.90)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 0.96)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
