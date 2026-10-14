# SPDX-License-Identifier: MIT
"""Verdecken Regenphantome Fahrzeuge? Test der Geraetesperre mit dem Regen (docs/totzeit.md, Versuch 1).

Jeder Datensatz sperrt das Geraet fuer tau Sekunden (kleinster Abstand zweier Datensaetze der Datei). Regenphantome kommen unabhaengig
vom Verkehr; der Anteil der Zeit, den sie sperren (Phantome je Stunde mal tau), sagt den Anteil verdeckter Fahrzeuge voraus, ohne Annahme
darueber, wie die Fahrzeuge ankommen. Je Datei und Regenklasse (rauschen.REGEN_KLASSEN):
  Fahrzeuge  = Datensaetze ab der Verkehrsschwelle; erwartet aus den trockenen Stunden derselben Zelle (Tagtyp, Stunde)
  Rueckgang  = 1 - beobachtet / erwartet
  Phantome   = langsame Datensaetze (unter der Verkehrsschwelle) je Regenstunde ueber der trockenen Erwartung
  Sperre     = Phantome je Stunde * tau / 3600
Ueber alle Dateien: Rueckgang = a + b * Sperre (gewichtet nach Regenstunden). a ist der Rueckgang ohne Phantome (Wetter, Verhalten),
b = 1 heisst: jede gesperrte Sekunde kostet so viele Fahrzeuge wie eine Sekunde Verkehr. Bootstrap ueber Dateien fuer den Bereich von b.

Aufruf: python3 -I tools/totzeit_regen.py [--auswertung _vorschau/auswertung.json] [--jobs 8]"""
import argparse
import collections
import datetime as dt
import json
import multiprocessing
import os
import random
import statistics
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)  # python -I nimmt das Skriptverzeichnis nicht auf


def sperre_sekunden(zeiten):
    """Kleinster positiver Abstand zweier aufeinanderfolgender Datensaetze in Sekunden (die Sperre des Geraets)."""
    ts = sorted(zeiten)
    pos = [(b - a).total_seconds() for a, b in zip(ts, ts[1:]) if b > a]
    return min(pos) if pos else None


def eine(a):
    rel, datei = a
    import dsd2csv as d
    import rauschen as r
    korrekturen = os.path.join(WURZEL, "belege", "korrekturen.json")
    kor = (json.load(open(korrekturen, encoding="utf-8")).get("tempolimit", {}) if os.path.exists(korrekturen) else {}).get(f"{rel}/{datei}")
    meta, veh, status, warn = d.parse(open(os.path.join(WURZEL, rel, datei), "rb").read())
    lim, _ = d.tempolimit(meta, None, kor)
    uhr, ber, teil, spannen = d.analysiere_uhr(veh, status, mit_spannen=True)
    if len(ber) < 3000 or not lim:
        return None
    tau = sperre_sekunden([t for t, _ in ber])
    if not tau or not 1 <= tau <= 10:
        return None
    rb = r.pruefen(ber, spannen, lim, regen=d.regenfunktion(ort=d.koordinaten(rel)))
    if not rb or not rb["_modell"].get("klassen"):
        return None
    m = rb["_modell"]
    klassen, vt = m["klassen"], m["est"]["vT"]
    autos, langsam = collections.Counter(), collections.Counter()
    for t, v in ber:
        key = (t.date(), t.hour)
        if key in klassen:
            (autos if v >= vt else langsam)[key] += 1

    def zelle(key):
        return (r.tagtyp(dt.datetime(key[0].year, key[0].month, key[0].day)), key[1])
    basis_a, basis_l = collections.defaultdict(list), collections.defaultdict(list)
    for key, k in klassen.items():
        if k == r.TROCKEN:
            basis_a[zelle(key)].append(autos[key])
            basis_l[zelle(key)].append(langsam[key])
    aus = {"datei": f"{rel}/{datei}", "tau": tau, "regen_belegt": bool((rb.get("regen") or {}).get("belegt")), "klassen": {},
           "erfassung_ab_kmh": d.byte_wert(meta.get("capture_min_speed"))}
    for k in (1, 2, 3):
        oa = ea = ol = el = 0.0
        h = 0
        for key, kk in klassen.items():
            z = zelle(key)
            if kk != k or len(basis_a[z]) < 3:
                continue
            oa += autos[key]
            ea += statistics.mean(basis_a[z])
            ol += langsam[key]
            el += statistics.mean(basis_l[z])
            h += 1
        if h >= 5 and ea > 0:
            phantome = max(0.0, (ol - el) / h)
            aus["klassen"][k] = {"stunden": h, "rueckgang": 1 - oa / ea, "phantome_je_h": phantome, "sperre": phantome * tau / 3600,
                                 "autos_je_h": ea / h}
    return aus


def gewichtete_gerade(punkte):
    """(a, b) der gewichteten Geraden y = a + b x aus [(x, y, w)]."""
    sw = sum(w for _, _, w in punkte)
    mx = sum(w * x for x, _, w in punkte) / sw
    my = sum(w * y for _, y, w in punkte) / sw
    sxx = sum(w * (x - mx) ** 2 for x, _, w in punkte)
    b = sum(w * (x - mx) * (y - my) for x, y, w in punkte) / sxx if sxx else 0.0
    return my - b * mx, b


def auswerten(erg):
    je_datei = [[(k["sperre"], k["rueckgang"], k["stunden"]) for k in e["klassen"].values()] for e in erg if e["klassen"]]
    punkte = [p for liste in je_datei for p in liste]
    print("%d Dateien, %d Paare (Datei, Regenklasse), %d Regenstunden" % (len(je_datei), len(punkte), sum(w for _, _, w in punkte)))
    a, b = gewichtete_gerade(punkte)
    rnd = random.Random(1)
    bs = []
    for _ in range(2000):
        stichprobe = [p for liste in (rnd.choice(je_datei) for _ in je_datei) for p in liste]
        bs.append(gewichtete_gerade(stichprobe)[1])
    bs.sort()
    print("Rueckgang = %.3f + %.2f * Sperre   (b: 95-%%-Bereich %.2f bis %.2f, Bootstrap ueber Dateien)" % (a, b, bs[50], bs[1949]))
    print("\nNach Sperranteil (Phantome je Regenstunde * tau / 3600):")
    for lo, hi in ((0, 0.002), (0.002, 0.01), (0.01, 0.03), (0.03, 0.1), (0.1, 1)):
        p = [x for x in punkte if lo <= x[0] < hi]
        if p:
            w = sum(x[2] for x in p)
            print("  %5.1f-%5.1f %%: %3d Paare, %5d Stunden, Sperre im Mittel %5.2f %%, Rueckgang im Mittel %5.1f %%" % (
                100 * lo, 100 * hi, len(p), w, 100 * sum(x[0] * x[2] for x in p) / w, 100 * sum(x[1] * x[2] for x in p) / w))
    print("\nSteigung b nach Geraeteeinstellung (ungespeicherte Echos unter der Erfassungsgrenze koennten mitsperren):")
    for name, filt in (("Erfassung ab bis 5 km/h", lambda e: (e["erfassung_ab_kmh"] or 0) <= 5),
                       ("Erfassung ab 6 bis 9 km/h", lambda e: 6 <= (e["erfassung_ab_kmh"] or 0) <= 9),
                       ("Erfassung ab 10 km/h und mehr", lambda e: (e["erfassung_ab_kmh"] or 0) >= 10),
                       ("Sperre 1 bis 2 s", lambda e: e["tau"] <= 2), ("Sperre 5 s", lambda e: e["tau"] == 5), ("Sperre 8 s", lambda e: e["tau"] == 8)):
        teil = [[(k["sperre"], k["rueckgang"], k["stunden"]) for k in e["klassen"].values()] for e in erg if e["klassen"] and filt(e)]
        p = [x for liste in teil for x in liste]
        if len(teil) >= 5 and len({round(x[0], 4) for x in p}) > 2:
            a_, b_ = gewichtete_gerade(p)
            rnd = random.Random(2)
            bs = sorted(gewichtete_gerade([x for liste in (rnd.choice(teil) for _ in teil) for x in liste])[1] for _ in range(1000))
            print("  %-30s %3d Dateien: Rueckgang = %.3f + %.2f * Sperre (b %.2f bis %.2f)" % (name, len(teil), a_, b_, bs[25], bs[974]))
        else:
            print("  %-30s %3d Dateien: zu wenige" % (name, len(teil)))
    print("\nNach Regenklasse (alle Dateien):")
    for k in ("1", "2", "3"):
        p = [(e["klassen"][k]["sperre"], e["klassen"][k]["rueckgang"], e["klassen"][k]["stunden"]) for e in erg if k in e["klassen"]]
        if p:
            w = sum(x[2] for x in p)
            print("  Klasse %s: %3d Dateien, Sperre %5.2f %%, Rueckgang %5.1f %%" % (k, len(p), 100 * sum(x[0] * x[2] for x in p) / w,
                                                                            100 * sum(x[1] * x[2] for x in p) / w))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--auswertung", default=os.path.join(WURZEL, "_vorschau", "auswertung.json"))
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args()
    aus = json.load(open(a.auswertung, encoding="utf-8"))["standorte"]
    with multiprocessing.Pool(a.jobs) as pool:
        erg = [x for x in pool.map(eine, [(r["standort"], r["datei"]) for r in aus]) if x]
    # JSON-Schluessel sind Zeichenketten: einheitlich machen
    erg = json.loads(json.dumps(erg))
    auswerten(erg)


if __name__ == "__main__":
    main()
