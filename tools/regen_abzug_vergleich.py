# SPDX-License-Identifier: MIT
"""Vergleich dreier Wege, den Regenanteil des Rauschbodens auf Stunden zu verteilen (docs/rauschen.md, Abschnitt "Verteilung auf Stunden").

  A  ganze Datei: wie ohne_rauschen() auf allen Fahrten (Kennzahlen, Abschnitte, Auswahl auf den Seiten, Aggregat)
  B  je Zeitraum: ohne_rauschen() je Tageszeit-Liste getrennt (feste Zeitraumtabelle der Seiten und YAML)
  C  je Regenstunde: jede Regenstunde zieht die c_k(v) Datensaetze je Regenstunde des Modells ab (Rest bis REGEN_UEBERTRAG wandert zur
     naechsten Regenstunde)

Pruefung: Nach dem Abzug sollten die langsamen Fahrten (v < Verkehrsschwelle) je Stunde dem Erwartungswert des Modells folgen (b(v) mal
Verkehr, plus a(v), wo der trockene Rauschboden nicht abgezogen ist), in Regenstunden so gut wie in trockenen. Gemessen werden die mittlere
Abweichung und der Quotient der Streuung (Regenstunden zu trockenen Stunden). Nur Dateien mit belegtem Regenanteil.

Aufruf: python3 -I tools/regen_abzug_vergleich.py [--auswertung _vorschau/auswertung.json] [--jobs 8]"""
import argparse
import collections
import json
import math
import multiprocessing
import os
import statistics
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)  # python -I nimmt das Skriptverzeichnis nicht auf

REGEN_UEBERTRAG = 2.0  # so viele Datensaetze bleiben hoechstens als Rest eines nicht abziehbaren Regenanteils stehen


def ohne_rauschen_stundenweise(fahrten, modell):
    """Weg C (siehe Modulkopf); der trockene Rauschboden ist derselbe Abzug wie in rauschen.ohne_rauschen."""
    import collections as co
    import rauschen as r
    p = r.anteile_zelle(modell)
    klassen = modell.get("klassen")
    gruppen = co.defaultdict(list)
    for f in fahrten:
        k = r.TROCKEN if klassen is None else klassen.get((f[0].date(), f[0].hour), r.UNKLAR)
        gruppen[(r.tagtyp(f[0]), f[0].hour, k, f[1])].append(f)
    weg = r._duenne(gruppen, {k: p[k] * len(g) for k, g in gruppen.items() if k in p})
    c = modell.get("regen")
    if c and klassen is not None:
        je_stunde = co.defaultdict(lambda: co.defaultdict(list))
        for f in fahrten:
            key = (f[0].date(), f[0].hour)
            if id(f) not in weg and klassen.get(key, r.UNKLAR) in c and f[1] in c[klassen[key]]:
                je_stunde[key][f[1]].append(f)
        rest = co.defaultdict(float)
        for key in sorted(klassen):
            ck = c.get(klassen[key])
            if not ck:
                continue
            for v in sorted(ck):
                rr = min(rest[(klassen[key], v)] + ck[v], REGEN_UEBERTRAG + ck[v])
                liste = je_stunde[key][v] if key in je_stunde else []
                n = min(int(rr), len(liste))
                rest[(klassen[key], v)] = rr - n
                for i in range(n):
                    weg.add(id(liste[int((i + 0.5) * len(liste) / n)]))
    return [f for f in fahrten if id(f) not in weg]


def eine(a):
    rel, datei = a
    import dsd2csv as d
    import gruppen
    import rauschen
    korrekturen = os.path.join(WURZEL, "belege", "korrekturen.json")
    kor = (json.load(open(korrekturen, encoding="utf-8")).get("tempolimit", {}) if os.path.exists(korrekturen) else {}).get(f"{rel}/{datei}")
    meta, veh, status, warn = d.parse(open(os.path.join(WURZEL, rel, datei), "rb").read())
    lim, _ = d.tempolimit(meta, None, kor)
    uhr, ber, teil, spannen = d.analysiere_uhr(veh, status, mit_spannen=True)
    rb = rauschen.pruefen(ber, spannen, lim, regen=d.regenfunktion(ort=d.koordinaten(rel)))
    if not rb or not (rb.get("regen") or {}).get("belegt"):
        return None
    m = rb["_modell"]
    c, D, klassen, est = m["regen"], m["D"], m["klassen"], m["est"]
    vt = est["vT"]
    modell_abzug = sum(sum(ck.values()) * sum(D[key] for key in D if key[2] == k) for k, ck in c.items())
    wege = {"A": rauschen.ohne_rauschen(ber, m), "C": ohne_rauschen_stundenweise(ber, m)}
    wege["B"] = [f for name in d.TEILZEITRAEUME if name != "schulweg" for f in rauschen.ohne_rauschen(teil[name], m)]
    aus = {"datei": f"{rel}/{datei}", "n": len(ber), "modell_regen_abzug": round(modell_abzug)}
    zeit = {n: set(gruppen.stunden(v, b)) for n, v, b in gruppen.ZEITSCHEIBEN}
    for name, liste in wege.items():
        je_zr = {n: [f for f in liste if f[0].hour in h] for n, h in zeit.items()}
        aus[name] = {"abgezogen": len(ber) - len(liste), "stats": d.stats(liste, lim), "zeitraum": {n: len(x) for n, x in je_zr.items()},
                     "v85_zeitraum": {n: (d.pct(sorted(v for _, v in x), 85) if x else None) for n, x in je_zr.items()}}
        je_h = collections.defaultdict(list)
        for f in liste:
            je_h[(f[0].date(), f[0].hour)].append(f[1])
        a_bleibt = {} if m.get("a_abziehen", True) else est["a"]
        res = {"regen": [], "trocken": []}
        for key, k in klassen.items():
            vs = je_h.get(key, [])
            T = sum(1 for v in vs if v >= vt)
            erw = sum(a_bleibt.get(v, 0.0) + est["ab"].get(v, (0.0, 0.0))[1] * T for v in range(int(vt)))
            if k in (1, 2, 3):
                res["regen"].append(sum(1 for v in vs if v < vt) - erw)
            elif k == 0:
                res["trocken"].append(sum(1 for v in vs if v < vt) - erw)
        aus[name]["resid"] = {g: [len(x), sum(x) / len(x) if x else None, math.sqrt(sum(y * y for y in x) / len(x)) if x else None] for g, x in res.items()}
    return aus


def med(xs):
    return statistics.median(xs)


def auswerten(erg):
    print(len(erg), "Dateien mit belegtem Regenanteil\n")
    print("Abgezogene Fahrzeuge gegen die Rechnung des Modells (Regenstunden mal c), Median:")
    for name in "ABC":
        print("  %s: %.2f" % (name, med([e[name]["abgezogen"] / max(1, e["modell_regen_abzug"]) for e in erg])))
    gut = [e for e in erg if e["A"]["resid"]["regen"][0] >= 20]
    print("\nLangsame Fahrten je Stunde gegen den Erwartungswert des Modells (%d Dateien mit mindestens 20 Regenstunden), Median:" % len(gut))
    for name in "ABC":
        bias = med([e[name]["resid"]["regen"][1] for e in gut])
        quot = med([e[name]["resid"]["regen"][2] / e[name]["resid"]["trocken"][2] for e in gut if e[name]["resid"]["trocken"][2]])
        print("  %s: mittlere Abweichung in Regenstunden %+.3f je Stunde, Streuung Regen/trocken %.2f" % (name, bias, quot))
    print("  Streuung in Regenstunden kleiner als bei A: C in %d, B in %d von %d Dateien" % (
        sum(1 for e in gut if e["C"]["resid"]["regen"][2] < e["A"]["resid"]["regen"][2]),
        sum(1 for e in gut if e["B"]["resid"]["regen"][2] < e["A"]["resid"]["regen"][2]), len(gut)))
    print("\nZeitraeume, Fahrzeugzahl von B gegen A (Median |Unterschied|, groesster, V85 verschieden in n Dateien):")
    for zr in ("nacht", "vormittag", "nachmittag", "abend"):
        d_ = [100 * (e["B"]["zeitraum"][zr] - e["A"]["zeitraum"][zr]) / max(1, e["A"]["zeitraum"][zr]) for e in erg]
        v = [(e["B"]["v85_zeitraum"][zr] or 0) - (e["A"]["v85_zeitraum"][zr] or 0) for e in erg]
        print("  %-10s %.2f %%, %.1f %%, V85 in %d von %d (bis %d km/h)" % (zr, med([abs(x) for x in d_]), max(abs(x) for x in d_),
                                                                          sum(1 for x in v if x), len(v), max(abs(x) for x in v)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--auswertung", default=os.path.join(WURZEL, "_vorschau", "auswertung.json"), help="auswertung.json von dsd2csv.py")
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args()
    aus = json.load(open(a.auswertung, encoding="utf-8"))["standorte"]
    auftraege = [(r["standort"], r["datei"]) for r in aus if ((r.get("rauschen") or {}).get("regen") or {}).get("abgezogen_fahrzeuge")]
    with multiprocessing.Pool(a.jobs) as pool:
        erg = [x for x in pool.map(eine, auftraege) if x]
    auswerten(erg)


if __name__ == "__main__":
    main()
