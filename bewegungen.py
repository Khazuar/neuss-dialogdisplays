# SPDX-License-Identifier: MIT
"""Gesamtstrom je Geraet, Bewegungen (Umhaengen, Inbetriebnahme) und Aufenthalte (docs/einsaetze.md).

Gesamtstrom: Je Geraet werden alle Dateien zu einem Strom von Einzelfahrzeugen in Ortszeit zusammengesetzt. Dateigrenzen spielen keine Rolle:
Oft wurde an einem Tag ausgelesen (neue Datei) und an einem anderen umgehaengt. Verwendet werden
  - Uhr-Segmente mit gueltiger Uhr (dsd2csv.bewerte_segmente) mit mindestens MIN_GUELTIG Fahrzeugen und Zeiten zwischen FRUEHESTENS und
    heute (kleinere "gueltige" Segmente sind meist Uhr-Muell);
  - Segmente mit zurueckgesetzter Uhr, deren Lage uhr_rekonstruktion.py belegt oder wahrscheinlich macht.
Doppelte Fahrzeuge (gleiche Zeit und Geschwindigkeit aus ueberlappenden Dateien) zaehlen einmal.

Bewegung: eine Unterbrechung mit minutengenauem Beginn und Ende, nach der sich der Verkehr aendert. Kandidaten:
  Pause   keine Fahrzeuge ueber mindestens PAUSE_H Stunden, davon mindestens eine Stunde im FENSTER eines Werktags (oder laenger als
          PAUSE_LANG_H; nachts ist an ruhigen Strassen oft stundenlang nichts los)
  Luecke  an einem Werktag die laengste Luecke im FENSTER, laenger als an jedem anderen Werktag im Umkreis von UMKREIS_TAGE Tagen und
          mindestens MIN_LUECKE_H
Kandidaten weniger als ZUSAMMEN_TAGE auseinander sind ein Umbau. Aenderung ueber den Kandidaten: bis zu TAGE_VERGLEICH Werktage davor gegen
danach (FENSTER, gleicher Ferienstatus, hoechstens SUCHE_TAGE weit, nicht ueber andere Montagen hinweg): Tempoverteilung (TVD ab KMIN km/h)
und Verkehrsmenge (|ln| des Verhaeltnisses der Fahrzeuge je Stunde). z = robuster z-Wert (Median, MAD) gegen dieselben Groessen an den
Tagesgrenzen im Umkreis von NULL_TAGE Tagen (ohne die Naehe von Kandidaten), der groessere von beiden.

Einstufung:
  umhaengen                   Luecke oder Pause bis PAUSE_LANG_H mit z >= Z_STARK, oder z >= Z_SICHER an einem Aktionstag (+-1 Tag)
  inbetriebnahme              Pause ueber PAUSE_LANG_H mit z >= Z_MOEGLICH; montiert spaetestens beim ersten Fahrzeug danach
  inbetriebnahme_ungeprueft   Pause ueber PAUSE_LANG_H ohne Vergleich (zu wenig Werktage davor oder danach)
  aktionstag                  an einem Aktionstag (Werktag mit einem Umhaengen oder einer Inbetriebnahme mit z >= Z_STARK an einem anderen
                              Geraet) aendert sich der Verkehr ueber den Tag (z >= Z_MOEGLICH), mit einer Luecke ab MIN_STELLE_MIN Minuten
  eingriff                    Luecke am Tag mit Aenderung, aber ohne stimmige Tagesprobe (Wartung, Neuausrichtung?); trennt nichts
  pause_gleicher_ort, moeglich, besuch, wochenmuster, unklar: trennen nichts
Tagesprobe (fuer umhaengen und aktionstag am selben Tag): Wechselpunkt im Tag aus Tempoverteilung und Verkehrsmenge (Poisson mit dem
Tagesgang der Tage davor und danach), PERMUTATIONEN Vertauschungen, p <= P_TAG, Richtung passend, hoechstens NAEHE_MIN Minuten neben der Luecke.

Bewegungen (umhaengen, inbetriebnahme, inbetriebnahme_ungeprueft, aktionstag) trennen Aufenthalte. Je Aufenthalt: Brueche (bruch.erkenne,
wie je Messung), Teile zwischen den Bruechen mit Merkmalen fuer die Zuordnung (einsaetze.py), Stunden (Format des Rohaggregats) und die
Tage je Datei.

Ablauf: erster Lauf nur mit gueltigen Uhren -> Montagetage -> Uhr-Rekonstruktion -> zweiter Lauf mit den rekonstruierten Segmenten.
Reines Python. Aufruf ueber einsaetze.py."""
import bisect
import collections
import datetime as dt
import hashlib
import math
import os
import random

import bruch
import dsd2csv
import kalender
import seiten_bauen
import uhr_belege
import uhr_rekonstruktion
import zwischenspeicher

HIER = os.path.dirname(os.path.abspath(__file__))
MIN_GUELTIG = 200
FRUEHESTENS = dt.datetime(2019, 1, 1)  # aeltere oder kuenftige "gueltige" Zeiten sind Uhr-Muell
REKONSTRUIERT = ("belegt", "wahrscheinlich")
PAUSE_H, PAUSE_LANG_H = 3.0, 48.0
FENSTER = (7, 19)
UMKREIS_TAGE = 21
MIN_LUECKE_H = 0.25
TAGE_VERGLEICH = 7
Z_SICHER, Z_MOEGLICH, Z_STARK = 4.0, 2.5, 8.0
PERMUTATIONEN, P_TAG, NAEHE_MIN = 300, 0.01, 30
TRENNEN = ("umhaengen", "inbetriebnahme", "inbetriebnahme_ungeprueft", "aktionstag")
ZUSAMMEN_TAGE = 2
SUCHE_TAGE = 21
MIN_STELLE_MIN = 10
NULL_TAGE, NULL_MIN, NULL_ABSTAND = 45, 15, 10
KMIN, KBIN, KMAX = 15, 2, 80
TAG = dt.timedelta(days=1)
STUNDE = dt.timedelta(hours=1)
CODE_DATEIEN = ("bewegungen.py", "uhr_rekonstruktion.py", "dsd2csv.py", "bruch.py", "kalender.py", "uhr_belege.py", "rauschen.py")


def werktag(tag):
    return tag.weekday() < 5 and not kalender.feiertag(tag)


def ferien(tag):
    return kalender.besonderer_tag(tag) == "ferien"


# ------------------------------------------------------------------ Gesamtstrom

def fahrzeuge_der_datei(rel, datei, veh, segs, entscheidungen, jetzt):
    """(Fahrzeuge [(Ortszeit, v)], Spannen [(von, bis)], rekonstruierte Spannen [(von, bis, Stufe)]) einer Datei."""
    out, spannen, rekon = [], [], []
    for nr, s in enumerate(segs):
        if not s["idx"]:
            continue
        if s.get("bewertung") == "gueltig" and len(s["idx"]) >= MIN_GUELTIG:
            teil = [(t, veh[i][1]) for t, i in zip(s["ortszeit"], s["idx"]) if FRUEHESTENS <= t <= jetzt]
        elif s.get("bewertung") == "werksdatum" and (rel, datei, nr) in entscheidungen:
            delta, stufe = entscheidungen[(rel, datei, nr)]
            teil = [(uhr_rekonstruktion.lokal(veh[i][0] + delta), veh[i][1]) for i in s["idx"]]
            rekon.append((min(t for t, _ in teil), max(t for t, _ in teil), stufe))
        else:
            continue
        if teil:
            out += teil
            spannen.append((min(t for t, _ in teil), max(t for t, _ in teil)))
    return out, spannen, rekon


def strom(dateien, gelesen, entscheidungen, jetzt):
    """Gesamtstrom eines Geraets: ([(Ortszeit, v, Datei-Index)] sortiert, doppelte nur einmal; Spannen [(von, bis)]; rekonstruierte Spannen
    [(von, bis, Stufe, Datei-Index)])."""
    alle, spannen, rekon = [], [], []
    for i, m in enumerate(dateien):
        if (m["rel"], m["datei"]) not in gelesen:
            continue
        veh, segs = gelesen[(m["rel"], m["datei"])]
        fz, sp, rk = fahrzeuge_der_datei(m["rel"], m["datei"], veh, segs, entscheidungen, jetzt)
        alle += [(t, v, i) for t, v in fz]
        spannen += sp
        rekon += [(a, b, st, i) for a, b, st in rk]
    alle.sort()
    out = []
    for x in alle:
        if out and out[-1][0] == x[0] and out[-1][1] == x[1]:
            continue
        out.append(x)
    return out, sorted(spannen), rekon


# ------------------------------------------------------------------ Kandidaten und Aenderung

def _beschnitten(a, b, tag):
    """Laenge (h) des Teils der Luecke (a, b), der im FENSTER des Tages liegt."""
    fa, fb = dt.datetime.combine(tag, dt.time(FENSTER[0])), dt.datetime.combine(tag, dt.time(FENSTER[1]))
    return max(0.0, (min(b, fb) - max(a, fa)).total_seconds() / 3600)


def kandidaten(s):
    """Pausen und ungewoehnliche Werktags-Luecken: [dict(art, von, bis, stunden, ...)]."""
    zeiten = [x[0] for x in s]
    pausen, je_tag = [], {}
    for a, b in zip(zeiten, zeiten[1:]):
        h = (b - a).total_seconds() / 3600
        tags = sum(_beschnitten(a, b, a.date() + i * TAG) for i in range((b.date() - a.date()).days + 1) if werktag(a.date() + i * TAG))
        if h >= PAUSE_H and (tags >= 1.0 or h > PAUSE_LANG_H):
            pausen.append({"art": "pause", "von": a, "bis": b, "stunden": round(h, 1)})
        tag = a.date()
        while tag <= b.date():
            if werktag(tag):
                lb = _beschnitten(a, b, tag)
                if lb > je_tag.get(tag, (0,))[0]:
                    je_tag[tag] = (lb, a, b)
            tag += TAG
    tage = sorted(je_tag)
    out = list(pausen)
    pausen_tage = {p["von"].date() for p in pausen} | {p["bis"].date() for p in pausen}
    for tag in tage:
        lb, a, b = je_tag[tag]
        if lb < MIN_LUECKE_H or (b - a).total_seconds() / 3600 >= PAUSE_H:
            continue
        umkreis = [je_tag[t][0] for t in tage[bisect.bisect_left(tage, tag - UMKREIS_TAGE * TAG):bisect.bisect_right(tage, tag + UMKREIS_TAGE * TAG)]
                   if t != tag and t not in pausen_tage]
        if umkreis and lb > max(umkreis):
            out.append({"art": "luecke", "von": a, "bis": b, "stunden": round((b - a).total_seconds() / 3600, 2),
                        "vorsprung_h": round(lb - max(umkreis), 2)})
    return sorted(out, key=lambda k: k["von"])


def zusammenfassen(kand):
    """Kandidaten, die weniger als ZUSAMMEN_TAGE auseinander liegen, sind ein Umbau (z.B. abends abgebaut, morgens aufgehaengt)."""
    out = []
    for k in kand:
        if out and (k["von"] - out[-1]["bis"]).total_seconds() < ZUSAMMEN_TAGE * 86400:
            v = out[-1]
            out[-1] = dict(v, bis=max(v["bis"], k["bis"]), art="pause" if "pause" in (v["art"], k["art"]) else "luecke",
                           stunden=round((max(v["bis"], k["bis"]) - v["von"]).total_seconds() / 3600, 1), teile=v.get("teile", 1) + 1)
        else:
            out.append(k)
    return out


def tagesaggregate(s):
    """{Werktag: (Histogramm ab KMIN, Fahrzeuge, Stunden mit Fahrzeugen)} fuer FENSTER."""
    out = {}
    for t, v, _i in s:
        if not (FENSTER[0] <= t.hour < FENSTER[1]) or not werktag(t.date()):
            continue
        h, n, std = out.setdefault(t.date(), (collections.Counter(), [0], set()))
        n[0] += 1
        std.add(t.hour)
        if v >= KMIN:
            h[min(v, KMAX) // KBIN] += 1
    return {d: (h, n[0], len(std)) for d, (h, n, std) in out.items()}


def _tage(agg, start, schritt, status, stopp=None):
    """Bis zu TAGE_VERGLEICH Werktage ab start in Richtung schritt (+-1 Tag) mit Ferienstatus status, hoechstens SUCHE_TAGE weit und nicht
    bis zum Tag stopp (dort wurde das Geraet umgehaengt)."""
    out, d = [], start
    for _ in range(SUCHE_TAGE):
        if stopp is not None and (d - stopp).days * schritt >= 0:
            break
        if d in agg and ferien(d) == status and agg[d][2] >= 6:
            out.append(d)
            if len(out) == TAGE_VERGLEICH:
                break
        d += schritt * TAG
    return out


def _seiten(agg, letzter_vor, erster_nach, grenzen):
    """(Tage davor, Tage danach) gleichen Ferienstatus, der Status mit den meisten Tagen auf beiden Seiten; None bei weniger als 3."""
    i = bisect.bisect_right(grenzen, letzter_vor)
    stopp_vor = grenzen[i - 1] if i else None
    j = bisect.bisect_left(grenzen, erster_nach)
    stopp_nach = grenzen[j] if j < len(grenzen) else None
    best = None
    for status in (False, True):
        vor, nach = _tage(agg, letzter_vor, -1, status, stopp_vor), _tage(agg, erster_nach, 1, status, stopp_nach)
        if len(vor) >= 3 and len(nach) >= 3 and (best is None or min(len(vor), len(nach)) > min(len(best[0]), len(best[1]))):
            best = (vor, nach)
    return best


def aenderung(agg, letzter_vor, erster_nach, grenzen=()):
    """Vergleich der Werktage bis letzter_vor mit denen ab erster_nach (siehe Modulkopf). grenzen: sortierte Tage anderer Montagen."""
    best = _seiten(agg, letzter_vor, erster_nach, grenzen)
    if not best:
        return None
    seiten = []
    for tage in best:
        h, n, std = collections.Counter(), 0, 0
        for d in tage:
            h.update(agg[d][0])
            n += agg[d][1]
            std += agg[d][2]
        seiten.append((h, n, std))
    (h1, n1, s1), (h2, n2, s2) = seiten
    m1, m2 = sum(h1.values()), sum(h2.values())
    if m1 < 200 or m2 < 200:
        return None
    tvd = 0.5 * sum(abs(h1[k] / m1 - h2[k] / m2) for k in set(h1) | set(h2))
    mittel = (sum((k * KBIN + 1) * c for k, c in h2.items()) / m2) - (sum((k * KBIN + 1) * c for k, c in h1.items()) / m1)
    return {"tvd": round(tvd, 3), "menge_ln": round(abs(math.log((n2 / s2) / (n1 / s1))), 3),
            "fz_h": [round(n1 / s1), round(n2 / s2)], "tempo_diff": round(mittel, 1), "ferien": ferien(best[0][0])}


def nullverteilung(agg, kand, grenzen=()):
    """Aenderungen an jeder Tagesgrenze (Vortag gegen Tag), ohne Tage naeher als NULL_ABSTAND an einem Kandidaten."""
    nah = set()
    for k in kand:
        t = k["von"].date() - NULL_ABSTAND * TAG
        while t <= k["bis"].date() + NULL_ABSTAND * TAG:
            nah.add(t)
            t += TAG
    out = []
    for tag in sorted(agg):
        if tag not in nah:
            x = aenderung(agg, tag - TAG, tag, grenzen)
            if x:
                out.append((tag, x))
    return out


def _z(wert, werte):
    werte = sorted(werte)
    med = werte[len(werte) // 2]
    mad = sorted(abs(w - med) for w in werte)[len(werte) // 2] * 1.4826 or 1e-3
    return (wert - med) / mad


def bewerten(k, null):
    """Robuster z-Wert der Aenderung gegen die Tagesgrenzen im Umkreis von NULL_TAGE Tagen (mindestens NULL_MIN, sonst alle des Geraets)."""
    if not k.get("aenderung") or not null:
        return None
    lokal = [x for t, x in null if min(abs((t - k["von"].date()).days), abs((t - k["bis"].date()).days)) <= NULL_TAGE]
    if len(lokal) < NULL_MIN:
        lokal, k["null"] = [x for _t, x in null], "geraet"
    return round(max(_z(k["aenderung"][g], [x[g] for x in lokal]) for g in ("tvd", "menge_ln")), 1)


def wochenmuster(kand):
    """Pausen, die sich 7 Tage frueher oder spaeter fast gleich wiederholen (Zeitschaltung oder Uhrfehler, kein Umhaengen)."""
    pausen = [k for k in kand if k["art"] == "pause"]
    for k in pausen:
        for j in pausen:
            if j is not k and abs(abs((j["von"] - k["von"]).total_seconds()) - 7 * 86400) <= 3 * 3600 \
                    and abs(j["stunden"] - k["stunden"]) <= 0.1 * k["stunden"]:
                k["wochenmuster"] = True


def einstufen(k):
    if k.get("wochenmuster"):
        return "wochenmuster"
    if k["art"] == "pause" and k["stunden"] > PAUSE_LANG_H:
        if k.get("z") is None:
            return "inbetriebnahme_ungeprueft"
        return "inbetriebnahme" if k["z"] >= Z_MOEGLICH else "pause_gleicher_ort"
    if k.get("z") is None:
        return "unklar"
    return "umhaengen" if k["z"] >= Z_SICHER else "moeglich" if k["z"] >= Z_MOEGLICH else "besuch"


def montagetage(kand):
    """Sortierte Tage, an denen das Geraet (de)montiert wurde: Beginn und Ende jeder trennenden Bewegung."""
    return sorted({d for k in kand if k["stufe"] in TRENNEN for d in (k["von"].date(), k["bis"].date())})


def geraet_auswerten(x):
    """Kandidaten eines Geraets mit Aenderung, z und Stufe (x: dict mit s); ergaenzt x um agg, null, grenzen, kandidaten."""
    s = x["s"]
    kand = zusammenfassen(kandidaten(s))
    agg = tagesaggregate(s)
    wochenmuster(kand)
    grenzen, null = [], []
    for _durchgang in range(2):  # im zweiten Durchgang reichen die Vergleiche nicht ueber die Montagen des ersten hinweg
        for k in kand:  # der Tag (die Tage) des Kandidaten selbst bleiben aus dem Vergleich
            andere = [d for d in grenzen if not k["von"].date() <= d <= k["bis"].date()]
            neu = aenderung(agg, k["von"].date() - TAG, k["bis"].date() + TAG, andere)
            # liegen zwei Kandidaten so dicht, dass die begrenzten Fenster zu kurz werden, gilt der unbegrenzte Vergleich
            k["aenderung"] = neu if neu is not None or not grenzen else k.get("aenderung")
        null = nullverteilung(agg, kand, grenzen)
        for k in kand:
            k.pop("null", None)
            k["z"] = bewerten(k, null)
            k["stufe"] = einstufen(k)
        grenzen = montagetage(kand)
    x.update(agg=agg, null=null, grenzen=grenzen, kandidaten=kand)


# ------------------------------------------------------------------ Aktionstage

def aktionstage(geraete):
    """{Tag: [Geraet, ...]}: Werktage mit einem Umhaengen oder einer Inbetriebnahme mit z >= Z_STARK (Ende der Luecke)."""
    out = collections.defaultdict(list)
    for x in geraete:
        for k in x["kandidaten"]:
            if k["stufe"] in ("umhaengen", "inbetriebnahme") and (k.get("z") or 0) >= Z_STARK and werktag(k["bis"].date()):
                out[k["bis"].date()].append(x["geraet"])
    return dict(out)


def schwache_pruefen(geraete, tage):
    """Umhaengen mit z unter Z_STARK gilt nur an einem Aktionstag (+-1 Tag), sonst ist es moeglich (Ferienbeginn, Feiertage und Wetter
    erreichen solche Werte auch)."""
    for x in geraete:
        for k in x["kandidaten"]:
            if k["stufe"] == "umhaengen" and k["z"] < Z_STARK:
                if any(abs((k["bis"].date() - d).days) <= 1 for d in tage):
                    k["am_aktionstag"] = True
                else:
                    k["stufe"] = "moeglich"


def laengste_luecke(s, tag):
    """(von, bis, Minuten) der laengsten Luecke im FENSTER eines Tages, wenn sie mindestens MIN_STELLE_MIN Minuten lang ist, sonst None."""
    a, b = dt.datetime.combine(tag, dt.time(FENSTER[0])), dt.datetime.combine(tag, dt.time(FENSTER[1]))
    zeiten = [x[0] for x in s]
    reihe = [a] + zeiten[bisect.bisect_left(zeiten, a):bisect.bisect_left(zeiten, b)] + [b]
    x, y = max(zip(reihe, reihe[1:]), key=lambda p: p[1] - p[0])
    minuten = (y - x).total_seconds() / 60
    return (x, y, round(minuten)) if minuten >= MIN_STELLE_MIN else None


def stufe2(geraete, tage):
    """Fuer jedes Geraet und jeden Aktionstag ohne eigenes sicheres Ereignis (+-1 Tag): aendert sich der Verkehr ueber den Tag hinweg?"""
    for x in geraete:
        eigene = {k["bis"].date() for k in x["kandidaten"] if k["stufe"] in TRENNEN}
        for tag in sorted(tage):
            if x["geraet"] in tage[tag] or any(abs((tag - d).days) <= 1 for d in eigene):
                continue
            if tag not in x["agg"] and tag - TAG not in x["agg"]:
                continue
            k = {"art": "aktionstag", "von": dt.datetime.combine(tag, dt.time(FENSTER[0])), "bis": dt.datetime.combine(tag, dt.time(FENSTER[1])),
                 "aenderung": aenderung(x["agg"], tag - TAG, tag + TAG, x["grenzen"])}
            k["z"] = bewerten(k, x["null"])
            if k["z"] is None or k["z"] < Z_MOEGLICH:
                continue
            lu = laengste_luecke(x["s"], tag)
            if not lu:  # ohne Unterbrechung laesst sich kein Display umhaengen
                continue
            k.update(von=lu[0], bis=lu[1], stunden=round(lu[2] / 60, 2), stufe="aktionstag", mit=tage[tag])
            x["kandidaten"].append(k)
        x["kandidaten"].sort(key=lambda k: k["von"])


# ------------------------------------------------------------------ Tagesprobe

def _verteilung(agg, tage):
    h = collections.Counter()
    for d in tage:
        h.update(agg[d][0])
    n = sum(h.values())
    k = (KMAX // KBIN) + 1
    return {b: (h[b] + 0.5) / (n + 0.5 * k) for b in range(k)}


def _stundenprofil(s, tage):
    """{Stunde: Fahrzeuge (ab KMIN) je Minute} im Mittel der Tage."""
    tage = set(tage)
    c = collections.Counter(t.hour for t, v, _i in s if t.date() in tage and v >= KMIN and FENSTER[0] <= t.hour < FENSTER[1])
    return {h: (c[h] + 0.5) / (60.0 * len(tage)) for h in range(FENSTER[0], FENSTER[1])}


def _integral(lv, ln, a, b, luecke):
    """Integral von (lambda_vor - lambda_nach) ueber [a, b] ohne die Luecke (Minuten-Raster)."""
    out, t = 0.0, a
    while t < b:
        e = min(b, t.replace(minute=0, second=0, microsecond=0) + STUNDE)
        dauer = (e - t).total_seconds() / 60
        ueberlapp = max(0.0, (min(e, luecke[1]) - max(t, luecke[0])).total_seconds() / 60)
        out += (lv[t.hour] - ln[t.hour]) * (dauer - ueberlapp)
        t = e
    return out


def tagesprobe(x, k, rng):
    """Wechselpunkt im Tag. Je Fahrzeug d = log p_vor(v)/p_nach(v) plus sein Beitrag zum Poisson-Prozess der Fahrzeuge (log
    lambda_vor(t)/lambda_nach(t) und die erwartete Zahl seit dem vorigen Fahrzeug, ohne die Luecke)."""
    tag = k["bis"].date()
    if k["von"].date() != tag:
        return None
    seiten = _seiten(x["agg"], tag - TAG, tag + TAG, [d for d in x["grenzen"] if d != tag])
    if not seiten:
        return None
    pv, pn = _verteilung(x["agg"], seiten[0]), _verteilung(x["agg"], seiten[1])
    lv, ln = _stundenprofil(x["s"], seiten[0]), _stundenprofil(x["s"], seiten[1])
    a, b = dt.datetime.combine(tag, dt.time(FENSTER[0])), dt.datetime.combine(tag, dt.time(FENSTER[1]))
    luecke = (k["von"], k["bis"])
    fz, vorig = [], a
    for t, v, _i in x["s"]:
        if not (a <= t < b and v >= KMIN):
            continue
        w = math.log(pv[min(v, KMAX) // KBIN] / pn[min(v, KMAX) // KBIN])
        w += math.log(lv[t.hour] / ln[t.hour]) - _integral(lv, ln, vorig, t, luecke)
        fz.append((t, w))
        vorig = t
    if len(fz) < 20:
        return None
    d = [w for _t, w in fz]
    rest = -_integral(lv, ln, vorig, b, luecke)  # gehoert immer zur Seite danach
    gesamt = sum(d) + rest

    def bester(werte):
        kum, best, bi = 0.0, -1e9, 0
        for i, w in enumerate(werte):
            kum += w
            s = 2 * kum - gesamt
            if s > best:
                best, bi = s, i + 1
        return best, bi

    s_max, i = bester(d)
    p = sum(1 for _ in range(PERMUTATIONEN) if bester(rng.sample(d, len(d)))[0] >= s_max) / PERMUTATIONEN
    schnitt = fz[i][0] if i < len(fz) else b
    vorher, nachher = d[:i], d[i:] + [rest]
    abstand = max(0.0, (k["von"] - schnitt).total_seconds(), (schnitt - k["bis"]).total_seconds()) / 60
    stimmig = (p <= P_TAG and vorher and nachher and sum(vorher) / len(vorher) > 0 and sum(nachher) / len(nachher) < 0
               and abstand <= NAEHE_MIN)
    return {"schnitt": schnitt, "p": p, "abstand_min": round(abstand), "stimmig": bool(stimmig)}


def tagesproben(geraete):
    """Tagesprobe fuer jedes Umhaengen und jeden Aktionstag mit Luecke am selben Tag. Nicht stimmig: der Aktionstag faellt weg, das Umhaengen
    wird zum Eingriff. Luecken ueber Nacht behalten ihre Einstufung."""
    rng = random.Random(1)
    for x in geraete:
        behalten = []
        for k in x["kandidaten"]:
            if k["stufe"] in ("umhaengen", "aktionstag") and k["von"].date() == k["bis"].date():
                k["tagesprobe"] = tagesprobe(x, k, rng)
                if not (k["tagesprobe"] and k["tagesprobe"]["stimmig"]):
                    if k["stufe"] == "aktionstag":
                        continue
                    k["stufe"] = "eingriff"
            behalten.append(k)
        x["kandidaten"] = behalten


def erkennen(geraete):
    """Bewegungen aller Geraete (x: dict mit geraet, s); gibt die Aktionstage zurueck."""
    for x in geraete:
        geraet_auswerten(x)
    tage = aktionstage(geraete)
    schwache_pruefen(geraete, tage)
    stufe2(geraete, tage)
    tagesproben(geraete)
    return tage


def konfidenz(k):
    """Wie genau ist der Beginn eines Aufenthalts bekannt?"""
    if not k:
        return "ungeprueft"
    if k["stufe"] == "umhaengen":
        return "transportluecke" if k["z"] >= Z_STARK else "transportluecke_aktionstag"
    return {"aktionstag": "aktionstag", "inbetriebnahme": "inbetriebnahme"}.get(k["stufe"], "ungeprueft")


# ------------------------------------------------------------------ Aufenthalte

def merkmal(fz):
    """Merkmale fuer die Zuordnung (einsaetze.py): Werktage ausserhalb von Ferien und Feiertagen, FENSTER: Tempoverteilung (2-km/h-Klassen ab
    KMIN bis KMAX), Fahrzeuge je Stunde, V85, Zahl der Tage."""
    h, n, std, v = collections.Counter(), 0, set(), []
    for t, x in fz:
        if t.weekday() >= 5 or kalender.besonderer_tag(t.date()) or not FENSTER[0] <= t.hour < FENSTER[1]:
            continue
        n += 1
        std.add((t.date(), t.hour))
        if x >= KMIN:
            h[min(x, KMAX) // KBIN] += 1
            v.append(x)
    v.sort()
    return {"hist": {str(k): c for k, c in sorted(h.items())}, "fz_h": round(n / len(std), 2) if std else 0,
            "v85": v[int(0.85 * len(v))] if v else None, "n": len(v), "tage": len({d for d, _h in std})}


def stunden(fz, spannen, von, bis):
    """Stunden eines Zeitraums im Format des Rohaggregats: ([[Datum, Stunde, UTC-Versatz, voll, [km/h, Anzahl, ...]]] mit Fahrzeugen,
    [[Datum, Stunde]] vollstaendig aufgezeichneter Stunden ohne Fahrzeug). voll: die Stunde liegt ganz in einer Spanne und in [von, bis]."""
    je = collections.defaultdict(collections.Counter)
    for t, v in fz:
        je[t.replace(minute=0, second=0, microsecond=0)][v] += 1
    voll = set()
    for a, b in spannen:
        a, b = max(a, von), min(b, bis)
        h = a.replace(minute=0, second=0, microsecond=0)
        if h < a:
            h += STUNDE
        while h + STUNDE <= b:
            voll.add(h)
            h += STUNDE
    zeilen = []
    for h in sorted(je):
        flach = []
        for v in sorted(je[h]):
            flach += [v, je[h][v]]
        zeilen.append([h.date().isoformat(), h.hour, dsd2csv.utc_versatz_h(dsd2csv.ortszeit_zu_utc(h)), 1 if h in voll else 0, flach])
    leer = [[h.date().isoformat(), h.hour] for h in sorted(voll - set(je))]
    return zeilen, leer


def aufenthalte(x, limits):
    """Aufenthalte zwischen trennenden Bewegungen, je mit Bruechen, Teilen, Stunden und Tagen je Datei. limits: Tempolimit je Datei-Index."""
    s, dateien = x["s"], x["dateien"]
    zeiten = [t for t, _v, _i in s]
    grenzen = [k for k in x["kandidaten"] if k["stufe"] in TRENNEN]
    starts = [(zeiten[0], None)] + [(k["bis"], k) for k in grenzen]
    enden = [(k["von"], k) for k in grenzen] + [(zeiten[-1], None)]
    out = []
    for (a, kb), (b, ke) in zip(starts, enden):
        teil = s[bisect.bisect_left(zeiten, a):bisect.bisect_right(zeiten, b)]
        if not teil:
            continue
        fz = [(t, v) for t, v, _i in teil]
        sp = [(max(p, a), min(q, b)) for p, q in x["spannen"] if q >= a and p <= b]
        je_datei = collections.Counter(i for _t, _v, i in teil)
        haupt = je_datei.most_common(1)[0][0]
        lim = limits.get(haupt)
        br = bruch.erkenne(fz, sp, max(10, int(round(0.5 * lim))) if lim else 15, lim, kalender.besonderer_tag)
        brueche = [{"datum": b_["datum"], "wahrscheinlichkeit": b_.get("wahrscheinlichkeit")} for b_ in br.get("brueche") or []] \
            if br.get("geprueft") else []
        # Teile zwischen den Bruechen (Grenze: Mitternacht vor dem Bruchtag)
        schnitte = [dt.datetime.combine(dt.date.fromisoformat(b_["datum"]), dt.time()) for b_ in brueche]
        teile = []
        for j, (p, q) in enumerate(zip([a] + schnitte, schnitte + [b])):
            tz = [(t, v, i) for t, v, i in teil if p <= t < q or (j == len(schnitte) and t == q)]
            if tz:  # von, bis: erstes und letztes Fahrzeug
                teile.append({"von": tz[0][0], "bis": tz[-1][0], "tage": len({t.date() for t, _v, _i in tz}), "fahrzeuge": len(tz),
                              "dateien": _je_datei(tz, dateien, x["rekon"]), "merkmal": merkmal([(t, v) for t, v, _i in tz])})
        zeilen, leer = stunden(fz, sp, a, b)
        out.append({"nr": len(out) + 1, "von": a, "bis": b, "beginn": _bewegung(kb), "ende": _bewegung(ke), "konfidenz": konfidenz(kb),
                    "tage": len({t.date() for t, _v, _i in teil}), "fahrzeuge": len(teil), "limit": lim, "dateien": _je_datei(teil, dateien, x["rekon"]),
                    "brueche": brueche, "teile": teile, "zeilen": zeilen, "voll_ohne_fahrzeuge": leer})
    return out


def _je_datei(tz, dateien, rekon):
    """{Messung: dict(fahrzeuge, tage, von, bis, rekonstruiert)} der Fahrzeuge tz [(Zeit, v, Datei-Index)]."""
    out = {}
    for i in sorted({i for _t, _v, i in tz}):
        zeiten = [t for t, _v, j in tz if j == i]
        spannen = [(p, q) for p, q, _st, r in rekon if r == i]
        out[dateien[i]["id"]] = {"fahrzeuge": len(zeiten), "tage": len({t.date() for t in zeiten}), "von": zeiten[0], "bis": zeiten[-1],
                                 "rekonstruiert": sum(1 for t in zeiten if any(p <= t <= q for p, q in spannen))}
    return out


def _bewegung(k):
    """Kurzfassung einer Bewegung fuer einsaetze.json."""
    if not k:
        return None
    a = k.get("aenderung") or {}
    tp = k.get("tagesprobe") or {}
    return {"stufe": k["stufe"], "art": k["art"], "von": k["von"], "bis": k["bis"], "z": k.get("z"), "konfidenz": konfidenz(k),
            "fz_h": a.get("fz_h"), "tempo_diff": a.get("tempo_diff"), "tvd": a.get("tvd"),
            **({"tagesprobe": tp["schnitt"]} if tp.get("stimmig") else {}), **({"mit": k["mit"]} if k.get("mit") else {})}


# ------------------------------------------------------------------ Ablauf

def _dateien_je_geraet(auswertung):
    je = collections.defaultdict(list)
    for r in auswertung["standorte"]:
        g = (r.get("geraet") or "").strip()
        if g:  # auch die stationaeren Geraete (Villestrasse: ein Geraet je Fahrtrichtung)
            je[g].append({"rel": r["standort"], "datei": r["datei"], "id": seiten_bauen.messung_id(r["standort"], r["datei"]),
                          "limit": r.get("tempolimit_kmh")})
    return je


def _laeufe(je_dateien, gelesen, entscheidungen, jetzt):
    geraete = []
    for g, dateien in sorted(je_dateien.items()):
        s, spannen, rekon = strom(dateien, gelesen, entscheidungen, jetzt)
        if s:
            geraete.append({"geraet": g, "dateien": dateien, "s": s, "spannen": spannen, "rekon": rekon})
    return geraete, erkennen(geraete)


def rechnen(auswertung, gelesen, jetzt=None):
    """Bewegungen und Aufenthalte aller Geraete. gelesen: {(Ordner, Datei): (Fahrzeuge, Uhr-Segmente mit Bewertung)} aller DSD-Dateien.
    Gibt ein JSON-faehiges dict zurueck (Zeiten als ISO-Text)."""
    jetzt = jetzt or dt.datetime.now()
    profile = [uhr_belege.merkmale(s, veh) for veh, segs in gelesen.values() for s in segs
               if s.get("bewertung") in ("gueltig", "auffaellig", "werksdatum") and s["idx"]]
    vorlage, referenz, _ = uhr_belege.referenzen(profile)
    je_dateien = _dateien_je_geraet(auswertung)
    # erster Lauf ohne rekonstruierte Uhren: Montagetage als Anker der Rekonstruktion
    geraete, _tage = _laeufe(je_dateien, gelesen, {}, jetzt)
    montage = {k["bis"].date() for x in geraete for k in x["kandidaten"] if k["stufe"] in ("umhaengen", "inbetriebnahme", "aktionstag")}
    segmente = collections.defaultdict(list)
    for g, dateien in je_dateien.items():
        for m in dateien:
            if (m["rel"], m["datei"]) in gelesen:
                veh, segs = gelesen[(m["rel"], m["datei"])]
                segmente[g] += [uhr_rekonstruktion.segment(m["rel"], m["datei"], nr, s, veh) for nr, s in enumerate(segs) if s["idx"]]
    rekon = uhr_rekonstruktion.rekonstruieren(segmente, vorlage, referenz, montage)
    entscheidungen = {(e["rel"], e["datei"], e["abschnitt"]): (dt.timedelta(seconds=e["delta_s"]), e["stufe"])
                      for e in rekon if e.get("stufe") in REKONSTRUIERT}
    geraete, tage = _laeufe(je_dateien, gelesen, entscheidungen, jetzt)
    return _json({"aktionstage": {d.isoformat(): g for d, g in sorted(tage.items())},
                  "geraete": [geraet_ausgabe(x, [e for e in rekon if e["geraet"] == x["geraet"]]) for x in geraete]})


def geraet_ausgabe(x, rekon=()):
    """Ergebnis eines Geraets nach erkennen(): Bewegungen, Aufenthalte, Rekonstruktionen (Zeiten noch als datetime)."""
    return {"geraet": x["geraet"], "dateien": [{k: m[k] for k in ("id", "rel", "datei")} for m in x["dateien"]], "fahrzeuge": len(x["s"]),
            "bewegungen": [_bewegung(k) for k in x["kandidaten"] if k["stufe"] in TRENNEN + ("eingriff", "pause_gleicher_ort", "moeglich")],
            "aufenthalte": aufenthalte(x, {i: m.get("limit") for i, m in enumerate(x["dateien"])}), "rekonstruktion": list(rekon)}


def _json(x):
    if isinstance(x, dict):
        return {k: _json(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_json(v) for v in x]
    if isinstance(x, (dt.datetime, dt.date)):
        return x.isoformat()
    return x


def berechnen(auswertung, wurzel, cache=None):
    """rechnen() fuer alle DSD-Dateien unter wurzel, mit Zwischenspeicher (Ebene 'bewegungen', Schluessel aus Inhalt der Dateien, Geraeten
    und Tempolimits der Auswertung und Code; nicht aus dem Tag: Zeiten nach dem Tag der Rechnung sind Uhr-Muell und bleiben es). Gibt
    (Ergebnis, benutzte Eintraege des Zwischenspeichers) zurueck."""
    pfade = []
    for ordner, _, namen in sorted(os.walk(wurzel)):
        for f in sorted(namen):
            if f.lower().endswith(".dsd"):
                pfade.append(os.path.join(ordner, f))
    h = hashlib.sha256()
    for p in pfade:
        with open(p, "rb") as fh:
            h.update(os.path.relpath(p, wurzel).encode("utf-8") + hashlib.sha256(fh.read()).digest())
    for r in auswertung["standorte"]:
        h.update(f'{r["standort"]}/{r["datei"]}|{r.get("geraet")}|{r.get("tempolimit_kmh")}'.encode("utf-8"))
    sp = zwischenspeicher.Zwischenspeicher(cache) if cache else None
    schl = None
    if sp:
        code = zwischenspeicher.code_hash(*[os.path.join(HIER, f) for f in CODE_DATEIEN])
        schl = zwischenspeicher.inhalts_hash(h.digest(), code)
        erg = sp.holen("bewegungen", schl)
        if erg is not None:
            return erg, sp.benutzt
    gelesen = {(rel, f): (veh, segs) for rel, f, segs, veh, _hb in uhr_belege.sammle(wurzel)}
    erg = rechnen(auswertung, gelesen)
    if sp:
        sp.speichern("bewegungen", schl, erg)
    return erg, sp.benutzt if sp else set()
