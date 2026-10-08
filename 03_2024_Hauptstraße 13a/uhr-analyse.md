# Geräteuhr: 03_2024_Hauptstraße 13a

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## DSD17385 Tempo30_3.dsd

131.130 Fahrzeuge in 1 Abschnitt(en): 131.130 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2024-04-22 08:38 bis 2024-07-24 07:15 | 131.130 | plausibel |

### 2024-04-22 08:38 bis 2024-07-24 07:15: plausibel (131.130 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 1.00)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (-15 min, Korrelation 0.98)
- Begründung: ris: Mitteilung 69/309/2024 (Bezirksausschuss IV - Holzheim, 2024-11-05) nennt den Ort und den Zeitraum 2024-04-22 bis 2024-07-24; Beginn und Ende des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 1.00)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (-15 min, Korrelation 0.98)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/309/2024 (Bezirksausschuss IV - Holzheim, 2024-11-05) nennt den Ort und den Zeitraum 2024-04-22 bis 2024-07-24; Beginn und Ende des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=215168&type=do>
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
