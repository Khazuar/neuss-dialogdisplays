# Betrieb: GitHub Pages und Impressum

Einmalige Einrichtung auf GitHub, damit der Workflow `pages.yml` die Seite veröffentlichen kann.

## GitHub Pages aktivieren

Settings → Pages → Source: **GitHub Actions**. Das Repository muss öffentlich sein, sonst benötigt
GitHub Pages einen kostenpflichtigen Plan.

## Impressum-Angaben als Repository-Variablen

Die Anschrift soll nicht in der Git-Historie stehen. Sie wird deshalb beim Bauen der Seite aus
Repository-Variablen in `site/impressum.html` eingesetzt (`site/impressum_bauen.py`).

Settings → Secrets and variables → Actions → **Variables** → New repository variable:

| Variable | Inhalt | Pflicht |
|----------|--------|---------|
| `IMPRESSUM_STRASSE` | Straße und Hausnummer | ja |
| `IMPRESSUM_ORT` | PLZ und Ort | ja |
| `IMPRESSUM_TELEFON` | Telefonnummer | nein |

Es sind bewusst **Variables** und keine Secrets: Secrets sind für Werte gedacht, die nie öffentlich
werden. Die Anschrift steht im veröffentlichten Impressum, nur eben nicht im Git.

Fehlt eine Pflichtvariable, bricht der Workflow mit einer Fehlermeldung ab. Die Seite wird dann nicht
neu veröffentlicht, die letzte Version bleibt online.

## Ablauf

- Push auf `main` oder manuell (Actions → Pages → Run workflow): Seite neu bauen und veröffentlichen.
- Tag `v*`: `release.yml` hängt ein ZIP mit allen Ergebnissen (CSV und YAML) an ein Release.
