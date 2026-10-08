# Geräteuhr: 107_Konradstraße

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## DSD14180 Tempo30_5.dsd

23.611 Fahrzeuge in 1 Abschnitt(en): 23.611 eingeschraenkt.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2025-12-03 09:17 bis 2026-03-25 17:53 | 23.611 | eingeschraenkt |

### 2025-12-03 09:17 bis 2026-03-25 17:53: eingeschraenkt, unzureichend belegt (23.611 Fahrzeuge)

- Begründung: nur 1 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.93)
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.93)
  - Tagesgang: offen. Tagesgang weicht etwas ab (+0 min, Korrelation 0.88)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
- Schätzung, nicht angewendet: Tageszeit +0 Minuten (positiv: Uhr geht vor)
