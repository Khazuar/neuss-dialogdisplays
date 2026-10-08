# Geräteuhr: 92_Konradstraße

Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen in `uhr_belege.py` und `docs/uhr-bewertung.md`.

## DSD16734 Tempo30_5.dsd

30.233 Fahrzeuge in 1 Abschnitt(en): 30.233 eingeschraenkt.

| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |
|---|---:|---|
| 2025-05-09 13:00 bis 2025-07-06 09:11 | 30.233 | eingeschraenkt |

### 2025-05-09 13:00 bis 2025-07-06 09:11: eingeschraenkt, widerspruch (30.233 Fahrzeuge)

- Begründung: wochenrhythmus: Wochenmuster passt erst, wenn das Datum der Uhr um 5 Tag(e) später liegt als der wahre Tag (Korrelation 0.85)
- Belege:
  - Datum: bestätigt. Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum
  - Wochenrhythmus: widerspricht. Wochenmuster passt erst, wenn das Datum der Uhr um 5 Tag(e) später liegt als der wahre Tag (Korrelation 0.85)
  - Tagesgang: bestätigt. Tagesgang entspricht dem typischen Verlauf (+0 min, Korrelation 0.94)
  - Zeitumstellung: offen. keine Zeitumstellung im Segment mit genug Daten davor und danach
  - Mitteilungen der Verwaltung: offen. Ort in keiner Mitteilung mit Erfassungszeitraum genannt
  - Kontinuität: bestätigt. Heartbeat lückenlos, keine Uhrsprünge
- Schätzung, nicht angewendet: Datum der Uhr 5 Tag(e) hinter dem wahren Tag (mod 7)
