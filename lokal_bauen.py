#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fabian Grewing
"""Baut die GitHub-Pages-Seite lokal, damit man sie vor dem Push im Browser ansehen kann.

Dieselben Schritte wie .github/workflows/pages.yml (ohne Tests):
  1. dsd2csv.py   Auswertungen, Zellen und Zusammenfassungen aus den DSD-Dateien (mit Zwischenspeicher, mehrere Prozesse)
  2. seiten_bauen.py   Detailseiten der Standorte
  3. site/*       Uebersichtsseite, Datenschutz, Stylesheet und filter.js
  4. Impressum aus den Umgebungsvariablen IMPRESSUM_STRASSE, IMPRESSUM_ORT, IMPRESSUM_TELEFON (ohne sie bleiben die Felder leer)

Aufruf:
  python3 -I lokal_bauen.py                  baut nach _vorschau/ und nennt die Adresse der Startseite
  python3 -I lokal_bauen.py --serve          baut und startet einen lokalen Server (nur dieser Rechner): http://127.0.0.1:8000/
  python3 -I lokal_bauen.py --serve --oeffnen   ... und oeffnet den Browser

Die Detailseiten funktionieren auch direkt aus dem Ordner (file://). Die Startseite laedt summary.csv und braucht den Server.
Der Ordner _vorschau/ und der Zwischenspeicher .zwischenspeicher/ gehoeren nicht ins Repository (.gitignore).
"""
import argparse
import functools
import http.server
import os
import shutil
import subprocess
import sys
import webbrowser

HIER = os.path.dirname(os.path.abspath(__file__))
SEITEN = ("index.html", "datenschutz.html", "style.css", "filter.js")


def befehle(eingabe, ziel, cache, jobs):
    """Die Aufrufe der Skripte (ohne Impressum und Kopieren), als Liste von Argumentlisten."""
    py = [sys.executable, "-I"]
    auswerten = py + [os.path.join(HIER, "dsd2csv.py"), eingabe, "-o", ziel, "--keine-csv", "--jobs", str(jobs)]
    if cache:
        auswerten += ["--cache", cache]
    return [auswerten, py + [os.path.join(HIER, "seiten_bauen.py"), "--auswertung", os.path.join(ziel, "auswertung.json"), "--ziel", ziel]]


def bauen(eingabe, ziel, cache, jobs, ausgabe=sys.stderr):
    os.makedirs(ziel, exist_ok=True)
    for befehl in befehle(eingabe, ziel, cache, jobs):
        print("$ " + " ".join(os.path.basename(b) if os.path.isabs(b) else b for b in befehl), file=ausgabe)
        subprocess.run(befehl, check=True)
    for name in SEITEN:
        shutil.copyfile(os.path.join(HIER, "site", name), os.path.join(ziel, name))
    subprocess.run([sys.executable, os.path.join(HIER, "site", "impressum_bauen.py"), os.path.join(HIER, "site", "impressum.html"),
                    os.path.join(ziel, "impressum.html")], check=True)
    return os.path.join(ziel, "index.html")


def starte_server(ziel, port, oeffnen):
    """Liefert den Ordner auf 127.0.0.1 aus (nur dieser Rechner), bis Strg+C gedrueckt wird."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ziel)
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as server:
        adresse = f"http://127.0.0.1:{port}/"
        print(f"Seite unter {adresse} (beenden mit Strg+C)", file=sys.stderr)
        if oeffnen:
            webbrowser.open(adresse)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("beendet", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--eingabe", default=HIER, help="Ordner mit den DSD-Dateien (Standard: Repository)")
    ap.add_argument("--ziel", default=os.path.join(HIER, "_vorschau"), help="Ausgabeordner (Standard: _vorschau)")
    ap.add_argument("--jobs", type=int, default=min(4, os.cpu_count() or 1), help="Dateien gleichzeitig auswerten")
    ap.add_argument("--ohne-cache", action="store_true", help="ohne Zwischenspeicher rechnen")
    ap.add_argument("--serve", action="store_true", help="danach einen lokalen Server starten")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--oeffnen", action="store_true", help="mit --serve den Browser oeffnen")
    a = ap.parse_args()
    cache = None if a.ohne_cache else os.path.join(HIER, ".zwischenspeicher")
    start = bauen(os.path.abspath(a.eingabe), os.path.abspath(a.ziel), cache, a.jobs)
    print("fertig: " + os.path.abspath(start), file=sys.stderr)
    if a.serve:
        starte_server(os.path.abspath(a.ziel), a.port, a.oeffnen)
    else:
        print("Detailseiten: direkt aus dem Ordner oeffnen (standorte/<name>.html); Startseite mit --serve.", file=sys.stderr)


if __name__ == "__main__":
    main()
