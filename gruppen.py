# SPDX-License-Identifier: MIT
"""Zellen fuer die Auswahl auf den Detailseiten (Tagschluessel x Stunde) und die Zeitscheiben der Tageszeit.

Eine Zelle ist das Histogramm der Fahrzeuge einer Kombination aus Tagschluessel (Montag bis Sonntag, Feiertag) und Stunde, nur aus
vollstaendig aufgezeichneten Stunden mit nutzbarer Zeit. Die Detailseiten rechnen daraus jede Auswahl (Tageszeit, Tage) im Browser.

Frueher stand hier auch die Zerlegung der Verteilung in Lognormal-Gruppen ("Formgruppen"); sie ist seit Oktober 2026 entfernt
(abgeloest durch die Abschnitte und die Verhaltensgruppen, docs/gruppen.md).
"""
import collections
import datetime as dt

import rauschen

# Zeitscheiben (Ortszeit): Name, von, bis (Stunde, bis exklusiv); der Schulweg (7-8 Uhr, Mo-Fr) steht in dsd2csv.TEILZEITRAEUME
ZEITSCHEIBEN = [("nacht", 22, 6), ("vormittag", 6, 12), ("nachmittag", 12, 19), ("abend", 19, 22)]
TAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag", "Feiertag"]  # Schluessel 0-7


def stunden(von, bis):
    """Stunden einer Zeitscheibe: stunden(22, 6) -> [22, 23, 0, 1, 2, 3, 4, 5]."""
    return [(von + i) % 24 for i in range((bis - von) % 24 or 24)]


# ------------------------------------------------------------------ Tage und Zellen

_FEIERTAGE = {}


def tagschluessel(zeit):
    """0-6 Montag bis Sonntag, 7 Feiertag (gesetzlicher Feiertag in NRW, der kein Sonntag ist)."""
    if zeit.weekday() == 6:
        return 6
    if zeit.year not in _FEIERTAGE:
        _FEIERTAGE[zeit.year] = rauschen.feiertage_nrw(zeit.year)
    return 7 if zeit.date() in _FEIERTAGE[zeit.year] else zeit.weekday()


def zellen_bauen(vorher, nachher, spannen, stunden_filter=None):
    """Zellen (Tagschluessel, Stunde) mit Histogrammen der Fahrzeuge in vollstaendig aufgezeichneten Stunden.

    vorher: [(Ortszeit, v)] mit nutzbarer Zeit vor dem Abzug des Rauschbodens, nachher: dieselbe Liste danach (gleiche Objekte,
    Teilmenge). stunden_filter: nur (Datum, Stunde), fuer die er True liefert (etwa trockene Stunden). Gibt dict mit D (abgedeckte
    Stunden je Zelle), z (Fahrzeuge je Zelle und Geschwindigkeit) und r (der herausgerechnete Rauschboden) zurueck.
    """
    abgedeckt = rauschen.abgedeckte_stunden(spannen)
    if stunden_filter is not None:  # etwa nur trockene Stunden (Auswahl auf der Detailseite)
        abgedeckt = {x for x in abgedeckt if stunden_filter(x)}
    behalten = {id(f) for f in nachher}
    D = collections.Counter()
    for datum, h in abgedeckt:
        D[(tagschluessel(dt.datetime(datum.year, datum.month, datum.day)), h)] += 1
    z = collections.defaultdict(collections.Counter)
    r = collections.defaultdict(collections.Counter)
    for f in vorher:
        t, v = f
        if (t.date(), t.hour) not in abgedeckt:
            continue
        zelle = (tagschluessel(t), t.hour)
        if id(f) in behalten:
            z[zelle][v] += 1
        else:
            r[zelle][v] += 1
    return {"D": D, "z": z, "r": r}


def zelle_kodiert(c):
    """Counter -> [v, n, v, n, ...] aufsteigend."""
    out = []
    for v in sorted(c):
        out += [v, c[v]]
    return out


def zellen_json(zd):
    """Die Zellen von zellen_bauen fuer die Datentabelle der Detailseite: {tage, z, r} mit Schluesseln 'Tag|Stunde'."""
    return {"tage": {f"{d}|{h}": c for (d, h), c in sorted(zd["D"].items()) if c},
            "z": {f"{d}|{h}": zelle_kodiert(c) for (d, h), c in sorted(zd["z"].items())},
            "r": {f"{d}|{h}": zelle_kodiert(c) for (d, h), c in sorted(zd["r"].items()) if c}}


def datentabelle(zd, limit):
    """Datentabelle der Detailseite (Version, Tempolimit, Zellen) oder None ohne Fahrzeuge in vollstaendig aufgezeichneten Stunden."""
    if not any(zd["z"].values()):
        return None
    return {"v": 1, "limit": limit, **zellen_json(zd)}
