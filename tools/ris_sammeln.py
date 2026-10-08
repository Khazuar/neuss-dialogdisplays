# SPDX-License-Identifier: MIT
"""Sammelt die Vorlagen und Dokumente zu den Dialog Displays aus dem Ratsinformationssystem
der Stadt Neuss (SessionNet, https://ris-neuss.itk-rheinland.de/sessionnetneubi/).

Die Mitteilungen der Verwaltung nennen Erfassungszeitraeume (Aufstellung bis Abbau) und
Standorte. Sie sind eine von der Geraeteuhr unabhaengige Datumsquelle, weil die Termine aus
dem Einsatz der Verwaltung stammen und nicht aus den DSD-Dateien.

Aufruf:
  python3 -I tools/ris_sammeln.py ris_roh

Schreibt nach ris_roh/ (steht nicht im Repository, siehe .gitignore):
  vo0050_<id>.html   Vorlage (Betreff, Dokumente)
  vo0053_<id>.html   Beratungsfolge (Gremium, Sitzungsdatum)
  do_<id>.pdf        Dokumente
  index.json         Zuordnung Vorlage -> Titel, Dokumente
Bereits geladene Dateien werden uebersprungen. Zwischen zwei Abrufen liegt eine Sekunde.

Die heruntergeladenen Dateien stammen aus einer fremden Quelle: sie werden nie ausgefuehrt, nur
als Text gelesen (siehe ris_auswerten.py).
"""
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

BASIS = "https://ris-neuss.itk-rheinland.de/sessionnetneubi/"
KENNUNG = "neuss-dialogdisplays/1.0 (Recherche; fabian.grewing@proton.me)"
SUCHBEGRIFFE = ["Dialog Displays", "Dialog-Displays", "Dialogdisplays", "Verkehrsmessungen",
                "Geschwindigkeitsanzeige", "Geschwindigkeitsanzeigetafel"]
TITEL_STICHWORTE = ("dialog", "display", "verkehrsmess", "verkehrsmengen", "geschwindigkeitsanzeige", "smiley")
PAUSE_S = 1.0
_letzter_abruf = [0.0]


def abrufen(url, daten=None):
    warte = PAUSE_S - (time.time() - _letzter_abruf[0])
    if warte > 0:
        time.sleep(warte)
    anfrage = urllib.request.Request(
        BASIS + url, headers={"User-Agent": KENNUNG},
        data=urllib.parse.urlencode(daten).encode() if daten else None)
    for versuch in range(3):
        try:
            with urllib.request.urlopen(anfrage, timeout=60) as r:
                inhalt = r.read()
            _letzter_abruf[0] = time.time()
            return inhalt
        except OSError as e:
            if versuch == 2:
                raise
            print(f"  Wiederholung wegen {e}", file=sys.stderr)
            time.sleep(5)


def zwischenspeichern(pfad, url):
    if not os.path.exists(pfad):
        with open(pfad, "wb") as f:
            f.write(abrufen(url))
    with open(pfad, "rb") as f:
        return f.read()


def suchen(begriff):
    """Vorlagen-Recherche; gibt {Vorlagen-ID: Titel} zurueck."""
    t = abrufen("vo0040.asp", {"__swords": begriff, "__sao": "1", "__axxdat_full": "2018-01-01",
                              "__exxdat_full": "2030-12-31", "__sgo": "Suchen"}).decode("utf-8", "replace")
    treffer = {}
    for zeile in t.split('<tr class="smc-t-r-l">')[1:]:
        zeile = zeile.split("</tr>")[0]
        m = re.search(r'href="vo0050\.asp\?__kvonr=(\d+)"[^>]*title="Vorlage anzeigen: ([^"]*)"', zeile)
        if m:
            treffer[m.group(1)] = html.unescape(m.group(2))
    return treffer


def dokumente(seite):
    return sorted(set(re.findall(r"getfile\.asp\?id=(\d+)&(?:amp;)?type=do", seite)), key=int)


def main():
    ziel = sys.argv[1] if len(sys.argv) > 1 else "ris_roh"
    os.makedirs(ziel, exist_ok=True)
    vorlagen = {}
    for begriff in SUCHBEGRIFFE:
        gefunden = suchen(begriff)
        print(f"Suche '{begriff}': {len(gefunden)} Treffer", file=sys.stderr)
        vorlagen.update(gefunden)
    relevant = {k: t for k, t in vorlagen.items() if any(s in t.lower() for s in TITEL_STICHWORTE)}
    print(f"{len(relevant)} relevante Vorlagen (von {len(vorlagen)})", file=sys.stderr)

    index = {}
    for n, (kvonr, titel) in enumerate(sorted(relevant.items(), key=lambda x: int(x[0])), 1):
        seite = zwischenspeichern(os.path.join(ziel, f"vo0050_{kvonr}.html"), f"vo0050.asp?__kvonr={kvonr}")
        zwischenspeichern(os.path.join(ziel, f"vo0053_{kvonr}.html"), f"vo0053.asp?__kvonr={kvonr}")
        dok = dokumente(seite.decode("utf-8", "replace"))
        for d in dok:
            zwischenspeichern(os.path.join(ziel, f"do_{d}.pdf"), f"getfile.asp?id={d}&type=do")
        index[kvonr] = {"titel": titel, "dokumente": dok,
                        "url": f"{BASIS}vo0050.asp?__kvonr={kvonr}"}
        print(f"[{n}/{len(relevant)}] {kvonr}: {titel[:60]} ({len(dok)} Dokumente)", file=sys.stderr)
    with open(os.path.join(ziel, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
