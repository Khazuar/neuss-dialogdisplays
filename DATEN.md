# Datenwörterbuch: bereinigte Daten der Dialogdisplays in Neuss

> Eigene Berechnung aus den Rohdaten der Stadt Neuss, nicht amtlich. Fehler in der Auswertung (Skripte, Annahmen, Zuordnung der Angaben)
> können nicht ausgeschlossen werden; alle Angaben ohne Gewähr. Lizenz: [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/deed.de).

Diese Dateien sind für Auswertungen gedacht, auch durch Sprachmodelle: Sie enthalten dieselben Fahrzeuge wie die Kennzahlen auf den
Detailseiten, aber **in Ortszeit, mit geprüfter Uhr, ohne Rauschboden und in Abschnitte geteilt**. Die rohen CSV-Dateien aus dem Release sind
dagegen nur ein exaktes Parsing der DSD-Dateien.

## Wo liegt was

| Ort | Inhalt |
| --- | --- |
| <https://khazuar.github.io/neuss-dialogdisplays/daten/> | die Dateien dieses Wörterbuchs, bei jedem Push neu erzeugt |
| Release (ZIP, Ordner `bereinigt/`) | dieselben Dateien zum Archivieren und Zitieren eines festen Stands |
| `summary.csv`, `auswertung.yaml` (Wurzel der Seite) | Kennzahlen je Messung und alle Blöcke der YAML (Rauschboden, Uhr, Gefährdung, Lärm …) |

## Welche Datei für welche Frage

| Frage | Datei |
| --- | --- |
| Welche Messungen gibt es, wo, mit welchem Tempolimit und wie verlässlich ist die Uhr? | `messungen.csv` |
| V85, Mittel, Einhaltung je Messung oder Abschnitt, auch nach Tageszeit | `kennzahlen.csv` |
| Wurde ein Gerät umgehängt (Brüche), wann beginnt ein Abschnitt? | `abschnitte.csv` |
| Warum gibt es einen Bruch (Umhängen, Ferien, unerklärt)? | `brueche.csv` |
| Wann hat ein Gerät tatsächlich wo gemessen (Einsätze, unsere Zuordnung)? | `einsaetze.csv`, Kennzahlen mit `bereich` = `einsatz` |
| Kennzahlen je Kalendertag (Ferien, Feiertage, Wochentag) | `tage.csv` |
| Eigene Zeitfenster (zum Beispiel 7–8 Uhr, nur Dienstage, nur Ferien), Verteilungen, jede andere Frage nach Stunde und Geschwindigkeit | `stunden/<standort_seite>.csv.gz` oder `stunden.csv.gz` |
| War in einer Stunde nichts los oder wurde nichts aufgezeichnet? | `luecken.csv` zusammen mit den Stundenzeilen |

**Für Fragen nach Datum, Tageszeit oder Stunde nicht die rohen CSV-Dateien verwenden:** Sie haben die Gerätezeit (ohne Sommerzeit, bei vielen
Geräten zurückgesetzt oder verstellt), keine Prüfung der Uhr und enthalten Rauschen, das keine Fahrzeuge sind.

## Was bereinigt ist

1. **Ortszeit.** Die Geräte stellen nie auf Sommerzeit um. Die Zeitstempel sind auf Ortszeit (Europe/Berlin, mit Sommerzeit) umgerechnet
   ([dsd-format.md](https://github.com/Khazuar/neuss-dialogdisplays/blob/main/docs/dsd-format.md)).
2. **Nutzbare Uhr.** Nur Fahrzeuge aus Zeitabschnitten, deren Uhr formal nutzbar ist (kein Reset auf 2020-01-01, keine Sprünge, kein Versatz um
   Stunden). Fahrzeuge ohne nutzbare Zeit fehlen. Ob die Uhrzeit wirklich stimmt, sagt nur `uhr_bewertung` in `messungen.csv`
   (plausibel, eingeschränkt, unbrauchbar; [uhr-bewertung.md](https://github.com/Khazuar/neuss-dialogdisplays/blob/main/docs/uhr-bewertung.md)).
   **Bei 13 von 109 Messungen ist die Uhr nur teilweise oder nicht nutzbar** (`uhr_nutzbarkeit`); ihre Datumsangaben sind nicht belastbar (einzelne
   Zeilen tragen dort Jahre wie 2020 oder 2030). Für Fragen nach Datum und Tageszeit zuerst auf `uhr_nutzbarkeit` = `nutzbar` filtern.
3. **Rauschboden und Regenanteil.** Sehr langsame Messwerte, die kein Verkehr sind (Fußgänger, Tiere, Echos, Regen), sind herausgerechnet, wo
   sich das belegen lässt ([rauschen.md](https://github.com/Khazuar/neuss-dialogdisplays/blob/main/docs/rauschen.md),
   [wetter.md](https://github.com/Khazuar/neuss-dialogdisplays/blob/main/docs/wetter.md)). Das ist ein statistischer Abzug je Gruppe von Fahrten,
   keine Entscheidung über einzelne Fahrzeuge. `rauschen_abgezogen` und `regenanteil_abgezogen` in `messungen.csv` nennen die Zahl.
4. **Abschnitte.** Eine Messreihe ist an statistisch erkannten Brüchen geteilt (etwa weil das Gerät umgehängt wurde;
   [abschnitte.md](https://github.com/Khazuar/neuss-dialogdisplays/blob/main/docs/abschnitte.md)). `abschnitt_nr` ordnet jede Zeile zu; ohne
   erkannten Bruch ist alles Abschnitt 1. **Brüche sind nicht von der Verwaltung bestätigt.** Ferien und Feiertage sind bei der Suche ausgenommen.

Nicht enthalten: Wetterdaten und die Verhaltensgruppen (Forschungsstand). Der Niederschlag je Stunde und Station liegt in
[`belege/wetter.json`](https://github.com/Khazuar/neuss-dialogdisplays/blob/main/belege/wetter.json) im Repository (CC BY 4.0, Quelle: Deutscher
Wetterdienst); welche Station zu einer Messung gehört, steht in `messungen.csv` (`wetterstation`, `wetterstation_abstand_km`). Die Regenklasse
je Stunde folgt daraus nach der Regel in `rauschen.regenklassen`.

## Dateien und Spalten

Alle Dateien: UTF-8, Komma als Trenner, Punkt als Dezimaltrenner, Zeilenende LF, leere Zelle = kein Wert, Zeiten in Ortszeit (Europe/Berlin; in den Stundendateien mit `utc_versatz_h`, in `luecken.csv` in UTC),
Reihenfolge deterministisch. `messung_id` ist die Kennung einer DSD-Datei (`m-<ordner>-<datei>`), `standort_seite` der Name der Standortseite
(`standorte/<standort_seite>.html`; mehrere Ordner und Messungen am selben Ort liegen unter einer Seite).

### `messungen.csv` (eine Zeile je DSD-Datei)

`messung_id`, `standort_seite`, `standort_name` (Name der Standortseite, meist die Straße), `ordner` (Ordner in der Lieferung der Stadt), `datei`,
`geraet` (Konfigurationsnummer), `tempolimit_kmh` und `tempolimit_quelle` (`dsd_konfiguration`, `mitteilung_verwaltung` aus `belege/korrekturen.json`,
`parameter`), `strasse`, `lage_breite`, `lage_laenge` (WGS 84), `lage_unsicherheit_m` und `lage_sicherheit` (`benannt`, `vermutet`, `widersprüchlich`,
`manuell korrigiert`), `fahrtrichtung` (aus Ordnername und Mitteilung der Verwaltung), `verdeckte_messung` (1 = das Display zeigte nichts an, DSD-Flag; nur an der Villestraße, siehe docs/verdeckt.md),
`beidseitige_messung` (1 = laut Mitteilung in beide
Richtungen, leer = unbekannt), `messzeitraum_von`/`_bis`
(erstes und letztes Fahrzeug mit nutzbarer Zeit), `fahrzeuge_in_datei`, `fahrzeuge_ohne_nutzbare_zeit`, `rauschen_abgezogen`,
`regenanteil_abgezogen` (Anzahl; der Regenanteil ist in `rauschen_abgezogen` nicht enthalten), `wetterstation` und `wetterstation_abstand_km`
(Station, deren Niederschlag für den Regenanteil gilt; leer ohne Regenanteil), `fahrzeuge_im_aggregat` (Summe aller
Stundenzeilen der Messung), `uhr_nutzbarkeit` (formale Prüfung: `nutzbar`, `teilweise_nutzbar`, `nicht_nutzbar`), `uhr_bewertung`,
`abschnitte` (Zahl), `bezeichnung_verwaltung` (Name der Messstelle in den Mitteilungen der Verwaltung, mehrere mit ` | ` getrennt).

### `abschnitte.csv` (eine Zeile je Abschnitt)

`messung_id`, `abschnitt_nr`, `von`, `bis` (erster und letzter Tag der Fahrzeuge), `tage`, `fahrzeuge`, `bruch_wahrscheinlichkeit` (Wahrscheinlichkeit
des Bruchs vor diesem Abschnitt, leer bei Abschnitt 1), `anmerkung` (`Beginn der Messung`, `Bruch davor`, `kein Bruch erkannt`, `nicht prüfbar`).

### `kennzahlen.csv` (je Messung und Abschnitt und Zeitraum)

`messung_id` (bei `einsatz` die Einsatz-ID), `bereich` (`messung` = ganze Datei, `abschnitt`, `einsatz`), `abschnitt_nr` (leer bei `messung` und `einsatz`), `zeitraum`, `fahrzeuge`, `mittel_kmh`, `v85_kmh`,
`v95_kmh`, `v99_kmh`, `einhaltung_prozent`, `qualifiziert_prozent` (Einhaltung nur mit Tempolimit), dazu die **Raten**
`fahrzeuge_je_stunde`, `ueber_limit_plus_toleranz_je_stunde` (Fahrzeuge über Limit plus Messtoleranz je Stunde) und `zusatzrisiko_je_stunde`
(Summe von max(0, (v / Tempolimit)⁴ − 1) je Stunde, Potenzmodell nach Nilsson). Die Raten zählen absolut statt anteilig und nur aus
vollständig aufgezeichneten Stunden; alle Raten gelten je Stunde der Auswahl und sind für Teilzeiträume vergleichbar (ganztägig mal 24 ergibt je Tag),
ohne Tempolimit leer (Begründung und Grenzen: [docs/raten.md](docs/raten.md)).

Zeiträume (Ortszeit, alle Tage, außer Schulweg): `alle` (ganze Datei oder ganzer Abschnitt), `nacht` 22–6 Uhr, `vormittag` 6–12, `nachmittag` 12–19,
`abend` 19–22, `schulweg` Montag bis Freitag 7–8 Uhr. „bis 6 Uhr“ heißt: Stunden 22, 23, 0 bis 5.

### `tage.csv` (je Messung, Abschnitt und Kalendertag)

`messung_id`, `abschnitt_nr`, `datum`, `wochentag` (1 Montag bis 7 Sonntag), `ferien` (1 = Schulferien in NRW), `feiertag` (1 = gesetzlicher Feiertag in
NRW), dazu dieselben Kennzahlen wie oben. Auch angebrochene Tage (Beginn und Ende der Messung) stehen drin.

### `stunden/<standort_seite>.csv.gz` und `stunden.csv.gz` (je Tag, Stunde und km/h)

Eine Zeile je Kombination mit mindestens einem Fahrzeug (nichts mit 0). `stunden.csv.gz` enthält alle Standorte (3,7 Mio. Zeilen, etwa 12 MB gzip,
rund 280 MB entpackt), die Dateien je Standortseite jeweils nur deren Messungen.

| Spalte | Bedeutung |
| --- | --- |
| `messung_id` | Kennung der DSD-Datei |
| `abschnitt_nr` | Abschnitt der Messreihe, 1, 2, … |
| `datum` | Kalendertag in Ortszeit (ISO 8601) |
| `wochentag` | 1 Montag bis 7 Sonntag |
| `stunde` | 0–23, Ortszeit |
| `utc_versatz_h` | Versatz der Ortszeit zu UTC in dieser Stunde: 1 (Winterzeit) oder 2 (Sommerzeit). UTC-Stunde = `datum` + `stunde` − `utc_versatz_h`. Die doppelte Stunde im Herbst („2A“ und „2B“) sind zwei Zeilen mit Versatz 2 und 1; im Frühjahr fehlt die Stunde 2. Schlüssel einer Stunde ist (`messung_id`, `datum`, `stunde`, `utc_versatz_h`). |
| `zeitraum` | `nacht`, `vormittag`, `nachmittag` oder `abend` (ergibt sich aus der Stunde); Schulweg: `stunde` = 7 und `wochentag` ≤ 5 |
| `ferien` | 1 = Schulferien NRW (nur 2022 bis 2026 bekannt, sonst 0) |
| `feiertag` | 1 = gesetzlicher Feiertag NRW (ein Feiertag in den Ferien zählt in beiden Spalten) |
| `voll` | 1 = die Stunde ist vollständig in einem Zeitabschnitt mit nutzbarer Uhr aufgezeichnet; 0 = angebrochen (Anfang, Ende, Lücke) |
| `regenklasse` | Regen in dieser Stunde an der zugeordneten Wetterstation (`wetterstation` in `messungen.csv`): 0 = trocken (diese Stunde, die drei davor und die danach unter 0,1 mm), 1 = 0,1 bis 0,5 mm, 2 = 0,5 bis 2 mm, 3 = ab 2 mm (Niederschlag der Stunde plus je die Hälfte der Nachbarstunden), 9 = Vor- oder Nachlauf eines Regens oder kein Wert; leer ohne Wetterdaten. Abgeleitet aus Daten des Deutschen Wetterdienstes (Quelle: Deutscher Wetterdienst, CC BY 4.0). |
| `kmh` | gemessene Geschwindigkeit in ganzen km/h (Auflösung der Geräte) |
| `anzahl` | Fahrzeuge dieser Geschwindigkeit in dieser Stunde |
| `einsatz_id` | Einsatz, zu dem die Stunde nach unserer Zuordnung gehört (`einsaetze.csv`); leer an ausgenommenen Umhängtagen |

### `einsaetze-stunden.csv.gz` (je Einsatz, Tag, Stunde und km/h)

Wie `stunden.csv.gz`, aber je Einsatz und mit dessen eigenem Abzug von Rauschboden und Regenanteil (geschätzt je Einsatz-Abschnitt, mit der
Wetterstation des Einsatzstandorts): `einsatz_id`, `einsatz_abschnitt_nr` (Abschnitt im Einsatz; Teile über eine Dateigrenze zählen als einer),
`datum`, `wochentag`, `stunde`, `utc_versatz_h`, `zeitraum`, `ferien`, `feiertag`, `voll`, `regenklasse`, `kmh`, `anzahl`. Für Auswertungen nach dem
tatsächlichen Einsatzort ist das die bessere Grundlage; `stunden.csv.gz` bleibt die Sicht der Messungen (Abzug je Abschnitt der Datei).

### `einsaetze.csv` (eine Zeile je Einsatz)

Ein **Einsatz** ist der Zeitraum, in dem ein Gerät tatsächlich an einem Standort in eine Fahrtrichtung gemessen hat (unsere Zuordnung,
[docs/einsaetze.md](docs/einsaetze.md)). Meist ist er gleich der Messung. Hing ein Gerät nach dem Auslesen noch am alten Ort, gehört dieser
Abschnitt der neuen Datei zum Einsatz des alten Standorts.

`einsatz_id`, `messung_id` (Messung, auf der der Einsatz beruht: Standort, Fahrtrichtung, Tempolimit), `standort_seite`, `standort_name`, `geraet`,
`fahrtrichtung`, `tempolimit_kmh`, `von`, `bis`, `status` (`identisch` = gleich der Messung, `abgeleitet` = aus mehreren Messungen
zusammengesetzt, nicht bestätigt, `unsicher` = zusammengesetzt nach einer nur möglichen Zuordnung, `bestaetigt` = Grenzen von der Verwaltung bestätigt, `gekuerzt` = Teile der Messung gehören zu einem anderen
Einsatz), `teile` (Messung#Abschnitt von..bis und Herkunft), `abgegeben` (Abschnitte, die zu einem anderen Einsatz gehören), `ausgenommene_tage`
(Umhängtage).

### `brueche.csv` (eine Zeile je Bruch)

`messung_id`, `abschnitt_nr` (Abschnitt nach dem Bruch), `datum`, `wahrscheinlichkeit`, `zuordnung` (`umhaengen`, `ereignis`, `verwaltung`,
`unerklaert`), `stufe` (`belegt`, `moeglich`, `plausibel`, `bestaetigt`, `offen`), `erklaerung`, dazu die Belege der besten Umhäng-Prüfung:
`umhaengen_richtung`, `umhaengen_von_messung`, `score`, `p_nulltest`, `verhaeltnis_fahrzeuge`, `gegenprobe_score`, `naht_stetig`; `ereignisse` in der Nähe
und `gleicher_tag` (Messungen mit einem Bruch ±1 Tag).

### `luecken.csv`

`messung_id`, `von_utc`, `bis_utc` (erste und letzte Stunde in **UTC**, `JJJJ-MM-TTTHH:00Z`), `stunden`: Stunden zwischen dem ersten und letzten Fahrzeug einer
Messung, die **nicht vollständig** aufgezeichnet sind (Anfang und Ende, Lücken, Uhrsprünge). Daraus folgt:

- Eine Stunde mit Zeilen in den Stundendateien und `voll` = 1 hat die Fahrzeuge der Zeilen.
- Eine Stunde im Messzeitraum, die weder in den Stundendateien noch in `luecken.csv` steht, war vollständig aufgezeichnet und hatte **0 Fahrzeuge**
  (die UTC-Stunde einer Zeile ist `datum` + `stunde` − `utc_versatz_h`).
- Eine Stunde in `luecken.csv` ist **unbekannt**, nicht null: Dort fehlen Daten (angebrochene Stunden haben trotzdem Zeilen, mit `voll` = 0).

## Kennzahlen aus den Stundenzeilen berechnen

Definitionen (wie in `dsd2csv.py`): **V85** (ebenso V95, V99) ist die kleinste Geschwindigkeit, bei der mindestens 85 % der Fahrzeuge
höchstens so schnell fahren. **Einhaltungsquote** = Anteil der Fahrzeuge mit v ≤ Tempolimit. **Qualifizierte Einhaltungsquote** = Anteil mit
v − Toleranz ≤ Tempolimit; die Toleranz beträgt 3 km/h unter 100 km/h und ab 100 km/h 3 % (aufgerundet).

```python
import math
import pandas as pd

basis = "https://khazuar.github.io/neuss-dialogdisplays/daten/"
messungen = pd.read_csv(basis + "messungen.csv")
stunden = pd.read_csv(basis + "stunden/bonner-strasse.csv.gz")      # Name: Spalte standort_seite in messungen.csv
stunden = stunden.merge(messungen[["messung_id", "tempolimit_kmh"]], on="messung_id")

def kennzahlen(g):
    h = g.groupby("kmh", as_index=False)["anzahl"].sum().sort_values("kmh")
    n = h["anzahl"].sum()
    kum = h["anzahl"].cumsum()
    limit = g["tempolimit_kmh"].iloc[0]
    tol = h["kmh"].map(lambda v: 3 if v < 100 else math.ceil(0.03 * v))
    return pd.Series({
        "fahrzeuge": n,
        "v85": h["kmh"][kum >= math.ceil(0.85 * n)].iloc[0],
        "einhaltung_prozent": round(100 * h["anzahl"][h["kmh"] <= limit].sum() / n, 2),
        "qualifiziert_prozent": round(100 * h["anzahl"][h["kmh"] - tol <= limit].sum() / n, 2),
    })

# Beispiel: Werktage, 7 bis 8 Uhr, ohne Ferien, je Messung und Abschnitt
w = stunden[(stunden.wochentag <= 5) & (stunden.stunde == 7) & (stunden.ferien == 0) & (stunden.feiertag == 0)]
print(w.groupby(["messung_id", "abschnitt_nr"]).apply(kennzahlen))

# Nur trockene Stunden: In Regenstunden verdecken Störungen Fahrzeuge (docs/totzeit.md); der Vergleich zeigt, wie stark das die Zahlen bewegt
trocken = stunden[stunden.regenklasse == 0]

# Zeitreihen und Verknüpfung mit UTC-Daten (zum Beispiel Wetter): UTC-Stunde aus Datum, Stunde und Versatz
stunden["utc"] = pd.to_datetime(stunden.datum) + pd.to_timedelta(stunden.stunde - stunden.utc_versatz_h, unit="h")
```

Für ganze Messungen, Abschnitte und die üblichen Zeiträume ist `kennzahlen.csv` schon fertig gerechnet.

## Grenzen

- **Keine Einzelfahrzeuge.** Zeitlücken zwischen Fahrzeugen, Pulks, minutengenaue Spitzen und die Nächte mit Fahrten ab doppeltem Tempolimit
  (`nacht_ereignisse` in der YAML) sind aus diesen Dateien nicht zu beantworten. Dafür gibt es die rohen CSV-Dateien im Release (mit den
  Einschränkungen oben) und die YAML.
- **Statistischer Abzug.** Rauschboden und Regenanteil sind Schätzungen. Der Regenanteil gilt je Regenklasse und Geschwindigkeit für die ganze
  Datei und wird nach den beobachteten Fahrten auf die Stunden verteilt
  ([rauschen.md](https://github.com/Khazuar/neuss-dialogdisplays/blob/main/docs/rauschen.md), Abschnitt „Verteilung des Regenabzugs auf Stunden“).
  Einzelne Regenstunden sind deshalb weniger verlässlich als Tage, Zeiträume oder ganze Messungen: Der Abzug kann in einer Stunde zu viel oder
  zu wenig entfernen, über viele Stunden gleicht es sich aus. Alle Dateien (Stunden, Tage, Zeiträume, Abschnitte, ganze Messung) beruhen auf
  demselben Abzug und stimmen exakt überein (seit Oktober 2026; vorher wichen die Zeiträume bei Messungen mit Regenanteil ab).
- **Lage.** Die Koordinaten sind eine Schätzung aus Straßenname, Hausnummer und Ortsangaben, kein Messprotokoll; `lage_unsicherheit_m` nennt die
  Spanne (im Median einige hundert Meter, bei ganzen Straßen bis über 1 km; [standorte.md](https://github.com/Khazuar/neuss-dialogdisplays/blob/main/docs/standorte.md)).
- **Zeitumstellung.** Datum und Stunde sind Ortszeit; `utc_versatz_h` macht sie eindeutig. Im Frühjahr (letzter Sonntag im März) gibt es die
  Stunde 2 nicht, im Herbst (letzter Sonntag im Oktober) kommt sie zweimal vor (Versatz 2 und 1). Wer nach `(datum, stunde)` allein sortiert oder
  gruppiert, wirft die beiden zusammen. Die UTC-Zeit je Fahrzeug ist eindeutig, weil die Geräteuhr UTC plus ein fester Versatz ist
  (`test_aggregat.py`, Klasse `Zeitumstellung`). `tage.csv` zählt Ortszeit-Tage (der Herbsttag hat 25, der Frühjahrstag 23 Stunden).
- **Regenstunden.** Bei Regen erzeugen die Geräte Störungen, und jede sperrt das Gerät für einige Sekunden. In Regenstunden fehlen deshalb
  Fahrzeuge, im Mittel etwa doppelt so viel wie die Sperrzeit der Störungen ([totzeit.md](https://github.com/Khazuar/neuss-dialogdisplays/blob/main/docs/totzeit.md)).
  Die Daten sind darum nicht korrigiert; wer Mengen vergleicht, kann mit `regenklasse` = 0 auf trockene Stunden beschränken.
- **Abschnitte** sind erkannte Brüche mit Wahrscheinlichkeit, keine bestätigten Ereignisse.
- **Messdauer.** Eine Messung dauert im Median 11 Wochen (die kürzesten 10 % unter 2, die längsten 10 % über 19 Wochen). Aussagen zum
  Jahresverlauf oder zu Zeiten außerhalb des Messzeitraums sind nicht möglich. Messzeiträume über viele Monate oder Jahre entstehen nur bei
  nicht oder teilweise nutzbarer Uhr und bei den stationären Messungen an der Villestraße (rund 10 Monate).
- **Tempolimit.** Das Limit stammt aus der DSD-Konfiguration, bei vier Messungen aus der Mitteilung der Verwaltung (`tempolimit_quelle`).
