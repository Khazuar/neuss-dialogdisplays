# Geräteuhr: 21_Hermannstraße

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## 0000000000000000_6.dsd

39.292 Fahrzeuge in 1 Abschnitt(en): 39.292 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2023-07-19 09:33 bis 2023-09-15 07:55 | 39.292 | plausibel |

### 2023-07-19 09:33 bis 2023-09-15 07:55: plausibel (39.292 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 1.00)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 0.98)
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 1.00)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 0.98)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
