# SPDX-License-Identifier: MIT
"""Stundentabellen aller Dateien fuer die Verhaltensanalyse (alle Fahrzeuge inkl. Rauschen, 2-km/h-Klassen 0..90),
Kontext je Stunde und Abschnitte (bruch.py mit Ferien/Feiertagen als Ausnahme).  Aufruf: python3 -I tools/verhalten/stunden.py [--jobs N]"""
import datetime as dt
import json
import math
import multiprocessing
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I nimmt das Skriptverzeichnis nicht auf
import gemeinsam  # noqa: E402  (Pfade, numpy)
SC = gemeinsam.DATEN
W = gemeinsam.WURZEL
import numpy as np  # noqa: E402

EPOCHE = dt.datetime(2020, 1, 1)
BREITE = 2
NBIN = 46  # 0-2, 2-4, ..., 88-90, >=90


def elevation(utc, breite, laenge):
    doy = utc.timetuple().tm_yday
    h = utc.hour + utc.minute / 60.0
    g = 2 * math.pi / 365 * (doy - 1 + (h - 12) / 24)
    eq = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    dek = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g)
           - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    ha = math.radians((h * 60 + eq + 4 * laenge) / 4 - 180)
    la = math.radians(breite)
    c = math.sin(la) * math.sin(dek) + math.cos(la) * math.cos(dek) * math.cos(ha)
    return 90 - math.degrees(math.acos(max(-1, min(1, c))))


def eine(args):
    rel, datei, lim = args
    import dsd2csv as d
    import bruch
    import kalender
    import rauschen
    name = (rel + "__" + datei).replace("/", "_").replace(" ", "_")
    ziel = os.path.join(SC, "stunden", name + ".npz")
    if os.path.exists(ziel):
        return name, "vorhanden"
    meta, veh, status, warn = d.parse(open(os.path.join(W, rel, datei), "rb").read())
    uhr, ber, teil, spannen = d.analysiere_uhr(veh, status, mit_spannen=True)
    if len(ber) < 5000 or not lim:
        return name, "zu wenig"
    ab = max(10, int(round(0.5 * lim)))
    br = bruch.erkenne(ber, spannen, ab, lim, kalender.besonderer_tag)
    grenzen = [b["datum"] for b in br.get("brueche", [])]
    ort = d.koordinaten(rel) or (51.2042, 6.6879)
    regen = d.regenfunktion(ort=ort)
    wetter = d._wetter(d.WETTER)["tage"]
    abged = sorted(rauschen.abgedeckte_stunden(spannen))
    hs = np.array([int((dt.datetime(t.year, t.month, t.day, h) - EPOCHE).total_seconds() // 3600) for t, h in abged], dtype=np.int64)
    idx = {int(h): i for i, h in enumerate(hs)}
    M = np.zeros((len(hs), NBIN), dtype=np.float32)
    for t, v in ber:
        i = idx.get(int((t - EPOCHE).total_seconds() // 3600))
        if i is not None:
            M[i, min(int(v) // BREITE, NBIN - 1)] += 1
    ctx = np.full((len(hs), 16), np.nan)
    for i, (tag, h) in enumerate(abged):
        lok = dt.datetime(tag.year, tag.month, tag.day, h)
        w = wetter.get(tag.isoformat(), {})
        r0 = regen(tag, h)
        p, n = lok - dt.timedelta(hours=1), lok + dt.timedelta(hours=1)
        rp, rn = regen(p.date(), p.hour), regen(n.date(), n.hour)
        mitte = lok + dt.timedelta(minutes=30)
        utc = mitte - dt.timedelta(hours=d.utc_versatz_h(mitte - dt.timedelta(hours=1)))
        bt = kalender.besonderer_tag(tag)
        abschnitt = sum(1 for g in grenzen if tag.isoformat() >= g)
        ctx[i] = [r0 if r0 is not None else np.nan, rp if rp is not None else np.nan, rn if rn is not None else np.nan,
                  w.get("tmk", np.nan), w.get("tnk", np.nan), w.get("fx", np.nan), w.get("shk", 0.0) or 0.0,
                  elevation(utc, ort[0], ort[1]), tag.weekday(), h, (tag - EPOCHE.date()).days,
                  1.0 if bt == "ferien" else 0.0, 1.0 if bt == "feiertag" else 0.0, abschnitt, 0, 0]
    np.savez_compressed(ziel, hs=hs, M=M, ctx=ctx, lim=lim, ort=np.array(ort), ab=ab,
                        abschnitte=json.dumps(br.get("abschnitte", [])), rel=rel, datei=datei)
    return name, "%d Stunden, %d Abschnitte" % (len(hs), len(br.get("abschnitte", [])) or 1)


def main():
    jobs = int(sys.argv[sys.argv.index("--jobs") + 1]) if "--jobs" in sys.argv else 6
    os.makedirs(os.path.join(SC, "stunden"), exist_ok=True)
    aus = json.load(open(os.environ.get("AUSWERTUNG") or os.path.join(W, "_vorschau", "auswertung.json"), encoding="utf-8"))
    auftraege = [(r["standort"], r["datei"], r.get("tempolimit_kmh")) for r in aus["standorte"]]
    with multiprocessing.Pool(jobs) as pool:
        for name, info in pool.imap_unordered(eine, auftraege):
            print(name.encode("ascii", "replace").decode()[:60], info, flush=True)


if __name__ == "__main__":
    main()
