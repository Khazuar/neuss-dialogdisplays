# Geräteuhr: 06_Rosellener Schulstraße

Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## _7.dsd

34.608 Fahrzeuge in 2 Abschnitt(en): 34.608 eingeschraenkt.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2023-05-04 17:02 bis 2023-05-08 09:31 | 1.021 | eingeschraenkt |
| 2020-01-01 12:00 bis 2020-03-12 06:40 | 33.587 | eingeschraenkt |

### 2023-05-04 17:02 bis 2023-05-08 09:31: eingeschraenkt, unzureichend belegt (1.021 Fahrzeuge)

- Begründung: nur 0 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (3 volle Tage, nötig 21)
  - Tagesgang: offen. zu wenige Fahrzeuge oder Werktage für den Tagesgang
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge

### 2020-01-01 12:00 bis 2020-03-12 06:40: eingeschraenkt, zurueckgesetzt (33.587 Fahrzeuge)

- Begründung: Uhr nach einem Reset auf das Standarddatum 2020-01-01 12:00 nicht neu gestellt
- Begründung: Die Uhr lief nach dem Reset gleichmäßig weiter: relative Zeiten sind nutzbar, Datum, Wochentag und Uhrzeit müssen rekonstruiert werden
- Belege:
  - Datum: widerspricht. Uhr nach einem Reset auf das Standarddatum 2020-01-01 12:00 nicht neu gestellt
  - Wochenrhythmus: widerspricht. Wochenmuster passt erst, wenn das Datum der Uhr um 1 Tag(e) später liegt als der wahre Tag (Korrelation 0.95)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (-60 min, Korrelation 0.94)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Datum der Uhr nicht verwertbar
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
- Schätzung, nicht angewendet: Datum der Uhr 1 Tag(e) hinter dem wahren Tag (mod 7)
