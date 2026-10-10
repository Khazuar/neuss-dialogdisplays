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
- `<Standortordner>/metadaten.yaml` – zusätzlich erhobene Metadaten, siehe [docs/metadaten.md](docs/metadaten.md)
- `belege/` – Ergebnisse der Prüfung (`uhr-bewertung.json`) und der Auswertung der Mitteilungen der
  Verwaltung (`ris.json`, `ris-messstellen.json`, `ris-zuordnung.json`, `metadaten.json`) sowie die
  Korrekturen des Tempolimits, wo die Mitteilung ein anderes Limit nennt als die DSD (`korrekturen.json`)
- `tools/` – holt die Mitteilungen der Verwaltung aus dem Ratsinformationssystem und zerlegt sie
  (`ris_sammeln.py`, `ris_auswerten.py`, `ris_messstellen.py`)
- `docs/uhr-bewertung.md` – wie über die Zuverlässigkeit der Uhren entschieden wird, mit Grenzen
- `docs/metadaten.md` – Herkunft, Zuordnung und Abdeckung der Metadaten
- `docs/rauschen.md` – Modell, Regeln und Grenzen des Rauschbodenabzugs
- `docs/gruppen.md` – Zerlegung der Verteilung in Gruppen, Zeitscheiben und die Auswahl auf den Detailseiten
- `docs/gefaehrdung.md` – Modelle und Annahmen für Gefährdung (Nilsson, Restgeschwindigkeit), Lärm und Ereignisse pro Nacht
- `seiten_bauen.py` – baut je Standort eine Detailseite für die GitHub Pages (`standorte/<name>.html`), mit
  Geschwindigkeits-Histogrammen als Inline-SVG
- `gruppen.py` – zerlegt die Verteilung je Datei in Gruppen (Lognormal-Mischung, Zahl der Gruppen aus den Daten) und baut die Zellen für die Auswahl nach Tageszeit, Tagen und Gruppe
- `zwischenspeicher.py` – Zwischenspeicher für Ergebnisse je Datei (nur geänderte Dateien oder Skripte werden neu gerechnet)
- `test_dsd2csv.py`, `test_uhr_belege.py`, `test_metadaten.py`, `test_seiten.py`, `test_rauschen.py`, `test_gruppen.py`, `test_filter.py` – Tests (`python3 -m unittest -v`)
- `docs/dsd-format.md` – Beschreibung des (undokumentierten) DSD-Formats und bekannte Datenprobleme
- `site/` – GitHub Pages: Übersichtstabelle der YAML-Auswertungen, Impressum (Vorlage) und Datenschutz, dazu `filter.js` (kleines Skript für die Auswahl auf den Detailseiten, liest nur die Daten der eigenen Seite)
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
- **ZIP-Archiv:** unter [Releases](https://github.com/Khazuar/neuss-dialogdisplays/releases) gibt es zu
  jedem Tag `v*` ein ZIP mit allen Ergebnissen inklusive der CSV-Dateien, zum Archivieren und Zitieren
  eines festen Stands.

Wer die Daten selbst erzeugen will, nutzt dazu das Skript (siehe unten).

## Benutzung

Python 3.7 oder neuer, nur Standardbibliothek.

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
    `spektrum` (Fahrten je 1000 Stunden, verkehrsunabhängig und insgesamt); `fahrzeuge_in_datei` ist die Zahl vor dem Abzug,
  - `bereinigt` – dieselben Kennzahlen nur für Fahrzeuge mit nutzbarer Zeit,
  - `teilzeitraeume` – dieselben Kennzahlen für `nacht` (22–6 Uhr), `vormittag` (6–12), `nachmittag` (12–19), `abend` (19–22)
    und `schulweg` (Mo–Fr 7–8 Uhr), jeweils in Ortszeit,
  - `gruppen` – Beschreibung der Verteilung als Mischung angepasster Kurven (Zahl der Gruppen aus den Daten, auch keine Zerlegung):
    Anteil, Modus, Kennzahlen je Kurve, dazu der Rest, den die Kurven nicht erklären, und die Abweichung des Modells
    (`docs/gruppen.md`),
  - `gefaehrdung` und `laerm` – Schätzungen je Zeitraum: relativer Risikoindex nach Nilsson, Aufprallgeschwindigkeit
    und Anteil der Fahrzeuge, die mit mehr als 30 bzw. 50 km/h aufträfen, Lärm gegenüber dem Tempolimit
    (`docs/gefaehrdung.md`),
  - `nacht_ereignisse` – Nächte (22–6 Uhr) mit Fahrten ab doppeltem Tempolimit, 100 und 120 km/h,
  - `histogramm` – Anzahl Fahrzeuge je ganzem km/h (`ab_kmh`, `anzahl`), auch je Zeitraum; steht nur in der YAML, nicht
    in `summary.csv`. Die Detailseiten zeichnen daraus die Verteilung: eine Klasse je km/h (Auflösung der Geräte), bei
    wenigen Fahrzeugen breitere Klassen nach Freedman-Diaconis (2 · Quartilsabstand · n^(−1/3), höchstens 5 km/h),
    und die Höhe ist der Anteil der Fahrzeuge je km/h. Die Skala endet beim 99,99-%-Perzentil; schnellere Fahrzeuge
    (meist Messfehler) werden unter dem Bild gezählt
- `<name>.zellen.json` – Histogramme je Wochentag und Stunde und Gewichte der Gruppen; daraus rechnet die Detailseite die Auswahl nach
  Tageszeit, Tagen und Gruppe
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

In diesem Repository gelten zwei Lizenzen:

| Was | Lizenz |
|-----|--------|
| Software: `dsd2csv.py`, `rauschen.py`, `gruppen.py`, `zwischenspeicher.py`, `uhr_belege.py`, `metadaten.py`, Tests, `tools/`, `site/`, `.github/` | [MIT](LICENSE) |
| Daten und Dokumentation: `.dsd`-Dateien, abgeleitete CSV- und YAML-Dateien, `metadaten.yaml`, `uhr-analyse.md`, `belege/`, `README.md`, `docs/` | [CC0 1.0](LICENSE-DATEN) (Public Domain Dedication) |

Die Quelldateien der Software tragen zusätzlich eine `SPDX-License-Identifier`-Zeile. Die Angaben in
`metadaten.yaml` und `belege/` stammen aus öffentlichen Mitteilungen der Verwaltung im Ratsinformationssystem der Stadt
Neuss und nennen jeweils ihre Quelle.

Die Rohdaten stammen aus Messungen der Stadt Neuss. Der Betreiber dieses Repositories ist nicht ihr
Urheber, beansprucht keine Rechte daran und geht davon aus, dass an reinen Messwerten keine Schutzrechte
bestehen. Mit CC0 verzichtet er auf alle Rechte, die er selbst an den hier veröffentlichten Dateien haben
könnte. Das ist keine Rechtsberatung.

## Kontakt, Impressum und Datenschutz

Fabian Grewing, <fabian.grewing@proton.me>

- [Impressum](https://khazuar.github.io/neuss-dialogdisplays/impressum.html)
- [Datenschutzerklärung](https://khazuar.github.io/neuss-dialogdisplays/datenschutz.html)
