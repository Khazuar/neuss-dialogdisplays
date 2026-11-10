# SPDX-License-Identifier: MIT
"""Rauschboden und Regenanteil je Abschnitt gegen je Datei (docs/einsaetze.md): Wie stark aendern sich V85 und Einhaltung der Messungen?

Fuer jede Messung mit mehr als einem Abschnitt: einmal ein Abzug fuer die ganze Datei (frueheres Verfahren), einmal je Abschnitt (jetzt), beides
aus dem Rohaggregat (Stunden x km/h vor jedem Abzug; Zeiten mit Stundenaufloesung). Aufruf: python3 -I tools/abzug_je_abschnitt.py"""
import collections
import datetime as dt
import json
import os
import statistics
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)
import dsd2csv  # noqa: E402
import einsaetze as E  # noqa: E402

ISO_UTC = "%Y-%m-%dT%H:00Z"
STUNDE = dt.timedelta(hours=1)


def stunden_lesen(agg):
    """(Fahrzeuge [(Ortszeit Mitte der Stunde, v)] je Datum, vollstaendig aufgezeichnete Stunden [(Datum, Stunde)]) aus dem Rohaggregat."""
    fz, utc = collections.defaultdict(list), []
    for d, h, off, _nr, _voll, _klasse, flach in agg.get("roh", agg.get("stunden")) or []:
        datum = dt.date.fromisoformat(d)
        t = dt.datetime(datum.year, datum.month, datum.day, h, 30)
        for v, n in zip(flach[0::2], flach[1::2]):
            fz[datum] += [(t, v)] * n
        utc.append(dt.datetime(datum.year, datum.month, datum.day, h) - dt.timedelta(hours=off))
    if not utc:
        return fz, []
    luecke = set()
    for a, _b, n in agg.get("luecken") or []:
        t = dt.datetime.strptime(a, ISO_UTC)
        luecke |= {t + i * STUNDE for i in range(n)}
    voll, h = [], min(utc)
    while h <= max(utc):
        if h not in luecke:
            lokal = h + dt.timedelta(hours=dsd2csv.utc_versatz_h(h))
            voll.append((lokal.date(), lokal.hour))
        h += STUNDE
    return fz, voll


def abzug(vehs, stunden, lim, regen):
    rb = dsd2csv.rauschen.pruefen(vehs, E._spannen(stunden), lim, regen=regen) if vehs else None
    return dsd2csv.rauschen.ohne_rauschen(vehs, rb["_modell"]) if rb and rb["abzug"] else vehs


def main():
    vorschau = sys.argv[1] if len(sys.argv) > 1 else os.path.join(WURZEL, "_vorschau")
    with open(os.path.join(vorschau, "auswertung.json"), encoding="utf-8") as fh:
        auswertung = json.load(fh)
    with open(os.path.join(WURZEL, "belege", "metadaten.json"), encoding="utf-8") as fh:
        metadaten = json.load(fh)
    zeilen = []
    for m in E.messungen_lesen(auswertung, metadaten):
        grenzen = sorted(d for _nr, d, _p in m["brueche"])
        pfad = os.path.join(vorschau + "-aggregat", m["rel"].replace("/", os.sep), os.path.splitext(m["datei"])[0] + ".aggregat.json")
        if not grenzen or not m["limit"] or not os.path.exists(pfad):
            continue
        with open(pfad, encoding="utf-8") as fh:
            fz, voll = stunden_lesen(json.load(fh))
        if not fz:
            continue
        regen = dsd2csv.regenfunktion(ort=m["ort"])
        ganz = abzug([f for d in sorted(fz) for f in fz[d]], voll, m["limit"], regen)
        je = []
        for von, bis in zip([dt.date.min] + grenzen, [g - dt.timedelta(days=1) for g in grenzen] + [dt.date.max]):
            je += abzug([f for d in sorted(fz) if von <= d <= bis for f in fz[d]], [x for x in voll if von <= x[0] <= bis], m["limit"], regen)
        a, b = dsd2csv.stats(ganz, m["limit"]), dsd2csv.stats(je, m["limit"])
        zeilen.append((m["id"], b["geschwindigkeit_kmh"]["v85"] - a["geschwindigkeit_kmh"]["v85"],
                       b["einhaltung"]["einhaltungsquote_prozent"] - a["einhaltung"]["einhaltungsquote_prozent"], len(je) - len(ganz)))
    print("%d Messungen mit mehreren Abschnitten" % len(zeilen))
    print("V85 je Abschnitt minus je Datei: verschieden in %d, Werte %s" % (sum(1 for z in zeilen if z[1]), sorted(z[1] for z in zeilen if z[1])))
    print("Einhaltung (Prozentpunkte): Median %+.2f, groesster Betrag %.2f" % (statistics.median(z[2] for z in zeilen), max(abs(z[2]) for z in zeilen)))
    print("Fahrzeuge nach Abzug: Median %+d, Spanne %+d bis %+d" % (statistics.median(z[3] for z in zeilen), min(z[3] for z in zeilen), max(z[3] for z in zeilen)))
    for z in sorted(zeilen, key=lambda z: -abs(z[2]))[:5]:
        print("  %-55s V85 %+d, Einhaltung %+.2f Pp., Fahrzeuge %+d" % (z[0][:55], z[1], z[2], z[3]))


if __name__ == "__main__":
    main()
