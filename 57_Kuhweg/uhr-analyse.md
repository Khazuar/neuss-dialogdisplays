# Geräteuhr: 57_Kuhweg

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## _8.dsd

169.444 Fahrzeuge in 4 Abschnitt(en): 24.372 plausibel, 145.072 eingeschraenkt.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2023-07-19 08:06 bis 2023-09-07 16:59 | 24.372 | plausibel |
| 2020-01-01 12:00 bis 2020-02-01 23:33 | 77.317 | eingeschraenkt |
| 2020-01-01 12:00 bis 2020-01-01 17:32 | 887 | eingeschraenkt |
| 2020-01-01 12:00 bis 2020-01-29 09:28 | 66.868 | eingeschraenkt |

### 2023-07-19 08:06 bis 2023-09-07 16:59: plausibel (24.372 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.78)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 0.91)
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.78)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 0.91)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge

### 2020-01-01 12:00 bis 2020-02-01 23:33: eingeschraenkt, zurueckgesetzt (77.317 Fahrzeuge)

- Begründung: Uhr nach einem Reset auf das Standarddatum 2020-01-01 12:00 nicht neu gestellt
- Begründung: Die Uhr lief nach dem Reset gleichmäßig weiter: relative Zeiten sind nutzbar, Datum, Wochentag und Uhrzeit müssen rekonstruiert werden
- Belege:
  - Datum: widerspricht. Uhr nach einem Reset auf das Standarddatum 2020-01-01 12:00 nicht neu gestellt
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.93)
  - Tagesgang: widerspricht. Tagesgang um -480 Minuten gegenüber dem typischen Verlauf verschoben
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Datum der Uhr nicht verwertbar
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
- Schätzung, nicht angewendet: Tageszeit -480 Minuten (positiv: Uhr geht vor)

### 2020-01-01 12:00 bis 2020-01-01 17:32: eingeschraenkt, zurueckgesetzt (887 Fahrzeuge)

- Begründung: Uhr nach einem Reset auf das Standarddatum 2020-01-01 12:00 nicht neu gestellt
- Begründung: Die Uhr lief nach dem Reset gleichmäßig weiter: relative Zeiten sind nutzbar, Datum, Wochentag und Uhrzeit müssen rekonstruiert werden
- Belege:
  - Datum: widerspricht. Uhr nach einem Reset auf das Standarddatum 2020-01-01 12:00 nicht neu gestellt
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (0 volle Tage, nötig 21)
  - Tagesgang: offen. zu wenige Fahrzeuge oder Werktage für den Tagesgang
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Datum der Uhr nicht verwertbar
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge

### 2020-01-01 12:00 bis 2020-01-29 09:28: eingeschraenkt, zurueckgesetzt (66.868 Fahrzeuge)

- Begründung: Uhr nach einem Reset auf das Standarddatum 2020-01-01 12:00 nicht neu gestellt
- Begründung: Die Uhr lief nach dem Reset gleichmäßig weiter: relative Zeiten sind nutzbar, Datum, Wochentag und Uhrzeit müssen rekonstruiert werden
- Belege:
  - Datum: widerspricht. Uhr nach einem Reset auf das Standarddatum 2020-01-01 12:00 nicht neu gestellt
  - Wochenrhythmus: widerspricht. Wochenmuster passt erst, wenn das Datum der Uhr um 6 Tag(e) später liegt als der wahre Tag (Korrelation 0.93)
  - Tagesgang: widerspricht. Tagesgang um -375 Minuten gegenüber dem typischen Verlauf verschoben
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Datum der Uhr nicht verwertbar
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
- Schätzung, nicht angewendet: Datum der Uhr 6 Tag(e) hinter dem wahren Tag (mod 7); Tageszeit -375 Minuten (positiv: Uhr geht vor)
