# Geräteuhr: 116_Martinstraße

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## DSD16734 Tempo30_8.dsd

151.706 Fahrzeuge in 1 Abschnitt(en): 151.706 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2026-03-29 09:09 bis 2026-08-02 09:42 | 151.706 | plausibel |

### 2026-03-29 09:09 bis 2026-08-02 09:42: plausibel (151.706 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.96)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 0.99)
- Begründung: ris: Mitteilung 69/0488/2026 (Bezirksausschuss IV - Holzheim, 2026-12-02) nennt den Ort und den Zeitraum 2026-03-29 bis 2026-08-02; Beginn und Ende des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.96)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 0.99)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/0488/2026 (Bezirksausschuss IV - Holzheim, 2026-12-02) nennt den Ort und den Zeitraum 2026-03-29 bis 2026-08-02; Beginn und Ende des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=255803&type=do>
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
