# Geräteuhr: 105_An der Obererft

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## _19.dsd

259.876 Fahrzeuge in 2 Abschnitt(en): 259.869 plausibel, 7 eingeschraenkt.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2025-10-26 08:19 bis 2026-03-29 07:53 | 259.869 | plausibel |
| 1 weitere Abschnitte | 7 | eingeschraenkt |

### 2025-10-26 08:19 bis 2026-03-29 07:53: plausibel (259.869 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.98)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (-15 min, Korrelation 0.99)
- Begründung: ris: Mitteilung 69/0459/2026 (Bezirksausschuss I - Innenstadt, 2026-06-17) nennt den Ort und den Zeitraum 2025-10-26 bis 2026-03-29; Beginn und Ende des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.98)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (-15 min, Korrelation 0.99)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/0459/2026 (Bezirksausschuss I - Innenstadt, 2026-06-17) nennt den Ort und den Zeitraum 2025-10-26 bis 2026-03-29; Beginn und Ende des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=245735&type=do>
  - Kontinuität: offen. Uhr wurde vor diesem Segment um 53 Minuten zurückgestellt
