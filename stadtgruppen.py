# SPDX-License-Identifier: MIT
"""Verhaltensgruppen auf drei Ebenen: Abschnitt (A), Messstelle/Standort (MS) und Stadt (S). Siehe docs/verhalten.md.

Liest die Abschnittsgruppen aus auswertung.json (dsd2csv.py mit verhalten.py) und schreibt verhaltensgruppen.json fuer die Seiten.

- A-Gruppen: Ergebnis des Modells je Abschnitt, benannt "A<Abschnitt>·<Gruppe>" (Gruppen nach Tempo geordnet). Nicht stabil ueber
  Neuberechnungen; stabil sind die Ebenen darueber.
- S-Gruppen: je Art (Tempolage gegenueber der Hauptgruppe) alle belastbaren A-Gruppen der Stadt. Ihr Verhalten ist die Metaanalyse
  (DerSimonian-Laird) der Unterschiede zur Hauptgruppe am selben Ort, verglichen mit dem Placebo-Durchgang (Wetter, Licht und Ferien
  verschoben). IDs und Deutungen stehen im Register belege/verhaltensgruppen-register.json und werden nie wiederverwendet.
- MS-Gruppen: A-Gruppen derselben Standortseite (alle Messungen, Abschnitte, Fahrtrichtungen), die sich gegenseitig entsprechen:
  gleiche Art, Profil-Kosinus mindestens 0,9 und Korrelation des Verhaltens mindestens 0,5.

Aufruf: python3 stadtgruppen.py --auswertung _site/auswertung.json [--metadaten belege/metadaten.json] [-o _site/verhaltensgruppen.json]
        [--register belege/verhaltensgruppen-register.json] [--register-schreiben]
Mit --register-schreiben uebernimmt das Register die neuen Vorlagen (Profile) und das Verhalten der S-Gruppen; Arten ohne Eintrag
bekommen eine neue ID. Deutung, Stufe, Kriterien und Belege bleiben, wie sie von Hand gepflegt sind.
"""
import argparse
import collections
import datetime as dt
import json
import math
import os
import statistics
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)  # python -I nimmt das Skriptverzeichnis nicht auf
import seiten_bauen  # noqa: E402

REGISTER = os.path.join(HIER, "belege", "verhaltensgruppen-register.json")
KLASSEN = collections.OrderedDict([
    ("haupt", "Hauptgruppe"),
    ("rauschen", "sehr langsam (unter 12 km/h)"),
    ("langsam", "langsam (12 bis 28 km/h)"),
    ("etwas_langsamer", "etwas langsamer als die Hauptgruppe"),
    ("schnell", "schneller als die Hauptgruppe"),
])
TEMPOLAGE = {"rauschen": "R", "langsam": "L", "etwas_langsamer": "M", "schnell": "F"}
MERKMALE = collections.OrderedDict([
    ("daemmerung", "Dämmerung (Sonne −6 bis 0 Grad)"), ("tiefe_sonne", "tiefe Sonne (0 bis 15 Grad)"), ("nacht", "Dunkelheit (unter −6 Grad)"),
    ("regen_0_1", "Regen 0,1 bis 0,5 mm"), ("regen_0_5", "Regen 0,5 bis 2 mm"), ("regen_2", "Regen ab 2 mm"), ("nach_regen", "nach Regen"),
    ("temp_10c", "10 Grad wärmer"), ("frost", "Frost"), ("wind_10ms", "10 m/s mehr Windspitze"), ("schnee", "Schnee"),
    ("ferien", "Schulferien"), ("feiertag", "Feiertag"), ("dichte_log", "2,7-mal so viel Verkehr")])
STUFEN = ("Hypothese", "gestützt", "tragfähig")
MIN_STANDORTE = 3  # so viele Standorte braucht eine S-Gruppe, um als stadtweit gefunden zu gelten
MS_KOSINUS = 0.9
MS_KORRELATION = 0.5
NBIN = 46
MITTE_REL = NBIN - 1  # Index der Hauptgruppe in relativen Profilen (Laenge 2 * NBIN - 1)


def meta(werte, se):
    """Random-Effects-Metaanalyse (DerSimonian-Laird): {mittel, se, tau, n} oder None (unter 3 Werten)."""
    paare = [(y, s) for y, s in zip(werte, se) if y is not None and s is not None and math.isfinite(y) and math.isfinite(s) and s > 0]
    if len(paare) < 3:
        return None
    w = [1 / s ** 2 for _, s in paare]
    m = sum(wi * y for wi, (y, _) in zip(w, paare)) / sum(w)
    q = sum(wi * (y - m) ** 2 for wi, (y, _) in zip(w, paare))
    df = len(paare) - 1
    tau2 = max(0.0, (q - df) / (sum(w) - sum(wi * wi for wi in w) / sum(w)))
    wr = [1 / (s ** 2 + tau2) for _, s in paare]
    return {"mittel": sum(wi * y for wi, (y, _) in zip(wr, paare)) / sum(wr), "se": math.sqrt(1 / sum(wr)), "tau": math.sqrt(tau2), "n": len(paare)}


def kosinus(a, b):
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b)) / (na * nb) if na and nb else 0.0


def korrelation(a, b):
    """Pearson-Korrelation zweier Verhaltensmuster {Merkmal: z} (auf ±10 begrenzt), nur gemeinsame Merkmale, mindestens 4."""
    k = [c for c in MERKMALE if a.get(c) is not None and b.get(c) is not None]
    if len(k) < 4:
        return None
    x = [max(-10.0, min(10.0, a[c])) for c in k]
    y = [max(-10.0, min(10.0, b[c])) for c in k]
    mx, my = sum(x) / len(x), sum(y) / len(y)
    sx = math.sqrt(sum((v - mx) ** 2 for v in x))
    sy = math.sqrt(sum((v - my) ** 2 for v in y))
    return sum((u - mx) * (v - my) for u, v in zip(x, y)) / (sx * sy) if sx and sy else None


def gegen_haupt(g, h):
    """Unterschied zur Hauptgruppe je Merkmal: {Merkmal: (log-Faktor, SE)}."""
    return {c: (g["effekte"][c] - h["effekte"][c], math.hypot(g["se"][c], h["se"][c])) for c in g["effekte"] if c in h["effekte"]}


def relativ(profil, modus_index):
    """Profil um den Modus der Hauptgruppe verschoben (Index MITTE_REL = Modus der Hauptgruppe)."""
    out = [0.0] * (2 * NBIN - 1)
    for j, p in enumerate(profil):
        out[j - modus_index + MITTE_REL] = p
    return out


def _argmax(xs):
    return max(range(len(xs)), key=lambda i: xs[i])


def quantil(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    i = p * (len(xs) - 1)
    lo = int(math.floor(i))
    return xs[lo] + (xs[min(lo + 1, len(xs) - 1)] - xs[lo]) * (i - lo)


# ------------------------------------------------------------------ Einlesen

def abschnitte_lesen(auswertung, seite_von):
    """[(Schluessel 'rel/datei', Seite, Abschnitt aus dem YAML-Block verhalten)], und je Abschnitt die A-Gruppen mit Namen und Bezug."""
    out = []
    for r in auswertung["standorte"]:
        v = r.get("verhalten") or {}
        if not v.get("geprueft"):
            continue
        for a in v["abschnitte"]:
            a = dict(a)
            a["schluessel"] = f'{r["standort"]}/{r["datei"]}'
            a["rel"], a["datei"], a["seite"] = r["standort"], r["datei"], seite_von.get(r["standort"])
            a["messung"] = seiten_bauen.messung_id(r["standort"], r["datei"])
            a["mehrere"] = len(v["abschnitte"]) > 1
            if a.get("geprueft"):
                h = next(g for g in a["gruppen"] if g["klasse"] == "haupt")
                hm = _argmax(h["profil"])
                for k, g in enumerate(a["gruppen"], 1):
                    g["name"] = f'A{a["nr"]}·{k}'
                    g["kennung"] = f'{a["messung"]}/{g["name"]}'
                    g["_haupt"] = h
                    g["_rel"] = relativ(g["profil"], hm)
                    if g is not h:
                        d = gegen_haupt(g, h)
                        g["_d"] = d
                        g["_z"] = {c: (x / s if s > 0 else None) for c, (x, s) in d.items()}
            out.append(a)
    return out


def paare_placebo(abschnitte):
    """Je Art [(Gruppe, Hauptgruppe)] der belastbaren Nebengruppen im Placebo-Durchgang."""
    out = collections.defaultdict(list)
    for a in abschnitte:
        p = a.get("placebo")
        if not p or p["K"] < 2:
            continue
        h = next(g for g in p["gruppen"] if g["klasse"] == "haupt")
        for g in p["gruppen"]:
            if g is not h and g["belastbar"]:
                out[g["klasse"]].append((g, h))
    return out


# ------------------------------------------------------------------ Stadtebene

def stadtgruppen(abschnitte, register):
    """S-Gruppen je Art mit Register-Eintrag, Metaanalyse, Placebo und Vorlage."""
    echt = collections.defaultdict(list)
    for a in abschnitte:
        for g in a.get("gruppen") or []:
            if g["klasse"] != "haupt" and g["belastbar"]:
                echt[g["klasse"]].append((a, g))
    plac = paare_placebo(abschnitte)
    eintraege = {g["klasse"]: g for g in register.get("gruppen", []) if g.get("status", "aktiv") == "aktiv"}
    erg = collections.OrderedDict()
    for k in KLASSEN:
        if k == "haupt":
            continue
        lst = echt.get(k, [])
        reg = eintraege.get(k)
        sid = reg["id"] if reg else f"S-{TEMPOLAGE[k]}?"
        s = {"id": sid, "klasse": k, "art": KLASSEN[k], "im_register": bool(reg), "gruppen": len(lst),
             "abschnitte": len({(a["schluessel"], a["nr"]) for a, _ in lst}), "standorte": sorted({a["seite"] for a, _ in lst if a["seite"]}),
             "placebo_gruppen": len(plac.get(k, [])), "effekte": collections.OrderedDict()}
        for f in ("deutung", "stufe", "kriterien", "belege", "aufgenommen"):
            s[f] = (reg or {}).get(f)
        if lst:
            s["modus_median_kmh"] = statistics.median(g["modus_kmh"] for _, g in lst)
            an = [g["anteil"] for _, g in lst]
            s["anteil_median"], s["anteil_spanne"] = round(statistics.median(an), 4), [round(quantil(an, 0.25), 4), round(quantil(an, 0.75), 4)]
        for c in MERKMALE:
            m = meta([g["_d"][c][0] for _, g in lst if c in g["_d"]], [g["_d"][c][1] for _, g in lst if c in g["_d"]])
            if not m:
                continue
            p = None
            if plac.get(k) and c != "dichte_log":  # die Verkehrsmenge ist im Placebo nicht verschoben: kein Vergleich
                pd = [gegen_haupt(g, h)[c] for g, h in plac[k] if c in g["effekte"]]
                p = meta([x for x, _ in pd], [se for _, se in pd])
            gesichert = (m["mittel"] - 1.96 * m["se"] > 0 or m["mittel"] + 1.96 * m["se"] < 0) and (
                p is None or abs(m["mittel"]) > abs(p["mittel"]) + 1.96 * math.hypot(m["se"], p["se"]))
            s["effekte"][c] = {"faktor": _exp(m["mittel"]), "von": _exp(m["mittel"] - 1.96 * m["se"]), "bis": _exp(m["mittel"] + 1.96 * m["se"]),
                               "placebo": _exp(p["mittel"]) if p else None, "gesichert": bool(gesichert), "_z": m["mittel"] / m["se"] if m["se"] > 0 else None}
        # gefunden: an mehreren Standorten und mit Verhalten, das der Placebo-Durchgang nicht erzeugt (die Verkehrsmenge ist dort nicht verschoben)
        s["gefunden"] = len(s["standorte"]) >= MIN_STANDORTE and any(v["gesichert"] for c, v in s["effekte"].items() if c != "dichte_log")
        s["anzeige"] = anzeige_s(s)
        if lst:  # Vorlage: sehr langsam in absoluten km/h (Stoerungen haengen nicht vom Verkehr ab), sonst relativ zur Hauptgruppe
            if k == "rauschen":
                prof = _mittelprofil([g["profil"] for _, g in lst])
                s["vorlage"] = {"bezug": "absolut", "profil": prof}
            else:
                prof = _mittelprofil([g["_rel"] for _, g in lst])
                s["vorlage"] = {"bezug": "relativ", "profil_relativ": prof, "mitte": MITTE_REL}
            s["verhalten"] = {c: round(math.log(v["faktor"]), 3) for c, v in s["effekte"].items()}
        erg[k] = s
    return erg


def _exp(x):
    return round(math.exp(max(-50.0, min(50.0, x))), 3)


def _mittelprofil(profile):
    n = len(profile)
    m = [sum(p[j] for p in profile) / n for j in range(len(profile[0]))]
    s = sum(m)
    return [round(x / s, 5) for x in m]


def anzeige_s(s):
    """Anzeigename: tragfähige Deutung ersetzt die ID ("Regenphantome (S-R1)"), sonst ID mit Stufe der Deutung."""
    if s.get("deutung") and s.get("stufe") == "tragfähig":
        return f'{s["deutung"]} ({s["id"]})'
    if s.get("deutung"):
        return f'{s["id"]} ({s["stufe"] or "Hypothese"}: {s["deutung"]})'
    return s["id"]


# ------------------------------------------------------------------ Standortebene

def standortgruppen_ms(abschnitte, stadt):
    """MS-Gruppen je Standortseite: Union-Find ueber belastbare A-Gruppen gleicher Art, die sich entsprechen. {Seite: [MS-Gruppe]}."""
    je_seite = collections.defaultdict(list)
    for a in abschnitte:
        for g in a.get("gruppen") or []:
            if g["klasse"] != "haupt" and g["belastbar"] and a["seite"]:
                je_seite[a["seite"]].append((a, g))
    out = {}
    for seite, lst in sorted(je_seite.items()):
        eltern = list(range(len(lst)))

        def wurzel(i):
            while eltern[i] != i:
                eltern[i] = eltern[eltern[i]]
                i = eltern[i]
            return i
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                (ai, gi), (aj, gj) = lst[i], lst[j]
                if gi["klasse"] != gj["klasse"] or (ai["schluessel"], ai["nr"]) == (aj["schluessel"], aj["nr"]):
                    continue
                r = korrelation(gi["_z"], gj["_z"])
                if kosinus(gi["profil"], gj["profil"]) >= MS_KOSINUS and r is not None and r >= MS_KORRELATION:
                    eltern[wurzel(i)] = wurzel(j)
        cluster = collections.defaultdict(list)
        for i in range(len(lst)):
            cluster[wurzel(i)].append(lst[i])
        gruppen_ = [c for c in cluster.values() if len(c) >= 2]
        gruppen_.sort(key=lambda c: (list(TEMPOLAGE).index(c[0][1]["klasse"]), -len(c), c[0][1]["kennung"]))
        nummer = collections.Counter()
        ms = []
        for c in gruppen_:
            k = c[0][1]["klasse"]
            nummer[k] += 1
            s = stadt.get(k)
            buchstabe = TEMPOLAGE[k] if s and s["gefunden"] else "x"
            mid = f"MS-{seite}-{buchstabe}{nummer[k]}"
            z = {}
            for m_ in MERKMALE:  # gemeinsames Verhalten: Mittel der z-Werte (zur Korrelation mit der Stadtebene)
                werte = [g["_z"][m_] for _, g in c if g["_z"].get(m_) is not None]
                if werte:
                    z[m_] = sum(werte) / len(werte)
            eintrag = {"id": mid, "klasse": k, "stadt": s["id"] if s else None, "mitglieder": [g["kennung"] for _, g in c],
                       "messungen": len({a["schluessel"] for a, _ in c}), "abschnitte": len({(a["schluessel"], a["nr"]) for a, _ in c}),
                       "modus_kmh": statistics.median(g["modus_kmh"] for _, g in c),
                       "anteil_median": round(statistics.median(g["anteil"] for _, g in c), 4), "_z": z}
            if s and s.get("effekte"):
                r = korrelation(z, {m_: v["_z"] for m_, v in s["effekte"].items()})
                eintrag["korrelation_stadt"] = None if r is None else round(r, 2)
            for _, g in c:
                g["ms"] = mid
            ms.append(eintrag)
        out[seite] = ms
    return out


# ------------------------------------------------------------------ Ausgabe

def abschnitt_ausgabe(a, stadt):
    e = {k: a.get(k) for k in ("nr", "geprueft", "grund", "tage", "fahrzeuge", "K", "cv_gewinn")}
    e["placebo_K"] = (a.get("placebo") or {}).get("K")
    gr = []
    for g in a.get("gruppen") or []:
        x = {k: g.get(k) for k in ("name", "kennung", "klasse", "anteil", "fahrzeuge", "modus_kmh", "mittel_kmh", "streuung_kmh", "profil",
                                     "stabil", "belastbar", "tagesgang")}
        if g["klasse"] != "haupt":
            s = stadt.get(g["klasse"])
            x["stadt"] = s["id"] if s else None
            x["ms"] = g.get("ms")
            x["effekte_gegen_haupt"] = {c: {"faktor": _exp(d), "z": round(d / se, 1) if se > 0 else None} for c, (d, se) in g["_d"].items()}
            if s and s.get("effekte"):
                r = korrelation(g["_z"], {c: v["_z"] for c, v in s["effekte"].items()})
                x["korrelation_stadt"] = None if r is None else round(r, 2)
        gr.append(x)
    e["gruppen"] = gr
    vorlagen = []
    eigene = {g["klasse"] for g in a.get("gruppen") or [] if g["belastbar"]}
    geprueft = {v["klasse"]: v for v in a.get("vorlagen") or []}
    for k, s in stadt.items():  # Stadtgruppen, die der Abschnitt nicht selbst hat: lokal nachgewiesen, nicht nachweisbar oder nur erwartet
        if k in eigene or not s["gefunden"]:
            continue
        v = geprueft.get(k)
        x = {"stadt": s["id"], "klasse": k, "erwartet_anteil": s.get("anteil_median"), "erwartet_spanne": s.get("anteil_spanne")}
        if v is None:
            x["stand"] = "erwartet"
        else:
            x["stand"] = "nachgewiesen" if v["nachgewiesen"] else "nicht_nachweisbar"
            x["gewinn"] = v["gewinn"]
            if v.get("anteil") is not None:
                x["anteil"] = v["anteil"]
        vorlagen.append(x)
    e["stadtgruppen"] = vorlagen
    return e


def einsatz_zeilen(auswertung, einsaetze):
    """Zeilen wie auswertung["standorte"] mit den Verhaltensgruppen der Einsaetze (einsaetze.py): Schluessel ist die Messung, auf der der
    Einsatz beruht (rel/Datei), so finden die Seiten die Gruppen beim Einsatz bzw. bei der Messung, die mit ihm zusammenfaellt."""
    datei_von = {seiten_bauen.messung_id(r["standort"], r["datei"]): (r["standort"], r["datei"]) for r in auswertung["standorte"]}
    out = []
    for e in einsaetze.get("einsaetze", []):
        if e["messung"] in datei_von and (e.get("kennzahlen") or {}).get("verhalten"):
            rel, datei = datei_von[e["messung"]]
            out.append({"standort": rel, "datei": datei, "verhalten": e["kennzahlen"]["verhalten"]})
    return {"standorte": out}


def ausgabe(auswertung, metadaten, register, einsaetze=None):
    seiten = seiten_bauen.standortgruppen(auswertung, metadaten)
    seite_von = {rel: slug for slug, _, rels in seiten for rel in rels}
    namen = {slug: name for slug, name, _ in seiten}
    abschnitte = abschnitte_lesen(einsatz_zeilen(auswertung, einsaetze) if einsaetze else auswertung, seite_von)
    stadt = stadtgruppen(abschnitte, register)
    ms = standortgruppen_ms(abschnitte, stadt)
    mit = [a for a in abschnitte if a.get("geprueft")]
    je = collections.OrderedDict()
    for a in abschnitte:
        je.setdefault(a["schluessel"], []).append(abschnitt_ausgabe(a, stadt))
    nachgewiesen = collections.Counter()
    geprueft_v = collections.Counter()
    for a in abschnitte:
        for v in a.get("vorlagen") or []:
            geprueft_v[v["klasse"]] += 1
            nachgewiesen[v["klasse"]] += bool(v["nachgewiesen"])
    for k, s in stadt.items():
        s["vorlagen_geprueft"], s["vorlagen_nachgewiesen"] = geprueft_v[k], nachgewiesen[k]
        s["standorte"] = [{"seite": x, "name": namen.get(x, x)} for x in s["standorte"]]
        for v in s["effekte"].values():
            v.pop("_z", None)
    for lst in ms.values():
        for m_ in lst:
            m_.pop("_z", None)
    return {"erzeugt_von": "stadtgruppen.py aus den Modellen je Abschnitt (verhalten.py)" + (", Abschnitte der Einsätze (einsaetze.py)" if einsaetze else ""),
            "hinweis": "Forschungsstand, siehe docs/verhalten.md. Eigene Berechnung, ohne Gewähr. Wetter: Quelle: Deutscher Wetterdienst.",
            "klassen_namen": KLASSEN, "merkmale": MERKMALE, "profil_klassen_kmh": "2-km/h-Klassen ab 0 (0-2, 2-4, ..., 88-90, ab 90)",
            "uebersicht": {"abschnitte": len(abschnitte), "mit_modell": len(mit), "mit_mehreren_gruppen": sum(1 for a in mit if a["K"] > 1),
                           "placebo_mit_mehreren_gruppen": sum(1 for a in mit if (a.get("placebo") or {}).get("K", 1) > 1)},
            "stadt": list(stadt.values()), "standorte": ms, "abschnitte": je}


def register_schreiben(pfad, register, stadt):
    """Vorlagen und Verhalten der S-Gruppen ins Register; Arten ohne Eintrag bekommen eine neue, nie wiederverwendete ID."""
    eintraege = {g["klasse"]: g for g in register["gruppen"] if g.get("status", "aktiv") == "aktiv"}
    for s in stadt:
        if not s.get("vorlage"):
            continue
        g = eintraege.get(s["klasse"])
        if g is None and s["gefunden"]:
            b = TEMPOLAGE[s["klasse"]]
            n = register["naechste_nummer"].get(b, 1)
            register["naechste_nummer"][b] = n + 1
            g = {"id": f"S-{b}{n}", "klasse": s["klasse"], "status": "aktiv", "aufgenommen": dt.date.today().isoformat(),
                 "deutung": None, "stufe": None, "kriterien": None, "belege": []}
            register["gruppen"].append(g)
        if g is not None:
            g["vorlage"] = s["vorlage"]
            g["verhalten"] = s["verhalten"]
    with open(pfad, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("{\n" + ",\n".join(f' {json.dumps(k, ensure_ascii=False)}: ' + (
            "[\n" + ",\n".join("  " + json.dumps(g, ensure_ascii=False) for g in v) + "\n ]" if k == "gruppen" else json.dumps(v, ensure_ascii=False))
            for k, v in register.items()) + "\n}\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--auswertung", required=True, help="auswertung.json von dsd2csv.py")
    ap.add_argument("--metadaten", default=os.path.join(HIER, "belege", "metadaten.json"))
    ap.add_argument("--register", default=REGISTER)
    ap.add_argument("--register-schreiben", action="store_true", help="Vorlagen und Verhalten der S-Gruppen ins Register schreiben")
    ap.add_argument("-o", "--ausgabe", help="Ziel (Standard: verhaltensgruppen.json neben der auswertung.json)")
    ap.add_argument("--einsaetze", help="einsaetze.json (einsaetze.py; Standard: neben der auswertung.json, falls vorhanden): Gruppen der Einsätze")
    a = ap.parse_args()
    with open(a.auswertung, encoding="utf-8") as fh:
        auswertung = json.load(fh)
    with open(a.metadaten, encoding="utf-8") as fh:
        metadaten = json.load(fh)
    register = {"naechste_nummer": {}, "gruppen": []}
    if os.path.exists(a.register):
        with open(a.register, encoding="utf-8") as fh:
            register = json.load(fh)
    pfad_e = a.einsaetze or os.path.join(os.path.dirname(os.path.abspath(a.auswertung)), "einsaetze.json")
    einsaetze = None
    if os.path.exists(pfad_e):
        with open(pfad_e, encoding="utf-8") as fh:
            einsaetze = json.load(fh)
    out = ausgabe(auswertung, metadaten, register, einsaetze)
    ziel = a.ausgabe or os.path.join(os.path.dirname(os.path.abspath(a.auswertung)), "verhaltensgruppen.json")
    with open(ziel, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")
    u = out["uebersicht"]
    print(f'{u["mit_modell"]} von {u["abschnitte"]} Abschnitten mit Modell, {u["mit_mehreren_gruppen"]} mit mehreren Gruppen '
          f'(Placebo {u["placebo_mit_mehreren_gruppen"]}) -> {ziel}')
    for s in out["stadt"]:
        ges = ", ".join(f'{c} ×{v["faktor"]}' for c, v in s["effekte"].items() if v["gesichert"])
        print(f'  {s["anzeige"]}: {s["gruppen"]} Gruppen an {len(s["standorte"])} Standorten, gefunden={s["gefunden"]}, '
              f'Vorlagen {s["vorlagen_nachgewiesen"]}/{s["vorlagen_geprueft"]}; gesichert: {ges or "-"}')
        if not s["im_register"]:
            print(f'    neu, nicht im Register ({s["id"]}); mit --register-schreiben aufnehmen')
    if a.register_schreiben:
        register_schreiben(a.register, register, out["stadt"])
        print("Register geschrieben:", a.register)


if __name__ == "__main__":
    main()
