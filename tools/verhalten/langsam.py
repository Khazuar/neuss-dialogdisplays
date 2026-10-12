# SPDX-License-Identifier: MIT
"""Gruppen im Bereich 12-28 km/h einzeln: Lage, Anteil, Effekte gegen die Hauptgruppe, Tagesgang-Spitzen."""
import collections
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I nimmt das Skriptverzeichnis nicht auf
import gemeinsam  # noqa: E402  (Pfade, numpy)
SC = gemeinsam.DATEN
W = gemeinsam.WURZEL
import numpy as np  # noqa: E402

G = json.load(open(os.path.join(SC, sys.argv[1] if len(sys.argv) > 1 else "modell.json"), encoding="utf-8"))
seg = collections.defaultdict(list)
for g in G:
    seg[(g["datei"], g["abschnitt"])].append(g)
KZ = [("regen_0_5", "R0.5"), ("regen_2", "R2"), ("temp_10c", "T+10"), ("nacht", "dunkel"), ("ferien", "Ferien"), ("schnee", "Schnee"), ("wind_10ms", "Wind")]
print("%-38s lim  modus  sd  Ant | " % "Abschnitt" + " ".join("%7s" % n for _, n in KZ) + " | Spitzen (Werktag)")
for (d, a), v in sorted(seg.items()):
    if len(v) < 2:
        continue
    h = max(v, key=lambda g: g["anteil"])
    for g in v:
        if g is h or not (12 <= g["modus"] <= 28) or g["mittel"] >= h["mittel"]:
            continue
        eff = []
        for k, _ in KZ:
            dlt = g["effekte"][k] - h["effekte"][k]
            se = math.sqrt(g["se"][k] ** 2 + h["se"][k] ** 2)
            eff.append("%6.2f%s" % (math.exp(dlt), "*" if abs(dlt / se) > 2 else " "))
        t = np.array([x if x is not None else np.nan for x in g["tagesgang"]], dtype=float)
        spitzen = np.argsort(-np.nan_to_num(t))[:3]
        print("%-38s %3.0f %5.0f %4.0f %4.0f%% | " % ((d[:34] + " A%d" % a).encode("ascii", "replace").decode(), g["limit"], g["modus"], g["sd"], 100 * g["anteil"])
              + " ".join(eff) + " | " + ",".join(str(int(x)) for x in sorted(spitzen)) + "  stab %s" % ("-" if g["stabil"] is None else "%.2f" % g["stabil"]))
