# SPDX-License-Identifier: MIT
"""Anteils- gegen Ratenkennzahlen je Messung: Wie stark verschiebt sich die Rangfolge, wenn schnelle Fahrzeuge nicht mehr durch langsame ausgeglichen werden?

Liest die bereinigten Stundendaten (daten_bauen.py, DATEN.md), nur vollstaendig aufgezeichnete Stunden. Stunden ohne Fahrzeuge zaehlen mit (DATEN.md:
im Messzeitraum, weder in den Stundendateien noch in luecken.csv). Je Messung (alle Abschnitte zusammen):
  alt:  Einhaltungsquote (Anteil <= Limit), V85, Risikoindex nach Nilsson (Mittel von (v/Limit)^4), Mittelungspegel gegenueber Limit
  neu:  Ueberschreitungen je Tag (v > Limit + Toleranz wie dsd2csv.toleranz), Zusatzrisiko je Stunde (Summe max(0, (v/Limit)^4 - 1) / Stunden),
        Zusatzpegel durch Ueberschreitungen (10 lg(E / E_gekappt), schnelle Fahrzeuge auf das Limit gekappt)
Ausgabe: Rangkorrelation (Spearman) alt gegen neu und die groessten Rangspruenge.
Aufruf: python3 -I tools/absolut_vergleich.py [_vorschau/daten]"""
import collections
import csv
import datetime as dt
import gzip
import math
import os
import statistics
import sys

WURZEL = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(WURZEL))
import dsd2csv  # noqa: E402


def utc_stunde(datum, stunde, versatz):
    d = dt.datetime.strptime(datum, "%Y-%m-%d") + dt.timedelta(hours=int(stunde) - int(versatz))
    return d


def pegel(v):
    return dsd2csv.pegel_pkw_db(v)


def raenge(werte):
    """Rang 1 = groesster Wert; gleiche Werte teilen sich den mittleren Rang."""
    ordnung = sorted(range(len(werte)), key=lambda i: -werte[i])
    r, i = [0.0] * len(werte), 0
    while i < len(ordnung):
        j = i
        while j + 1 < len(ordnung) and werte[ordnung[j + 1]] == werte[ordnung[i]]:
            j += 1
        for k in range(i, j + 1):
            r[ordnung[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(a, b):
    ra, rb = raenge(a), raenge(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    return sum((x - ma) * (y - mb) for x, y in zip(ra, rb)) / math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))


def main():
    ordner = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(WURZEL), "_vorschau", "daten")
    with open(os.path.join(ordner, "messungen.csv"), encoding="utf-8", newline="") as fh:
        info = {m["messung_id"]: m for m in csv.DictReader(fh) if m["tempolimit_kmh"]}
    luecken = collections.Counter()
    with open(os.path.join(ordner, "luecken.csv"), encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            luecken[r["messung_id"]] += int(r["stunden"])
    hist = collections.defaultdict(collections.Counter)
    alle_h = collections.defaultdict(lambda: [None, None])
    angebrochen = collections.defaultdict(set)
    with gzip.open(os.path.join(ordner, "stunden.csv.gz"), "rt", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            mid = r["messung_id"]
            if mid not in info:
                continue
            u = utc_stunde(r["datum"], r["stunde"], r["utc_versatz_h"])
            lo_hi = alle_h[mid]
            lo_hi[0] = u if lo_hi[0] is None or u < lo_hi[0] else lo_hi[0]
            lo_hi[1] = u if lo_hi[1] is None or u > lo_hi[1] else lo_hi[1]
            if r["voll"] == "1":
                hist[mid][int(r["kmh"])] += int(r["anzahl"])
            else:
                angebrochen[mid].add(u)
    zeilen = []
    for mid, h in hist.items():
        lim = int(info[mid]["tempolimit_kmh"])
        lo, hi = alle_h[mid]
        stunden = int((hi - lo).total_seconds() / 3600) + 1 - luecken[mid] - len(angebrochen[mid])
        n = sum(h.values())
        if stunden < 24 * 14 or n < 2000:
            continue
        schwelle = [v for v in h if v - dsd2csv.toleranz(v) > lim]
        ueber = sum(h[v] for v in schwelle)
        e = sum(c * 10 ** ((pegel(v) - pegel(lim)) / 10) for v, c in h.items())
        e_gekappt = sum(c * 10 ** ((pegel(min(v, lim)) - pegel(lim)) / 10) for v, c in h.items())
        k = sorted(h)
        kum, v85 = 0, k[-1]
        for v in k:
            kum += h[v]
            if kum >= 0.85 * n:
                v85 = v
                break
        zeilen.append({
            "id": mid, "n": n, "stunden": stunden, "limit": lim,
            "einhaltung": 100 * sum(c for v, c in h.items() if v <= lim) / n, "v85": v85 - lim,
            "risiko": sum(c * (v / lim) ** 4 for v, c in h.items() if v > 0) / n,
            "pegel": 10 * math.log10(e / n),
            "ueber_tag": ueber / (stunden / 24),
            "zusatzrisiko_h": sum(c * max(0.0, (v / lim) ** 4 - 1) for v, c in h.items()) / stunden,
            "zusatzpegel": 10 * math.log10(e / e_gekappt),
        })
    print("%d Messungen (mindestens 14 Tage und 2.000 Fahrzeuge in vollstaendig aufgezeichneten Stunden)" % len(zeilen))
    alt = {"schlechte Einhaltung": [-z["einhaltung"] for z in zeilen], "V85 ueber Limit": [z["v85"] for z in zeilen],
           "Risikoindex": [z["risiko"] for z in zeilen]}
    neu = {"Ueberschreitungen je Tag": [z["ueber_tag"] for z in zeilen], "Zusatzrisiko je Stunde": [z["zusatzrisiko_h"] for z in zeilen],
           "Zusatzpegel": [z["zusatzpegel"] for z in zeilen]}
    print("Rangkorrelation (Spearman):")
    for a, wa in alt.items():
        print("  %-22s " % a + "  ".join("%s %.2f" % (b, spearman(wa, wb)) for b, wb in neu.items()))
    print("  Zusatzrisiko je Stunde gegen Ueberschreitungen je Tag: %.2f" % spearman(neu["Zusatzrisiko je Stunde"], neu["Ueberschreitungen je Tag"]))
    print("  Mittelungspegel (alt) gegen Zusatzpegel: %.2f" % spearman([z["pegel"] for z in zeilen], neu["Zusatzpegel"]))
    ra, rb = raenge(alt["V85 ueber Limit"]), raenge(neu["Zusatzrisiko je Stunde"])
    print("Groesste Rangspruenge V85 ueber Limit -> Zusatzrisiko je Stunde (von %d):" % len(zeilen))
    for i in sorted(range(len(zeilen)), key=lambda i: -abs(ra[i] - rb[i]))[:8]:
        z = zeilen[i]
        print("  %-52s V85 %+d (Rang %3d) -> Rang %3d | Einhaltung %5.1f %%, %5.0f Fz/Tag, %4.0f Ueberschr./Tag, Limit %d" % (
            z["id"][:52], z["v85"], ra[i], rb[i], z["einhaltung"], z["n"] / (z["stunden"] / 24), z["ueber_tag"], z["limit"]))
    print("Verteilung: Ueberschreitungen je Tag Median %.0f (min %.1f, max %.0f); Zusatzpegel Median %.2f dB (max %.2f)" % (
        statistics.median(neu["Ueberschreitungen je Tag"]), min(neu["Ueberschreitungen je Tag"]), max(neu["Ueberschreitungen je Tag"]),
        statistics.median(neu["Zusatzpegel"]), max(neu["Zusatzpegel"])))


if __name__ == "__main__":
    main()
