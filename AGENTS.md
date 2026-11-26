# Hinweise für KI-Assistenten

Dieses Repository enthält die Rohdaten (DSD-Dateien) der Dialogdisplays in Neuss und die Skripte, die daraus die Seite
<https://khazuar.github.io/neuss-dialogdisplays/> bauen. Für Fragen zu einem Standort oder zu Geschwindigkeiten gilt:

## 1. Fertige Daten laden, nicht selbst rechnen

Die bereinigten Daten liegen fertig unter <https://khazuar.github.io/neuss-dialogdisplays/daten/> (per `curl` erreichbar,
Spalten in [DATEN.md](DATEN.md)). Sie sind in Ortszeit, mit geprüfter Uhr, ohne Rauschboden und nach Einsätzen zugeordnet.
`dsd2csv.py` auf eine einzelne DSD-Datei anzuwenden, liefert dagegen die rohe Sicht der Datei: Gerätezeit, Rauschen und
Fahrzeuge anderer Standorte. Die ganze Pipeline lokal nachzurechnen (`.github/workflows/pages.yml`) dauert über zehn Minuten
und ist nur nötig, wenn Skripte oder Belege geändert werden.

## 2. Einsätze, nicht Messungen

Ein Ordner mit einer DSD-Datei ist eine **Messung** (Sicht der Verwaltung), kein Standort. Meist wurde das Gerät ausgelesen und
erst Tage oder Wochen später umgehängt: **Der Anfang einer Datei gehört oft noch zum vorigen Standort**, das Ende manchmal schon
zum nächsten. Ein Bruch in der Mitte einer Datei ist darum oft ein Ortswechsel und kein Effekt am Standort.

Die Hauptauswertung folgt den **Einsätzen** (wann ein Gerät tatsächlich wo gemessen hat, [docs/einsaetze.md](docs/einsaetze.md)):

| Frage | Datei unter /daten/ |
| --- | --- |
| Zeitraum, Gerät, Status eines Einsatzes; welche Teile anderer Dateien dazugehören | `einsaetze.csv` |
| V85, Mittel, Einhaltung, Raten eines Standorts, auch nach Tageszeit | `kennzahlen.csv` mit `bereich` = `einsatz` und `messung_id` = Einsatz-ID |
| eigene Zeitfenster, Verteilungen | `einsaetze-stunden.csv.gz` |
| Umhängen, Inbetriebnahme (minutengenau) | `bewegungen.csv` |

Die Einsatz-ID steht in der Adresse der Detailseite: `standorte/martinstrasse.html#e-116-martinstrasse-dsd16734-tempo30-8/allgemein`
gehört zu `einsatz_id` = `e-116-martinstrasse-dsd16734-tempo30-8`. Zeilen mit `bereich` = `messung` oder `abschnitt` und die
Dateien `summary.csv` und `auswertung.yaml` sind die Sicht der Messungen; sie nur nehmen, wenn ausdrücklich nach der Sicht der
Verwaltung gefragt ist.

## 3. Lage

Die Koordinaten der Standorte sind meist Schätzungen aus dem Straßennamen ([docs/standorte.md](docs/standorte.md)). `sicherheit`
= `manuell korrigiert` heißt: von Hand angegeben, in `belege/standort-hinweise.json` mit Quelle. Neue Ortsangaben kommen dorthin,
danach `python3 -I metadaten.py .` und die erzeugten Dateien (`*/metadaten.yaml`, `belege/metadaten.json`, `belege/standorte.json`)
mit committen.

## 4. Keine Deutung

Repository und Seite beschreiben die Daten, sie bewerten keine Standorte. Deutungen gehören nicht in Commits, Doku oder Seiten.
