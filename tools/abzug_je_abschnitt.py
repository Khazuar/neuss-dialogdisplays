# SPDX-License-Identifier: MIT
"""Rauschboden und Regenanteil je Abschnitt gegen je Datei (docs/einsaetze.md): Wie stark aendern sich V85 und Einhaltung der Messungen?

Fuer jede Messung mit mehr als einem Abschnitt: einmal ein Abzug fuer die ganze Datei (frueheres Verfahren), einmal je Abschnitt (jetzt), beides
aus dem Rohaggregat (Stunden x km/h vor jedem Abzug; Zeiten mit Stundenaufloesung). Aufruf: python3 -I tools/abzug_je_abschnitt.py"""
import json
import os
import statistics
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)
import dsd2csv  # noqa: E402
import einsaetze as E  # noqa: E402


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
    for m in E.messungen_lesen(auswertung, metadaten, vorschau + "-aggregat"):
        abschnitte = E.abschnitte_der_messung(m)
        if len(abschnitte) < 2 or not m["limit"] or not m["zeilen"]:
            continue
        regen = dsd2csv.regenfunktion(ort=m["ort"])
        ganz = abzug(E._fahrzeuge_aus(m["zeilen"]), m["voll"], m["limit"], regen)
        je = []
        for nr, von, bis in abschnitte:
            je += abzug(E._fahrzeuge_aus([z for z in m["zeilen"] if von <= z[0] <= bis]), [x for x in m["voll"] if von <= x[0] <= bis], m["limit"], regen)
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
