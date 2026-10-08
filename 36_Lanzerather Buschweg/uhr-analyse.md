# Geräteuhr: 36_Lanzerather Buschweg

Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## DSD 14178 325er.dsd

14.399 Fahrzeuge in 1 Abschnitt(en): 14.399 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2024-04-22 09:20 bis 2024-07-24 07:11 | 14.399 | plausibel |

### 2024-04-22 09:20 bis 2024-07-24 07:11: plausibel (14.399 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.94)
- Begründung: ris: Mitteilung 69/309/2024 (Bezirksausschuss IV - Holzheim, 2024-11-05) nennt den Ort und den Zeitraum 2024-04-22 bis 2024-07-24; Beginn und Ende des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.94)
  - Tagesgang: offen. Tagesgang weicht etwas ab (+75 min, Korrelation 0.93)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/309/2024 (Bezirksausschuss IV - Holzheim, 2024-11-05) nennt den Ort und den Zeitraum 2024-04-22 bis 2024-07-24; Beginn und Ende des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=215168&type=do>
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
- Schätzung, nicht angewendet: Tageszeit +75 Minuten (positiv: Uhr geht vor)
