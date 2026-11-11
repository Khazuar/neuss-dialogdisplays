# SPDX-License-Identifier: MIT
"""Einsaetze bilden: Aufenthalte der Geraete den Messungen zuordnen und Brueche erklaeren (docs/einsaetze.md).

Begriffe: Eine Messung ist eine Datei der Verwaltung (Standort, Fahrtrichtung, Zeitraum, wie geliefert). Ein Einsatz ist der Zeitraum, in dem
ein Geraet tatsaechlich an einem Standort in eine Fahrtrichtung gemessen hat. Grundlage ist der Gesamtstrom je Geraet (bewegungen.py): alle
Dateien zusammen, mit rekonstruierten Uhren, zerlegt an den Bewegungen (Umhaengen, Inbetriebnahme) in Aufenthalte und diese an den Bruechen
in Teile.

1. Zuordnung: Jedes Teil gehoert zu einer Messung desselben Geraets oder zu keiner. Die Reihenfolge der Messungen (nach dem ersten Fahrzeug
   ihrer Datei im Gesamtstrom) gilt als richtig; jede Messung bekommt einen zusammenhaengenden Block von Teilen (auch keinen). Punkte je Paar
   (Teil, Messung):
     datei       Anteil der Tage des Teils in der Datei der Messung x GEWICHT_DATEI x Groesse (Tage / VOLL_TAGE, hoechstens 1). Nach dem
                 Muster "erst auslesen, dann umhaengen" beginnt eine Datei oft noch am vorigen Standort; der Anteil ist ein Hinweis, kein Beweis.
     zeitraum    Anteil des Teils im Erfassungszeitraum der Mitteilung (belege/korrekturen.json) x GEWICHT_ZEITRAUM, ohne Ueberlappung -1;
                 Beginn oder Ende auf +-1 Tag gleich: je +1.
     tempolimit  V85 passt nicht zum Limit der Messung (Limit ab 50: V85 unter 35; Limit bis 30: V85 ueber Limit + 20): -1.
     keine       Teil keiner Messung zugeordnet: STRAFE_KEINE x Groesse.
   Zwischen zwei aufeinanderfolgenden Teilen: verschiedene Aufenthalte in derselben Messung, die sich deutlich unterscheiden (TVD der
   Tempoverteilung ueber MAX_TVD oder Verkehrsmenge ausserhalb VERHAELTNIS): STRAFE_UNAEHNLICH; derselbe Aufenthalt in verschiedenen
   Messungen (Ortswechsel an einem Bruch ohne erkannte Bewegung): STRAFE_OHNE_BEWEGUNG. Je Messung, deren Datei Daten im Gesamtstrom hat, die
   aber kein Teil bekommt: STRAFE_LEER (die Verwaltung hat dort gemessen).
   Loesung: dynamische Programmierung. Sicherheit je Teil: Abstand der besten Loesung zur besten, in der das Teil woanders hingehoert
   (sicher ab SICHER_AB).
2. Einsaetze: je Messung einer aus ihren Teilen; jedes Teil ist ein Einsatz-Abschnitt. Grenzen: Bewegung (minutengenau; die Luecke gehoert
   zu keinem Einsatz), Bruch (bleibt im Einsatz: Ereignis oder unerklaert) oder Ortswechsel ohne Bewegung (Bruchtag und Vortag gehoeren zu
   keinem Einsatz). Teile, die keiner Messung zugeordnet sind, sind "nicht beruecksichtigt".
3. Brueche der Messungen (dsd2csv.py), Zuordnung in dieser Rangfolge: Angabe der Verwaltung (belege/brueche-verwaltung.json), Bewegung
   desselben Geraets kurz davor (die Bruchsuche braucht bruch.MIN_ABSCHNITT_TAGE auf jeder Seite und laesst Ferien aus), Ereignis (Ferienende,
   laengere Ereignisse, belege/ereignisse.json), unerklaert. Die Brueche in den Aufenthalten werden genauso erklaert, ohne die Bewegung.
4. Je Einsatz (Durchgang C): je Einsatz-Abschnitt Rauschboden und Regenanteil, Kennzahlen, Gefaehrdung, Laerm, Naechte, Zellen,
   Verhaltensgruppen und das bereinigte Aggregat.

Messungen, deren Auswertung die Verwaltung selbst "defekt" oder "fehlerhaft" nennt (PDF im selben Ordner, bei Datum im Namen mit gleichem
Datum wie die Datei), stehen unter "defekt"; ihre Daten gehen in die Einsaetze ein.
Reines Python. Aufruf: python3 -I einsaetze.py --auswertung _vorschau/auswertung.json --aggregat _vorschau-aggregat
"""
import argparse
import collections
import datetime as dt
import json
import multiprocessing
import os
import re
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import bewegungen  # noqa: E402
import bruch  # noqa: E402
import dsd2csv  # noqa: E402
import gruppen  # noqa: E402
import kalender  # noqa: E402
import seiten_bauen  # noqa: E402
import uhr_rekonstruktion  # noqa: E402
import zwischenspeicher  # noqa: E402

GEWICHT_DATEI, GEWICHT_ZEITRAUM = 3.0, 3.0
STRAFE_KEINE, STRAFE_UNAEHNLICH, STRAFE_OHNE_BEWEGUNG, STRAFE_LEER = -0.5, -3.0, -2.0, -2.0
SICHER_AB = 1.5
VOLL_TAGE = 14                  # ab so vielen Tagen zaehlen Datei-Anteil und "keine Messung" voll
MIN_TAGE_MERKMAL = 3            # mit weniger Werktagen gilt ein Teil als aehnlich (zu wenig Daten fuer ein Urteil)
MAX_TVD, VERHAELTNIS = 0.1, (0.7, 1.4)
BEWEGUNG_VOR_BRUCH = bruch.MIN_ABSCHNITT_TAGE + 1  # so viele gewoehnliche Tage (ohne Ferien, Feiertage) vor dem Bruch darf die Bewegung liegen
EREIGNIS_TAGE = 1               # Bruchtag hoechstens so weit neben Beginn oder Ende eines Ereignisses
DEFEKT = re.compile(r"defekt|fehlerhaft", re.IGNORECASE)
STUNDE = dt.timedelta(hours=1)
TAG = dt.timedelta(days=1)


def _zeit(x):
    return dt.datetime.fromisoformat(x) if isinstance(x, str) else x


# ------------------------------------------------------------------ Messungen

def messungen_lesen(auswertung, metadaten):
    """Eine Beschreibung je Messung (Datei) mit ihren Bruechen (dsd2csv.py)."""
    seite = {}
    for slug, name, rels in seiten_bauen.standortgruppen(auswertung, metadaten):
        for rel in rels:
            seite[rel] = (slug, name)
    out = []
    for r in auswertung["standorte"]:
        rel, datei = r["standort"], r["datei"]
        meta = next((m for m in ((metadaten.get("standorte") or {}).get(rel) or {}).get("messungen", []) if m["datei"] == datei), {})
        liste = (r.get("abschnitte") or {}).get("liste") or []
        brueche = [(a["nr"], dt.date.fromisoformat(a["beginn"]["datum"]), a["beginn"].get("wahrscheinlichkeit"))
                   for a in liste if (a.get("beginn") or {}).get("art") == "Bruch"]
        out.append({
            "id": seiten_bauen.messung_id(rel, datei), "rel": rel, "datei": datei, "geraet": (r.get("geraet") or "").strip(),
            "limit": r.get("tempolimit_kmh"), "seite": seite.get(rel, (None, rel))[0], "name": seite.get(rel, (None, rel))[1],
            "fahrtrichtung": ", ".join(seiten_bauen.fahrtrichtungen(meta, rel)), "brueche": brueche,
            "aussen": bool(any(a.get("ausserhalb_erfassungszeitraum") for a in liste)), "zeile": r,
            "ort": dsd2csv.koordinaten(rel) or dsd2csv.ORT_NEUSS})
    return out


def zeitraeume_laden(pfad):
    """{Ordner/Datei: [(von, bis)]} der Erfassungszeitraeume aus den Mitteilungen (belege/korrekturen.json)."""
    if not pfad or not os.path.exists(pfad):
        return {}
    with open(pfad, encoding="utf-8") as fh:
        k = json.load(fh).get("zeitraum", {})
    return {schl: [(dt.date.fromisoformat(a), dt.date.fromisoformat(b)) for a, b in v.get("zeitraeume", [])] for schl, v in k.items()}


def defekt(messungen, wurzel):
    """{Messung: PDF} fuer Messungen, deren Auswertung die Verwaltung "defekt" oder "fehlerhaft" nennt: PDF im Ordner der Messung oder im
    obersten Ordner darueber; traegt der Name ein Datum, muss es das Datum im Namen der Datei sein."""
    out = {}
    for m in messungen:
        teile = m["rel"].split("/")
        for ordner in {m["rel"], teile[0]}:
            pfad = os.path.join(wurzel, ordner)
            for f in sorted(os.listdir(pfad)) if os.path.isdir(pfad) else []:
                if f.lower().endswith(".pdf") and DEFEKT.search(f):
                    datum = uhr_rekonstruktion.dateidatum(f)
                    if datum is None or datum == uhr_rekonstruktion.dateidatum(m["datei"]):
                        out[m["id"]] = f
    return out


# ------------------------------------------------------------------ Zuordnung der Teile

def groesse(a):
    """Gewicht eines Teils nach Laenge: ein paar Tage am Dateianfang (oft noch der vorige Standort) zaehlen weniger."""
    return min(1.0, a["tage"] / VOLL_TAGE)


def belege(a, m, zr):
    """(Punkte, Begruendungen) fuer Teil a -> Messung m."""
    p, gruende = 0.0, []
    anteil = (a["dateien"].get(m["id"]) or {}).get("tage", 0) / max(a["tage"], 1)
    if anteil:
        p += GEWICHT_DATEI * anteil * groesse(a)
        gruende.append(f"{round(100 * anteil)} % der Tage in der Datei")
    z = zr.get(f'{m["rel"]}/{m["datei"]}')
    if z:
        von, bis = _zeit(a["von"]).date(), _zeit(a["bis"]).date()
        drin = sum(max(0, (min(bis, zb) - max(von, za)).days + 1) for za, zb in z) / max((bis - von).days + 1, 1)
        p += GEWICHT_ZEITRAUM * drin - (1.0 if drin == 0 else 0.0)
        gruende.append(f"{round(100 * drin)} % im Erfassungszeitraum " + ", ".join(f"{x:%d.%m.%Y}–{y:%d.%m.%Y}" for x, y in z))
        if any(abs((von - za).days) <= 1 for za, _ in z):
            p += 1
            gruende.append("Beginn = Beginn des Erfassungszeitraums")
        if any(abs((bis - zb).days) <= 1 for _, zb in z):
            p += 1
            gruende.append("Ende = Ende des Erfassungszeitraums")
    lim, v85 = m.get("limit"), (a.get("merkmal") or {}).get("v85")
    if lim and v85 and ((lim >= 50 and v85 < 35) or (lim <= 30 and v85 > lim + 20)):
        p -= 1
        gruende.append(f"V85 {v85} passt nicht zu Tempo {lim}")
    return p, gruende


def vergleich(a, b):
    """(TVD der Tempoverteilungen, Verhaeltnis der Fahrzeuge je Stunde b/a) zweier Teile; None ohne Daten."""
    ha, hb = (a.get("merkmal") or {}).get("hist") or {}, (b.get("merkmal") or {}).get("hist") or {}
    na, nb = sum(ha.values()), sum(hb.values())
    if not na or not nb:
        return None, None
    tvd = 0.5 * sum(abs(ha.get(k, 0) / na - hb.get(k, 0) / nb) for k in set(ha) | set(hb))
    qa, qb = a["merkmal"]["fz_h"], b["merkmal"]["fz_h"]
    return tvd, (qb / qa if qa else None)


def aehnlich(a, b):
    ma, mb = a.get("merkmal") or {}, b.get("merkmal") or {}
    if ma.get("tage", 0) < MIN_TAGE_MERKMAL or mb.get("tage", 0) < MIN_TAGE_MERKMAL:
        return True  # zu wenig Daten fuer ein Urteil
    tvd, q = vergleich(a, b)
    return tvd is not None and tvd <= MAX_TVD and q is not None and VERHAELTNIS[0] <= q <= VERHAELTNIS[1]


def loesen(teile, punkte, verboten=None):
    """Beste Zuordnung: (Liste je Teil: Messungs-Index oder None, Gesamtpunkte). teile: mit 'aufenthalt' (gleicher Wert: derselbe
    Aufenthalt), punkte[i][j]: Punkte fuer Teil i -> Messung j; verboten: (i, j) darf nicht vorkommen (j None: keine Messung)."""
    n = len(teile)
    if not n:
        return [], 0.0
    mm = len(punkte[0])
    neg = float("-inf")
    # Zustand j (Messung des Teils i, mm: keine); best[i][j] = (Punkte, Zustand des vorigen Teils); letzte[i][j]: zuletzt benutzte Messung
    best = [[(neg, None)] * (mm + 1) for _ in range(n)]
    letzte = [[None] * (mm + 1) for _ in range(n)]
    for i in range(n):
        gleich = i and teile[i]["aufenthalt"] == teile[i - 1]["aufenthalt"]
        for j in range(mm + 1):
            if verboten and verboten == (i, j if j < mm else None):
                continue
            eigen = punkte[i][j] if j < mm else STRAFE_KEINE * groesse(teile[i])
            if i == 0:
                best[i][j], letzte[i][j] = (eigen + (STRAFE_LEER * j if j < mm else 0.0), None), (j if j < mm else -1)
                continue
            kand = []
            for jv in range(mm + 1):
                pv, _ = best[i - 1][jv]
                if pv == neg:
                    continue
                lz = letzte[i - 1][jv]
                if j < mm and lz > j:
                    continue  # Reihenfolge der Messungen
                s = pv + eigen + (STRAFE_LEER * (j - lz - 1) if j < mm and lz < j else 0.0)  # uebersprungene Messungen bleiben leer
                if gleich and jv != j and teile[i].get("grenze") != "dateigrenze":  # an einer ungeprueften Dateigrenze ist der Wechsel normal
                    s += STRAFE_OHNE_BEWEGUNG
                elif not gleich and j < mm and jv == j and not aehnlich(teile[i - 1], teile[i]):
                    s += STRAFE_UNAEHNLICH
                kand.append((s, jv, j if j < mm else lz))
            if kand:
                s, jv, lz = max(kand, key=lambda k: k[0])
                best[i][j], letzte[i][j] = (s, jv), lz
    ende = [best[n - 1][x][0] + STRAFE_LEER * (mm - 1 - letzte[n - 1][x]) if best[n - 1][x][0] != neg else neg for x in range(mm + 1)]
    j = max(range(mm + 1), key=lambda x: ende[x])
    total = ende[j]
    weg = [None] * n
    for i in range(n - 1, -1, -1):
        weg[i] = j if j < mm else None
        j = best[i][j][1]
    return weg, total


def zuordnen_geraet(g, messungen, zr):
    """Teile der Aufenthalte eines Geraets (g aus bewegungen.json) den Messungen zuordnen. Gibt (Teile mit 'messung', 'abstand', 'belege',
    Messungen in Reihenfolge) zurueck."""
    nach_id = {m["id"]: m for m in messungen}
    erster = {}
    for a in g["aufenthalte"]:
        for t in a["teile"]:
            for mid, info in t["dateien"].items():
                erster[mid] = min(erster.get(mid, info["von"]), info["von"])
    reihe = sorted((nach_id[mid] for mid in erster if mid in nach_id), key=lambda m: erster[m["id"]])
    teile = []
    for a in g["aufenthalte"]:
        for k, t in enumerate(a["teile"]):
            teile.append(dict(t, aufenthalt=a["nr"], nr_im_aufenthalt=k, letztes_im_aufenthalt=k == len(a["teile"]) - 1))
    punkte, gruende = [], []
    for t in teile:
        zeile = [belege(t, m, zr) for m in reihe]
        punkte.append([p for p, _ in zeile])
        gruende.append([gz for _, gz in zeile])
    weg, total = loesen(teile, punkte)
    for i, t in enumerate(teile):
        j = weg[i]
        _w, alt = loesen(teile, punkte, verboten=(i, j))
        t["messung"] = reihe[j]["id"] if j is not None else None
        t["abstand"] = round(total - alt, 2) if alt != float("-inf") else None
        t["sicher"] = t["abstand"] is None or t["abstand"] >= SICHER_AB
        t["belege"] = gruende[i][j] if j is not None else []
    return teile, reihe


# ------------------------------------------------------------------ Brueche erklaeren

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


def verwaltung_laden(pfad):
    if not pfad or not os.path.exists(pfad):
        return {}
    with open(pfad, encoding="utf-8") as fh:
        return {(e["messung"], e["bruch"]): e for e in json.load(fh).get("brueche", [])}


def bewegung_vor(tag, liste):
    """Die letzte trennende Bewegung, die einen Bruch am Tag tag erklaert: ihr Ende liegt hoechstens BEWEGUNG_VOR_BRUCH gewoehnliche Tage
    (Ferien und Feiertage zaehlen nicht, die Bruchsuche laesst sie aus) vor dem Bruch oder einen Tag danach. None ohne solche Bewegung."""
    frueh, n = tag, 0
    while n < BEWEGUNG_VOR_BRUCH:
        frueh -= TAG
        if not kalender.besonderer_tag(frueh):
            n += 1
    kand = [b for b in liste if b["stufe"] in bewegungen.TRENNEN and frueh <= _zeit(b["bis"]).date() <= tag + TAG]
    return max(kand, key=lambda b: b["bis"]) if kand else None


STUFE_BEWEGUNG = {"umhaengen": "belegt", "aktionstag": "belegt", "inbetriebnahme": "belegt", "inbetriebnahme_ungeprueft": "plausibel"}
BEWEGUNG_TEXT = {"umhaengen": "Umhängen", "aktionstag": "Umhängen am Aktionstag", "inbetriebnahme": "Inbetriebnahme nach Pause",
                 "inbetriebnahme_ungeprueft": "Inbetriebnahme nach Pause (ohne Vergleich)"}


def bewegung_text(b):
    von, bis = _zeit(b["von"]), _zeit(b["bis"])
    zeit = (f"{von:%d.%m.%Y} {von:%H:%M}–{bis:%H:%M}" if von.date() == bis.date() else f"{von:%d.%m.%Y %H:%M} bis {bis:%d.%m.%Y %H:%M}")
    return f'{BEWEGUNG_TEXT.get(b["stufe"], b["stufe"])} {zeit}' + (f' (Änderung z = {b["z"]})' if b.get("z") is not None else "")


def erklaeren(tag, seite, schluessel, ereignisse, verwaltung, bew=None):
    """Zuordnung eines Bruchs: (dict art, stufe, text, Ereignisse in der Naehe, Angabe der Verwaltung)."""
    ev = ereignis_kandidaten(tag, seite, ereignisse)
    v = verwaltung.get((schluessel, tag.isoformat()))
    if v:
        zu = {"art": v.get("art", "verwaltung"), "stufe": "bestaetigt", "text": v.get("erklaerung", ""), "quelle": v.get("quelle")}
    elif bew:
        zu = {"art": "bewegung", "stufe": STUFE_BEWEGUNG[bew["stufe"]], "text": bewegung_text(bew), "bewegung": bew}
    elif any(e["erklaerung"] for e in ev):
        zu = {"art": "ereignis", "stufe": "plausibel", "text": "; ".join(e["name"] for e in ev if e["erklaerung"])}
    else:
        zu = {"art": "unerklaert", "stufe": "offen", "text": ""}
    return zu, ev, v


def brueche_der_messungen(messungen, geraete, ereignisse, verwaltung):
    """Brueche der Messungen (dsd2csv.py) mit Zuordnung."""
    bew_von = {g["geraet"]: g["bewegungen"] for g in geraete}
    alle_tage = collections.defaultdict(list)
    for m in messungen:
        for _nr, tag, _p in m["brueche"]:
            alle_tage[tag].append(m["id"])
    out = []
    for m in messungen:
        for nr, tag, p in m["brueche"]:
            bew = bewegung_vor(tag, bew_von.get(m["geraet"], []))
            zu, ev, v = erklaeren(tag, m["seite"], f'{m["rel"]}/{m["datei"]}', ereignisse, verwaltung, bew)
            gleich = sorted({i for d in (tag - TAG, tag, tag + TAG) for i in alle_tage.get(d, []) if i != m["id"]})
            out.append({"messung": m["id"], "rel": m["rel"], "datei": m["datei"], "seite": m["seite"], "name": m["name"], "nr": nr,
                        "datum": tag.isoformat(), "wahrscheinlichkeit": p, "zuordnung": zu, "ereignisse": ev, "gleicher_tag": gleich, "verwaltung": v})
    return out


# ------------------------------------------------------------------ Einsaetze

def _grenze_zwischen(a, b, ereignisse, verwaltung, m):
    """Art der Grenze zwischen zwei aufeinanderfolgenden Teilen a, b desselben Einsatzes."""
    if a["aufenthalt"] != b["aufenthalt"]:
        bew = b["_aufenthalt"]["beginn"]
        text = ("Pause, danach am selben Standort weiter (ohne Vergleich, zu wenig Daten davor oder danach)" if bew["stufe"] == "inbetriebnahme_ungeprueft"
                else "Bewegung ohne Wechsel der Messung (ungeklärt: anderer Mast, andere Richtung, Neuausrichtung?)")
        return {"art": "bewegung", "text": text, "bewegung": bew}
    br = bruch_vor(b)
    if br.get("art") == "dateigrenze":
        return {"art": "dateigrenze_ungeprueft", "datum": br["datum"], "grund": br.get("grund")}
    tag = dt.date.fromisoformat(br["datum"]) if br else _zeit(b["von"]).date()
    zu, ev, _v = erklaeren(tag, m["seite"], f'{m["rel"]}/{m["datei"]}', ereignisse, verwaltung)
    return {"art": "bruch", "datum": tag.isoformat(), "zeit": br.get("zeit"), "verfeinert": br.get("verfeinert"),
            "wahrscheinlichkeit": br.get("wahrscheinlichkeit"), "zuordnung": zu, "ereignisse": ev}


def bruch_vor(t):
    """Der Bruch des Aufenthalts, an dem das Teil t beginnt (verfeinerter Zeitpunkt am naechsten an seinem ersten Fahrzeug); {} ohne."""
    liste = t["_aufenthalt"]["brueche"]
    von = _zeit(t["von"])
    return min(liste, key=lambda x: abs((_zeit(x.get("zeit") or x["datum"]) - von).total_seconds())) if liste else {}


def einsaetze_bilden(geraete, messungen, zr, ereignisse=(), verwaltung=None):
    """(Einsaetze, nicht zugeordnete Teile, Messungen ohne Einsatz, Einsatz-Abschnitte je Einsatz fuer Durchgang C)."""
    verwaltung = verwaltung or {}
    nach_id = {m["id"]: m for m in messungen}
    einsaetze, nicht_zugeordnet, abschnitte_von = [], [], {}
    ohne = []
    for g in geraete:
        auf = {a["nr"]: a for a in g["aufenthalte"]}
        teile, reihe = zuordnen_geraet(g, [m for m in messungen if m["geraet"] == g["geraet"]], zr)
        for t in teile:
            t["_aufenthalt"] = auf[t["aufenthalt"]]
            t["_von"], t["_bis"] = _zeit(t["von"]), _zeit(t["bis"])
        # Wechsel der Messung an einem Bruch ohne Bewegung: der Tag des Wechsels gehoert zu keinem Einsatz (dort wurde ausgelesen, umgestellt
        # oder umgehaengt, ohne dass sich eine Luecke zeigt); ist der Zeitpunkt nicht verfeinert (nur der Bruchtag bekannt), auch der Vortag
        for a, b in zip(teile, teile[1:]):
            if a["aufenthalt"] == b["aufenthalt"] and a["messung"] != b["messung"]:
                br = bruch_vor(b)
                if br.get("art") == "dateigrenze":  # ungeprueft: kein Schnitt, nur gekennzeichnet
                    a["schnitt_ende"] = b["schnitt_beginn"] = {"art": "dateigrenze_ungeprueft", "datum": b["_von"].date().isoformat(),
                                                               "grund": br.get("grund"), "ausgenommen": []}
                    continue
                tag = b["_von"].date()
                weg = [tag] if br.get("verfeinert") else [tag - TAG, tag]
                a["_bis"] = min(a["_bis"], dt.datetime.combine(weg[0], dt.time()) - dt.timedelta(seconds=1))
                b["_von"] = max(b["_von"], dt.datetime.combine(tag + TAG, dt.time()))
                gleich = a["messung"] and b["messung"] and nach_id[a["messung"]]["seite"] == nach_id[b["messung"]]["seite"]
                a["schnitt_ende"] = b["schnitt_beginn"] = {"art": "messungswechsel_am_bruch" if gleich else "ortswechsel_ohne_bewegung",
                                                           "datum": tag.isoformat(), "zeit": br.get("zeit"),
                                                           "ausgenommen": [d.isoformat() for d in weg]}
        for t in teile:
            if t["messung"] is None:
                nicht_zugeordnet.append({"geraet": g["geraet"], "von": t["_von"].isoformat(), "bis": t["_bis"].isoformat(), "tage": t["tage"],
                                         "fahrzeuge": t["fahrzeuge"], "dateien": sorted(t["dateien"]), "abstand": t["abstand"],
                                         "merkmal": {k: t["merkmal"].get(k) for k in ("fz_h", "v85", "tage")}})
        benutzt = {t["messung"] for t in teile}
        for m in reihe:
            if m["id"] not in benutzt:
                bei = sorted({"e-" + t["messung"][2:] for t in teile if m["id"] in t["dateien"] and t["messung"]})
                ohne.append({"messung": m["id"], "geraet": g["geraet"], "daten_in": bei,
                             "grund": ("die Daten der Datei gehören nach unserer Zuordnung zu " + ", ".join(bei)) if bei
                             else "kein Teil des Gesamtstroms zugeordnet"})
        for m in reihe:
            eigene = [t for t in teile if t["messung"] == m["id"] and t["_von"] < t["_bis"]]
            if not eigene:
                continue
            e = _einsatz(m, eigene, teile, ereignisse, verwaltung, nach_id)
            einsaetze.append(e)
            abschnitte_von[e["id"]] = eigene
    bekannt = {mid for g in geraete for a in g["aufenthalte"] for t in a["teile"] for mid in t["dateien"]}
    ohne += [{"messung": m["id"], "geraet": m["geraet"], "daten_in": [], "grund": "keine Fahrzeuge mit nutzbarer oder rekonstruierter Uhr "
              "(Uhr-Müll, zu kurze Segmente oder doppelte Datei)" if m["geraet"] else "ohne Gerätenummer"}
             for m in messungen if m["id"] not in bekannt]
    return einsaetze, nicht_zugeordnet, ohne, abschnitte_von


def _einsatz(m, eigene, teile, ereignisse, verwaltung, nach_id):
    """Ein Einsatz aus den Teilen 'eigene' der Messung m (teile: alle Teile des Geraets)."""
    eid = "e-" + m["id"][2:]
    abschnitte, stuecke = [], []
    for nr, t in enumerate(eigene, 1):
        if nr == 1:
            grenze = t.get("schnitt_beginn") or ({"art": "bewegung", "bewegung": t["_aufenthalt"]["beginn"]} if t["nr_im_aufenthalt"] == 0
                                                 else {"art": "bruch", "datum": t["_von"].date().isoformat()})
            if grenze["art"] == "bewegung" and not grenze["bewegung"]:
                grenze = {"art": "datenbeginn"}
        else:
            grenze = _grenze_zwischen(eigene[nr - 2], t, ereignisse, verwaltung, m)
        abschnitte.append({"nr": nr, "von": t["_von"].isoformat(), "bis": t["_bis"].isoformat(), "aufenthalt": t["aufenthalt"],
                           "grenze_davor": grenze, "sicher": t["sicher"], "abstand": t["abstand"], "belege": t["belege"]})
        for mid, info in sorted(t["dateien"].items(), key=lambda x: x[1]["von"]):
            von, bis = max(_zeit(info["von"]), t["_von"]), min(_zeit(info["bis"]), t["_bis"])
            if von > bis:
                continue
            stuecke.append({"messung": mid, "abschnitt": nr, "von": von.date().isoformat(), "bis": bis.date().isoformat(),
                            "von_zeit": von.isoformat(), "bis_zeit": bis.isoformat(), "herkunft": "eigen" if mid == m["id"] else "andere_messung",
                            "rekonstruiert": info["rekonstruiert"], "fahrzeuge": info["fahrzeuge"], "stufe": "sicher" if t["sicher"] else "unsicher"})
    letzt = eigene[-1]
    if letzt.get("schnitt_ende"):
        ende = letzt["schnitt_ende"]
    elif letzt["letztes_im_aufenthalt"]:
        ende = {"art": "bewegung", "bewegung": letzt["_aufenthalt"]["ende"]} if letzt["_aufenthalt"]["ende"] else {"art": "datenende"}
    else:
        ende = {"art": "bruch", "datum": letzt["_bis"].date().isoformat()}
    # eigene Daten in anderen Einsaetzen oder in keinem
    abgegeben, nicht = [], []
    for t in teile:
        info = t["dateien"].get(m["id"])
        if not info or t["messung"] == m["id"]:
            continue
        x = {"von": max(_zeit(info["von"]), t["_von"]).isoformat(), "bis": min(_zeit(info["bis"]), t["_bis"]).isoformat(), "fahrzeuge": info["fahrzeuge"]}
        if t["messung"]:
            abgegeben.append(dict(x, an="e-" + t["messung"][2:], sicher=t["sicher"]))
        else:
            nicht.append(dict(x, grund="keiner Messung zugeordnet (Standort ohne Messung oder unklar)"))
    fremd = any(s["herkunft"] != "eigen" for s in stuecke)
    unsicher = any(not t["sicher"] for t in eigene) or any(not a["sicher"] for a in abgegeben)
    rekon = any(s["rekonstruiert"] for s in stuecke if s["herkunft"] == "eigen")
    status = ("unsicher" if unsicher and (fremd or abgegeben or nicht) else "abgeleitet" if fremd else "gekuerzt" if abgegeben or nicht
              else "ergaenzt" if m["aussen"] or rekon else "identisch")
    ausgenommen = sorted({d for t in eigene for s in (t.get("schnitt_beginn"), t.get("schnitt_ende")) if s for d in s["ausgenommen"]})
    return {"id": eid, "messung": m["id"], "seite": m["seite"], "name": m["name"], "fahrtrichtung": m["fahrtrichtung"], "geraet": m["geraet"],
            "limit": m["limit"], "status": status, "von": eigene[0]["_von"].date().isoformat(), "bis": letzt["_bis"].date().isoformat(),
            "von_zeit": eigene[0]["_von"].isoformat(), "bis_zeit": letzt["_bis"].isoformat(), "beginn": abschnitte[0]["grenze_davor"],
            "ende": ende, "abschnitte": abschnitte, "teile": stuecke, "abgegeben": abgegeben, "nicht_beruecksichtigt": nicht,
            "ausgenommene_tage": ausgenommen, "rekonstruiert": sum(s["rekonstruiert"] for s in stuecke)}


def _auftrag(e, teile, zeile, ort):
    """Eingaben eines Einsatzes fuer Durchgang C (klein genug fuer andere Prozesse): je Einsatz-Abschnitt die Stunden (Zeilen des
    Rohaggregats aus bewegungen.py, nur im Zeitraum des Teils) und die vollstaendig aufgezeichneten Stunden, dazu Limit, Ort und bei
    unveraenderten Einsaetzen die Auswertung der Messung."""
    abschnitte = []
    for t in teile:
        a = t["_aufenthalt"]
        von = t["_von"].replace(minute=0, second=0, microsecond=0)

        def drin(d, h):
            return von <= dt.datetime.fromisoformat(d) + h * STUNDE <= t["_bis"]
        zeilen = [z for z in a["zeilen"] if drin(z[0], z[1])]
        voll = [[z[0], z[1]] for z in zeilen if z[3]] + [x for x in a["voll_ohne_fahrzeuge"] if drin(x[0], x[1])]
        abschnitte.append({"von": t["_von"].isoformat(), "bis": t["_bis"].isoformat(), "zeilen": zeilen, "voll": sorted(voll),
                           "versatz": [[z[0], z[1], z[2]] for z in zeilen]})
    return {"id": e["id"], "status": e["status"], "limit": e["limit"], "ort": ort, "abschnitte": abschnitte,
            "messung_zeile": zeile if e["status"] == "identisch" else None}


def _spannen(stunden):
    """Spannen [(von, bis)] (Ortszeit) aus vollstaendig aufgezeichneten Stunden (Datum, Stunde), zusammenhaengende Stunden verbunden."""
    out = []
    for d, h in sorted(set(stunden)):
        a = dt.datetime(d.year, d.month, d.day, h)
        if out and out[-1][1] == a:
            out[-1] = (out[-1][0], a + STUNDE)
        else:
            out.append((a, a + STUNDE))
    return out


def _fahrzeuge_aus(zeilen):
    """Fahrzeuge [(Ortszeit, v)] aus Stunden-Zeilen [Datum, Stunde, Versatz, voll, [km/h, Anzahl, ...]] (Zeit: Mitte der Stunde)."""
    out = []
    for d, h, _off, _voll, flach in zeilen:
        datum = dt.date.fromisoformat(d)
        t_ = dt.datetime(datum.year, datum.month, datum.day, h, 30)
        for v, n in zip(flach[0::2], flach[1::2]):
            out.extend([(t_, v)] * n)
    return out


def einsatz_rechnen(auftrag, speicher=None):
    """Durchgang C fuer einen Einsatz: je Einsatz-Abschnitt Rauschboden und Regenanteil (bei unveraendertem Einsatz neben der Schaetzung der
    Messung), dann Kennzahlen, Gefaehrdung, Laerm, Naechte, Zellen (mit Rauschboden), Verhaltensgruppen und das bereinigte Aggregat."""
    lim, ort = auftrag["limit"], tuple(auftrag["ort"])
    regen_f = dsd2csv.regenfunktion(ort=ort)
    zeile = auftrag["messung_zeile"]
    roh, sauber_alle, stunden_alle, rausch_bloecke, grenzen, roh_je, sauber_je, stunden_je = [], [], [], [], [], [], [], []
    liste_zeile = ((zeile or {}).get("abschnitte") or {}).get("liste") or []
    for i, a in enumerate(auftrag["abschnitte"]):
        vehs = _fahrzeuge_aus(a["zeilen"])
        stunden = [(dt.date.fromisoformat(d), h) for d, h in a["voll"]]
        sp = _spannen(stunden)
        if i:
            grenzen.append(dt.date.fromisoformat(a["von"][:10]))
        rb = dsd2csv.rauschen.pruefen(vehs, sp, lim, regen=regen_f) if vehs else None
        sauber, regen_weg = vehs, 0
        if rb and rb["abzug"]:
            modell = rb["_modell"]
            sauber = dsd2csv.rauschen.ohne_rauschen(vehs, modell)
            if modell.get("regen"):
                regen_weg = len(dsd2csv.rauschen.ohne_rauschen(vehs, dict(modell, regen=None))) - len(sauber)
        block = dsd2csv.rauschen_block(rb, len(vehs) - len(sauber), len(vehs), regen_weg)
        if zeile is not None:  # Einsatz = Messung: Rauschboden und Regen der Messung (je Abschnitt gleich geschaetzt) als Beleg daneben
            alt = (liste_zeile[i].get("rauschen") if len(liste_zeile) > 1 and i < len(liste_zeile) else zeile.get("rauschen"))
            if alt:
                block["messung"] = {"abgezogen_fahrzeuge": alt.get("abgezogen_fahrzeuge"), "belegt": alt.get("belegt")}
        rausch_bloecke.append(block)
        roh += vehs
        sauber_alle += sauber
        stunden_alle += stunden
        roh_je.append(vehs)
        sauber_je.append(sauber)
        stunden_je.append(stunden)
    sp_alle = _spannen(stunden_alle)
    abged = set(stunden_alle)

    def zusatz(vehs, ab=None):
        r = dsd2csv.raten(vehs, lim, ab) if ab else None
        return {k: x for k, x in (("histogramm", dsd2csv.histogramm(vehs)), ("raten", r), ("gefaehrdung", dsd2csv.gefaehrdung(vehs, lim, ab)),
                                  ("laerm", dsd2csv.laerm(vehs, lim, ab))) if x}
    teil = {k: [f for f in sauber_alle if in_zeitraum(f[0])] for k, (_, in_zeitraum) in dsd2csv.TEILZEITRAEUME.items()}
    block, teilzeitraeume = dsd2csv.kennzahlen_je_zeitraum(sauber_alle, teil, lim, 0, zusatz, abged)
    klassen = dsd2csv.rauschen.regenklassen(regen_f, abged) if regen_f else None
    trocken = (lambda x: klassen.get(x) == dsd2csv.rauschen.TROCKEN) if klassen else None
    daten = gruppen.datentabelle(gruppen.zellen_bauen(roh, sauber_alle, sp_alle), lim)
    if daten and trocken:
        daten["trocken"] = gruppen.zellen_json(gruppen.zellen_bauen(roh, sauber_alle, sp_alle, trocken))
    liste, daten_abschnitte = [], []
    if len(auftrag["abschnitte"]) > 1:
        for i, a in enumerate(auftrag["abschnitte"]):
            von, bis = a["von"][:10], a["bis"][:10]
            r_i, s_i = roh_je[i], sauber_je[i]
            st_i = set(stunden_je[i])
            sp_i = _spannen(st_i)
            teil_i = {k: [f for f in s_i if in_zeitraum(f[0])] for k, (_, in_zeitraum) in dsd2csv.TEILZEITRAEUME.items()}
            e_i = {"nr": i + 1, "von": von, "bis": bis, "tage": (dt.date.fromisoformat(bis) - dt.date.fromisoformat(von)).days + 1,
                   **(dsd2csv.stats(s_i, lim) or {"anzahl_fahrzeuge": 0})}
            if e_i["anzahl_fahrzeuge"]:
                e_i.update(zusatz(s_i, st_i))
                e_i["teilzeitraeume"] = dsd2csv.kennzahlen_je_zeitraum(s_i, teil_i, lim, 0, zusatz, st_i)[1]
            e_i["rauschen"] = rausch_bloecke[i]
            liste.append(e_i)
            z_i = gruppen.datentabelle(gruppen.zellen_bauen(r_i, s_i, sp_i), lim)
            if z_i:
                if trocken:
                    z_i["trocken"] = gruppen.zellen_json(gruppen.zellen_bauen(r_i, s_i, sp_i, trocken))
                daten_abschnitte.append({"nr": i + 1, "von": von, "bis": bis, **z_i})
    if daten and daten_abschnitte:
        daten["abschnitte"] = daten_abschnitte
    vb, vz = dsd2csv.verhalten_auswerten(roh, sp_alle, grenzen, lim, ort, speicher)
    if daten:
        for d in daten.get("abschnitte") or [daten]:
            if vz.get(d.get("nr", 1)):
                d["verhalten"] = vz[d.get("nr", 1)]
    # bereinigtes Aggregat des Einsatzes: Zeilen [Datum, Stunde, UTC-Versatz, Einsatz-Abschnitt, voll, Regenklasse, [km/h, Anzahl, ...]]
    versatz, abschnitt_von = {}, {}
    for i, a in enumerate(auftrag["abschnitte"]):
        for d, h, o in a["versatz"]:
            versatz[(dt.date.fromisoformat(d), h)] = o
            abschnitt_von[(dt.date.fromisoformat(d), h)] = i + 1
    je_stunde = collections.defaultdict(collections.Counter)
    for t_, v in sauber_alle:
        je_stunde[(t_.date(), t_.hour)][v] += 1
    agg = []
    for (d, h), c in sorted(je_stunde.items()):
        flach = []
        for v in sorted(c):
            flach += [v, c[v]]
        agg.append([d.isoformat(), h, versatz.get((d, h)), abschnitt_von.get((d, h), 1), 1 if (d, h) in abged else 0,
                    klassen.get((d, h)) if klassen else None, flach])
    kennzahlen = {"bereinigt": block, "teilzeitraeume": teilzeitraeume, "rauschen": rausch_bloecke[0] if len(rausch_bloecke) == 1 else
                  {"geprueft": True, "je_abschnitt": True, "belegt": any(b_.get("belegt") for b_ in rausch_bloecke),
                   "abgezogen_fahrzeuge": len(roh) - len(sauber_alle),
                   "grund": "Rauschboden und Regenanteil sind je Einsatz-Abschnitt geschätzt"},
                  "abschnitte": {"geprueft": True, "liste": liste} if liste else {"geprueft": False},
                  "nacht_ereignisse": dsd2csv.nacht_ereignisse(sauber_alle, sp_alle, lim), "verhalten": vb}
    nah = dsd2csv.stationen_nach_abstand(ort)
    if nah and kennzahlen["rauschen"].get("regen"):
        kennzahlen["rauschen"]["regen"]["wetterstation"] = {"name": nah[0][2], "abstand_km": nah[0][0],
                                                            "weitere": [f"{n} ({k} km)" for k, _, n in nah[1:3]]}
    return {"kennzahlen": kennzahlen, "zellen": daten, "aggregat": agg}


CODE = None


def _code():
    global CODE
    if CODE is None:
        dateien = [os.path.join(HIER, f) for f in ("einsaetze.py", "dsd2csv.py", "rauschen.py", "gruppen.py", "verhalten.py",
                                                   os.path.join("belege", "wetter.json"), os.path.join("belege", "standorte.json"))]
        CODE = zwischenspeicher.code_hash(*[f for f in dateien if os.path.exists(f)]) + ("n" if verhalten_da() else "")
    return CODE


def verhalten_da():
    return dsd2csv.verhalten.verfuegbar()


def _arbeit(args):
    """Ein Einsatz in einem eigenen Prozess, mit Zwischenspeicher (Ebene 'einsatz'). Gibt (ID, Ergebnis, benutzte Eintraege) zurueck."""
    auftrag, ordner = args
    sp = zwischenspeicher.Zwischenspeicher(ordner) if ordner else None
    schl = None
    if sp:
        roh = json.dumps(auftrag, sort_keys=True, default=str).encode("utf-8")
        schl = zwischenspeicher.inhalts_hash(roh, _code())
        erg = sp.holen("einsatz", schl)
        if erg is not None:
            return auftrag["id"], erg, sorted(sp.benutzt)
    erg = json.loads(json.dumps(einsatz_rechnen(auftrag, sp), default=str))
    if sp:
        sp.speichern("einsatz", schl, erg)
    return auftrag["id"], erg, sorted(sp.benutzt) if sp else []


# ------------------------------------------------------------------ Ausgabe

def bilden(auswertung, metadaten, bew, wurzel=HIER, ereignisse=(), verwaltung=None, zr=None):
    """(einsaetze.json ohne Kennzahlen, Teile je Einsatz) aus der Auswertung und dem Ergebnis von bewegungen.py."""
    messungen = messungen_lesen(auswertung, metadaten)
    einsaetze, nicht, ohne, teile_von = einsaetze_bilden(bew["geraete"], messungen, zr or {}, ereignisse, verwaltung)
    brueche = brueche_der_messungen(messungen, bew["geraete"], ereignisse, verwaltung or {})
    zaehlung = collections.Counter(b["zuordnung"]["art"] + "/" + b["zuordnung"]["stufe"] for b in brueche)
    geraete = [{"geraet": g["geraet"], "fahrzeuge": g["fahrzeuge"], "bewegungen": g["bewegungen"], "rekonstruktion": g["rekonstruktion"],
                "aufenthalte": [{k: a[k] for k in ("nr", "von", "bis", "beginn", "ende", "konfidenz", "tage", "fahrzeuge", "dateien", "brueche")}
                                for a in g["aufenthalte"]]} for g in bew["geraete"]]
    return ({"einsaetze": einsaetze, "brueche": brueche, "zaehlung": dict(zaehlung), "nicht_zugeordnet": nicht, "messungen_ohne_einsatz": ohne,
             "defekt": defekt(messungen, wurzel), "aktionstage": bew["aktionstage"], "geraete": geraete}, teile_von, messungen)


def auswerten(auswertung, metadaten, wurzel=HIER, ereignisse_pfad=None, verwaltung_pfad=None, korrekturen_pfad=None, cache=None, jobs=1):
    """(einsaetze.json, Zellen je Einsatz, Aggregat je Einsatz)."""
    bew, benutzt_b = bewegungen.berechnen(auswertung, wurzel, cache)
    out, teile_von, messungen = bilden(auswertung, metadaten, bew, wurzel, ereignisse_laden(ereignisse_pfad), verwaltung_laden(verwaltung_pfad),
                                       zeitraeume_laden(korrekturen_pfad))
    nach_id = {m["id"]: m for m in messungen}
    auftraege = [(_auftrag(e, teile_von[e["id"]], nach_id[e["messung"]]["zeile"], nach_id[e["messung"]]["ort"]), cache) for e in out["einsaetze"]]
    if jobs > 1:
        with multiprocessing.Pool(jobs) as pool:
            ergebnisse = pool.map(_arbeit, auftraege, chunksize=1)
    else:
        ergebnisse = [_arbeit(x) for x in auftraege]
    erg_von = {i: erg for i, erg, _ in ergebnisse}
    benutzt = {tuple(x) for _, _, b in ergebnisse for x in b} | set(benutzt_b)
    zellen, aggregate = {}, {}
    for e in out["einsaetze"]:
        erg = erg_von.get(e["id"])
        if erg:
            e["kennzahlen"] = erg["kennzahlen"]
            zellen[e["id"]], aggregate[e["id"]] = erg["zellen"], erg["aggregat"]
    if cache:  # nicht mehr benutzte Einsaetze, Bewegungen und Verhaltensgruppen entfernen (die Ebenen je Datei raeumt dsd2csv.py auf)
        zwischenspeicher.Zwischenspeicher(cache).aufraeumen(benutzt, ("datei", "datei-ohne-numpy"))
    return out, zellen, aggregate


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--auswertung", required=True, help="auswertung.json von dsd2csv.py")
    ap.add_argument("--aggregat", required=True, help="Ordner der Aggregate (dsd2csv.py --aggregat); dorthin kommt einsaetze.aggregat.json")
    ap.add_argument("--daten", default=HIER, help="Ordner mit den DSD-Dateien (Standard: dieses Verzeichnis)")
    ap.add_argument("--metadaten", default=os.path.join(HIER, "belege", "metadaten.json"))
    ap.add_argument("--ereignisse", default=os.path.join(HIER, "belege", "ereignisse.json"))
    ap.add_argument("--verwaltung", default=os.path.join(HIER, "belege", "brueche-verwaltung.json"))
    ap.add_argument("--korrekturen", default=os.path.join(HIER, "belege", "korrekturen.json"), help="Erfassungszeitraeume der Mitteilungen")
    ap.add_argument("-o", "--ausgabe", help="Ziel (Standard: einsaetze.json neben der auswertung.json; die Zellen in einsaetze-zellen.json)")
    ap.add_argument("--cache", help="Zwischenspeicher (wie dsd2csv.py --cache)")
    ap.add_argument("--jobs", type=int, default=1, help="Einsaetze gleichzeitig rechnen")
    a = ap.parse_args()
    with open(a.auswertung, encoding="utf-8") as fh:
        auswertung = json.load(fh)
    with open(a.metadaten, encoding="utf-8") as fh:
        metadaten = json.load(fh)
    out, zellen, aggregate = auswerten(auswertung, metadaten, a.daten, a.ereignisse, a.verwaltung, a.korrekturen, a.cache, a.jobs)
    ziel = a.ausgabe or os.path.join(os.path.dirname(os.path.abspath(a.auswertung)), "einsaetze.json")
    with open(ziel, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")
    with open(os.path.join(os.path.dirname(ziel), "einsaetze-zellen.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(zellen, fh, ensure_ascii=False, separators=(",", ":"))
    os.makedirs(a.aggregat, exist_ok=True)
    with open(os.path.join(a.aggregat, "einsaetze.aggregat.json"), "w", encoding="utf-8", newline="\n") as fh:  # fuer daten_bauen.py
        json.dump(aggregate, fh, ensure_ascii=False, separators=(",", ":"))
    st = collections.Counter(e["status"] for e in out["einsaetze"])
    print(f'{len(out["einsaetze"])} Einsätze ({", ".join(f"{k} {v}" for k, v in sorted(st.items()))}), {len(out["nicht_zugeordnet"])} Teile ohne '
          f'Messung, {len(out["messungen_ohne_einsatz"])} Messungen ohne Einsatz, {len(out["brueche"])} Brüche: '
          + ", ".join(f"{k} {v}" for k, v in sorted(out["zaehlung"].items())) + f" -> {ziel}")


if __name__ == "__main__":
    main()
