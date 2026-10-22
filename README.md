# Dialogdisplay-Messdaten (IFG-Anfrage)

Rohdaten (`.dsd`) von Geschwindigkeits-Dialogdisplays, die per Informationsfreiheitsanfrage (IFG)
bei der Stadt Neuss angefragt wurden, dazu ein Skript, das sie in lesbare Formate umwandelt und je
Messstelle auswertet.

> **Hinweis:** Die Auswertungen (CSV, YAML und Kennzahlen wie V85 oder Einhaltungsquote) sind meine
> eigenen Berechnungen aus den Rohdaten. Sie stammen weder von der Stadt Neuss noch vom Hersteller der
> Geräte, sind nicht amtlich und nicht für Bußgeld- oder Gerichtsverfahren gedacht. **Fehler in der Auswertung
> (Skripte, Annahmen, Zuordnung der Angaben zu den Messungen) können nicht ausgeschlossen werden; alle Angaben
> sind ohne Gewähr.** Gefährdung, Lärm und Ereignisse pro Nacht sind Schätzungen und kein Gutachten. – Fabian Grewing

**Im Repository liegen nur die DSD-Rohdaten und die Skripte.** Die abgeleiteten Daten (CSV und YAML)
werden aus den DSDs erzeugt und separat veröffentlicht, siehe [Abgeleitete Daten](#abgeleitete-daten).

## Inhalt

- `<Nr>_<Straße>/*.dsd` – je Ordner eine oder mehrere Messungen
- `dsd2csv.py` – DSD → CSV und YAML-Auswertung
- `uhr_belege.py` – prüft für jeden Abschnitt einer Aufzeichnung, ob man der Geräteuhr glauben darf
  (`plausibel`, `eingeschraenkt`, `unbrauchbar`), mit Belegen
- `rauschen.py` – schätzt je Datei den Rauschboden (sehr langsame Messwerte, deren Rate nicht vom Verkehr abhängt) und rechnet
  ihn heraus, wo das belegt ist
- `<Standortordner>/uhr-analyse.md` – je Standort eine lesbare Fassung der Urteile mit allen Belegen
- `metadaten.py` – ordnet die Angaben der Verwaltung (Messstelle, Fahrtrichtung, Zeitraum, Tempolimit, V85 …) den
  DSD-Dateien zu und schreibt je Standort eine `metadaten.yaml` mit Quellen
- `<Standortordner>/metadaten.yaml` – zusätzlich erhobene Metadaten, siehe [docs/metadaten.md](docs/metadaten.md), darunter der
  geschätzte Standort mit Koordinaten und Unsicherheit ([docs/standorte.md](docs/standorte.md))
- `standorte.py` – schätzt aus Straße, Hausnummer und Ortsangaben die Koordinaten der Messstellen (`python3 -I standorte.py` zeigt die Tabelle)
- `belege/` – Ergebnisse der Prüfung (`uhr-bewertung.json`) und der Auswertung der Mitteilungen der
  Verwaltung (`ris.json`, `ris-messstellen.json`, `ris-zuordnung.json`, `metadaten.json`) sowie die
  Korrekturen des Tempolimits, wo die Mitteilung ein anderes Limit nennt als die DSD (`korrekturen.json`), und die
  Wetterdaten des Deutschen Wetterdienstes je Tag (`wetter.json`, **CC BY 4.0**, siehe [Lizenz](#lizenz)), die Hauskoordinaten der
  Stadt Neuss (`neuss-adressen.csv`, Geobasis NRW, dl-de/zero-2-0), die Ortshinweise zu den Messstellen (`standort-hinweise.json`)
  die geschätzte Lage der Standortordner (`standorte.json`, bestimmt auch die Wetterstation je Messstelle) und das Register der
  Verhaltensgruppen der Stadt (`verhaltensgruppen-register.json`: feste Namen, Deutung mit Stufe, Vorlagen; Forschungsstand)
- `tools/` – holt die Mitteilungen der Verwaltung aus dem Ratsinformationssystem und zerlegt sie
  (`ris_sammeln.py`, `ris_auswerten.py`, `ris_messstellen.py`) und die Hauskoordinaten von Geobasis NRW (`adressen_laden.py`)
- `docs/uhr-bewertung.md` – wie über die Zuverlässigkeit der Uhren entschieden wird, mit Grenzen
- `docs/metadaten.md` – Herkunft, Zuordnung und Abdeckung der Metadaten
- `docs/standorte.md` – Standort der Messstellen: Quellen, Verfahren, Annahmen für die Unsicherheit, Ergebnis und Grenzen
- `docs/rauschen.md` – Modell, Regeln und Grenzen des Rauschbodenabzugs
- `docs/gruppen.md` – Zeitscheiben, Zellen und die Auswahl auf den Detailseiten (dazu die früheren Formgruppen)
- `docs/abschnitte.md` – Brüche in einer Messreihe (Geräte umgehängt?) und die getrennte Auswertung der Abschnitte
- `docs/verhalten.md` – Verhaltensgruppen (Gruppen mit eigener Reaktion auf Tageszeit, Licht, Wetter, Ferien und Verkehrsmenge) mit Placebo-Prüfung,
  drei Ebenen (Abschnitt, Standort, Stadt), Namen, Deutungen und Stadt-Vorlagen; Forschungsstand
- `docs/einsaetze.md` – Einsätze: Brüche erklären (Umhängen, Ereignisse) und Messungen nach dem tatsächlichen Einsatzort abgrenzen
- `docs/verdeckt.md` – Villestraße: offene gegen verdeckte Messung (Display ohne Anzeige), Befund und Grenzen
- `docs/raten.md` – Raten statt Anteile: warum zu schnelle Fahrzeuge je Tag gezählt werden und was daraus folgt
- `docs/gefaehrdung.md` – Modelle und Annahmen für Gefährdung (Nilsson, Restgeschwindigkeit), Lärm und Ereignisse pro Nacht
- `docs/wetter.md` – Wetterdaten des DWD (Quelle, Lizenz, Stationswahl, Zeitangabe) und der Befund, dass Regen das Radar stört
- `seiten_bauen.py` – baut je Standort (gleiche Straße, sich überlappende Lage; alle Messungen und Fahrtrichtungen zusammen) eine Detailseite für die GitHub Pages (`standorte/<name>.html`) mit den Reitern Allgemein, Verwaltung, Messung, Analyse, Gruppen, Vergleich, Gefährdung und Lärm, dazu Weiterleitungen von den alten Seiten je Ordner, `uebersicht.json` für die Übersicht und die Übersicht der Verhaltensgruppen (`verhaltensgruppen.html`);
  Geschwindigkeits-Histogrammen als Inline-SVG
- `DATEN.md` – Datenwörterbuch der bereinigten Daten (welche Datei für welche Frage, Spalten, Bereinigung, Berechnung von V85 und Einhaltung, Grenzen); `site/llms.txt` verweist darauf
- `aggregat.py` – fasst die Fahrzeuge einer Datei je Tag, Stunde und km/h zusammen (Ortszeit, nutzbare Zeit, Rauschboden abgezogen, Abschnitte); `daten_bauen.py` schreibt daraus und aus der Auswertung die CSV-Dateien unter `daten/` (`messungen.csv`, `abschnitte.csv`, `kennzahlen.csv`, `tage.csv`, `luecken.csv`, `stunden/<standort>.csv.gz`, `stunden.csv.gz`)
- `kalender.py` – Schulferien und Feiertage in NRW
- `verhalten.py` – Verhaltensgruppen je Abschnitt (Modell, Placebo, Stadt-Vorlagen; braucht numpy, rechnet jeden Abschnitt einzeln mit Zwischenspeicher);
  `einsaetze.py` – ordnet die Brüche zu und bildet die Einsätze (`einsaetze.json`, `brueche.html`);
  `stadtgruppen.py` – fasst sie zu Gruppen je Standort (MS) und der Stadt (S) zusammen, vergibt Namen aus dem Register und schreibt `verhaltensgruppen.json`
- `tools/verhalten/` – Forschungsskripte der Verhaltensanalyse (brauchen numpy, nicht Teil der Auswertung)
- `bruch.py` – erkennt Brüche in der Messreihe einer Datei (Verhalten des Verkehrs ändert sich dauerhaft) und zerlegt sie in Abschnitte mit Begründung und Wahrscheinlichkeit; `dsd2csv.py` wertet jeden Abschnitt einzeln aus (YAML-Block `abschnitte`)
- `gruppen.py` – Zeitscheiben und die Zellen für die Auswahl nach Tageszeit und Tagen auf den Detailseiten
- `wetter.py` – erzeugt `belege/wetter.json` aus den Daten des Deutschen Wetterdienstes (Niederschlag je Stunde und Tag, Tageswerte von Temperatur, Wind und Schnee); `tageslicht.py` – Sonnenaufgang, Sonnenuntergang und Dämmerung für Neuss, rein rechnerisch
- `zwischenspeicher.py` – Zwischenspeicher für Ergebnisse je Datei (nur geänderte Dateien oder Skripte werden neu gerechnet)
- `lokal_bauen.py` – baut die GitHub-Pages-Seite lokal nach `_vorschau/` und startet auf Wunsch einen lokalen Server, um sie vor dem Push im Browser anzusehen (`docs/betrieb.md`)
- `test_dsd2csv.py`, `test_uhr_belege.py`, `test_metadaten.py`, `test_seiten.py`, `test_rauschen.py`, `test_gruppen.py`, `test_filter.py`, `test_lokal.py`, `test_wetter.py`, `test_standorte.py`, `test_bruch.py`, `test_verhalten.py`, `test_aggregat.py` – Tests (`python3 -m unittest -v`; die Modelltests brauchen numpy)
- `docs/dsd-format.md` – Beschreibung des (undokumentierten) DSD-Formats und bekannte Datenprobleme
- `site/` – GitHub Pages: Übersichtstabelle der YAML-Auswertungen, Datenschutz und Impressum-Vorlage (derzeit nicht veröffentlicht), dazu `filter.js` (Auswahl nach Tageszeit, Tagen, Abschnitt und Gruppe auf den Detailseiten, liest nur die Daten der eigenen Seite) und `seite.js` (Reiter und Auswahl der Messung; ohne JavaScript steht alles untereinander), `labor.js` (Labor-Modus mit `?labor`: blendet den Forschungsstand, derzeit die Verhaltensgruppen, für alle anderen aus). Die Übersicht zeigt wahlweise Messungen (wie bei der Verwaltung) oder Abschnitte (`abschnitte.json`)
- `docs/betrieb.md` – Einrichtung von GitHub Pages und Impressum
- `LICENSE`, `LICENSE-DATEN` – Lizenzen für Software bzw. Daten und Dokumentation, siehe [Lizenz](#lizenz)
- `.github/workflows/` – erzeugt die abgeleiteten Daten und veröffentlicht sie

## Abgeleitete Daten

Die CSV- und YAML-Dateien liegen nicht im Repository, sondern werden von GitHub Actions aus den DSDs
erzeugt:

- **Webseite:** <https://khazuar.github.io/neuss-dialogdisplays/> – Übersichtstabelle mit allen Messungen
  und den YAML-Auswertungen zum Herunterladen, außerdem `summary.csv` und `auswertung.yaml` mit allen
  Messungen. Die Seite wird bei jedem Push auf `main` neu gebaut. Die einzelnen CSV-Dateien (ein Fahrzeug
  pro Zeile, zusammen rund 270 MB) stehen dort bewusst nicht.
- **Bereinigte Daten:** unter `daten/` auf der Seite (und im Release unter `bereinigt/`), erklärt im [Datenwörterbuch](DATEN.md):
  Kennzahlen je Messung, Abschnitt, Zeitraum und Tag als CSV sowie die Fahrzeuge je Tag, Stunde und km/h (gzip, rund 12 MB). Im
  Unterschied zu den rohen CSV-Dateien in Ortszeit, nur mit nutzbarer Uhr, ohne Rauschboden und nach Abschnitten geteilt.
- **ZIP-Archiv:** unter [Releases](https://github.com/Khazuar/neuss-dialogdisplays/releases) gibt es zu
  jedem Tag `v*` ein ZIP mit allen Ergebnissen inklusive der CSV-Dateien, zum Archivieren und Zitieren
  eines festen Stands.

Wer die Daten selbst erzeugen will, nutzt dazu das Skript (siehe unten).

## Benutzung

Python 3.7 oder neuer, nur Standardbibliothek. Nur die Verhaltensgruppen (`verhalten.py`) brauchen zusätzlich numpy; ohne numpy
fehlen sie in der Auswertung, alles andere bleibt gleich.

```sh
python3 -I dsd2csv.py .                     # alle DSDs rekursiv: .csv + .yaml neben jeder DSD,
                                            # dazu auswertung.yaml und summary.csv im Ordner
python3 -I dsd2csv.py datei.dsd             # eine Datei
python3 -I dsd2csv.py . -o ausgabe          # Ergebnisse unter ausgabe/ (Ordnerstruktur bleibt)
```

Optionen: `--limit N` (Tempolimit erzwingen), `--min-kmh N` (Standard 0, zusätzlich; Werte unter N km/h aus der Auswertung
nehmen), `--meta`, `--status`, `--keine-csv` (keine CSV je Datei), `--cache ORDNER` (Zwischenspeicher, siehe `docs/gruppen.md`), `--jobs N` (N Dateien gleichzeitig). Mit `-I` startet Python isoliert; das ist bei Dateien aus fremder Quelle
sinnvoll.

### Ausgabe

- `<name>.csv` – ein Fahrzeug pro Zeile: `zeitstempel`, `geschwindigkeit_kmh`
- `<name>.yaml` – Auswertung je Messung: Standort (relativer Ordnerpfad), Tempolimit samt Quelle,
  Anzahl Fahrzeuge, Messzeitraum, mittlere/maximale Geschwindigkeit, V85/V95/V99, Einhaltungsquote und
  qualifizierte Einhaltungsquote, außerdem
  - `uhr` – formale Prüfung der Zeitstempel (`nutzbarkeit`: `nutzbar`, `teilweise_nutzbar`, `nicht_nutzbar`) mit
    Hinweisen und den Uhr-Segmenten. Sie sagt nicht, ob die Uhrzeit stimmt; das belegt `uhr_belege.py`
    (`plausibel`, `eingeschraenkt`, `unbrauchbar`, `belege/uhr-bewertung.json`),
  - `rauschen` – Rauschboden: `belegt`, `abgezogen_fahrzeuge`, Anteil, Mittel und Obergrenze in km/h, Stabilität und das
    `spektrum` (Fahrten je 1000 Stunden, verkehrsunabhängig und insgesamt) und `regen` (zusätzliche langsame Datensätze bei Regen,
    siehe `docs/wetter.md`); `fahrzeuge_in_datei` ist die Zahl vor dem Abzug,
  - `bereinigt` – dieselben Kennzahlen nur für Fahrzeuge mit nutzbarer Zeit,
  - `teilzeitraeume` – dieselben Kennzahlen für `nacht` (22–6 Uhr), `vormittag` (6–12), `nachmittag` (12–19), `abend` (19–22)
    und `schulweg` (Mo–Fr 7–8 Uhr), jeweils in Ortszeit,
  - `verhalten` – Verhaltensgruppen je Abschnitt: Zahl der Gruppen, Vorhersagegewinn, je Gruppe Art, Anteil, Profil, Stabilität, Verhalten
    (Effekte mit Standardfehler) und Tagesgang, dazu der Placebo-Durchgang und die geprüften Stadt-Vorlagen (`docs/verhalten.md`),
  - `raten` – absolute Kennzahlen je Stunde statt Anteile: Fahrzeuge, Überschreitungen und Zusatzrisiko
    (`docs/raten.md`; gelten für vollständig aufgezeichnete Stunden),
  - `gefaehrdung` und `laerm` – Schätzungen je Zeitraum: Aufprallgeschwindigkeit und Fahrzeuge je Stunde, die mit mehr als 30 bzw.
    50 km/h aufträfen, lautere Vorbeifahrten je Stunde gegenüber dem Tempolimit (`docs/gefaehrdung.md`),
  - `nacht_ereignisse` – Nächte (22–6 Uhr) mit Fahrten ab doppeltem Tempolimit, 100 und 120 km/h,
  - `histogramm` – Anzahl Fahrzeuge je ganzem km/h (`ab_kmh`, `anzahl`), auch je Zeitraum; steht nur in der YAML, nicht
    in `summary.csv`. Die Detailseiten zeichnen daraus die Verteilung: eine Klasse je km/h (Auflösung der Geräte), bei
    wenigen Fahrzeugen breitere Klassen nach Freedman-Diaconis (2 · Quartilsabstand · n^(−1/3), höchstens 5 km/h),
    und die Höhe ist der Anteil der Fahrzeuge je km/h. Die Skala endet beim 99,99-%-Perzentil; schnellere Fahrzeuge
    (meist Messfehler) werden unter dem Bild gezählt
- `<name>.zellen.json` – Histogramme je Wochentag und Stunde, je Abschnitt, und die Verhaltensgruppen (Profile und erwartete Fahrzeuge je
  Wochentag und Stunde); daraus rechnet die Detailseite die Auswahl nach Tageszeit, Tagen, Abschnitt und Gruppe
- `verhaltensgruppen.json` – Verhaltensgruppen auf allen drei Ebenen mit Namen und Beziehungen (`stadtgruppen.py`)
- `auswertung.yaml`, `summary.csv` – alle Messungen zusammengefasst

Die Geräte stellen ihre Uhr nicht auf Sommerzeit um und sind teils zurückgesetzt oder verstellt. Die
Auswertungen nach Tageszeit rechnen deshalb auf Ortszeit um und lassen Fahrzeuge ohne nutzbare Zeit aus (zurückgesetzte Uhr, Datumssprünge, Versatz um Stunden). Nutzbar heißt nicht
belegt: Ob die Uhrzeit stimmt, zeigen die Belege je Abschnitt auf den Detailseiten.
Das Verfahren und die Belege dafür stehen in `docs/dsd-format.md`. Die Kennzahlen auf der obersten Ebene der
YAML enthalten weiterhin alle Fahrzeuge der Datei, abzüglich des **Rauschbodens**: Sehr langsame Messwerte (Fußgänger,
Tiere, Echos, Störungen), deren Rate nicht vom Verkehr abhängt, schätzt `rauschen.py` je Datei und rechnet sie heraus, wo das
belegt ist (Modell und Regeln in `docs/rauschen.md`). Eine feste Mindestgeschwindigkeit gibt es nicht mehr; `--min-kmh` ist
optional. Die CSV-Dateien bleiben vollständig.

Das **Tempolimit** wird aus der DSD gelesen (`safety_speed`, eine Anzeige-Schwelle des Geräts), siehe `docs/dsd-format.md`.
Nennt die Mitteilung der Verwaltung ein deutlich anderes Limit, gilt dieses (`belege/korrekturen.json`, vier Messungen,
siehe `docs/metadaten.md`).
**Einhaltungsquote** = Anteil der Fahrzeuge mit v ≤ Limit. **Qualifizierte Einhaltungsquote** = Anteil mit
v − Toleranz ≤ Limit; die Toleranz beträgt 3 km/h unter 100 km/h und ab 100 km/h 3 % (aufgerundet).

## Bekannte Einschränkungen

Einzelne Dateien enthalten fehlerhafte Zeitstempel und Ausreißer, und die berechneten Überschreitungs-
quoten weichen bei manchen Messungen von den Auswertungen der Software des Geräteherstellers ab.
Details in `docs/dsd-format.md`. Die Auswertungen sind daher vor einer Interpretation je Messstelle zu
prüfen.

## Lizenz

In diesem Repository gelten drei Lizenzen:

| Was | Lizenz |
|-----|--------|
| Software: `dsd2csv.py`, `rauschen.py`, `gruppen.py`, `zwischenspeicher.py`, `uhr_belege.py`, `metadaten.py`, `standorte.py`, `bruch.py`, `kalender.py`, `verhalten.py`, `stadtgruppen.py`, `aggregat.py`, `daten_bauen.py`, Tests, `tools/`, `site/`, `.github/` | [MIT](LICENSE) |
| Daten und Dokumentation: `.dsd`-Dateien, abgeleitete CSV- und YAML-Dateien, `metadaten.yaml`, `uhr-analyse.md`, `belege/` (außer `belege/wetter.json`), `README.md`, `DATEN.md`, `docs/` | [CC0 1.0](LICENSE-DATEN) (Public Domain Dedication) |
| Wetterdaten: `belege/wetter.json` (Daten des Deutschen Wetterdienstes, ausgewählt, auf Ortszeit-Tage umgerechnet und zusammengefasst) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.de), **Quelle: Deutscher Wetterdienst** |

Die Wetterdaten sind **nicht** CC0: Der Deutsche Wetterdienst gibt seine frei zugänglichen Wetter- und Klimadaten unter CC BY 4.0 mit
Quellenvermerk frei (<https://www.dwd.de/DE/service/rechtliche_hinweise/rechtliche_hinweise_node.html>). Wer `belege/wetter.json` oder
Auswertungen verwendet, die darauf beruhen (zum Beispiel die Einteilung in Regentage), muss den Deutschen Wetterdienst nennen und
Änderungen kenntlich machen; Einzelheiten in `docs/wetter.md`.

`belege/neuss-adressen.csv` enthält Hauskoordinaten der Stadt Neuss aus den Gebäudereferenzen von Geobasis NRW. Sie stehen unter der
Datenlizenz Deutschland – Zero – Version 2.0 (<https://www.govdata.de/dl-de/zero-2-0>), also ohne Einschränkung und Bedingung und damit
vereinbar mit CC0; die Quelle wird trotzdem genannt (Geobasis NRW, <https://www.opengeodata.nrw.de/produkte/geobasis/lk/akt/gebref_txt/>).

Die Quelldateien der Software tragen zusätzlich eine `SPDX-License-Identifier`-Zeile. Die Angaben in
`metadaten.yaml` und `belege/` stammen aus öffentlichen Mitteilungen der Verwaltung im Ratsinformationssystem der Stadt
Neuss und nennen jeweils ihre Quelle.

Die Rohdaten stammen aus Messungen der Stadt Neuss. Der Betreiber dieses Repositories ist nicht ihr
Urheber, beansprucht keine Rechte daran und geht davon aus, dass an reinen Messwerten keine Schutzrechte
bestehen. Mit CC0 verzichtet er auf alle Rechte, die er selbst an den hier veröffentlichten Dateien haben
könnte. Das ist keine Rechtsberatung.

## Kontakt, Impressum und Datenschutz

Fabian Grewing, <fabian.grewing@proton.me>

- [Datenschutzerklärung](https://khazuar.github.io/neuss-dialogdisplays/datenschutz.html)
