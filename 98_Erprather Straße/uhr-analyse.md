# Geräteuhr: 98_Erprather Straße

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## DSD17400 Tempo50.dsd

191.480 Fahrzeuge in 1 Abschnitt(en): 191.480 eingeschraenkt.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2025-07-18 10:00 bis 2025-10-26 09:21 | 191.480 | eingeschraenkt |

### 2025-07-18 10:00 bis 2025-10-26 09:21: eingeschraenkt, unzureichend belegt (191.480 Fahrzeuge)

- Begründung: nur 0 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. Wochenmuster nicht eindeutig (beste Korrelation 0.47, Abstand 0.12)
  - Tagesgang: offen. Tagesgang weicht etwas ab (+45 min, Korrelation 0.86)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
- Schätzung, nicht angewendet: Tageszeit +45 Minuten (positiv: Uhr geht vor)
