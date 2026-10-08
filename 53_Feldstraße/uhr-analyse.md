# Geräteuhr: 53_Feldstraße

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## DSD16733 Tempo30_3.dsd

27.543 Fahrzeuge in 2 Abschnitt(en): 27.543 eingeschraenkt.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2023-01-31 13:57 bis 2023-03-15 09:47 | 27.535 | eingeschraenkt |
| 1 weitere Abschnitte | 8 | eingeschraenkt |

### 2023-01-31 13:57 bis 2023-03-15 09:47: eingeschraenkt, unzureichend belegt (27.535 Fahrzeuge)

- Begründung: nur 0 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. Wochenmuster nicht eindeutig (beste Korrelation 0.67, Abstand 0.30)
  - Tagesgang: offen. Tagesgang weicht etwas ab (-15 min, Korrelation 0.87)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: offen. Uhr wurde vor diesem Segment um 50 Minuten zurückgestellt
- Schätzung, nicht angewendet: Tageszeit -15 Minuten (positiv: Uhr geht vor)
