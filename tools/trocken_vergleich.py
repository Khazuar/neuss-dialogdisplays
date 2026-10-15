# SPDX-License-Identifier: MIT
"""Alle Stunden gegen nur trockene Stunden je Messung (docs/totzeit.md): Fahrzeuge je vollstaendig aufgezeichneter Stunde, V85 und Einhaltung.

Liest die bereinigten Stundendaten (daten_bauen.py, DATEN.md). Trocken = regenklasse 0. Je Messung mit mindestens 200 trockenen und 50 Regenstunden.
Aufruf: python3 -I tools/trocken_vergleich.py [_vorschau/daten]"""
import collections
import csv
import gzip
import math
import os
import statistics
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def v85(hist):
    n = sum(hist.values())
    k, kum = math.ceil(0.85 * n), 0
    for v in sorted(hist):
        kum += hist[v]
        if kum >= k:
            return v


def main():
    ordner = sys.argv[1] if len(sys.argv) > 1 else os.path.join(WURZEL, "_vorschau", "daten")
    with open(os.path.join(ordner, "messungen.csv"), encoding="utf-8", newline="") as fh:
        limits = {m["messung_id"]: int(m["tempolimit_kmh"]) for m in csv.DictReader(fh) if m["tempolimit_kmh"]}
    je = collections.defaultdict(lambda: {"alle": [collections.Counter(), set()], "trocken": [collections.Counter(), set()], "regen": set()})
    with gzip.open(os.path.join(ordner, "stunden.csv.gz"), "rt", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["voll"] != "1" or r["regenklasse"] == "":
                continue
            e = je[r["messung_id"]]
            stunde = (r["datum"], r["stunde"], r["utc_versatz_h"])
            v, n = int(r["kmh"]), int(r["anzahl"])
            e["alle"][0][v] += n
            e["alle"][1].add(stunde)
            if r["regenklasse"] == "0":
                e["trocken"][0][v] += n
                e["trocken"][1].add(stunde)
            elif r["regenklasse"] in ("1", "2", "3"):
                e["regen"].add(stunde)
    zeilen = []
    for mid, e in je.items():
        if len(e["trocken"][1]) < 200 or len(e["regen"]) < 50 or mid not in limits:
            continue
        lim = limits[mid]
        out = []
        for art in ("alle", "trocken"):
            h, stunden = e[art]
            n = sum(h.values())
            out.append((n / len(stunden), v85(h), 100 * sum(c for v, c in h.items() if v <= lim) / n))
        zeilen.append((mid, len(e["regen"]) / len(e["alle"][1]), out))
    print("%d Messungen (mindestens 200 trockene und 50 Regenstunden)" % len(zeilen))
    print("Anteil der Regenstunden an den Stunden: Median %.0f %%" % (100 * statistics.median(z[1] for z in zeilen)))
    je_h = [100 * (z[2][1][0] / z[2][0][0] - 1) for z in zeilen]
    dv = [z[2][1][1] - z[2][0][1] for z in zeilen]
    de = [z[2][1][2] - z[2][0][2] for z in zeilen]
    print("Nur trocken gegen alle: Fahrzeuge je Stunde Median %+.1f %% (10 %% %+.1f, 90 %% %+.1f, groesster %+.1f)" % (
        statistics.median(je_h), sorted(je_h)[len(je_h) // 10], sorted(je_h)[int(0.9 * len(je_h))], max(je_h)))
    print("  V85: verschieden in %d von %d Messungen %s; Einhaltung Median %+.2f Prozentpunkte (groesster Betrag %.2f)" % (
        sum(1 for x in dv if x), len(dv), dict(collections.Counter(dv)), statistics.median(de), max(abs(x) for x in de)))
    print("Groesste Unterschiede der Fahrzeuge je Stunde:")
    for z, x in sorted(zip(zeilen, je_h), key=lambda p: -abs(p[1]))[:5]:
        print("  %-60s Regenstunden %2.0f %%, je Stunde alle %.1f / trocken %.1f (%+.1f %%), V85 %s / %s" % (
            z[0][:60], 100 * z[1], z[2][0][0], z[2][1][0], x, z[2][0][1], z[2][1][1]))


if __name__ == "__main__":
    main()
