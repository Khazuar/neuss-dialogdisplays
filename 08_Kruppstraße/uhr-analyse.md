# Geräteuhr: 08_Kruppstraße

Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## DSD16735_6.dsd

100.815 Fahrzeuge in 2 Abschnitt(en): 100.815 eingeschraenkt.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2020-01-09 13:59 bis 2020-01-09 15:37 | 88 | eingeschraenkt |
| 2022-10-16 22:08 bis 2023-01-31 12:26 | 100.727 | eingeschraenkt |

### 2020-01-09 13:59 bis 2020-01-09 15:37: eingeschraenkt, unzureichend belegt (88 Fahrzeuge)

- Begründung: nur 0 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (0 volle Tage, nötig 21)
  - Tagesgang: offen. zu wenige Fahrzeuge oder Werktage für den Tagesgang
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge

### 2022-10-16 22:08 bis 2023-01-31 12:26: eingeschraenkt, widerspruch (100.727 Fahrzeuge)

- Begründung: zeitumstellung: Tagesgang springt bei der Zeitumstellung am 2022-10-30 um -105 Minuten (Ferien oder verstellte Uhr)
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.97)
  - Tagesgang: offen. Gerät lief nur zu 67% der Zeit (Heartbeat), der Tagesgang ist abgeschnitten und nicht beurteilbar
  - Zeitumstellung: widerspricht. Tagesgang springt bei der Zeitumstellung am 2022-10-30 um -105 Minuten (Ferien oder verstellte Uhr)
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: offen. Gerät lief nur zu 67% der Zeit (Heartbeat), Aufzeichnungslücken
