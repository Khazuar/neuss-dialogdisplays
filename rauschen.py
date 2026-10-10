# SPDX-License-Identifier: MIT
"""Rauschbodenschaetzer: Messwerte, deren Rate nicht vom Verkehr abhaengt.

Die Geraete zeichnen auch sehr langsame Werte auf (Fussgaenger, Tiere, Echos, Stoerungen; was es ist, sagen die Daten
nicht). Statt einer festen Mindestgeschwindigkeit wird fuer jede Datei geschaetzt, welcher Teil der Messwerte
verkehrsunabhaengig ist, und dieser Teil aus der Auswertung herausgerechnet. Verfahren und Grenzen: docs/rauschen.md.

Modell: Je Zelle (Tagtyp, Stunde) gilt fuer die Fahrten je Stunde mit Geschwindigkeit v
    y(v, Zelle) = a(v) + b(v) * T(Zelle).
T(Zelle) = Fahrten je Stunde ab der Verkehrsschwelle vT (echter Verkehr). a(v) ist die verkehrsunabhaengige Rate
(Rauschboden), b(v) der verkehrsgebundene Teil. a(v) zaehlt nur, wenn es mindestens SIGMA Standardfehler ueber 0 liegt.
Nur der Zeitverlauf wird genutzt, keine Annahme ueber die Form der Verteilung.
"""
import collections
import datetime as dt
import math

SIGMA = 3.0  # a(v) zaehlt nur ab so vielen Standardfehlern ueber 0
MIN_TAGE = 3  # Zellen mit weniger abgedeckten Stunden werden nicht verwendet
MIN_FAHRZEUGE = 3000  # kleinere Dateien werden nicht geprueft
OBERGRENZE_KMH = 15  # das Rauschen gilt nur als belegt, wenn 95 % davon darunter liegen
INSTABIL_PP = 0.015  # Haelften gerade/ungerade Tage weichen um mehr als so viel (Anteil) ...
INSTABIL_REL = 0.5  # ... und um mehr als diesen Teil des groesseren Werts ab: nicht belegt
TYPEN = ("Werktag", "Samstag", "Sonn-/Feiertag")


# ------------------------------------------------------------------ Tagtyp

def ostern(jahr):
    """Ostersonntag (Gaussche Osterformel, anonym-gregorianisch)."""
    a, b, c = jahr % 19, jahr // 100, jahr % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    monat = (h + l - 7 * m + 114) // 31
    tag = (h + l - 7 * m + 114) % 31 + 1
    return dt.date(jahr, monat, tag)


def feiertage_nrw(jahr):
    o = ostern(jahr)
    t = dt.timedelta
    return {dt.date(jahr, 1, 1), o - t(days=2), o + t(days=1), dt.date(jahr, 5, 1), o + t(days=39), o + t(days=50),
            o + t(days=60), dt.date(jahr, 10, 3), dt.date(jahr, 11, 1), dt.date(jahr, 12, 25), dt.date(jahr, 12, 26)}


_FEIERTAGE = {}


def tagtyp(zeit):
    """'Werktag', 'Samstag' oder 'Sonn-/Feiertag' (gesetzliche Feiertage in NRW)."""
    if zeit.year not in _FEIERTAGE:
        _FEIERTAGE[zeit.year] = feiertage_nrw(zeit.year)
    if zeit.weekday() == 6 or zeit.date() in _FEIERTAGE[zeit.year]:
        return "Sonn-/Feiertag"
    return "Samstag" if zeit.weekday() == 5 else "Werktag"


# ------------------------------------------------------------------ Zellen

def abgedeckte_stunden(spannen):
    """Menge der (Datum, Stunde), die vollstaendig in einem Abschnitt mit nutzbarer Zeit liegen."""
    s = set()
    for a, b in spannen:
        h = a.replace(minute=0, second=0, microsecond=0)
        if h < a:
            h += dt.timedelta(hours=1)
        while h + dt.timedelta(hours=1) <= b:
            s.add((h.date(), h.hour))
            h += dt.timedelta(hours=1)
    return s


def zellen(fahrten, spannen, tage_filter=None):
    """(counts, D): counts[(typ, stunde)][v] Fahrzeuge, D[(typ, stunde)] Anzahl abgedeckter Stunden (Tage)."""
    abd = abgedeckte_stunden(spannen)
    if tage_filter is not None:
        abd = {x for x in abd if tage_filter(x[0])}
    D = collections.Counter()
    for datum, h in abd:
        D[(tagtyp(dt.datetime(datum.year, datum.month, datum.day)), h)] += 1
    counts = collections.defaultdict(collections.Counter)
    for t, v in fahrten:
        if (t.date(), t.hour) in abd:
            counts[(tagtyp(t), t.hour)][v] += 1
    return counts, D


# ------------------------------------------------------------------ Schaetzung

def wls(xs, ys, ws, iterationen=3):
    """y = a + b x mit a, b >= 0 (gewichtete kleinste Quadrate mit Poisson-Gewichten). Gibt (a, b, se_a) zurueck."""
    n = len(xs)
    lam = [max(y, 1e-3) for y in ys]
    a = b = 0.0
    for _ in range(iterationen):
        w = [wi / l for wi, l in zip(ws, lam)]
        sw = sum(w)
        sx = sum(wi * x for wi, x in zip(w, xs))
        sy = sum(wi * y for wi, y in zip(w, ys))
        sxx = sum(wi * x * x for wi, x in zip(w, xs))
        sxy = sum(wi * x * y for wi, x, y in zip(w, xs, ys))
        det = sw * sxx - sx * sx
        if det <= 0 or sxx <= 0:
            return 0.0, 0.0, float("nan")
        b = (sw * sxy - sx * sy) / det
        a = (sy - b * sx) / sw
        if a < 0:
            a, b = 0.0, max(sxy / sxx, 0.0)
        if b < 0:
            a, b = max(sy / sw, 0.0), 0.0
        lam = [max(a + b * x, 1e-3) for x in xs]
    w = [wi / l for wi, l in zip(ws, lam)]
    sw = sum(w)
    sx = sum(wi * x for wi, x in zip(w, xs))
    sxx = sum(wi * x * x for wi, x in zip(w, xs))
    det = sw * sxx - sx * sx
    phi = max(sum(wi * (y - (a + b * x)) ** 2 for wi, x, y in zip(w, xs, ys)) / max(n - 2, 1), 1.0)  # Ueberstreuung
    se = math.sqrt(phi * sxx / det) if det > 0 else float("nan")
    return a, b, se


def verkehrsschwelle(limit):
    return max(0.7 * limit, 15) if limit else 20


def schaetzen(counts, D, limit):
    """Schaetzt a(v) fuer v unterhalb der Verkehrsschwelle. Gibt dict mit 'a' (v -> Rate je Stunde), 'keys', 'vT' zurueck."""
    vt = verkehrsschwelle(limit)
    keys = [k for k in D if D[k] >= MIN_TAGE]
    T = {k: sum(n for v, n in counts[k].items() if v >= vt) / D[k] for k in keys}
    a = {}
    for v in range(0, int(vt)):
        ys = [counts[k].get(v, 0) / D[k] for k in keys]
        if not any(ys):
            continue
        aa, bb, se = wls([T[k] for k in keys], ys, [D[k] for k in keys])
        if aa >= SIGMA * se and aa > 0:  # nan > 0 ist falsch: ohne Standardfehler kein Rauschen
            a[v] = aa
    return {"vT": vt, "a": a, "keys": keys}


def anteil(est, counts, D):
    """Anteil der Fahrzeuge in den verwendeten Zellen, die zum Rauschboden gehoeren."""
    gesamt = sum(n for k in est["keys"] for n in counts[k].values())
    stunden = sum(D[k] for k in est["keys"])
    return sum(est["a"].values()) * stunden / gesamt if gesamt else 0.0


def lage(est):
    """(Mittel, 95-%-Grenze) der Rauschmasse in km/h, None ohne Rauschen."""
    masse = sorted(est["a"].items())
    s = sum(m for _, m in masse)
    if not s:
        return None, None
    mittel, cum, q95 = sum(v * m for v, m in masse) / s, 0.0, masse[-1][0]
    for v, m in masse:
        cum += m
        if cum >= 0.95 * s:
            q95 = v
            break
    return mittel, q95


def pruefen(fahrten, spannen, limit):
    """Schaetzt und bewertet den Rauschboden einer Datei. fahrten: [(Ortszeit, v)] mit nutzbarer Zeit.

    Gibt None zurueck, wenn die Datei zu klein ist. Sonst ein dict mit den Kennzahlen und 'belegt' (True: wird
    abgezogen) samt 'grund'; unter '_modell' liegt, was fuer den Abzug gebraucht wird.
    """
    if limit is None or len(fahrten) < MIN_FAHRZEUGE:
        return None
    counts, D = zellen(fahrten, spannen)
    est = schaetzen(counts, D, limit)
    if not est["keys"]:
        return None
    a_ges = anteil(est, counts, D)
    mittel, q95 = lage(est)
    tage = sorted({t.date() for t, _ in fahrten})
    gerade = {t for i, t in enumerate(tage) if i % 2 == 0}
    haelften = []
    for filt in (lambda d: d in gerade, lambda d: d not in gerade):
        c2, d2 = zellen(fahrten, spannen, filt)
        e2 = schaetzen(c2, d2, limit)
        haelften.append(anteil(e2, c2, d2) if e2["keys"] else 0.0)
    unterschied = abs(haelften[0] - haelften[1])
    stabil = not (unterschied > INSTABIL_PP and unterschied > INSTABIL_REL * max(haelften))
    if not est["a"]:
        belegt, grund = False, "kein verkehrsunabhaengiger Rauschboden nachweisbar"
    elif q95 > OBERGRENZE_KMH:
        belegt, grund = False, f"reicht bis {q95} km/h (mehr als {OBERGRENZE_KMH}), nicht von langsamem Verkehr zu trennen"
    elif not stabil:
        belegt, grund = False, "Anteil in den Haelften (gerade/ungerade Tage) nicht stabil"
    else:
        belegt, grund = True, None
    stunden = sum(D[k] for k in est["keys"])
    vmax = max(est["a"]) if est["a"] else 0
    vs = range(min(est["a"]), vmax + 1) if est["a"] else range(0)
    ergebnis = {
        "belegt": belegt, "grund": grund, "anteil": a_ges, "mittel_kmh": mittel, "obergrenze_kmh": q95, "stabil": stabil,
        "anteil_haelften": haelften, "verkehrsschwelle_kmh": est["vT"], "stunden": stunden,
        "_modell": {"est": est, "counts": counts, "D": D},
    }
    if est["a"]:
        ergebnis["spektrum"] = {
            "ab_kmh": vs[0],
            "rausch": [round(1000 * est["a"].get(v, 0)) for v in vs],
            "alle": [round(1000 * sum(counts[k].get(v, 0) for k in est["keys"]) / stunden) for v in vs],
        }
    return ergebnis


# ------------------------------------------------------------------ Abzug

def _duenne(gruppen, erwartet):
    """Entfernt je Gruppe etwa 'erwartet' Elemente (gleichmaessig verteilt; Rundungsreste laufen in die naechste Gruppe).

    gruppen: {schluessel: [element, ...]} (Reihenfolge der Elemente = Zeitreihenfolge), erwartet: {schluessel: float}.
    Gibt die Menge der entfernten Elemente (id) zurueck.
    """
    weg, rest = set(), 0.0
    for k in sorted(gruppen, key=repr):
        liste = gruppen[k]
        rest += erwartet.get(k, 0.0)
        n = min(int(rest), len(liste))
        rest -= n
        for i in range(n):
            weg.add(id(liste[int((i + 0.5) * len(liste) / n)]))
    return weg


def anteile_zelle(modell):
    """p[(typ, stunde, v)] = Wahrscheinlichkeit, dass ein Fahrzeug dieser Zelle und Geschwindigkeit Rauschen ist."""
    est, counts, D = modell["est"], modell["counts"], modell["D"]
    p = {}
    for k in est["keys"]:
        for v, n in counts[k].items():
            a = est["a"].get(v)
            if a:
                p[(k[0], k[1], v)] = min(1.0, a * D[k] / n)
    return p


def anteile_je_v(modell):
    """p[v] = Rauschanteil bei Geschwindigkeit v ueber alle verwendeten Zellen.

    Wie beim Abzug je Zelle kann in einer Zelle nicht mehr entfernt werden, als dort gemessen wurde (nachts liegt die
    Rate des Rauschens oft unter dem Mittel). Beide Abzuege entfernen so gleich viel.
    """
    est, counts, D = modell["est"], modell["counts"], modell["D"]
    p = {}
    for v, a in est["a"].items():
        n = sum(counts[k].get(v, 0) for k in est["keys"])
        if n:
            p[v] = sum(min(a * D[k], counts[k].get(v, 0)) for k in est["keys"]) / n
    return p


def ohne_rauschen(fahrten, modell):
    """[(Ortszeit, v)] ohne den erwarteten Rauschanteil je Zelle und Geschwindigkeit (Reihenfolge bleibt)."""
    p = anteile_zelle(modell)
    gruppen = collections.defaultdict(list)
    for f in fahrten:
        gruppen[(tagtyp(f[0]), f[0].hour, f[1])].append(f)
    erwartet = {k: p[k] * len(g) for k, g in gruppen.items() if k in p}
    weg = _duenne(gruppen, erwartet)
    return [f for f in fahrten if id(f) not in weg]


def ohne_rauschen_je_v(fahrten, modell):
    """Wie ohne_rauschen, fuer Fahrten ohne nutzbare Uhrzeit: nur nach Geschwindigkeit."""
    p = anteile_je_v(modell)
    gruppen = collections.defaultdict(list)
    for f in fahrten:
        gruppen[f[1]].append(f)
    erwartet = {v: p[v] * len(g) for v, g in gruppen.items() if v in p}
    weg = _duenne(gruppen, erwartet)
    return [f for f in fahrten if id(f) not in weg]
