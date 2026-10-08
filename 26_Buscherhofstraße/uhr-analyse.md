# Geräteuhr: 26_Buscherhofstraße

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## 2023_07_19_17386.dsd

40.064 Fahrzeuge in 2 Abschnitt(en): 40.064 eingeschraenkt.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2023-05-04 15:45 bis 2023-05-08 08:38 | 2.001 | eingeschraenkt |
| 2020-01-01 12:00 bis 2020-03-12 06:07 | 38.063 | eingeschraenkt |

### 2023-05-04 15:45 bis 2023-05-08 08:38: eingeschraenkt, unzureichend belegt (2.001 Fahrzeuge)

- Begründung: nur 0 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (3 volle Tage, nötig 21)
  - Tagesgang: offen. zu wenige Fahrzeuge oder Werktage für den Tagesgang
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge

### 2020-01-01 12:00 bis 2020-03-12 06:07: eingeschraenkt, zurueckgesetzt (38.063 Fahrzeuge)

- Begründung: Uhr nach einem Reset auf das Standarddatum 2020-01-01 12:00 nicht neu gestellt
- Begründung: Die Uhr lief nach dem Reset gleichmäßig weiter: relative Zeiten sind nutzbar, Datum, Wochentag und Uhrzeit müssen rekonstruiert werden
- Belege:
  - Datum: widerspricht. Uhr nach einem Reset auf das Standarddatum 2020-01-01 12:00 nicht neu gestellt
  - Wochenrhythmus: offen. Wochenmuster nicht eindeutig (beste Korrelation 0.72, Abstand 0.30)
  - Tagesgang: widerspricht. Tagesgang um -105 Minuten gegenüber dem typischen Verlauf verschoben
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Datum der Uhr nicht verwertbar
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
- Schätzung, nicht angewendet: Tageszeit -105 Minuten (positiv: Uhr geht vor)
