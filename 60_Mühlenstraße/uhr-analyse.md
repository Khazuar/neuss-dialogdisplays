# Geräteuhr: 60_Mühlenstraße

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## DSD 14180 325er.dsd

37.753 Fahrzeuge in 1 Abschnitt(en): 37.753 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2023-12-12 09:07 bis 2024-02-13 15:51 | 37.753 | plausibel |

### 2023-12-12 09:07 bis 2024-02-13 15:51: plausibel (37.753 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.97)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+15 min, Korrelation 0.95)
- Begründung: ris: Mitteilung 69/281/2024 (Bezirksausschuss I - Innenstadt, 2024-06-19) nennt den Ort und den Zeitraum 2023-12-12 bis 2024-03-19; Beginn des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.97)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+15 min, Korrelation 0.95)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/281/2024 (Bezirksausschuss I - Innenstadt, 2024-06-19) nennt den Ort und den Zeitraum 2023-12-12 bis 2024-03-19; Beginn des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=209217&type=do>
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
