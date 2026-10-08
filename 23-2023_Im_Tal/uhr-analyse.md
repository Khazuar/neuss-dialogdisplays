# Geräteuhr: 23-2023_Im_Tal

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## DSD16734 Tempo30_3.dsd

19.669 Fahrzeuge in 1 Abschnitt(en): 19.669 eingeschraenkt.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2024-05-06 07:08 bis 2024-07-24 09:24 | 19.669 | eingeschraenkt |

### 2024-05-06 07:08 bis 2024-07-24 09:24: eingeschraenkt, unzureichend belegt (19.669 Fahrzeuge)

- Begründung: nur 1 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.83)
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.83)
  - Tagesgang: offen. Gerät lief nur zu 50% der Zeit (Heartbeat), der Tagesgang ist abgeschnitten und nicht beurteilbar
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: offen. Gerät lief nur zu 50% der Zeit (Heartbeat), Aufzeichnungslücken
