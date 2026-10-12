# Wetterdaten

> Eigene Auswertung; Fehler können nicht ausgeschlossen werden (ohne Gewähr). Das ist keine Rechtsberatung.

Die Geschwindigkeitsmessungen hängen vom Wetter ab, auf zwei Arten: Das Radar der Geräte reagiert auf Regen (Störsignal), und
die Verkehrsteilnehmer reagieren auf das Wetter (Verkehrsmittelwahl, Tempo). `wetter.py` erzeugt aus öffentlichen Daten des
Deutschen Wetterdienstes (DWD) eine kleine Tabelle, `belege/wetter.json`, die diese Zusammenhänge zu untersuchen erlaubt.

## Quelle und Lizenz

**Quelle:** Deutscher Wetterdienst (DWD), Climate Data Center, <https://opendata.dwd.de/climate_environment/CDC/>:
stündlicher Niederschlag (`hourly/precipitation`) und Tageswerte der Klimastation Düsseldorf (`daily/kl`).

**Lizenz: CC BY 4.0, nicht CC0.** Der DWD schreibt auf seiner Seite „Rechtliche Hinweise“
(<https://www.dwd.de/DE/service/rechtliche_hinweise/rechtliche_hinweise_node.html>, abgerufen am 12.10.2026): Die vom DWD veröffentlichten
Inhalte unterliegen dem Urheber- und Leistungsschutzrecht, eine Weiterverwendung ist „ausschließlich unter den Bedingungen der
Creative-Commons-Lizenz BY 4.0 sowie unter Angabe einer ordnungsgemäßen Quellenkennzeichnung zulässig“. „Alle frei zugänglichen
Geodaten […] dürfen unter den Bedingungen der Lizenz Creative Commons BY 4.0 unter Beigabe eines Quellenvermerks
weiterverwendet werden. Zu den Geodaten zählen alle bereitgestellten meteorologischen Wetter- und Klimainformationen mit
Ortsbezug.“ Die Beschreibung des Datensatzes selbst nennt dieselbe Lizenz („Es gelten die Bedingungen der Lizenz Creative Commons BY
4.0“) und sagt, die Daten stammen von Stationen des DWD „und rechtlich sowie qualitativ gleichgestellten Partnernetzen“. Ob
Messwerte für sich genommen geschützt sind, ist deshalb hier nicht zu entscheiden: Die Lizenz erlaubt die Weiterverwendung und
Wiederveröffentlichung, auch geändert, mit Quellenvermerk.

Was das für dieses Repository heißt:

- `belege/wetter.json` steht unter **CC BY 4.0**, nicht unter CC0 (Ausnahme zur Lizenz der übrigen Daten, siehe README). Die Datei trägt
  Quelle, Lizenz, Vermerk und Änderungshinweis im eigenen Kopf.
- **Quellenvermerk** nach den Vorgaben des DWD (<https://www.dwd.de/DE/service/rechtliche_hinweise/vorlagen_quellenangabe.html>):
  „Quelle: Deutscher Wetterdienst“. Er steht unmittelbar an der verwendeten Information; bei Änderungen („Datenbasis: Deutscher
  Wetterdienst, …“) und bei weitergehender Bearbeitung mindestens in einem zentralen Quellenverzeichnis oder im Impressum.
  Auswertungen, die Wetterdaten verwenden, nennen den DWD deshalb ebenfalls.
- Der DWD-Server muss nicht mehr abgefragt werden: Die Tabelle liegt im Repository, der Build lädt nichts herunter.

## Inhalt von `belege/wetter.json`

Je Kalendertag (Ortszeit) von 2022-03-01 bis 2026-09-01 (1 646 Tage; die nutzbaren Messungen liegen zwischen 2022-03-31 und 2026-08-01):

| Feld | Inhalt |
|---|---|
| `st` | Station des Niederschlags |
| `mm` | Niederschlag des Tages (Summe der Ortszeit-Stunden), mm |
| `std` | Niederschlag je Ortszeit-Stunde 0 bis 23, mm; `null` = fehlt; nur an Tagen mit mindestens 0,1 mm (854 Tage) |
| `tmk`, `tnk`, `txk`, `tgk` | Tagesmittel, -minimum, -maximum der Temperatur, Minimum in 5 cm Höhe (Bodenfrost), °C |
| `fx`, `fm` | Windspitze und mittlere Windgeschwindigkeit, m/s |
| `shk` | Schneehöhe, cm |

Temperatur, Wind und Schnee sind die Tageswerte der DWD-Station Düsseldorf (11,7 km von Neuss, die nächste mit diesen Werten). Der
DWD-Tageswert des Niederschlags (`RSK`) gilt nicht für den Kalendertag (06 bis 06 Uhr UTC); der Niederschlag des Tages ist deshalb aus den
Stundenwerten gebildet.

**Station je Messstelle.** Seit Oktober 2026 rechnet `dsd2csv.py` den Regen einer Datei nicht mehr mit der Tabelle für Neuss, sondern mit der
Station, die der geschätzten Lage des Standortordners am nächsten liegt ([standorte.md](standorte.md), `belege/standorte.json`). Dazu enthält
`belege/wetter.json` unter `reihen` den Niederschlag jeder Station einzeln (Tage mit mindestens 22 gültigen Stunden, Felder `mm` und `std` wie
unten, dazu Name und Lage). Je Tag gilt die nächste Station, die für den Tag Werte hat; vor August 2024, als es in Neuss noch keine Stationen
gab, und bei Lücken ist das der Rückfall auf Düsseldorf, Dormagen-Zons oder eine weiter entfernte Station. Die Station steht in der
Auswertung unter `rauschen.regen.wetterstation` (nächste Station und die beiden nächsten danach). Das Ergebnis: Von 99 Dateien mit Regenblock
sind 65 belegt (vorher mit der Stadtmitte als Bezug 64). Einen Vorteil gegenüber der Stadtmitte belegt das nicht; die Stationen in Neuss liegen
höchstens 8 km auseinander, der Regen fällt nicht überall gleich, die Entscheidung folgt aber der Lage.

**Station je Tag (Tabelle `tage`, Bezugsort Neuss).** Für den Niederschlag nimmt `wetter.py` je Tag die nächstgelegene Station (Abstand zur Stadtmitte Neuss; die
Messstellen haben im Datenbestand keine Koordinaten), die für den Tag mindestens 22 gültige Stunden hat. Seit August 2024 gibt es in Neuss
sieben Stationen (Kennungen 19833 bis 19839); vorher und bei Lücken dienen Düsseldorf (01078, 11,7 km) und Dormagen-Zons (01024, 15,0 km)
als Rückfall. Berücksichtigt werden nur Stationen mit „Abgabe: Frei“ im Umkreis von 25 km (Grevenbroich und Korschenbroich stehen in
der Stationsliste, haben aber keine frei abgegebenen Stundenwerte). In der Tabelle kommen vor: Düsseldorf 889 Tage, Neuss Steinhausstraße
(19839) 720, Neuss Kläranlage Ost (19834) 29, Dormagen-Zons 6, Neuss Mühlenbachstraße (19836) und Neuss Am Blankenwasser (19833) je 1.
Die Station wechselt an 18 Stellen (9-mal zwischen Neusser Stationen, 3-mal von Düsseldorf oder Dormagen auf eine Neusser Station,
2-mal zurück, 4-mal zwischen Düsseldorf und Dormagen); der Wechsel ist im Feld `st` ablesbar und soll auf den Seiten ausgezeichnet werden.
Die Daten des Teils `recent` haben die Qualitätsprüfung des DWD noch nicht abgeschlossen.

**Zeitangabe.** Die DWD-Stundenwerte tragen UTC, der Zeitstempel ist das **Ende** der Stunde. Der Niederschlag der Ortszeit-Stunde
[h, h+1) ist der Wert zum Zeitstempel UTC(h) + 1 Stunde. Das ist an den Daten selbst nachgeprüft (nicht nur der DWD-Beschreibung geglaubt): Der
Anteil langsamer Datensätze (bis 0,3 × Tempolimit) je Stunde ist dann am höchsten, wenn man die Regenreihe um genau eine Stunde gegen
die Ortszeit verschiebt (bei 53 von 87 Dateien mit Düsseldorf, bei 18 von 30 mit einer Neusser Station).

## Tageslicht

`tageslicht.py` berechnet Sonnenaufgang, Sonnenuntergang, bürgerliche Dämmerung und Tageslänge für Neuss nach den NOAA-Formeln, ohne
Daten von außen (Genauigkeit einige Minuten). Gebraucht wird es, um tageszeitabhängige von tageslichtabhängigen Effekten zu trennen: Im
Frühling und Herbst verschiebt sich Sonnenauf- und -untergang innerhalb einer dreimonatigen Messung um Stunden (Tageslänge im Oktober
etwa zwei Stunden kürzer pro Monat).

## Befund: Regen stört das Radar

Die Messungen enthalten bei Regen sehr viele langsame Datensätze, die nicht von Fahrzeugen stammen (ohne Abzug gemessen). Verhältnis der Datensätze je Stunde
in Regenstunden zur selben Tageszeit bei Trockenheit (Mittel über alle Dateien, Düsseldorf; Referenz: Stunde und die drei davor unter 0,1 mm;
87 Dateien, 190 699 Stunden, davon 21 001 mit mindestens 0,1 mm):

| Regen je Stunde | bis 6 km/h | 7–9 | 10–12 | 13–17 | 18–25 | 26–40 | ab 41 km/h |
|---|---|---|---|---|---|---|---|
| 0,1–0,5 mm | 6,3 | 3,6 | 1,7 | 1,03 | 0,92 | 0,99 | 0,98 |
| 0,5–1 mm | 11,9 | 6,3 | 2,6 | 1,15 | 0,90 | 0,99 | 0,97 |
| 1–2 mm | 20,5 | 9,0 | 3,2 | 1,28 | 0,91 | 0,99 | 0,92 |
| 2–5 mm | 26,4 | 11,0 | 3,9 | 1,28 | 0,84 | 0,96 | 0,87 |
| ab 5 mm | 17,7 | 8,2 | 3,2 | 1,18 | 0,82 | 0,91 | 0,90 |

- Das Störsignal reicht bis etwa 12 bis 17 km/h und wächst mit der Regenmenge; bei sehr starkem Regen sinkt es wieder (vermutlich
  Sättigung). Es beginnt in der Stunde vor dem Regen (2,7-fach bei Datensätzen bis 12 km/h) und ist in der Regenstunde am höchsten (6-fach). Nach
  Regenende fällt es innerhalb von ein bis zwei Stunden fast auf den Normalwert (1,7-fach, dann 1,2-fach).
- Mit der näheren Station werden die Verhältnisse steiler: Auf denselben 32 Dateien ab September 2024 sind es bei 1–5 mm und 7–9 km/h
  14- bis 17-fach mit den Neusser Stationen gegen 10- bis 11-fach mit Düsseldorf.
- Bei den Fahrzeugen ab halbem Tempolimit ändert sich das Tempo bei Regen nicht (+0,0 km/h bei Regentagen, −0,03 km/h bei Regenstunden); das
  scheinbar langsamere Fahren (Tag −1,1 km/h, Regenstunde −3,1 km/h, bei Dateien mit abgezogenem Rauschboden −2,0 bzw. −4,6 km/h) ist das
  Störsignal. Der frühere Rauschboden-Abzug kannte keinen Regen und fing das nicht auf: Der abgezogene Rauschboden war bei Regen im Median
  2,8-fach (Regentag) bzw. 6,4-fach (Regenstunde) so hoch, in 38 von 39 bis 40 Dateien. Das ist jetzt berücksichtigt (nächster Abschnitt).
- Ab 18 km/h sinken die Zahlen bei stärkerem Regen um 10 bis 25 %. Möglicherweise verdecken die Stördatensätze Fahrzeuge, weil jeder Datensatz
  das Gerät für einige Sekunden sperrt: In 100 von 106 Dateien kommt kein Abstand unter 2 bis 8 s zwischen zwei Datensätzen vor (bei
  80 Dateien 5 s, passend zu `ar_timeout = 05` bzw. `dead_time` in der Gerätekonfiguration). Ob die Stördatensätze Fahrzeuge so verdecken,
  ist nicht geprüft; es kann auch ein echter Rückgang sein. Die Verkehrsmenge in Regenstunden ist deshalb nicht verlässlich.

## Regenmodell im Rauschboden

`rauschen.py` schätzt mit diesen Wetterdaten für jede Regenklasse einen Regenanteil und rechnet ihn heraus; Verfahren, Schwellen und Grenzen
in [rauschen.md](rauschen.md). Ergebnis auf den 109 Dateien (99 geprüft): Regenanteil **belegt bei 64**, bei 51 davon als einziger Abzug
(kein trockener Rauschboden belegt). Der trockene Rauschboden ist nur noch bei 14 Dateien belegt (vorher 41; der Rest war zu großen Teilen Regen). Abgezogen
wird im Median 4,2 % der Fahrzeuge je Datei (Quartile 1,1 und 10,0 %), am meisten bei `02_2024_Bauerbahn` (40 %: 344 Regenstunden mit im
Mittel 55 Stördatensätzen bis 8 km/h bei Tempo 20 und wenig Verkehr), `53_Feldstraße` (29 %) und `54-2023_Holunderweg` (21 %).

Kontrolle an den Daten (Regenstunden gegen trockene Stunden, gleiche Tagesart, Tageszeit und gleicher Monat): Der Tempo-Unterschied der
bereinigten Fahrzeuge fällt im Median von −3,13 auf −0,24 km/h, bei Regentagen von −1,06 auf −0,29 km/h; bei den Dateien mit belegtem Regenanteil
von −4,5 auf −0,4 km/h (Regenstunden). Das Tempo der Fahrzeuge ab halbem Limit wird nicht verändert (−0,01 km/h), die Menge ab halbem Limit auch
nicht (0,965). Die Verzerrung bleibt bei den Dateien ohne belegten Regenanteil, bei etwa einem Drittel von ihnen über 1 km/h. Fahrzeuge ohne
nutzbare Uhrzeit sind nicht korrigiert (Gesamtwerte): Ohne Uhrzeit weiß man nicht, ob es regnete.

## Erzeugen

```sh
python3 -I wetter.py --von 2022-03-01 --bis 2026-09-01 --laden ROHDATEN -o belege/wetter.json
python3 -I wetter.py --von 2022-03-01 --bis 2026-09-01 --roh ROHDATEN -o belege/wetter.json    # ohne Download
```

`--laden` lädt die DWD-Dateien (Stationen im Umkreis von 25 km) in den angegebenen Ordner. Die Dateien sind Fremddaten: eigener Ordner,
nur die Produktdatei der Archive wird gelesen, mit `-I` starten. Ist die Zertifikatsprüfung nicht möglich (unter Windows fehlte dem hier
verwendeten Python das Zwischenzertifikat des DWD-Servers), hilft `SSL_CERT_FILE` mit einem CA-Bündel; die Prüfung wird nicht abgeschaltet.

Tests: `test_wetter.py` (Einlesen, Umrechnung auf Ortszeit, Stationsauswahl, Tabelle, Tageslicht).
