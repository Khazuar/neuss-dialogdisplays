# SPDX-License-Identifier: MIT
"""Verhaltensgruppen fuer die Seiten: belege/verhaltensgruppen.json aus modell_dichte.json (und dem Placebo-Durchgang).

Je Abschnitt die Gruppen des Modells (Profil, Anteil, Verhalten), ihre Art (Klasse) und stadtweit je Klasse die gemittelten Effekte
gegenueber der Hauptgruppe mit dem Placebo-Vergleich. Die Seiten (seiten_bauen.py) lesen nur diese Datei; numpy braucht nur dieses Skript.

Aufruf: python3 -I tools/verhalten/belege.py [modell_dichte.json] [modell_placebo_dichte.json] [-o belege/verhaltensgruppen.json]"""
import collections
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I nimmt das Skriptverzeichnis nicht auf
import gemeinsam  # noqa: E402  (Pfade, numpy)
import numpy as np  # noqa: E402
from stadtweit import meta  # noqa: E402

SC = gemeinsam.DATEN
KLASSEN = collections.OrderedDict([
    ("haupt", "Hauptgruppe"),
    ("rauschen", "sehr langsam (unter 12 km/h)"),
    ("langsam", "langsam (12 bis 28 km/h)"),
    ("etwas_langsamer", "etwas langsamer als die Hauptgruppe"),
    ("schnell", "schneller als die Hauptgruppe"),
])
MIN_ANTEIL = 0.02
MIN_STABIL = 0.9


def klasse(g, haupt):
    if g is haupt:
        return "haupt"
    if g["modus"] < 12:
        return "rauschen"
    if g["modus"] <= 28 and g["mittel"] < haupt["mittel"] - 5:
        return "langsam"
    return "etwas_langsamer" if g["mittel"] < haupt["mittel"] else "schnell"


def segmente(G):
    seg = collections.OrderedDict()
    for g in G:
        seg.setdefault((g["rel"], g["datei"].split("__", 1)[1], g["abschnitt"]), []).append(g)
    return seg


def paare(seg):
    """Je Klasse: [(Gruppe, Hauptgruppe)] fuer belastbare Nebengruppen (Anteil, Stabilitaet)."""
    out = collections.defaultdict(list)
    for v in seg.values():
        if len(v) < 2:
            continue
        h = max(v, key=lambda g: g["anteil"])
        for g in v:
            if g is h or g["anteil"] < MIN_ANTEIL or (g["stabil"] is not None and g["stabil"] < MIN_STABIL):
                continue
            out[klasse(g, h)].append((g, h))
    return out


def klassen_stadtweit(seg, seg_placebo):
    echt, plac = paare(seg), paare(seg_placebo) if seg_placebo else {}
    kov = list(next(iter(seg.values()))[0]["effekte"])
    erg = collections.OrderedDict()
    for k in KLASSEN:
        if k == "haupt" or not echt.get(k):
            continue
        lst = echt[k]
        e = {"name": KLASSEN[k], "gruppen": len(lst), "abschnitte": len({(g["datei"], g["abschnitt"]) for g, _ in lst}),
             "standorte": len({g["rel"].split("/")[0] for g, _ in lst}), "modus_median_kmh": float(np.median([g["modus"] for g, _ in lst])),
             "anteil_median": float(np.median([g["anteil"] for g, _ in lst])), "placebo_gruppen": len(plac.get(k, [])), "effekte": {}}
        for c in kov:
            m = meta([g["effekte"][c] - h["effekte"][c] for g, h in lst], [math.sqrt(g["se"][c] ** 2 + h["se"][c] ** 2) for g, h in lst])
            if not m:
                continue
            p = None
            if plac.get(k) and c != "dichte_log":  # die Verkehrsmenge ist im Placebo nicht verschoben: kein Vergleich
                p = meta([g["effekte"][c] - h["effekte"][c] for g, h in plac[k]], [math.sqrt(g["se"][c] ** 2 + h["se"][c] ** 2) for g, h in plac[k]])
            gesichert = (m["mittel"] - 1.96 * m["se"] > 0 or m["mittel"] + 1.96 * m["se"] < 0) and (
                p is None or abs(m["mittel"]) > abs(p["mittel"]) + 1.96 * math.hypot(m["se"], p["se"]))
            e["effekte"][c] = {"faktor": round(math.exp(max(-50, min(50, m["mittel"]))), 3),
                               "von": round(math.exp(max(-50, min(50, m["mittel"] - 1.96 * m["se"]))), 3),
                               "bis": round(math.exp(max(-50, min(50, m["mittel"] + 1.96 * m["se"]))), 3),
                               "placebo": round(math.exp(max(-50, min(50, p["mittel"]))), 3) if p else None, "gesichert": bool(gesichert)}
        rel = []
        for g, h in lst:
            a = np.array([x if x is not None else np.nan for x in g["tagesgang"]], dtype=float)
            b = np.array([x if x is not None else np.nan for x in h["tagesgang"]], dtype=float)
            rel.append((a / np.nansum(a)) / (b / np.nansum(b)))
        e["tagesgang_gegen_haupt"] = [None if np.isnan(x) else round(float(x), 2) for x in np.nanmedian(np.array(rel), 0)]
        erg[k] = e
    return erg


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-o")]
    ziel = sys.argv[sys.argv.index("-o") + 1] if "-o" in sys.argv else os.path.join(gemeinsam.WURZEL, "belege", "verhaltensgruppen.json")
    args = [a for a in args if a != ziel]
    echt = json.load(open(os.path.join(SC, args[0] if args else "modell_dichte.json"), encoding="utf-8"))
    pfad_p = os.path.join(SC, args[1] if len(args) > 1 else "modell_placebo_dichte.json")
    placebo = json.load(open(pfad_p, encoding="utf-8")) if os.path.exists(pfad_p) else None
    seg = segmente(echt)
    abschnitte = []
    for (rel, datei, a), v in seg.items():
        h = max(v, key=lambda g: g["anteil"])
        gruppen = []
        for g in sorted(v, key=lambda g: g["mittel"]):
            gang = np.array([x if x is not None else np.nan for x in g["tagesgang"]], dtype=float)
            gang = gang / np.nanmean(gang)
            gegen = {}
            for c in g["effekte"]:
                d = g["effekte"][c] - h["effekte"][c]
                se = math.hypot(g["se"][c], h["se"][c])
                gegen[c] = {"faktor": round(math.exp(max(-50, min(50, d))), 3), "z": round(d / se, 1) if se > 0 else None}
            gruppen.append({"klasse": klasse(g, h), "anteil": round(g["anteil"], 4), "fahrzeuge": int(round(g["fahrzeuge"])),
                            "modus_kmh": g["modus"], "mittel_kmh": round(g["mittel"], 1), "streuung_kmh": round(g["sd"], 1),
                            "profil": [round(x, 5) for x in g["profil"]], "stabil": None if g["stabil"] is None else round(g["stabil"], 3),
                            "belastbar": g is h or (g["anteil"] >= MIN_ANTEIL and (g["stabil"] is None or g["stabil"] >= MIN_STABIL)),
                            "effekte_gegen_haupt": None if g is h else gegen,
                            "tagesgang": [None if np.isnan(x) else round(float(x), 3) for x in gang]})
        abschnitte.append({"standort": rel, "datei": datei, "abschnitt": a + 1, "tage": v[0]["tage"], "gruppen_zahl": len(v),
                           "vorhersagegewinn": [round(x, 5) for x in v[0]["cv_gewinn"]], "gruppen": gruppen})
    nseg = len(seg)
    mehr = sum(1 for v in seg.values() if len(v) > 1)
    mehr_p = sum(1 for v in segmente(placebo).values() if len(v) > 1) if placebo else None
    out = {"erzeugt_von": "tools/verhalten/belege.py (Modell: tools/verhalten/modell.py mit Verkehrsdichte)",
           "hinweis": "Forschungsstand, siehe docs/verhalten.md. Eigene Berechnung, ohne Gewaehr. Wetter: Quelle: Deutscher Wetterdienst.",
           "klassen_namen": KLASSEN, "profil_klassen_kmh": "2-km/h-Klassen ab 0 (0-2, 2-4, ..., 88-90, ab 90)",
           "merkmale": {"daemmerung": "Dämmerung (Sonne -6 bis 0 Grad)", "tiefe_sonne": "tiefe Sonne (0 bis 15 Grad)", "nacht": "Dunkelheit (unter -6 Grad)",
                        "regen_0_1": "Regen 0,1 bis 0,5 mm", "regen_0_5": "Regen 0,5 bis 2 mm", "regen_2": "Regen ab 2 mm", "nach_regen": "nach Regen",
                        "temp_10c": "10 Grad wärmer", "frost": "Frost", "wind_10ms": "10 m/s mehr Windspitze", "schnee": "Schnee",
                        "ferien": "Schulferien", "feiertag": "Feiertag", "dichte_log": "2,7-mal so viel Verkehr"},
           "uebersicht": {"abschnitte": nseg, "mit_mehreren_gruppen": mehr, "placebo_mit_mehreren_gruppen": mehr_p},
           "klassen": klassen_stadtweit(seg, segmente(placebo) if placebo else None), "abschnitte": abschnitte}
    with open(ziel, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")
    print("%d Abschnitte, %d mit mehreren Gruppen -> %s" % (nseg, mehr, ziel), file=sys.stderr)


if __name__ == "__main__":
    main()
