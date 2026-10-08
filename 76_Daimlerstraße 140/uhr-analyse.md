# Geräteuhr: 76_Daimlerstraße 140

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## DSD16135 Tempo30.dsd

38.975 Fahrzeuge in 1 Abschnitt(en): 38.975 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2024-04-22 09:27 bis 2024-07-24 09:40 | 38.975 | plausibel |

### 2024-04-22 09:27 bis 2024-07-24 09:40: plausibel (38.975 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.91)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (-15 min, Korrelation 0.97)
- Begründung: ris: Mitteilung 69/310/2024 (Bezirksausschuss II - Nordstadt, 2024-11-06) nennt den Ort und den Zeitraum 2024-04-22 bis 2024-07-24; Beginn und Ende des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.91)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (-15 min, Korrelation 0.97)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/310/2024 (Bezirksausschuss II - Nordstadt, 2024-11-06) nennt den Ort und den Zeitraum 2024-04-22 bis 2024-07-24; Beginn und Ende des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=215167&type=do>
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
