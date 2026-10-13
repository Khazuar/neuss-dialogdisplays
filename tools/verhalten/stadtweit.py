# SPDX-License-Identifier: MIT
"""Stadtweite Auswertung der Verhaltensgruppen (v3_modell.json): Wie viele Abschnitte brauchen mehr als eine Gruppe? Welche Gruppen
kehren wieder, und reagieren sie ueberall gleich?  Je Abschnitt wird jede Nebengruppe mit der Hauptgruppe (groesster Anteil)
verglichen: Differenz der Effekte (gleicher Ort, gleiche Stunden, gleiches Wetter -> Ortseinfluesse fallen heraus).
Aufruf: python3 -I tools/verhalten/stadtweit.py [datei.json]"""
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

KOV = ["daemmerung", "tiefe_sonne", "nacht", "regen_0_1", "regen_0_5", "regen_2", "nach_regen", "temp_10c", "frost", "wind_10ms",
       "schnee", "ferien", "feiertag"]
NAMEN = {"daemmerung": "Dämmerung", "tiefe_sonne": "tiefe Sonne", "nacht": "Dunkelheit", "regen_0_1": "Regen 0,1–0,5", "regen_0_5": "Regen 0,5–2",
         "regen_2": "Regen ≥2 mm", "nach_regen": "nach Regen", "temp_10c": "+10 °C", "frost": "Frost", "wind_10ms": "+10 m/s Wind",
         "schnee": "Schnee", "ferien": "Schulferien", "feiertag": "Feiertag", "dichte_log": "Verkehr x2,7"}


def meta(werte, se):
    """Random-Effects-Metaanalyse (DerSimonian-Laird): Mittel, SE, tau, I2, Anteil positiv, n."""
    y, s = np.array(werte), np.array(se)
    ok = np.isfinite(y) & np.isfinite(s) & (s > 0)
    y, s = y[ok], s[ok]
    if len(y) < 3:
        return None
    w = 1 / s ** 2
    m = (w * y).sum() / w.sum()
    Q = (w * (y - m) ** 2).sum()
    df = len(y) - 1
    tau2 = max(0.0, (Q - df) / (w.sum() - (w ** 2).sum() / w.sum()))
    wr = 1 / (s ** 2 + tau2)
    mr = (wr * y).sum() / wr.sum()
    ser = math.sqrt(1 / wr.sum())
    return {"mittel": mr, "se": ser, "tau": math.sqrt(tau2), "I2": max(0.0, (Q - df) / Q) if Q > 0 else 0.0,
            "positiv": float((y > 0).mean()), "n": len(y), "signifikant_pos": int(((y / s) > 2).sum()), "signifikant_neg": int(((y / s) < -2).sum())}


def main(pfad):
    global KOV
    G = json.load(open(pfad, encoding="utf-8"))
    if G and "dichte_log" in G[0]["effekte"]:
        KOV = KOV + ["dichte_log"]
    seg = collections.OrderedDict()
    for g in G:
        seg.setdefault((g["datei"], g["abschnitt"]), []).append(g)
    Ks = collections.Counter(len(v) for v in seg.values())
    print("Abschnitte:", len(seg), " Zahl der Gruppen je Abschnitt:", dict(sorted(Ks.items())))
    gains = np.array([v[0]["cv_gewinn"] for v in seg.values()])
    print("Vorhersagegewinn ungesehener Wochen gegen eine Gruppe (nats je Fahrzeug), Median ueber Abschnitte fuer K=2..5:",
          np.round(np.median(gains[:, 1:], 0), 4), " Anteil Abschnitte mit Gewinn > 0 bei K=2:", round(float((gains[:, 1] > 0).mean()), 2))
    paare = collections.defaultdict(list)
    for (d, a), v in seg.items():
        if len(v) < 2:
            continue
        haupt = max(v, key=lambda g: g["anteil"])
        for g in v:
            if g is haupt or g["anteil"] < 0.02 or (g["stabil"] is not None and g["stabil"] < 0.9):
                continue
            # Klassen nach Lage: absolute Geschwindigkeit fuer langsame, relativ zur Hauptgruppe fuer die uebrigen
            if g["modus"] < 12:
                klasse = "sehr langsam (<12 km/h)"
            elif g["modus"] <= 28 and g["mittel"] < haupt["mittel"] - 5:
                klasse = "langsam (12-28 km/h)"
            elif g["mittel"] < haupt["mittel"]:
                klasse = "etwas langsamer als die Hauptgruppe"
            else:
                klasse = "schneller als die Hauptgruppe"
            diff = {k: g["effekte"][k] - haupt["effekte"][k] for k in KOV}
            se = {k: math.sqrt(g["se"][k] ** 2 + haupt["se"][k] ** 2) for k in KOV}
            paare[klasse].append((g, haupt, diff, se))
    for klasse in ("sehr langsam (<12 km/h)", "langsam (12-28 km/h)", "etwas langsamer als die Hauptgruppe", "schneller als die Hauptgruppe"):
        lst = paare.get(klasse, [])
        if not lst:
            continue
        print("\n== %s: %d Gruppen in %d Abschnitten, %d Standorten; Modus Median %.0f km/h, Anteil Median %.0f %%" % (
            klasse, len(lst), len({(g["datei"], g["abschnitt"]) for g, _, _, _ in lst}), len({g["rel"] for g, _, _, _ in lst}),
            np.median([g["modus"] for g, _, _, _ in lst]), 100 * np.median([g["anteil"] for g, _, _, _ in lst])))
        print("   %-16s %8s %7s %6s %5s %10s  (Effekt gegen die Hauptgruppe am selben Ort, Faktor auf die Menge)" % ("", "Faktor", "95%", "tau", "pos", "sig+/sig-"))
        for k in KOV:
            m = meta([d[k] for _, _, d, _ in lst], [s[k] for _, _, _, s in lst])
            if not m:
                continue
            lo, hi = math.exp(max(-50, min(50, m["mittel"] - 1.96 * m["se"]))), math.exp(max(-50, min(50, m["mittel"] + 1.96 * m["se"])))
            print("   %-16s %8.2f %s %6.2f %4.0f%% %4d/%-4d" % (NAMEN[k], math.exp(max(-50, min(50, m["mittel"]))), "%.2f-%.2f" % (lo, hi), m["tau"],
                                                         100 * m["positiv"], m["signifikant_pos"], m["signifikant_neg"]))
        # Tagesgang (Werktage ohne Ferien): Verhaeltnis Nebengruppe/Hauptgruppe je Stunde, normiert, Median
        rel = []
        for g, h, _, _ in lst:
            a = np.array([x if x is not None else np.nan for x in g["tagesgang"]], dtype=float)
            b = np.array([x if x is not None else np.nan for x in h["tagesgang"]], dtype=float)
            r = (a / np.nansum(a)) / (b / np.nansum(b))
            rel.append(r)
        rel = np.array(rel)
        print("   Tagesgang relativ zur Hauptgruppe (Median, Stunden 0..23):")
        print("   " + " ".join("%4.2f" % x for x in np.nanmedian(rel, 0)))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(SC, "modell.json"))
