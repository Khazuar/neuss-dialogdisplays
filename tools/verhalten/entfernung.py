# SPDX-License-Identifier: MIT
"""Wiederkehr der schnellen Gruppe in mehreren Abschnitten desselben Ordners und Aehnlichkeit ihrer Effekte nach Entfernung (Mantel)."""
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

KOV = ["daemmerung", "nacht", "regen_0_5", "regen_2", "ferien", "schnee"]
G = json.load(open(os.path.join(SC, sys.argv[1] if len(sys.argv) > 1 else "modell.json"), encoding="utf-8"))
seg = collections.OrderedDict()
for g in G:
    seg.setdefault((g["datei"], g["abschnitt"]), []).append(g)


def schnell(v):
    h = max(v, key=lambda g: g["anteil"])
    return [g for g in v if g is not h and g["mittel"] > h["mittel"] and g["anteil"] >= 0.02 and (g["stabil"] is None or g["stabil"] >= 0.9)], h


hat = {k: bool(schnell(v)[0]) for k, v in seg.items()}
basis = np.mean(list(hat.values()))
je_ordner = collections.defaultdict(list)
for (d, a), v in seg.items():
    je_ordner[v[0]["rel"].split("/")[0]].append(hat[(d, a)])
paare = [(x, y) for lst in je_ordner.values() if len(lst) > 1 for i, x in enumerate(lst) for y in lst[i + 1:]]
gleich = np.mean([x == y for x, y in paare]) if paare else float("nan")
erwartet = basis ** 2 + (1 - basis) ** 2
print("Abschnitte mit schneller Gruppe: %.0f %%; Paare von Abschnitten im selben Ordner: %d, gleich (beide/keiner) %.0f %% (bei Unabhaengigkeit %.0f %%)"
      % (100 * basis, len(paare), 100 * gleich, 100 * erwartet))
# Effektvektoren der schnellen Gruppe gegen die Hauptgruppe, je Abschnitt
pkt, vek = [], []
for k, v in seg.items():
    s, h = schnell(v)
    if not s:
        continue
    g = max(s, key=lambda x: x["anteil"])
    z = [(g["effekte"][c] - h["effekte"][c]) / math.sqrt(g["se"][c] ** 2 + h["se"][c] ** 2) for c in KOV]
    pkt.append(g["ort"])
    vek.append(np.clip(z, -10, 10))
pkt, vek = np.array(pkt), np.array(vek)
n = len(pkt)
dist = np.zeros((n, n))
sim = np.zeros((n, n))
for i in range(n):
    for j in range(n):
        dist[i, j] = 111.2 * math.hypot(pkt[i, 0] - pkt[j, 0], (pkt[i, 1] - pkt[j, 1]) * math.cos(math.radians(51.2)))
        sim[i, j] = np.corrcoef(vek[i], vek[j])[0, 1]
iu = np.triu_indices(n, 1)
r = np.corrcoef(dist[iu], sim[iu])[0, 1]
rng = np.random.RandomState(0)
null = []
for _ in range(2000):
    p = rng.permutation(n)
    null.append(np.corrcoef(dist[iu], sim[np.ix_(p, p)][iu])[0, 1])
print("Schnelle Gruppen: %d Abschnitte; mittlere Aehnlichkeit der Effektmuster (Korrelation der z-Werte) %.2f" % (n, np.nanmean(sim[iu])))
for lo, hi in ((0, 0.3), (0.3, 2), (2, 4), (4, 15)):
    m = (dist[iu] >= lo) & (dist[iu] < hi)
    print("   Entfernung %.1f-%.0f km: %4d Paare, Aehnlichkeit %.2f" % (lo, hi, m.sum(), np.nanmean(sim[iu][m])))
print("Mantel-Korrelation Entfernung/Aehnlichkeit %.3f, p (einseitig, negativ) = %.3f" % (r, np.mean(np.array(null) <= r)))
