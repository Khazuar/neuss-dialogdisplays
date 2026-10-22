# SPDX-License-Identifier: MIT
"""Brueche zuordnen und Einsaetze bilden (docs/einsaetze.md).

Begriffe: Eine Messung ist eine Datei der Verwaltung (Standort, Fahrtrichtung, Zeitraum, wie geliefert). Ein Abschnitt ist ein zeitlicher
Bereich einer Messung mit aehnlichen Daten, ein Bruch die Grenze zwischen zwei Abschnitten (bruch.py). Ein Einsatz ist der Zeitraum, in dem ein
Geraet tatsaechlich an einem Standort in eine Fahrtrichtung gemessen hat; er besteht aus Abschnitten, auch aus Abschnitten anderer Messungen
desselben Geraets (zusammengesetzte Abschnitte).

Zuordnung eines Bruchs, in dieser Rangfolge:
  1. Angabe der Verwaltung (belege/brueche-verwaltung.json): bestaetigt.
  2. Umhaengen belegt: Der Abschnitt vor dem Bruch gleicht dem letzten Abschnitt der Vorgaenger-Messung desselben Geraets an einem anderen
     Standort (oder spiegelbildlich der Abschnitt nach dem letzten Bruch dem ersten Abschnitt des Nachfolgers): Geschwindigkeitsverteilung und
     Tagesgang innerhalb des Rauschens, Verkehrsmenge passend, aehnlicher als fast alle anderen Abschnitte gleichen Tempolimits (Nulltest),
     Gegenprobe (der Abschnitt auf der anderen Seite des Bruchs gleicht dem Vorgaenger nicht), stetige Naht, sicherer Bruch.
  3. Ereignis: erster Schultag nach Ferien, Beginn oder Ende eines laenger dauernden Ereignisses am Standort oder stadtweit
     (belege/ereignisse.json). Kurze Ereignisse (Feste) werden nur als zeitliche Naehe genannt.
  4. Umhaengen moeglich (schwaechere Kriterien): nur Hinweis.
  5. Unerklaert: fuer die Nachfrage bei der Verwaltung.
Nur belegte oder bestaetigte Zuordnungen veraendern die Einsaetze; der Bruchtag und der Tag davor (Umhaengen, Transport, Montage) gehoeren
dann zu keinem Einsatz.

Grundlage ist das Aggregat je Datei (aggregat.py: Fahrzeuge je Stunde und km/h, nur nutzbare Zeit, Rauschboden abgezogen). Reines Python.
Aufruf: python3 -I einsaetze.py --auswertung _vorschau/auswertung.json --aggregat _vorschau-aggregat
"""
import argparse
import bisect
import collections
import datetime as dt
import json
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import dsd2csv  # noqa: E402
import gruppen  # noqa: E402
import kalender  # noqa: E402
import seiten_bauen  # noqa: E402

KMIN, KMAX = 15, 100            # Geschwindigkeiten fuer den Vergleich (darunter Fussgaenger, Rauschboden)
MIN_FAHRZEUGE = 1500            # kleinere Abschnitte werden nicht verglichen
RAUSCHEN_MIN = (0.015, 0.02)    # Untergrenzen des Rauschens (Verteilung, Tagesgang)
FOLGE_TAGE = 3                  # Ende des Vorgaengers hoechstens so viele Tage neben dem Beginn der Messung
VERHAELTNIS = (0.7, 1.4)        # Fahrzeuge je Stunde, Abschnitt gegen Vergleich
SCORE_BELEGT, SCORE_MOEGLICH = 1.15, 1.5
P_BELEGT, P_MOEGLICH = 0.05, 0.10
NULL_MIN = 20                   # so viele Vergleichsabschnitte gleichen Limits braucht der Nulltest, sonst alle Limits
GEGENPROBE = 3.0                # Score, ab dem der Abschnitt auf der anderen Seite des Bruchs dem Vorgaenger nicht gleicht
BRUCH_P = 0.9
NAHT_TAGE, NAHT_SCORE, NAHT_MIN = 7, 2.0, 300
EREIGNIS_TAGE = 1               # Bruchtag hoechstens so weit neben Beginn oder Ende eines Ereignisses
STUNDE = dt.timedelta(hours=1)
TAG = dt.timedelta(days=1)
ISO_UTC = "%Y-%m-%dT%H:00Z"


# ------------------------------------------------------------------ Daten je Messung

def stunden_lesen(agg):
    """(Zeilen, vollstaendig aufgezeichnete Stunden) aus einem Aggregat. Zeile: (Datum, Stunde, voll, Regenklasse, Counter km/h -> Anzahl);
    vollstaendig: [(Datum, Stunde)] in Ortszeit, auch Stunden ohne Fahrzeug (zwischen erster und letzter Stunde, ausser den Luecken)."""
    zeilen, utc = [], []
    for d, h, off, _nr, voll, klasse, flach in agg.get("stunden") or []:
        datum = dt.date.fromisoformat(d)
        zeilen.append((datum, h, voll, klasse, collections.Counter(dict(zip(flach[0::2], flach[1::2])))))
        utc.append(dt.datetime(datum.year, datum.month, datum.day, h) - dt.timedelta(hours=off))
    if not utc:
        return zeilen, []
    luecke = set()
    for a, _b, n in agg.get("luecken") or []:
        t = dt.datetime.strptime(a, ISO_UTC)
        for i in range(n):
            luecke.add(t + i * STUNDE)
    voll, h, ende = [], min(utc), max(utc)
    while h <= ende:
        if h not in luecke:
            lokal = h + dt.timedelta(hours=dsd2csv.utc_versatz_h(h))
            voll.append((lokal.date(), lokal.hour))
        h += STUNDE
    return zeilen, voll


def messungen_lesen(auswertung, metadaten, aggregat_ordner):
    """Eine Beschreibung je Messung (Datei) mit Abschnitten, Bruechen und den Stunden des Aggregats."""
    seite = {}
    for slug, name, rels in seiten_bauen.standortgruppen(auswertung, metadaten):
        for rel in rels:
            seite[rel] = (slug, name)
    out = []
    for r in auswertung["standorte"]:
        rel, datei = r["standort"], r["datei"]
        meta = next((m for m in ((metadaten.get("standorte") or {}).get(rel) or {}).get("messungen", []) if m["datei"] == datei), {})
        pfad = os.path.join(aggregat_ordner, rel.replace("/", os.sep), os.path.splitext(datei)[0] + ".aggregat.json")
        agg = {}
        if os.path.exists(pfad):
            with open(pfad, encoding="utf-8") as fh:
                agg = json.load(fh)
        zeilen, voll = stunden_lesen(agg)
        liste = (r.get("abschnitte") or {}).get("liste") or []
        brueche = [(a["nr"], dt.date.fromisoformat(a["beginn"]["datum"]), a["beginn"].get("wahrscheinlichkeit"))
                   for a in liste if (a.get("beginn") or {}).get("art") == "Bruch"]
        tage = sorted({z[0] for z in zeilen})
        out.append({
            "id": seiten_bauen.messung_id(rel, datei), "rel": rel, "datei": datei, "geraet": (r.get("geraet") or "").strip(),
            "limit": r.get("tempolimit_kmh"), "seite": seite.get(rel, (None, rel))[0], "name": seite.get(rel, (None, rel))[1],
            "fahrtrichtung": ", ".join(seiten_bauen.fahrtrichtungen(meta, rel)),
            "uhr_nutzbar": (r.get("uhr") or {}).get("nutzbarkeit") == "nutzbar", "brueche": brueche,
            "grenzen": [b[1] for b in brueche], "zeilen": zeilen, "voll": voll,
            "von": tage[0] if tage else None, "bis": tage[-1] if tage else None,
        })
    return out


def abschnitte_der_messung(m):
    """[(Nr, von, bis)] der Abschnitte einer Messung (Datumsbereiche, einschliesslich), aus den Bruechen."""
    if not m["von"]:
        return [(1, None, None)]
    grenzen = m["grenzen"]
    out, von = [], m["von"]
    for i, g in enumerate(grenzen):
        out.append((i + 1, von, g - TAG))
        von = g
    out.append((len(grenzen) + 1, von, m["bis"]))
    return out


# ------------------------------------------------------------------ Merkmale und Abstand

def merkmale(zeilen, voll, von, bis):
    """Merkmale eines Datumsbereichs aus vollstaendig aufgezeichneten Stunden: Verteilung (KMIN bis KMAX-1), Tagesgang (Stunde x Werktag/Wochenende),
    beides auch getrennt nach geraden und ungeraden Tagen (Rauschen), Fahrzeuge und Stunden. None ohne Fahrzeuge."""
    nb = KMAX - KMIN
    hv, hp = [0.0] * nb, [0.0] * 48
    hva, hvb, hpa, hpb = [0.0] * nb, [0.0] * nb, [0.0] * 48, [0.0] * 48
    n = 0
    for datum, h, ist_voll, _k, c in zeilen:
        if not ist_voll or datum < von or datum > bis:
            continue
        p = (24 if datum.weekday() >= 5 else 0) + h
        gerade = datum.toordinal() % 2 == 0
        for v, a in c.items():
            if KMIN <= v < KMAX:
                hv[v - KMIN] += a
                hp[p] += a
                (hva if gerade else hvb)[v - KMIN] += a
                (hpa if gerade else hpb)[p] += a
                n += a
    stunden = sum(1 for d, _ in voll if von <= d <= bis)
    if not n or not stunden:
        return None
    return {"v": norm(hv), "p": norm(hp), "rausch_v": tvd(norm(hva), norm(hvb)), "rausch_p": tvd(norm(hpa), norm(hpb)),
            "n": n, "stunden": stunden, "je_stunde": n / stunden}


def norm(x):
    s = sum(x)
    return [a / s for a in x] if s else x


def tvd(a, b):
    return 0.5 * sum(abs(x - y) for x, y in zip(a, b))


def score(a, b, rauschen_aus=None):
    """Mittel aus Abstand der Verteilungen und der Tagesgaenge, jeweils durch das groessere Rauschen beider (oder von rauschen_aus) geteilt."""
    r = rauschen_aus or (a, b)
    nv = max(max(x["rausch_v"] for x in r), RAUSCHEN_MIN[0])
    npf = max(max(x["rausch_p"] for x in r), RAUSCHEN_MIN[1])
    return 0.5 * (tvd(a["v"], b["v"]) / nv + tvd(a["p"], b["p"]) / npf)


def verhaeltnis(a, b):
    return a["je_stunde"] / b["je_stunde"] if b["je_stunde"] else float("inf")


def passt_menge(q):
    return VERHAELTNIS[0] <= q <= VERHAELTNIS[1]


# ------------------------------------------------------------------ Umhaengen

def kandidaten(messungen):
    """Paare (Vorgaenger, Messung) desselben Geraets an verschiedenen Standorten, unmittelbar nacheinander, beide mit nutzbarer Uhr."""
    je_geraet = collections.defaultdict(list)
    for m in messungen:
        if m["geraet"] and m["von"] and m["uhr_nutzbar"]:
            je_geraet[m["geraet"]].append(m)
    out = []
    for liste in je_geraet.values():
        liste.sort(key=lambda m: (m["von"], m["bis"]))
        for y, x in zip(liste, liste[1:]):
            if y["seite"] != x["seite"] and abs((x["von"] - y["bis"]).days) <= FOLGE_TAGE:
                out.append((y, x))
    return out


def pruefe_umhaengen(y, x, richtung, alle_abschnitte, abschnitt_merkmale):
    """Pruefung einer Zuordnung. richtung 'vorgaenger': der erste Abschnitt von x stammt vom Standort y; 'nachfolger': der letzte Abschnitt
    von y stammt vom Standort x. Gibt ein dict mit Belegen und Stufe zurueck oder None, wenn es nichts zu pruefen gibt."""
    ax, ay = abschnitte_der_messung(x), abschnitte_der_messung(y)
    if richtung == "vorgaenger":
        if len(ax) < 2:
            return None
        quelle, probe, andere, bruch_m, bruch_nr = (y["id"], ay[-1][0]), (x["id"], 1), (x["id"], 2), x, 2
    else:
        if len(ay) < 2:
            return None
        quelle, probe, andere, bruch_m, bruch_nr = (x["id"], 1), (y["id"], ay[-1][0]), (y["id"], ay[-1][0] - 1), y, ay[-1][0]
    fq, fp, fa = abschnitt_merkmale.get(quelle), abschnitt_merkmale.get(probe), abschnitt_merkmale.get(andere)
    if not fq or not fp:
        return None
    s = score(fp, fq)
    q = verhaeltnis(fp, fq)
    # Nulltest: wie viele Abschnitte anderer Standorte gleichen der Quelle mindestens so gut (gleiches Tempolimit, sonst alle)?
    lim = (y if richtung == "vorgaenger" else x)["limit"]
    ausgenommen = {y["seite"], x["seite"]}
    vergleich = [(k, f) for k, f in abschnitt_merkmale.items() if alle_abschnitte[k]["seite"] not in ausgenommen]
    gleich = [(k, f) for k, f in vergleich if alle_abschnitte[k]["limit"] == lim]
    null = gleich if len(gleich) >= NULL_MIN else vergleich
    treffer = sum(1 for _, f in null if score(f, fq) <= s and passt_menge(verhaeltnis(f, fq)))
    p = (1 + treffer) / (1 + len(null))
    gegen = score(fa, fq) if fa else None
    bruch_p = next((b[2] for b in bruch_m["brueche"] if b[0] == bruch_nr), None)
    bruchtag = next((b[1] for b in bruch_m["brueche"] if b[0] == bruch_nr), None)
    naht = None
    mq, mp = (y, x) if richtung == "vorgaenger" else (x, y)  # Quelle/Probe-Messung
    if richtung == "vorgaenger":
        a = merkmale(mq["zeilen"], mq["voll"], mq["bis"] - (NAHT_TAGE - 1) * TAG, mq["bis"])
        b = merkmale(mp["zeilen"], mp["voll"], mp["von"], mp["von"] + (NAHT_TAGE - 1) * TAG)
    else:
        a = merkmale(mq["zeilen"], mq["voll"], mq["von"], mq["von"] + (NAHT_TAGE - 1) * TAG)
        b = merkmale(mp["zeilen"], mp["voll"], mp["bis"] - (NAHT_TAGE - 1) * TAG, mp["bis"])
    if a and b and a["n"] >= NAHT_MIN and b["n"] >= NAHT_MIN:
        ns = score(b, a)  # Rauschen der beiden Fenster selbst (7 Tage rauschen staerker als ganze Abschnitte)
        naht = {"score": round(ns, 2), "verhaeltnis": round(verhaeltnis(b, a), 2), "stetig": ns <= NAHT_SCORE and passt_menge(verhaeltnis(b, a))}
    belegt = (s <= SCORE_BELEGT and passt_menge(q) and p <= P_BELEGT and gegen is not None and gegen > GEGENPROBE
              and (bruch_p or 0) >= BRUCH_P and (naht is None or naht["stetig"]))
    moeglich = s <= SCORE_MOEGLICH and passt_menge(q) and p <= P_MOEGLICH
    return {"richtung": richtung, "von_messung": quelle[0], "von_abschnitt": quelle[1], "abschnitt_messung": probe[0], "abschnitt": probe[1],
            "bruch_messung": bruch_m["id"], "bruch_nr": bruch_nr, "bruchtag": bruchtag.isoformat() if bruchtag else None,
            "bruch_wahrscheinlichkeit": bruch_p, "score": round(s, 2), "tvd_verteilung": round(tvd(fp["v"], fq["v"]), 3),
            "tvd_tagesgang": round(tvd(fp["p"], fq["p"]), 3), "rauschen": [round(max(fp["rausch_v"], fq["rausch_v"]), 3),
                                                                          round(max(fp["rausch_p"], fq["rausch_p"]), 3)],
            "verhaeltnis_fahrzeuge": round(q, 2), "p_nulltest": round(p, 3), "nulltest_abschnitte": len(null),
            "nulltest_gleiches_limit": null is gleich, "gegenprobe_score": round(gegen, 2) if gegen is not None else None, "naht": naht,
            "stufe": "belegt" if belegt else "moeglich" if moeglich else "keine"}


# ------------------------------------------------------------------ Ereignisse

def ereignisse_laden(pfad):
    if not pfad or not os.path.exists(pfad):
        return []
    with open(pfad, encoding="utf-8") as fh:
        return json.load(fh).get("ereignisse", [])


def ereignis_kandidaten(tag, seite, ereignisse):
    """Ereignisse, die zu einem Bruchtag passen: erster Schultag nach Ferien bzw. erster Ferientag (Erklaerung), Beginn oder Ende eines
    dauerhaften Ereignisses (Erklaerung), kurze Ereignisse in der Naehe (nur Hinweis), Feiertag am Bruchtag (Hinweis)."""
    out = []
    for beginn, ende, name in kalender.SCHULFERIEN_NRW:
        b, e = dt.date.fromisoformat(beginn), dt.date.fromisoformat(ende)
        schultag = e + TAG
        while schultag.weekday() >= 5 or kalender.feiertag(schultag):
            schultag += TAG
        if abs((tag - schultag).days) <= EREIGNIS_TAGE:
            out.append({"art": "ferienende", "name": f"Ende der {name} (erster Schultag {schultag.isoformat()})", "erklaerung": True})
        if abs((tag - b).days) <= EREIGNIS_TAGE:
            out.append({"art": "ferienbeginn", "name": f"Beginn der {name} ({b.isoformat()})", "erklaerung": True})
    for d in (tag - TAG, tag, tag + TAG):
        if kalender.feiertag(d):
            out.append({"art": "feiertag", "name": f"Feiertag am {d.isoformat()}", "erklaerung": False})
    for e in ereignisse:
        if e.get("ort") and e["ort"] != seite:
            continue
        von, bis = dt.date.fromisoformat(e["von"]), dt.date.fromisoformat(e["bis"])
        if e.get("art") == "dauerhaft":
            if abs((tag - von).days) <= EREIGNIS_TAGE or abs((tag - (bis + TAG)).days) <= EREIGNIS_TAGE:
                out.append({"art": "ereignis", "name": e["name"], "quelle": e.get("quelle"), "erklaerung": True})
        elif von - EREIGNIS_TAGE * TAG <= tag <= bis + (EREIGNIS_TAGE + 1) * TAG:
            out.append({"art": "kurz", "name": e["name"], "quelle": e.get("quelle"), "erklaerung": False})
    return out


# ------------------------------------------------------------------ Zuordnung aller Brueche

def verwaltung_laden(pfad):
    if not pfad or not os.path.exists(pfad):
        return {}
    with open(pfad, encoding="utf-8") as fh:
        return {(e["messung"], e["bruch"]): e for e in json.load(fh).get("brueche", [])}


def zuordnen(messungen, ereignisse=(), verwaltung=None):
    """(Brueche mit Zuordnung, Umhaengungen fuer die Einsaetze). Umhaengung: dict mit von_messung, abschnitt_messung, abschnitt, nach (Messung,
    deren Einsatz den Abschnitt bekommt), ausgenommene Tage, Stufe."""
    verwaltung = verwaltung or {}
    nach_id = {m["id"]: m for m in messungen}
    alle, merk = {}, {}
    for m in messungen:
        for nr, von, bis in abschnitte_der_messung(m):
            if von is None:
                continue
            alle[(m["id"], nr)] = m
            f = merkmale(m["zeilen"], m["voll"], von, bis)
            if f and f["n"] >= MIN_FAHRZEUGE:
                merk[(m["id"], nr)] = f
    pruefungen = collections.defaultdict(list)  # (Messung, Bruch-Nr) -> Pruefungen
    vorgaenger_paare = {}  # (Abschnitt der Quelle, Abschnitt der Probe) -> Pruefung in Richtung Vorgaenger
    for y, x in kandidaten(messungen):
        for richtung in ("vorgaenger", "nachfolger"):
            erg = pruefe_umhaengen(y, x, richtung, alle, merk)
            if not erg:
                continue
            if richtung == "vorgaenger":
                vorgaenger_paare[((erg["von_messung"], erg["von_abschnitt"]), (erg["abschnitt_messung"], erg["abschnitt"]))] = erg
            pruefungen[(erg["bruch_messung"], erg["bruch_nr"])].append(erg)
    # Dasselbe Paar in beiden Richtungen zeigt nur, dass beide Abschnitte zu einem Einsatz gehoeren. Die Lesart "Vorgaenger" (das Geraet hing nach
    # dem Auslesen noch am alten Ort) hat Vorrang, wenn sie mindestens moeglich ist; die Gegenlesung "Nachfolger" wird dann zurueckgestellt.
    for liste in pruefungen.values():
        for e in liste:
            if e["richtung"] == "nachfolger":
                gegen = vorgaenger_paare.get(((e["abschnitt_messung"], e["abschnitt"]), (e["von_messung"], e["von_abschnitt"])))
                if gegen and gegen["stufe"] in ("belegt", "moeglich") and e["stufe"] != "keine":
                    e["stufe_ohne_vorrang"], e["stufe"] = e["stufe"], "zurueckgestellt"
                    e["grund"] = (f'dasselbe Abschnittspaar ist als Vorgänger-Zuordnung beim Bruch vom {gegen["bruchtag"]} '
                                  f'({gegen["stufe"]}) erklärt; diese Lesart hat Vorrang')
    alle_tage = collections.defaultdict(list)
    for m in messungen:
        for nr, tag, _p in m["brueche"]:
            alle_tage[tag].append(m["id"])
    brueche, umhaengen = [], []
    for m in messungen:
        for nr, tag, p in m["brueche"]:
            schluessel = f'{m["rel"]}/{m["datei"]}'
            pr = sorted(pruefungen.get((m["id"], nr), []), key=lambda e: e["score"])
            ev = ereignis_kandidaten(tag, m["seite"], ereignisse)
            v = verwaltung.get((schluessel, tag.isoformat()))
            gleich = sorted({i for d in (tag - TAG, tag, tag + TAG) for i in alle_tage.get(d, []) if i != m["id"]})
            belegt = [e for e in pr if e["stufe"] == "belegt"]
            moeglich = [e for e in pr if e["stufe"] == "moeglich"]
            if v:
                zu = {"art": v.get("art", "verwaltung"), "stufe": "bestaetigt", "text": v.get("erklaerung", ""), "quelle": v.get("quelle")}
            elif belegt:
                zu = {"art": "umhaengen", "stufe": "belegt", "text": _text_umhaengen(belegt[0], nach_id)}
            elif any(e["erklaerung"] for e in ev):
                zu = {"art": "ereignis", "stufe": "plausibel", "text": "; ".join(e["name"] for e in ev if e["erklaerung"])}
            elif moeglich:
                zu = {"art": "umhaengen", "stufe": "moeglich", "text": _text_umhaengen(moeglich[0], nach_id)}
            else:
                zu = {"art": "unerklaert", "stufe": "offen", "text": ""}
            brueche.append({"messung": m["id"], "rel": m["rel"], "datei": m["datei"], "seite": m["seite"], "name": m["name"], "nr": nr,
                            "datum": tag.isoformat(), "wahrscheinlichkeit": p, "zuordnung": zu, "umhaengen": pr, "ereignisse": ev,
                            "gleicher_tag": gleich, "verwaltung": v})
            wahl = None
            if v and v.get("art") == "umhaengen" and v.get("abschnitt_von"):
                kand = [e for e in pr if e["von_messung"] == v["abschnitt_von"]] or pr
                wahl = dict(kand[0], stufe="bestaetigt") if kand else None
                if wahl and v.get("ausgenommen"):
                    wahl["ausgenommen_bestaetigt"] = v["ausgenommen"]
            elif belegt and not v:
                wahl = belegt[0]
            if wahl:
                umhaengen.append(wahl)
    return brueche, umhaengen


def _text_umhaengen(e, nach_id):
    q = nach_id[e["von_messung"]]
    if e["richtung"] == "vorgaenger":
        return (f'Abschnitt {e["abschnitt"]} gleicht dem letzten Abschnitt der vorigen Messung desselben Geräts ({q["name"]}, {q["datei"]}): '
                f'Score {e["score"]}, Nulltest p = {e["p_nulltest"]}')
    return (f'Abschnitt {e["abschnitt"]} gleicht dem ersten Abschnitt der folgenden Messung desselben Geräts ({q["name"]}, {q["datei"]}): '
            f'Score {e["score"]}, Nulltest p = {e["p_nulltest"]}')


# ------------------------------------------------------------------ Einsaetze

def einsaetze_bilden(messungen, umhaengen):
    """Einsaetze: je Messung einer, mit ihren eigenen Abschnitten, ohne abgegebene und mit hinzugekommenen; Umhaengtage (Bruchtag und Vortag,
    bei Bestaetigung die bestaetigten Tage) fallen heraus. Teil: (Messung, Abschnitt, von, bis, Herkunft, Stufe)."""
    nach_id = {m["id"]: m for m in messungen}
    weg, dazu, ausgenommen = set(), collections.defaultdict(list), collections.defaultdict(set)
    for u in umhaengen:
        teil = (u["abschnitt_messung"], u["abschnitt"])
        ziel = u["von_messung"]
        weg.add(teil)
        dazu[ziel].append((teil, u))
        tag = dt.date.fromisoformat(u["bruchtag"])
        tage = ({dt.date.fromisoformat(d) for d in u["ausgenommen_bestaetigt"]} if u.get("ausgenommen_bestaetigt")
                else {tag - TAG, tag})
        ausgenommen[u["bruch_messung"]] |= tage
    out = []
    for m in messungen:
        teile = []
        for nr, von, bis in abschnitte_der_messung(m):
            if (m["id"], nr) not in weg:
                teile.append({"messung": m["id"], "abschnitt": nr, "von": von, "bis": bis, "herkunft": "eigen", "stufe": None})
        for (mid, nr), u in dazu.get(m["id"], []):
            q = nach_id[mid]
            von, bis = next((a[1], a[2]) for a in abschnitte_der_messung(q) if a[0] == nr)
            beleg = {k: u.get(k) for k in ("bruch_messung", "bruch_nr", "bruchtag", "bruch_wahrscheinlichkeit", "score", "tvd_verteilung", "tvd_tagesgang",
                                          "rauschen", "verhaeltnis_fahrzeuge", "p_nulltest", "nulltest_abschnitte", "gegenprobe_score", "naht")}
            teile.append({"messung": mid, "abschnitt": nr, "von": von, "bis": bis, "herkunft": u["richtung"], "stufe": u["stufe"], "beleg": beleg})
        aus = set()
        for t in teile:  # Umhaengtage abschneiden
            weg_tage = ausgenommen.get(t["messung"], set())
            if t["von"] is None:
                continue
            while t["von"] in weg_tage and t["von"] <= t["bis"]:
                aus.add(t["von"])
                t["von"] += TAG
            while t["bis"] in weg_tage and t["bis"] >= t["von"]:
                aus.add(t["bis"])
                t["bis"] -= TAG
        teile = [t for t in teile if t["von"] is None or t["von"] <= t["bis"]]
        teile.sort(key=lambda t: (t["von"] or dt.date.min))
        fremd = [t for t in teile if t["herkunft"] != "eigen"]
        abgegeben = [(mid, nr) for (mid, nr) in weg if mid == m["id"]]
        status = ("bestaetigt" if fremd and all(t["stufe"] == "bestaetigt" for t in fremd) else "abgeleitet" if fremd
                  else "gekuerzt" if abgegeben else "identisch")
        datiert = [t for t in teile if t["von"]]
        out.append({"id": "e-" + m["id"][2:], "messung": m["id"], "seite": m["seite"], "name": m["name"], "fahrtrichtung": m["fahrtrichtung"],
                    "geraet": m["geraet"], "limit": m["limit"], "status": status,
                    "von": min(t["von"] for t in datiert).isoformat() if datiert else None,
                    "bis": max(t["bis"] for t in datiert).isoformat() if datiert else None,
                    "teile": [dict(t, von=t["von"].isoformat() if t["von"] else None, bis=t["bis"].isoformat() if t["bis"] else None)
                              for t in teile],
                    "abgegeben": [{"abschnitt": nr, "an": "e-" + next(u["von_messung"] for u in umhaengen
                                                                   if (u["abschnitt_messung"], u["abschnitt"]) == (mid, nr))[2:]}
                                  for mid, nr in sorted(abgegeben)],
                    "ausgenommene_tage": sorted(d.isoformat() for d in aus)})
    return out


def _fahrzeuge(m, von, bis, nur_voll=False):
    """Fahrzeuge [(Ortszeit, v)] eines Datumsbereichs aus dem Aggregat (Zeit: Mitte der Stunde)."""
    out = []
    for datum, h, voll, _k, c in m["zeilen"]:
        if von <= datum <= bis and (voll or not nur_voll):
            t = dt.datetime(datum.year, datum.month, datum.day, h, 30)
            for v, a in c.items():
                out.extend([(t, v)] * a)
    return out


def _zusatz(lim):
    def zusatz(vehs, abged=None):  # wie dsd2csv.rechnen: Histogramm, Raten, Gefaehrdung, Laerm
        r = dsd2csv.raten(vehs, lim, abged) if abged else None
        return {k: x for k, x in (("histogramm", dsd2csv.histogramm(vehs)), ("raten", r), ("gefaehrdung", dsd2csv.gefaehrdung(vehs, lim, abged)),
                                  ("laerm", dsd2csv.laerm(vehs, lim, abged))) if x}
    return zusatz


def _zellen(teile, nach_id):
    """Zellen (Tagschluessel x Stunde) wie gruppen.zellen_bauen aus den Teilen eines Einsatzes, dazu nur trockene Stunden."""
    def bauen(nur_trocken):
        D, z = collections.Counter(), collections.defaultdict(collections.Counter)
        for t in teile:
            m = nach_id[t["messung"]]
            von, bis = dt.date.fromisoformat(t["von"]), dt.date.fromisoformat(t["bis"])
            trocken = {(d, h) for d, h, voll, k, _c in m["zeilen"] if k == 0} if nur_trocken else None
            for d, h in m["voll"]:
                if von <= d <= bis and (trocken is None or (d, h) in trocken):
                    D[(gruppen.tagschluessel(dt.datetime(d.year, d.month, d.day)), h)] += 1
            for d, h, voll, k, c in m["zeilen"]:
                if voll and von <= d <= bis and (not nur_trocken or k == 0):
                    z[(gruppen.tagschluessel(dt.datetime(d.year, d.month, d.day)), h)].update(c)
        return {"D": D, "z": z, "r": {}}
    return bauen(False), bauen(True)


def kennzahlen_einsatz(e, nach_id):
    """Kennzahlen eines Einsatzes wie in der YAML (Block bereinigt, teilzeitraeume) und die Datentabelle der Detailseite (je Teil ein Abschnitt)."""
    teile = [t for t in e["teile"] if t["von"]]
    if not teile:
        return None, None
    lim = e["limit"]
    vehs, abged = [], set()
    for t in teile:
        m = nach_id[t["messung"]]
        von, bis = dt.date.fromisoformat(t["von"]), dt.date.fromisoformat(t["bis"])
        vehs += _fahrzeuge(m, von, bis)
        abged |= {(d, h) for d, h in m["voll"] if von <= d <= bis}
    teil = {k: [f for f in vehs if in_zeitraum(f[0])] for k, (_, in_zeitraum) in dsd2csv.TEILZEITRAEUME.items()}
    block, teilzeitraeume = dsd2csv.kennzahlen_je_zeitraum(vehs, teil, lim, 0, _zusatz(lim), abged)
    alle, trocken = _zellen(teile, nach_id)
    daten = gruppen.datentabelle(alle, lim)
    if daten:
        if any(trocken["z"].values()):
            daten["trocken"] = gruppen.zellen_json(trocken)
        if len(teile) > 1:
            liste = []
            for i, t in enumerate(teile):
                a, tr = _zellen([t], nach_id)
                if any(a["z"].values()):
                    d = {"nr": i + 1, "von": t["von"], "bis": t["bis"], **gruppen.zellen_json(a)}
                    if any(tr["z"].values()):
                        d["trocken"] = gruppen.zellen_json(tr)
                    liste.append(d)
            daten["abschnitte"] = liste
    return {"bereinigt": block, "teilzeitraeume": teilzeitraeume}, daten


# ------------------------------------------------------------------ Ausgabe

def auswerten(auswertung, metadaten, aggregat_ordner, ereignisse_pfad=None, verwaltung_pfad=None):
    messungen = messungen_lesen(auswertung, metadaten, aggregat_ordner)
    brueche, umh = zuordnen(messungen, ereignisse_laden(ereignisse_pfad), verwaltung_laden(verwaltung_pfad))
    einsaetze = einsaetze_bilden(messungen, umh)
    nach_id = {m["id"]: m for m in messungen}
    zellen = {}
    for e in einsaetze:
        if e["status"] != "identisch":  # identische Einsaetze zeigen die Kennzahlen der Messung
            e["kennzahlen"], zellen[e["id"]] = kennzahlen_einsatz(e, nach_id)
    zaehlung = collections.Counter(b["zuordnung"]["art"] + "/" + b["zuordnung"]["stufe"] for b in brueche)
    return {"einsaetze": einsaetze, "brueche": brueche, "zaehlung": dict(zaehlung)}, zellen


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--auswertung", required=True, help="auswertung.json von dsd2csv.py")
    ap.add_argument("--aggregat", required=True, help="Ordner der Aggregate (dsd2csv.py --aggregat)")
    ap.add_argument("--metadaten", default=os.path.join(HIER, "belege", "metadaten.json"))
    ap.add_argument("--ereignisse", default=os.path.join(HIER, "belege", "ereignisse.json"))
    ap.add_argument("--verwaltung", default=os.path.join(HIER, "belege", "brueche-verwaltung.json"))
    ap.add_argument("-o", "--ausgabe", help="Ziel (Standard: einsaetze.json neben der auswertung.json; die Zellen in einsaetze-zellen.json)")
    a = ap.parse_args()
    with open(a.auswertung, encoding="utf-8") as fh:
        auswertung = json.load(fh)
    with open(a.metadaten, encoding="utf-8") as fh:
        metadaten = json.load(fh)
    out, zellen = auswerten(auswertung, metadaten, a.aggregat, a.ereignisse, a.verwaltung)
    ziel = a.ausgabe or os.path.join(os.path.dirname(os.path.abspath(a.auswertung)), "einsaetze.json")
    with open(ziel, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")
    with open(os.path.join(os.path.dirname(ziel), "einsaetze-zellen.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(zellen, fh, ensure_ascii=False, separators=(",", ":"))
    st = collections.Counter(e["status"] for e in out["einsaetze"])
    print(f'{len(out["einsaetze"])} Einsätze ({", ".join(f"{k} {v}" for k, v in sorted(st.items()))}), {len(out["brueche"])} Brüche: '
          + ", ".join(f"{k} {v}" for k, v in sorted(out["zaehlung"].items())) + f" -> {ziel}")


if __name__ == "__main__":
    main()
