# SPDX-License-Identifier: MIT
"""Ergaenzt die gebaute Seite um das, was Suchmaschinen und KI-Abrufer ohne JavaScript brauchen.

Aufruf (nach dem Kopieren von site/* nach _site):
  python3 -I seo_bauen.py --ziel _site

Schreibt:
  robots.txt    alles erlaubt, mit Verweis auf die Sitemap
  sitemap.xml   Startseite, Standortseiten, Verhaltensgruppen, Datenwoerterbuch, llms.txt, CSV-Dateien
Ersetzt in index.html die Marke <!--STATISCH--> durch eine feste Tabelle (eine Zeile je Messung) aus summary.csv. Die interaktive
Tabelle blendet sie aus, sobald sie geladen ist; ohne JavaScript bleibt sie sichtbar.
"""
import argparse
import csv
import datetime
import html
import json
import os
import re
import sys

BASIS = "https://khazuar.github.io/neuss-dialogdisplays/"
MARKE = "<!--STATISCH-->"
DATEIEN = ("DATEN.md", "llms.txt", "daten/messungen.csv", "daten/kennzahlen.csv", "daten/abschnitte.csv", "daten/tage.csv",
           "daten/luecken.csv", "summary.csv")


def e(x):
    return html.escape(str(x), quote=True)


def zahl(s, stellen=0):
    try:
        return f"{float(s):.{stellen}f}".replace(".", ",")
    except (TypeError, ValueError):
        return "–"


def datum(s):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s or "")
    return f"{m.group(3)}.{m.group(2)}.{m.group(1)}" if m else "–"


def statische_tabelle(ziel):
    """Feste Tabelle der Messungen (bereinigte Werte aus summary.csv); None, wenn summary.csv fehlt."""
    pfad = os.path.join(ziel, "summary.csv")
    if not os.path.exists(pfad):
        return None
    seiten = {}
    if os.path.exists(os.path.join(ziel, "uebersicht.json")):
        with open(os.path.join(ziel, "uebersicht.json"), encoding="utf-8") as f:
            seiten = json.load(f)
    zeilen = []
    with open(pfad, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            # bereinigte Werte: Ortszeit, nur Fahrzeuge mit nutzbarer Uhrzeit, Rauschboden und Regen abgezogen (wie daten/kennzahlen.csv)
            p = "bereinigt."
            n = int(float(r.get(p + "anzahl_fahrzeuge") or 0))
            if not n:
                continue
            s = seiten.get(f'{r["standort"]}/{r["datei"]}') or {}
            name = s.get("standort") or r["standort"]
            ort = f'<a href="{e(s["seite"])}">{e(name)}</a>' if s.get("seite") else e(name)
            hinweis = "" if r.get("uhr.nutzbarkeit") == "nutzbar" else "Uhr nur teilweise oder nicht nutzbar, wenige Fahrzeuge"
            zeilen.append((name.lower(), r[p + "messzeitraum.start"],
                           f'<tr><td>{ort}</td><td>{e(r["tempolimit_kmh"] or "–")}</td>'
                           f'<td>{datum(r[p + "messzeitraum.start"])} bis {datum(r[p + "messzeitraum.ende"])}</td><td>{n}</td>'
                           f'<td>{zahl(r[p + "geschwindigkeit_kmh.v85"])}</td>'
                           f'<td>{zahl(r[p + "einhaltung.einhaltungsquote_prozent"], 1)}</td><td>{e(hinweis)}</td></tr>'))
    zeilen.sort(key=lambda z: (z[0], z[1]))
    return ('<section id="statisch"><h2>Messungen im Überblick</h2>'
            '<p class="muted">Feste Fassung der Übersicht ohne JavaScript: eine Zeile je Messung, '
            f'{len(zeilen)} Messungen mit Fahrzeugen. Die Werte sind bereinigt wie in den CSV-Dateien unter /daten/: Ortszeit, nur Fahrzeuge '
            'mit nutzbarer Uhrzeit, Rauschboden und Regenanteil abgezogen (<a href="DATEN.md">Datenwörterbuch</a>). V85 in km/h, Einhaltung '
            'in Prozent der Fahrzeuge bis zum Tempolimit. Die interaktive Tabelle teilt zusätzlich an erkannten Brüchen, zeigt Tageszeiten und '
            'färbt nach den Stufen der Verwaltung; Messungen mit unplausiblen Geschwindigkeiten sind hier nicht ausgesondert.</p>'
            '<div class="statisch-wrap" style="overflow-x:auto"><table><thead><tr><th>Messstelle</th><th>Tempolimit km/h</th><th>Zeitraum</th>'
            '<th>Fahrzeuge</th><th>V85 km/h</th><th>Einhaltung %</th><th>Hinweis</th></tr></thead><tbody>' +
            "".join(z[2] for z in zeilen) + '</tbody></table></div></section>')


def sitemap(ziel):
    heute = datetime.date.today().isoformat()
    urls = [""]
    for name in ("verhaltensgruppen.html",):
        if os.path.exists(os.path.join(ziel, name)):
            urls.append(name)
    sdir = os.path.join(ziel, "standorte")
    if os.path.isdir(sdir):
        urls += ["standorte/" + n for n in sorted(os.listdir(sdir)) if n.endswith(".html")]
    urls += [d for d in DATEIEN if os.path.exists(os.path.join(ziel, d))]
    eintraege = "".join(f"<url><loc>{e(BASIS + u)}</loc><lastmod>{heute}</lastmod></url>\n" for u in urls)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + eintraege + "</urlset>\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ziel", required=True, help="gebauter Seitenordner (_site)")
    a = ap.parse_args()
    pfad = os.path.join(a.ziel, "index.html")
    with open(pfad, encoding="utf-8") as f:
        seite = f.read()
    tabelle = statische_tabelle(a.ziel)
    if MARKE in seite:
        seite = seite.replace(MARKE, tabelle or "")
        with open(pfad, "w", encoding="utf-8", newline="") as f:
            f.write(seite)
    else:
        print(f"Warnung: Marke {MARKE} fehlt in index.html", file=sys.stderr)
    with open(os.path.join(a.ziel, "robots.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(f"User-agent: *\nAllow: /\n\nSitemap: {BASIS}sitemap.xml\n")
    with open(os.path.join(a.ziel, "sitemap.xml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(sitemap(a.ziel))


if __name__ == "__main__":
    main()
