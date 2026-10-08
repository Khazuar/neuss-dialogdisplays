# Geräteuhr: 106_Düsseldorfer Straße

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## DSD17400 Tempo50_2.dsd

283.810 Fahrzeuge in 2 Abschnitt(en): 283.810 eingeschraenkt.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2025-10-26 08:38 bis 2026-03-29 07:31 | 283.804 | eingeschraenkt |
| 1 weitere Abschnitte | 6 | eingeschraenkt |

### 2025-10-26 08:38 bis 2026-03-29 07:31: eingeschraenkt, unzureichend belegt (283.804 Fahrzeuge)

- Begründung: nur 1 von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht
- Begründung: ris: Mitteilung 69/0460/2026 (Bezirksausschuss II - Nordstadt, 2026-06-24) nennt den Ort und den Zeitraum 2025-10-26 bis 2026-03-29; Beginn und Ende des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. Wochenmuster nicht eindeutig (beste Korrelation 0.60, Abstand 0.33)
  - Tagesgang: offen. Tagesgang weicht etwas ab (+30 min, Korrelation 0.83)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/0460/2026 (Bezirksausschuss II - Nordstadt, 2026-06-24) nennt den Ort und den Zeitraum 2025-10-26 bis 2026-03-29; Beginn und Ende des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=245759&type=do>
  - Kontinuität: offen. Uhr wurde vor diesem Segment um 51 Minuten zurückgestellt
- Schätzung, nicht angewendet: Tageszeit +30 Minuten (positiv: Uhr geht vor)
