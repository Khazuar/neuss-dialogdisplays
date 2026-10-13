# SPDX-License-Identifier: MIT
"""Rauschboden zweimal: rauschen.py (Modell a(v) + b(v) * Verkehr, Regenanteil je Regenklasse) gegen die sehr langsame Verhaltensgruppe
(modell.py, Modus unter 12 km/h). Vergleich der Raten je Stunde und des Regeneffekts je Datei.

Aufruf: python3 -I tools/verhalten/rauschboden.py [modell.json]   (braucht _vorschau/auswertung.json oder AUSWERTUNG)"""
import collections
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I nimmt das Skriptverzeichnis nicht auf
import gemeinsam  # noqa: E402  (Pfade, numpy)
import numpy as np  # noqa: E402

SC = gemeinsam.DATEN


def main(name):
    G = json.load(open(os.path.join(SC, name), encoding="utf-8"))
    aus = json.load(open(os.environ.get("AUSWERTUNG") or os.path.join(gemeinsam.WURZEL, "_vorschau", "auswertung.json"), encoding="utf-8"))
    rb = {(r["standort"], r["datei"]): r.get("rauschen") or {} for r in aus["standorte"]}
    seg = collections.defaultdict(list)
    for g in G:
        seg[(g["rel"], g["datei"], g["abschnitt"])].append(g)
    je_datei = collections.defaultdict(lambda: {"fz": 0.0, "std": 0.0, "regen": [], "abschnitte": 0, "mit_gruppe": 0, "zusatz": []})
    for (rel, datei, a), v in seg.items():
        name_dsd = v[0]["datei"].split("__", 1)[1]
        e = je_datei[(rel, name_dsd)]
        e["abschnitte"] += 1
        e["std"] += 24.0 * v[0]["tage"]
        haupt = max(v, key=lambda g: g["anteil"])
        langsam = [g for g in v if g is not haupt and g["modus"] < 12]
        if langsam:
            e["mit_gruppe"] += 1
            for g in langsam:
                e["fz"] += g["fahrzeuge"]
                e["regen"].append(g["effekte"]["regen_2"] - haupt["effekte"]["regen_2"])
                # zusaetzliche Datensaetze je Stunde mit mindestens 2 mm Regen: Grundrate der Gruppe mal (exp(Regeneffekt) - 1)
                e["zusatz"].append(g["fahrzeuge"] / (24.0 * v[0]["tage"]) * (math.exp(g["effekte"]["regen_2"]) - 1))
    zeilen = []
    for (rel, datei), e in je_datei.items():
        r = rb.get((rel, datei)) or {}
        sp = r.get("spektrum") or {}
        trocken = sum(sp.get("rausch") or []) / 1000.0 if sp else None  # verkehrsunabhaengige Fahrten je Stunde (trocken)
        rg = r.get("regen") or {}
        zeilen.append({"rel": rel, "datei": datei, "gruppe_je_stunde": e["fz"] / e["std"] if e["std"] else 0.0, "mit_gruppe": e["mit_gruppe"] > 0,
                       "rausch_je_stunde": trocken, "rausch_belegt": bool(r.get("belegt")), "regen_belegt": bool(rg.get("belegt")),
                       "regen_faktor_gruppe": math.exp(float(np.mean(e["regen"]))) if e["regen"] else None,
                       "zusatz_gruppe": float(np.sum(e["zusatz"])) if e["zusatz"] else None,
                       "zusatz_rauschen": (rg.get("zusatz_je_klasse") or {}).get("3") if rg.get("belegt") else None})
    n = len(zeilen)
    mg = [z for z in zeilen if z["mit_gruppe"]]
    print("Dateien im Modell: %d; mit sehr langsamer Gruppe: %d" % (n, len(mg)))
    for a, b in ((True, True), (True, False), (False, True), (False, False)):
        k = sum(1 for z in zeilen if z["mit_gruppe"] == a and z["rausch_belegt"] == b)
        print("   Gruppe %-5s Rauschboden belegt %-5s: %d" % ("ja" if a else "nein", "ja" if b else "nein", k))
    for a, b in ((True, True), (True, False), (False, True), (False, False)):
        k = sum(1 for z in zeilen if z["mit_gruppe"] == a and z["regen_belegt"] == b)
        print("   Gruppe %-5s Regenanteil belegt %-5s: %d" % ("ja" if a else "nein", "ja" if b else "nein", k))
    paar = [(z["gruppe_je_stunde"], z["rausch_je_stunde"]) for z in mg if z["rausch_je_stunde"]]
    if len(paar) >= 3:
        x, y = np.log([p[0] for p in paar]), np.log([max(p[1], 1e-3) for p in paar])
        print("Raten je Stunde (Gruppe gegen rauschen.py, trocken): n=%d, Korrelation der Logarithmen %.2f, Verhaeltnis Median %.2f"
              % (len(paar), float(np.corrcoef(x, y)[0, 1]), float(np.median(np.exp(x - y)))))
    zp = [(z["zusatz_gruppe"], z["zusatz_rauschen"]) for z in mg if z["zusatz_gruppe"] and z["zusatz_rauschen"] and z["zusatz_gruppe"] > 0 and z["zusatz_rauschen"] > 0]
    if len(zp) >= 3:
        x, y = np.log([p[0] for p in zp]), np.log([p[1] for p in zp])
        print("Zusaetzliche Datensaetze je Regenstunde ab 2 mm (Gruppe gegen rauschen.py): n=%d, Korrelation der Logarithmen %.2f, Verhaeltnis Gruppe/rauschen.py Median %.2f (Quartile %.2f-%.2f)"
              % (len(zp), float(np.corrcoef(x, y)[0, 1]), float(np.median(np.exp(x - y))), float(np.percentile(np.exp(x - y), 25)), float(np.percentile(np.exp(x - y), 75))))
    lueck = [z for z in mg if not z["regen_belegt"] and z["regen_faktor_gruppe"]]
    print("Dateien ohne belegten Regenanteil in rauschen.py, aber mit Gruppe: %d; deren Regenfaktor (ab 2 mm) im Median %.1f, davon > 3: %d"
          % (len(lueck), float(np.median([z["regen_faktor_gruppe"] for z in lueck])) if lueck else float("nan"),
             sum(1 for z in lueck if z["regen_faktor_gruppe"] > 3)))
    json.dump(zeilen, open(os.path.join(SC, "rauschboden_vergleich.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "modell.json")
