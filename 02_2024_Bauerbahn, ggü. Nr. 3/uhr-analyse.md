# Geräteuhr: 02_2024_Bauerbahn, ggü. Nr. 3

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## 20 km.dsd

47.453 Fahrzeuge in 1 Abschnitt(en): 47.453 eingeschraenkt.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2024-04-25 18:14 bis 2024-07-24 06:43 | 47.453 | eingeschraenkt |

### 2024-04-25 18:14 bis 2024-07-24 06:43: eingeschraenkt, widerspruch (47.453 Fahrzeuge)

- Begründung: tagesgang: Tagesgang um +90 Minuten gegenüber dem typischen Verlauf verschoben
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: offen. Wochenmuster nicht eindeutig (beste Korrelation 0.38, Abstand 0.05)
  - Tagesgang: widerspricht. Tagesgang um +90 Minuten gegenüber dem typischen Verlauf verschoben
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: bestätigt. Mitteilung 69/313/2024 (Bezirksausschuss I - Innenstadt, 2024-12-04) nennt den Ort und den Zeitraum 2024-04-23 bis 2024-07-23; Ende des Abschnitts stimmt(en) auf den Tag überein Quelle: <https://ris-neuss.itk-rheinland.de/sessionnetneubi/getfile.asp?id=217893&type=do>
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
- Schätzung, nicht angewendet: Tageszeit +90 Minuten (positiv: Uhr geht vor)
