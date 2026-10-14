# SPDX-License-Identifier: MIT
"""Doppelmessungen schneller Fahrzeuge? (docs/totzeit.md, Versuch 6)

Nach Datensaetzen ab 60 km/h folgt auffaellig oft ein weiterer Datensatz kurz nach der Sperre. Ist das dasselbe Fahrzeug, zweimal gemessen,
muesste der Folgedatensatz fast dieselbe Geschwindigkeit haben. Je Datei mit 5 s Sperre: Paare mit Abstand unter tau + 5 s, nach Tempo des
ersten Datensatzes; Anteil mit |v2 - v1| <= 2 km/h gegen Paare mit Abstand 30 bis 120 s (unabhaengige Fahrzeuge, gleiche Tempoklasse).

Aufruf: python3 -I tools/totzeit_doppelt.py [--auswertung _vorschau/auswertung.json] [--jobs 8]"""
import argparse
import collections
import json
import multiprocessing
import os
import statistics
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)  # python -I nimmt das Skriptverzeichnis nicht auf
KLASSEN = [(0, 30), (30, 60), (60, 1000)]


def eine(a):
    rel, datei = a
    import dsd2csv as d
    meta, veh, status, warn = d.parse(open(os.path.join(WURZEL, rel, datei), "rb").read())
    uhr, ber, teil, spannen = d.analysiere_uhr(veh, status, mit_spannen=True)
    if len(ber) < 3000:
        return None
    ts = sorted(ber, key=lambda f: f[0])
    pos = [(b[0] - a_[0]).total_seconds() for a_, b in zip(ts, ts[1:]) if b[0] > a_[0]]
    if not pos or min(pos) != 5:
        return None
    tau = 5
    z = collections.defaultdict(lambda: [0, 0, 0, 0, []])  # Klasse -> [kurz, kurz gleich, fern, fern gleich, Differenzen kurz]
    for (t1, v1), (t2, v2) in zip(ts, ts[1:]):
        g = (t2 - t1).total_seconds()
        k = next((i for i, (lo, hi) in enumerate(KLASSEN) if lo <= v1 < hi), None)
        if k is None:
            continue
        if tau <= g < tau + 5:
            z[k][0] += 1
            z[k][1] += abs(v2 - v1) <= 2
            z[k][4].append(v2 - v1)
        elif 30 <= g <= 120:
            z[k][2] += 1
            z[k][3] += abs(v2 - v1) <= 2
    # Ueberschuss: schnelle Datensaetze (ab 60 km/h), denen binnen tau + 5 s ein um mindestens 15 km/h langsamerer folgt, gegen solche, denen
    # binnen tau + 5 s ein um mindestens 15 km/h langsamerer vorausging (zeitlich gespiegelt; bei echtem Verkehr etwa gleich haeufig)
    schnell = danach = davor = 0
    for i in range(1, len(ts) - 1):
        t, v = ts[i]
        if v < 60:
            continue
        schnell += 1
        g_n, g_v = (ts[i + 1][0] - t).total_seconds(), (t - ts[i - 1][0]).total_seconds()
        danach += g_n < tau + 5 and ts[i + 1][1] <= v - 15
        davor += g_v < tau + 5 and ts[i - 1][1] <= v - 15
    # Wiedermessung langsamer Objekte? Abstand bei Paaren unter 20 km/h: gleich schnell (|dv| <= 2) gegen verschieden (|dv| >= 6), je Sekunde 5-9
    wieder = {"gleich": [0] * 5, "verschieden": [0] * 5}
    for (t1, v1), (t2, v2) in zip(ts, ts[1:]):
        g = int((t2 - t1).total_seconds())
        if v1 < 20 and v2 < 20 and 5 <= g <= 9:
            if abs(v2 - v1) <= 2:
                wieder["gleich"][g - 5] += 1
            elif abs(v2 - v1) >= 6:
                wieder["verschieden"][g - 5] += 1
    return {"datei": f"{rel}/{datei}", "schnell": [schnell, danach, davor], "wieder": wieder,
            "z": {str(k): [x[0], x[1], x[2], x[3], statistics.median(x[4]) if x[4] else None] for k, x in z.items()}}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--auswertung", default=os.path.join(WURZEL, "_vorschau", "auswertung.json"))
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args()
    aus = json.load(open(a.auswertung, encoding="utf-8"))["standorte"]
    with multiprocessing.Pool(a.jobs) as pool:
        erg = [x for x in pool.map(eine, [(r["standort"], r["datei"]) for r in aus]) if x]
    print("%d Dateien mit 5 s Sperre" % len(erg))
    for k, (lo, hi) in enumerate(KLASSEN):
        s = [e["z"][str(k)] for e in erg if str(k) in e["z"]]
        kurz, kg, fern, fg = (sum(x[i] for x in s) for i in range(4))
        dm = [x[4] for x in s if x[4] is not None]
        print("  erstes Fahrzeug %d-%s km/h: Paare kurz (5-10 s) %d, davon |dv| <= 2 km/h: %.1f %% | Paare fern (30-120 s) %d, davon %.1f %% | "
              "Median dv kurz (Median ueber Dateien) %+.1f km/h" % (lo, hi if hi < 1000 else "", kurz, 100 * kg / max(1, kurz), fern, 100 * fg / max(1, fern),
                                                                    statistics.median(dm) if dm else float("nan")))
    n, na, nv = (sum(e["schnell"][i] for e in erg) for i in range(3))
    print("  Datensaetze ab 60 km/h: %d; binnen 10 s danach ein um >= 15 km/h langsamerer: %d (%.1f %%), davor: %d (%.1f %%); Ueberschuss %.1f %% der schnellen" % (
        n, na, 100 * na / max(1, n), nv, 100 * nv / max(1, n), 100 * (na - nv) / max(1, n)))
    for art in ("gleich", "verschieden"):
        w = [sum(e["wieder"][art][i] for e in erg) for i in range(5)]
        print("  Paare unter 20 km/h, %-11s Abstand 5/6/7/8/9 s: %s  (Anteil bei 5 s: %.0f %%)" % (art, " / ".join(str(x) for x in w), 100 * w[0] / max(1, sum(w))))
    ue = sorted((100 * (e["schnell"][1] - e["schnell"][2]) / e["schnell"][0], e["schnell"][0], e["datei"]) for e in erg if e["schnell"][0] >= 100)
    if ue:
        print("  je Datei (mindestens 100 schnelle): Ueberschuss Median %.1f %%, groesster %.1f %% (%s, %d schnelle)" % (
            statistics.median(x[0] for x in ue), ue[-1][0], ue[-1][2][:50], ue[-1][1]))


if __name__ == "__main__":
    main()
