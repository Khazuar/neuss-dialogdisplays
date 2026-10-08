# Geräteuhr: 84_Am Alten Bach

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## _7.dsd

84.076 Fahrzeuge in 3 Abschnitt(en): 66.595 plausibel, 17.262 eingeschraenkt, 219 unbrauchbar.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2024-12-13 08:54 bis 2025-02-26 15:53 | 66.595 | plausibel |
| 2024-12-30 01:43 bis 2024-12-30 04:30 | 219 | unbrauchbar |
| 2025-02-26 18:45 bis 2025-03-19 15:46 | 17.262 | eingeschraenkt |

### 2024-12-13 08:54 bis 2025-02-26 15:53: plausibel (66.595 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.77)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (-30 min, Korrelation 0.97)
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.77)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (-30 min, Korrelation 0.97)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge

### 2024-12-30 01:43 bis 2024-12-30 04:30: unbrauchbar (219 Fahrzeuge)

- Begründung: Zeitstempel springen um 59 Tage zurück
- Belege:
  - Datum: widerspricht. Zeitstempel springen um 59 Tage zurück
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (0 volle Tage, nötig 21)
  - Tagesgang: offen. zu wenige Fahrzeuge oder Werktage für den Tagesgang
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Datum der Uhr nicht verwertbar
  - Kontinuität: offen. Uhr wurde vor diesem Segment um 84369 Minuten zurückgestellt

### 2025-02-26 18:45 bis 2025-03-19 15:46: eingeschraenkt, unzureichend belegt (17.262 Fahrzeuge)

- Begründung: nur 1 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (-15 min, Korrelation 0.98)
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. zu kurz für das Wochenmuster (20 volle Tage, nötig 21)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (-15 min, Korrelation 0.98)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
