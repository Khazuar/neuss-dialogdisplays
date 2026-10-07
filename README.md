# Dialogdisplay-Messdaten (IFG-Anfrage)

Rohdaten (`.dsd`) von Geschwindigkeits-Dialogdisplays, die per Informationsfreiheitsanfrage (IFG)
bei der Stadt Neuss angefragt wurden, dazu ein Skript, das sie in lesbare Formate umwandelt und je
Messstelle auswertet.

**Im Repository liegen nur die DSD-Rohdaten und die Skripte.** Die abgeleiteten Daten (CSV und YAML)
werden aus den DSDs erzeugt und separat veröffentlicht, siehe [Abgeleitete Daten](#abgeleitete-daten).

## Inhalt

- `<Nr>_<Straße>/*.dsd` – je Ordner eine oder mehrere Messungen
- `dsd2csv.py` – DSD → CSV und YAML-Auswertung
- `docs/dsd-format.md` – Beschreibung des (undokumentierten) DSD-Formats und bekannte Datenprobleme
- `site/index.html` – Startseite der GitHub Pages (Übersichtstabelle der YAML-Auswertungen)
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

Optionen: `--limit N` (Tempolimit erzwingen), `--min-kmh N` (Werte unter N km/h aus der Auswertung
nehmen), `--meta`, `--status`. Mit `-I` startet Python isoliert; das ist bei Dateien aus fremder Quelle
sinnvoll.

### Ausgabe

- `<name>.csv` – ein Fahrzeug pro Zeile: `zeitstempel`, `geschwindigkeit_kmh`
- `<name>.yaml` – Auswertung je Messung: Standort (relativer Ordnerpfad), Tempolimit samt Quelle,
  Anzahl Fahrzeuge, Messzeitraum, mittlere/maximale Geschwindigkeit, V85/V95/V99, Einhaltungsquote und
  qualifizierte Einhaltungsquote
- `auswertung.yaml`, `summary.csv` – alle Messungen zusammengefasst

Das **Tempolimit** wird aus der DSD gelesen (`safety_speed`), siehe `docs/dsd-format.md`.
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
| Software: `dsd2csv.py`, `site/`, `.github/` | [MIT](LICENSE) |
| Daten und Dokumentation: `.dsd`-Dateien, abgeleitete CSV- und YAML-Dateien, `README.md`, `docs/` | [CC0 1.0](LICENSE-DATEN) (Public Domain Dedication) |

Die Quelldateien der Software tragen zusätzlich eine `SPDX-License-Identifier`-Zeile.

Die Rohdaten stammen aus Messungen der Stadt Neuss. Der Betreiber dieses Repositories ist nicht ihr
Urheber, beansprucht keine Rechte daran und geht davon aus, dass an reinen Messwerten keine Schutzrechte
bestehen. Mit CC0 verzichtet er auf alle Rechte, die er selbst an den hier veröffentlichten Dateien haben
könnte. Das ist keine Rechtsberatung.
