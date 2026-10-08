# Geräteuhr: 97_Preußenstraße

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## _18.dsd

162.620 Fahrzeuge in 1 Abschnitt(en): 162.620 plausibel.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2025-07-06 07:56 bis 2025-10-26 09:00 | 162.620 | plausibel |

### 2025-07-06 07:56 bis 2025-10-26 09:00: plausibel (162.620 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt zu den Kalendertagen (Korrelation 0.98)
- Begründung: tagesgang: Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 0.99)
- Begründung: ris: Mitteilung 69/0459/2026 (Bezirksausschuss I - Innenstadt, 2026-06-17) nennt den Ort und den Zeitraum 2025-07-06 bis 2025-10-26; Beginn und Ende des Abschnitts stimmt(en) auf den Tag überein
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: bestätigt. Wochenmuster passt zu den Kalendertagen (Korrelation 0.98)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 0.99)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/0459/2026 (Bezirksausschuss I - Innenstadt, 2026-06-17) nennt den Ort und den Zeitraum 2025-07-06 bis 2025-10-26; Beginn und Ende des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=245735&type=do>
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
