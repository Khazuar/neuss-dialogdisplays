# Geräteuhr: 55_Alte Uferstraße

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## _2.dsd

22.886 Fahrzeuge in 1 Abschnitt(en): 22.886 eingeschraenkt.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2023-05-04 14:30 bis 2023-07-19 08:20 | 22.886 | eingeschraenkt |

### 2023-05-04 14:30 bis 2023-07-19 08:20: eingeschraenkt, unzureichend belegt (22.886 Fahrzeuge)

- Begründung: nur 0 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. Wochenmuster nicht eindeutig (beste Korrelation 0.81, Abstand 0.15)
  - Tagesgang: offen. Tagesgang weicht etwas ab (+60 min, Korrelation 0.87)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
- Schätzung, nicht angewendet: Tageszeit +60 Minuten (positiv: Uhr geht vor)
