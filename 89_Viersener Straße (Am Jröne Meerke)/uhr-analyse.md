# Geräteuhr: 89_Viersener Straße (Am Jröne Meerke)

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## DSD17386 Tempo30_5.dsd

128.623 Fahrzeuge in 3 Abschnitt(en): 128.388 eingeschraenkt, 235 unbrauchbar.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2025-05-15 07:55 bis 2025-05-29 18:42 | 35.749 | eingeschraenkt |
| 2000-11-30 00:00 bis 2000-11-30 04:30 | 235 | unbrauchbar |
| 2025-05-29 20:26 bis 2025-07-06 08:22 | 92.639 | eingeschraenkt |

### 2025-05-15 07:55 bis 2025-05-29 18:42: eingeschraenkt, unzureichend belegt (35.749 Fahrzeuge)

- Begründung: nur 0 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (13 volle Tage, nötig 21)
  - Tagesgang: offen. Tagesgang weicht etwas ab (+60 min, Korrelation 0.86)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
- Schätzung, nicht angewendet: Tageszeit +60 Minuten (positiv: Uhr geht vor)

### 2000-11-30 00:00 bis 2000-11-30 04:30: unbrauchbar (235 Fahrzeuge)

- Begründung: Zeitstempel im Jahr 2000
- Belege:
  - Datum: widerspricht. Zeitstempel im Jahr 2000
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (0 volle Tage, nötig 21)
  - Tagesgang: offen. zu wenige Fahrzeuge oder Werktage für den Tagesgang
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Datum der Uhr nicht verwertbar
  - Kontinuität: offen. Gerät lief nur zu 37% der Zeit (Heartbeat), Aufzeichnungslücken

### 2025-05-29 20:26 bis 2025-07-06 08:22: eingeschraenkt, unzureichend belegt (92.639 Fahrzeuge)

- Begründung: nur 0 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. Wochenmuster nicht eindeutig (beste Korrelation 0.44, Abstand 0.02)
  - Tagesgang: offen. Tagesgang weicht etwas ab (+75 min, Korrelation 0.82)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
- Schätzung, nicht angewendet: Tageszeit +75 Minuten (positiv: Uhr geht vor)

## DSD17386 Tempo50_3.dsd

128.645 Fahrzeuge in 1 Abschnitt(en): 128.645 eingeschraenkt.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2025-03-19 14:19 bis 2025-05-15 07:55 | 128.645 | eingeschraenkt |

### 2025-03-19 14:19 bis 2025-05-15 07:55: eingeschraenkt, unzureichend belegt (128.645 Fahrzeuge)

- Begründung: nur 0 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. Wochenmuster nicht eindeutig (beste Korrelation 0.67, Abstand 0.00)
  - Tagesgang: offen. Tagesgang weicht etwas ab (+30 min, Korrelation 0.90)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
- Schätzung, nicht angewendet: Tageszeit +30 Minuten (positiv: Uhr geht vor)
