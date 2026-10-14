# SPDX-License-Identifier: MIT
"""Geraetesperre: Eichung an Geraeten mit kurzer Sperre, Verzerrung von Tempo und Einhaltung, Sperre nach Geschwindigkeit (docs/totzeit.md).

Versuch 2 (Eichung): Geraete mit 1 bis 2 s Sperre sehen Fahrzeuge, die ein Geraet mit 5 (oder 8) s Sperre verpasst. Auf ihre Datensaetze wird
  eine feste Sperre von 5 (8) s nach jedem behaltenen Datensatz gelegt. Anteil verpasster Fahrzeuge je Stunde, nach Verkehrsdichte (behaltene
  Datensaetze je Stunde), gegen die Poisson-Erwartung (verpasst = Datensaetze je Stunde * Sperre / 3600).
Versuch 3 (Tempo der Verpassten): Mittel der verpassten gegen die behaltenen Fahrzeuge derselben Stunde; V85, Mittel und Einhaltung mit und
  ohne die simulierte Sperre.
Versuch 4 (Sperre nach Geschwindigkeit): Bleibt das Geraet nach einem langsamen Ziel laenger gesperrt? Je Datensatz: Abstand zum naechsten
  (nach dem Datensatz, also unter seiner Sperre) gegen Abstand zum vorigen (unter der Sperre des Vorgaengers, gleiche Verkehrslage).
  R(v) = Anteil kurzer Abstaende danach / davor, kurz = unter tau + 5 s. R faellt mit der Geschwindigkeit nicht, wenn die Sperre fest ist.
Versuch 5 (Hochrechnung): Die Eichung aus Versuch 2 auf die Geraete mit 5 s Sperre angewandt: Faktor je Datei.

Aufruf: python3 -I tools/totzeit_eichung.py [--auswertung _vorschau/auswertung.json] [--jobs 8]"""
import argparse
import bisect
import collections
import json
import multiprocessing
import os
import statistics
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)  # python -I nimmt das Skriptverzeichnis nicht auf

DICHTE = [0, 25, 50, 100, 150, 200, 300, 10 ** 9]  # Klassen der Datensaetze je Stunde (wie sie das Geraet mit langer Sperre saehe)
TEMPO = [0, 10, 20, 30, 40, 60, 1000]  # Klassen der Geschwindigkeit fuer Versuch 4


def simuliere(ts, sperre):
    """Indizes der Datensaetze, die ein Geraet mit fester Sperre 'sperre' (s) nach jedem behaltenen Datensatz behielte."""
    behalten, frei_ab = [], None
    for i, (t, _) in enumerate(ts):
        if frei_ab is None or (t - frei_ab).total_seconds() >= sperre:
            behalten.append(i)
            frei_ab = t
    return behalten


def eine(a):
    rel, datei = a
    import dsd2csv as d
    korrekturen = os.path.join(WURZEL, "belege", "korrekturen.json")
    kor = (json.load(open(korrekturen, encoding="utf-8")).get("tempolimit", {}) if os.path.exists(korrekturen) else {}).get(f"{rel}/{datei}")
    meta, veh, status, warn = d.parse(open(os.path.join(WURZEL, rel, datei), "rb").read())
    lim, _ = d.tempolimit(meta, None, kor)
    uhr, ber, teil, spannen = d.analysiere_uhr(veh, status, mit_spannen=True)
    if len(ber) < 3000:
        return None
    ts = sorted(ber, key=lambda f: f[0])
    gaps = [(b[0] - a_[0]).total_seconds() for a_, b in zip(ts, ts[1:])]
    pos = [g for g in gaps if g > 0]
    if not pos:
        return None
    tau = min(pos)
    aus = {"datei": f"{rel}/{datei}", "tau": tau, "limit": lim, "n": len(ts)}
    # Versuch 4: kurze Abstaende danach / davor nach Geschwindigkeit
    kurz = tau + 5
    v4 = collections.defaultdict(lambda: [0, 0, 0])  # Klasse -> [Datensaetze, kurz danach, kurz davor]
    for i in range(1, len(ts) - 1):
        nach, vor = gaps[i], gaps[i - 1]
        if nach > 600 or vor > 600:
            continue
        k = bisect.bisect_right(TEMPO, ts[i][1]) - 1
        v4[k][0] += 1
        v4[k][1] += nach < kurz
        v4[k][2] += vor < kurz
    aus["v4"] = {str(k): x for k, x in v4.items()}
    # Hochrechnung braucht die Datensaetze je Stunde aller Geraete
    je_h = collections.Counter((t.date(), t.hour) for t, _ in ts)
    aus["stunden"] = list(je_h.values())
    if tau <= 2:
        for sperre in (5, 8):
            b = simuliere(ts, sperre)
            bset = set(b)
            alle_h, beh_h = collections.Counter(), collections.Counter()
            for i, (t, _) in enumerate(ts):
                alle_h[(t.date(), t.hour)] += 1
                if i in bset:
                    beh_h[(t.date(), t.hour)] += 1
            klassen = collections.defaultdict(lambda: [0, 0, 0.0])  # Dichteklasse -> [alle, behalten, Summe m*Stunden]
            for key, n_alle in alle_h.items():
                m = beh_h[key]
                k = bisect.bisect_right(DICHTE, m) - 1
                klassen[k][0] += n_alle
                klassen[k][1] += m
                klassen[k][2] += m * m * sperre / 3600  # fuer die Poisson-Erwartung, gewichtet mit m
            aus["eichung_%d" % sperre] = {str(k): x for k, x in klassen.items()}
            # Versuch 3: Tempo der verpassten gegen die behaltenen derselben Stunde, Kennzahlen mit und ohne Sperre
            v_beh = [ts[i][1] for i in b]
            alle_v = [v for _, v in ts]
            s_alle, s_beh = d.stats(ts, lim), d.stats([ts[i] for i in b], lim)
            diff, gew = 0.0, 0
            je_stunde = collections.defaultdict(lambda: [[], []])
            for i, (t, v) in enumerate(ts):
                je_stunde[(t.date(), t.hour)][0 if i in bset else 1].append(v)
            for beh, verp in je_stunde.values():
                if beh and verp:
                    diff += (statistics.mean(verp) - statistics.mean(beh)) * len(verp)
                    gew += len(verp)
            aus["tempo_%d" % sperre] = {
                "verpasst": len(alle_v) - len(v_beh), "verpasst_minus_behalten_kmh": diff / gew if gew else None,
                "v85": [s_alle["geschwindigkeit_kmh"]["v85"], s_beh["geschwindigkeit_kmh"]["v85"]],
                "mittel": [s_alle["geschwindigkeit_kmh"]["mittel"], s_beh["geschwindigkeit_kmh"]["mittel"]],
                "einhaltung": [(s_alle.get("einhaltung") or {}).get("einhaltungsquote_prozent"), (s_beh.get("einhaltung") or {}).get("einhaltungsquote_prozent")]}
    return aus


def auswerten(erg):
    kurz_tau = [e for e in erg if e["tau"] <= 2]
    print("Versuch 2/3: %d Dateien mit Sperre bis 2 s: %s" % (len(kurz_tau), ", ".join(e["datei"].split("/")[0] for e in kurz_tau)))
    kurven = {}
    for sperre in (5, 8):
        ges = collections.defaultdict(lambda: [0, 0, 0.0])
        for e in kurz_tau:
            for k, x in e.get("eichung_%d" % sperre, {}).items():
                for j in range(3):
                    ges[int(k)][j] += x[j]
        print("\nSimulierte Sperre %d s: verpasste Fahrzeuge nach Verkehrsdichte (Datensaetze je Stunde, wie das Geraet sie saehe)" % sperre)
        kurve = {}
        for k in sorted(ges):
            alle, beh, mm = ges[k]
            if not alle:
                continue
            verpasst = (alle - beh) / alle
            poisson = mm / beh / (1 + mm / beh) if beh else 0.0  # Anteil der verpassten an allen bei Poisson: m*tau / (1 + ...)? siehe unten
            # Poisson, nicht verlaengerbare Sperre: beobachtet m = n / (1 + n tau) -> verpasst/alle = n tau / (1 + n tau) = m tau
            poisson = mm / beh if beh else 0.0
            kurve[k] = verpasst
            print("  %4d-%-5s: %8d Fahrzeuge, verpasst %5.1f %%, Poisson %5.1f %%" % (DICHTE[k], str(DICHTE[k + 1]) if DICHTE[k + 1] < 10 ** 8 else "", alle,
                                                                               100 * verpasst, 100 * poisson))
        kurven[sperre] = kurve
        t = [e["tempo_%d" % sperre] for e in kurz_tau if "tempo_%d" % sperre in e]
        if t:
            dv85 = [x["v85"][1] - x["v85"][0] for x in t]
            dm = [x["mittel"][1] - x["mittel"][0] for x in t]
            de = [x["einhaltung"][1] - x["einhaltung"][0] for x in t if x["einhaltung"][0] is not None]
            vm = [x["verpasst_minus_behalten_kmh"] for x in t if x["verpasst_minus_behalten_kmh"] is not None]
            print("  Tempo: verpasste minus behaltene derselben Stunde: Median %+.2f km/h (min %+.2f, max %+.2f)" % (statistics.median(vm), min(vm), max(vm)))
            print("  mit Sperre minus ohne: V85 %s km/h, Mittel Median %+.2f km/h, Einhaltung Median %+.2f Prozentpunkte (max |%.2f|)" % (
                dict(collections.Counter(dv85)), statistics.median(dm), statistics.median(de), max(abs(x) for x in de)))
    print("\nVersuch 4: Sperre nach Geschwindigkeit des Datensatzes, R = Anteil kurzer Abstaende danach / davor (Median ueber Dateien)")
    for gruppe, filt in (("Sperre 5 s", lambda e: e["tau"] == 5), ("Sperre 1-2 s", lambda e: e["tau"] <= 2)):
        zeile = []
        for k in range(len(TEMPO) - 1):
            rs = [x[1] / x[2] for e in erg if filt(e) for kk, x in e["v4"].items() if int(kk) == k and x[0] >= 200 and x[2]]
            zeile.append("%d-%d: %s" % (TEMPO[k], TEMPO[k + 1], "%.2f (%d)" % (statistics.median(rs), len(rs)) if rs else "-"))
        print("  %-12s %s" % (gruppe, " | ".join(zeile)))
    print("\nVersuch 5: Hochrechnung fuer Geraete mit 5 s Sperre (Eichkurve aus Versuch 2 gegen Poisson)")
    kurve = kurven.get(5) or {}
    f_eich, f_poi = [], []
    for e in erg:
        if e["tau"] != 5:
            continue
        m = e["stunden"]
        geschaetzt = sum(x / (1 - kurve.get(bisect.bisect_right(DICHTE, x) - 1, 0.0)) for x in m)
        f_eich.append(geschaetzt / sum(m))
        f_poi.append(sum(x / max(0.05, 1 - x * 5 / 3600) for x in m) / sum(m))
    if f_eich:
        f_eich.sort()
        f_poi.sort()
        print("  %d Dateien: Faktor nach Eichung Median %.3f (90 %% %.3f, max %.3f); nach Poisson Median %.3f (max %.3f)" % (
            len(f_eich), statistics.median(f_eich), f_eich[int(0.9 * len(f_eich))], f_eich[-1], statistics.median(f_poi), f_poi[-1]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--auswertung", default=os.path.join(WURZEL, "_vorschau", "auswertung.json"))
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args()
    aus = json.load(open(a.auswertung, encoding="utf-8"))["standorte"]
    with multiprocessing.Pool(a.jobs) as pool:
        erg = [x for x in pool.map(eine, [(r["standort"], r["datei"]) for r in aus]) if x]
    auswerten(json.loads(json.dumps(erg)))


if __name__ == "__main__":
    main()
