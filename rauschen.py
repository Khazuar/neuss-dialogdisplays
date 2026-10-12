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

Regen: Regen erzeugt im Radar zusaetzliche langsame Datensaetze, die nicht vom Verkehr abhaengen, aber nicht ueber den Tag
gleichmaessig verteilt sind (docs/wetter.md). Mit einer Regenfunktion (Niederschlag je Ortszeit-Stunde, wetter.py) werden die Stunden
in Regenklassen eingeteilt. a(v) und b(v) werden nur aus trockenen Stunden geschaetzt; fuer jede Regenklasse k kommt ein Regenanteil
c_k(v) hinzu (Datensaetze je Regenstunde, die ueber a(v) + b(v) * T hinausgehen). Ohne Regenfunktion gilt das Modell von oben.
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
# Regenklassen nach der Intensitaet der Stunde: Niederschlag der Stunde plus je die Haelfte der beiden Nachbarstunden (mm)
REGEN_KLASSEN = ((1, 0.1, 0.5), (2, 0.5, 2.0), (3, 2.0, float("inf")))  # (Klasse, von, bis)
TROCKEN = 0  # trockene Stunde: diese und die drei Stunden davor und die danach unter 0,1 mm
UNKLAR = 9  # Nachlauf oder Vorlauf des Regens oder kein Wert: nicht fuer die Schaetzung, abgezogen wird nur a(v)
MIN_REGENSTUNDEN = 12  # Klassen mit weniger Stunden uebernehmen die Schaetzung der naechsten Klasse
REGEN_REL = 0.5  # Regenanteil zaehlt nur, wo er mindestens so viel (Anteil) ueber dem Erwarteten ohne Regen liegt: 1,5-fach
REGEN_LAUF = 3  # ... und nur in zusammenhaengenden Laeufen von mindestens so vielen Geschwindigkeiten (Luecken bis 1 km/h): Das Stoersignal
# ist zusammenhaengend; einzelne Ausreisser bei vielen Tests (Klassen x Geschwindigkeiten) sind Zufall. Die Signifikanz (SIGMA) gilt fuer
# den ganzen Lauf, nicht je Geschwindigkeit: Je Geschwindigkeit sind die Zaehlwerte klein, ueber den Lauf nicht.
REGEN_EINZEL_SIGMA = 1.0  # jede Geschwindigkeit eines Laufs muss mindestens so viele Standardfehler ueber 0 liegen
INSTABIL_REGEN = 1.0  # Haelften: mittlerer Regenanteil je Regenstunde weicht um mehr als so viele Datensaetze ...
INSTABIL_REGEN_REL = 0.8  # ... und um mehr als diesen Teil des groesseren Werts ab (eine Haelfte hat unter einem Fuenftel der anderen): nicht
# belegt. Lockerer als beim trockenen Rauschboden: Die Staerke der Stoerung haengt von der Regenmenge in der Klasse ab, und die Haelften
# der Tage enthalten zufaellig unterschiedlich viel starken Regen; belegt sein muss, dass der Regenanteil in beiden Haelften auftritt.


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


def regenklassen(regen, stunden):
    """{(Datum, Stunde): Regenklasse} fuer die Ortszeit-Stunden `stunden`.

    regen(datum, stunde) -> Niederschlag der Stunde in mm oder None. Klasse 1 bis 3 nach REGEN_KLASSEN (Stunde plus je die Haelfte der
    Nachbarstunden), TROCKEN, wenn Stunde und Nachbarn und die drei Stunden davor trocken sind (unter 0,1 mm), sonst UNKLAR."""
    out = {}
    for key in stunden:
        t = dt.datetime(key[0].year, key[0].month, key[0].day, key[1])
        m = {}
        for o in (-3, -2, -1, 0, 1):
            u = t + dt.timedelta(hours=o)
            m[o] = regen(u.date(), u.hour)
        if m[0] is None:
            out[key] = UNKLAR
            continue
        r = m[0] + 0.5 * ((m[-1] or 0.0) + (m[1] or 0.0))
        klasse = None
        for k, lo, hi in REGEN_KLASSEN:
            if lo <= r < hi:
                klasse = k
        if klasse is None:
            klasse = UNKLAR if any(m[o] is None or m[o] >= 0.1 for o in (-3, -2, -1, 1)) else TROCKEN
        out[key] = klasse
    return out


def zellen(fahrten, spannen, tage_filter=None, klassen=None):
    """(counts, D): counts[(typ, stunde, klasse)][v] Fahrzeuge, D[(typ, stunde, klasse)] Anzahl abgedeckter Stunden (Tage).

    klassen: {(Datum, Stunde): Regenklasse} (regenklassen); ohne sind alle Stunden TROCKEN."""
    abd = abgedeckte_stunden(spannen)
    if tage_filter is not None:
        abd = {x for x in abd if tage_filter(x[0])}

    def kl(datum, h):
        return TROCKEN if klassen is None else klassen.get((datum, h), UNKLAR)
    D = collections.Counter()
    for datum, h in abd:
        D[(tagtyp(dt.datetime(datum.year, datum.month, datum.day)), h, kl(datum, h))] += 1
    counts = collections.defaultdict(collections.Counter)
    for t, v in fahrten:
        if (t.date(), t.hour) in abd:
            counts[(tagtyp(t), t.hour, kl(t.date(), t.hour))][v] += 1
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
    keys = [k for k in D if k[2] == TROCKEN and D[k] >= MIN_TAGE]
    T = {k: sum(n for v, n in counts[k].items() if v >= vt) / D[k] for k in keys}
    a, ab = {}, {}
    for v in range(0, int(vt)):
        ys = [counts[k].get(v, 0) / D[k] for k in keys]
        if not any(ys):
            continue
        aa, bb, se = wls([T[k] for k in keys], ys, [D[k] for k in keys])
        ab[v] = (aa, bb)  # Anpassung der trockenen Stunden, auch wo a(v) nicht zaehlt (Grundlage des Regenanteils)
        if aa >= SIGMA * se and aa > 0:  # nan > 0 ist falsch: ohne Standardfehler kein Rauschen
            a[v] = aa
    return {"vT": vt, "a": a, "ab": ab, "keys": keys}


def _laeufe(kand, stunden):
    """Regenanteil je Stunde {v: c} aus den Kandidaten {v: (Ueberschuss, Zahl der Datensaetze)} einer Klasse mit `stunden` Stunden.

    Bleiben: Laeufe von mindestens REGEN_LAUF aufeinanderfolgenden Geschwindigkeiten (Luecken bis 1 km/h), deren Ueberschuss zusammen
    mindestens SIGMA Standardfehler (Poisson, ueber die Datensaetze des Laufs) ueber 0 liegt."""
    laeufe, aktuell = [], []
    for v in sorted(kand):
        if aktuell and v - aktuell[-1] > 2:
            laeufe.append(aktuell)
            aktuell = []
        aktuell.append(v)
    if aktuell:
        laeufe.append(aktuell)
    out = {}
    for lauf in laeufe:
        if len(lauf) < REGEN_LAUF:
            continue
        roh, n = sum(kand[v][0] for v in lauf), sum(kand[v][1] for v in lauf)
        if roh >= SIGMA * math.sqrt(max(n, 1)):
            out.update({v: kand[v][0] / stunden for v in lauf})
    return out


def regen_ueberschuss(est, counts, D):
    """Regenanteil c_k(v): Datensaetze je Regenstunde der Klasse k und Geschwindigkeit v ueber a(v) + b(v) * T hinaus.

    T ist der Verkehr (Fahrten je Stunde ab der Verkehrsschwelle) in den Regenstunden derselben Zelle. Eine Geschwindigkeit ist Kandidat,
    wenn die Datensaetze in den Regenstunden mindestens (1 + REGEN_REL)-mal so haeufig sind wie ohne Regen erwartet (Fahrzeuge,
    kleine Abweichungen vom Modell, sollen nicht fuer Stoerung gehalten werden; das Stoersignal ist ein Vielfaches) und mindestens
    REGEN_EINZEL_SIGMA Standardfehler (Poisson) ueber 0 liegt. c_k(v) zaehlt nur in zusammenhaengenden Laeufen von mindestens REGEN_LAUF
    Kandidaten, deren Summe mindestens SIGMA Standardfehler ueber 0 liegt (siehe _laeufe). Gibt ({k: {v: c}}, {k: Stunden}) zurueck; Klassen mit weniger als
    MIN_REGENSTUNDEN Stunden uebernehmen c der naechsten Klasse mit genug Stunden (leer, wenn es keine gibt)."""
    klassen = [k for k, _, _ in REGEN_KLASSEN]
    stunden = {k: sum(D[key] for key in D if key[2] == k) for k in klassen}
    vt = est["vT"]
    c = {}
    for k in klassen:
        if stunden[k] < 1:
            c[k] = {}
            continue
        zk = [key for key in D if key[2] == k]
        T = {key: sum(n for v, n in counts[key].items() if v >= vt) / D[key] for key in zk}
        kand = {}
        for v in range(0, int(vt)):
            aa, bb = est["ab"].get(v, (0.0, 0.0))
            erwartet = sum((aa + bb * T[key]) * D[key] for key in zk)
            n_v = sum(counts[key].get(v, 0) for key in zk)
            roh = n_v - erwartet
            if roh > 0 and roh >= REGEN_EINZEL_SIGMA * math.sqrt(max(n_v, 1)) and roh >= REGEN_REL * erwartet:
                kand[v] = (roh, n_v)
        c[k] = _laeufe(kand, stunden[k])
    gueltig = [k for k in klassen if stunden[k] >= MIN_REGENSTUNDEN]
    for k in klassen:
        if stunden[k] < MIN_REGENSTUNDEN:
            c[k] = dict(c[min(gueltig, key=lambda x: abs(x - k))]) if gueltig else {}
    return c, stunden


def regen_kennzahlen(c, stunden):
    """(mittlerer Regenanteil je Regenstunde [Datensaetze], Mittel km/h, 95-%-Grenze km/h) ueber alle Regenstunden; None ohne Anteil."""
    masse = collections.Counter()
    for k, ck in c.items():
        for v, x in ck.items():
            masse[v] += x * stunden[k]
    gesamt = sum(stunden.values())
    s = sum(masse.values())
    if not s or not gesamt:
        return 0.0, None, None
    mittel, cum, q95 = sum(v * m for v, m in masse.items()) / s, 0.0, max(masse)
    for v in sorted(masse):
        cum += masse[v]
        if cum >= 0.95 * s:
            q95 = v
            break
    return s / gesamt, mittel, q95


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


def _bewerte_regen(ue, st, haelften, limit):
    """Befund zum Regenanteil: (dict, c oder None). Belegt, wenn genug Regenstunden, ein Anteil nachweisbar, er bis hoechstens
    OBERGRENZE_KMH reicht und in beiden Haelften der Tage etwa gleich gross ist."""
    gesamt = sum(st.values())
    je_stunde, mittel, q95 = regen_kennzahlen(ue, st)
    befund = {"regenstunden": gesamt, "stunden_je_klasse": {str(k): v for k, v in st.items()},
              "zusatz_je_regenstunde": round(je_stunde, 2), "mittel_kmh": None if mittel is None else round(mittel, 1), "obergrenze_kmh": q95,
              "zusatz_je_klasse": {str(k): round(sum(ck.values()), 2) for k, ck in ue.items()}}
    stabil = True
    if len(haelften) == 2:
        u = abs(haelften[0] - haelften[1])
        stabil = not (u > INSTABIL_REGEN and u > INSTABIL_REGEN_REL * max(haelften))
    befund["stabil"] = stabil
    if gesamt < MIN_REGENSTUNDEN:
        befund.update(belegt=False, grund=f"weniger als {MIN_REGENSTUNDEN} Regenstunden in der Datei")
    elif not je_stunde:
        befund.update(belegt=False, grund="kein Regenanteil nachweisbar")
    elif q95 > OBERGRENZE_KMH:
        befund.update(belegt=False, grund=f"reicht bis {q95} km/h (mehr als {OBERGRENZE_KMH}), nicht von langsamem Verkehr zu trennen")
    elif not stabil:
        befund.update(belegt=False, grund="Regenanteil in den Haelften (gerade/ungerade Tage) nicht stabil")
    else:
        befund.update(belegt=True, grund=None)
    return befund, ue if befund["belegt"] else None


def pruefen(fahrten, spannen, limit, regen=None):
    """Schaetzt und bewertet den Rauschboden einer Datei. fahrten: [(Ortszeit, v)] mit nutzbarer Zeit.

    regen: Funktion (Datum, Stunde) -> Niederschlag der Ortszeit-Stunde in mm oder None (Wetterdaten); ohne gibt es keinen Regenanteil.
    Gibt None zurueck, wenn die Datei zu klein ist. Sonst ein dict mit den Kennzahlen und 'belegt' (True: wird
    abgezogen) samt 'grund'; unter 'regen' der Befund zum Regenanteil (None ohne Wetterdaten), unter '_modell', was fuer den Abzug
    gebraucht wird. 'abzug' ist True, wo etwas abgezogen wird (trockener Rauschboden und/oder Regenanteil belegt).
    """
    if limit is None or len(fahrten) < MIN_FAHRZEUGE:
        return None
    klassen = regenklassen(regen, abgedeckte_stunden(spannen)) if regen else None
    counts, D = zellen(fahrten, spannen, klassen=klassen)
    est = schaetzen(counts, D, limit)
    if not est["keys"]:
        return None
    a_ges = anteil(est, counts, D)
    mittel, q95 = lage(est)
    tage = sorted({t.date() for t, _ in fahrten})
    gerade = {t for i, t in enumerate(tage) if i % 2 == 0}
    haelften, regen_haelften = [], []
    for filt in (lambda d: d in gerade, lambda d: d not in gerade):
        c2, d2 = zellen(fahrten, spannen, filt, klassen)
        e2 = schaetzen(c2, d2, limit)
        haelften.append(anteil(e2, c2, d2) if e2["keys"] else 0.0)
        if klassen is not None and e2["keys"]:
            ue2, st2 = regen_ueberschuss(e2, c2, d2)
            regen_haelften.append(regen_kennzahlen(ue2, st2)[0])
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
    befund, c_regen = None, None
    if klassen is not None:
        ue, st = regen_ueberschuss(est, counts, D)
        befund, c_regen = _bewerte_regen(ue, st, regen_haelften, limit)
    stunden = sum(D[k] for k in est["keys"])
    vmax = max(est["a"]) if est["a"] else 0
    vs = range(min(est["a"]), vmax + 1) if est["a"] else range(0)
    ergebnis = {
        "belegt": belegt, "grund": grund, "anteil": a_ges, "mittel_kmh": mittel, "obergrenze_kmh": q95, "stabil": stabil,
        "anteil_haelften": haelften, "verkehrsschwelle_kmh": est["vT"], "stunden": stunden,
        "regen": befund, "abzug": belegt or bool(befund and befund["belegt"]),
        "obergrenze_abzug_kmh": max([x for x in (q95 if belegt else None, befund["obergrenze_kmh"] if befund and befund["belegt"] else None) if x is not None], default=None),
        "_modell": {"est": est, "counts": counts, "D": D, "klassen": klassen, "a_abziehen": belegt, "regen": c_regen},
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
    """p[(typ, stunde, klasse, v)] = Wahrscheinlichkeit, dass ein Fahrzeug dieser Zelle und Geschwindigkeit Rauschen ist.

    Erwartet wird je Zelle a(v) (wenn der trockene Rauschboden belegt ist) mal Zahl der Stunden. Trockene Zellen zaehlen nur mit
    mindestens MIN_TAGE Stunden (wie bei der Schaetzung). Der Regenanteil c_k(v) wird nicht je Zelle abgezogen, sondern je Klasse
    (siehe ohne_rauschen): Er haengt nur von der Regenklasse ab, und je Zelle wuerde dort gekappt, wo die Stoerung unter dem
    Klassenmittel liegt, und bliebe dort stehen, wo sie darueber liegt."""
    est, counts, D = modell["est"], modell["counts"], modell["D"]
    a_ab = est["a"] if modell.get("a_abziehen", True) else {}
    p = {}
    for key, zaehler in counts.items():
        if key[2] == TROCKEN and key not in est["keys"]:
            continue
        for v, n in zaehler.items():
            erwartet = a_ab.get(v, 0.0)
            if erwartet:
                p[(key[0], key[1], key[2], v)] = min(1.0, erwartet * D[key] / n)
    return p


def anteile_je_v(modell):
    """p[v] = Rauschanteil bei Geschwindigkeit v ueber alle verwendeten Zellen.

    Wie beim Abzug je Zelle kann in einer Zelle nicht mehr entfernt werden, als dort gemessen wurde (nachts liegt die
    Rate des Rauschens oft unter dem Mittel). Beide Abzuege entfernen so gleich viel.
    """
    est, counts, D = modell["est"], modell["counts"], modell["D"]
    p = {}
    for v, a in (est["a"] if modell.get("a_abziehen", True) else {}).items():
        n = sum(counts[k].get(v, 0) for k in est["keys"])
        if n:
            p[v] = sum(min(a * D[k], counts[k].get(v, 0)) for k in est["keys"]) / n
    return p


def ohne_rauschen(fahrten, modell):
    """[(Ortszeit, v)] ohne den erwarteten Rauschanteil je Zelle und Geschwindigkeit (Reihenfolge bleibt)."""
    p = anteile_zelle(modell)
    klassen = modell.get("klassen")
    gruppen = collections.defaultdict(list)
    for f in fahrten:
        k = TROCKEN if klassen is None else klassen.get((f[0].date(), f[0].hour), UNKLAR)
        gruppen[(tagtyp(f[0]), f[0].hour, k, f[1])].append(f)
    erwartet = {k: p[k] * len(g) for k, g in gruppen.items() if k in p}
    weg = _duenne(gruppen, erwartet)
    c = modell.get("regen")
    if c:  # Regenanteil je Klasse und Geschwindigkeit ueber alle Zellen der Klasse, die in den Fahrten vorkommen
        D = modell["D"]
        je_kv, zellen_je_k = collections.defaultdict(list), collections.defaultdict(set)
        for f in fahrten:
            k = klassen.get((f[0].date(), f[0].hour), UNKLAR) if klassen is not None else TROCKEN
            if id(f) in weg or k not in c:
                continue
            zellen_je_k[k].add((tagtyp(f[0]), f[0].hour, k))
            if f[1] in c[k]:
                je_kv[(k, f[1])].append(f)
        erwartet2 = {(k, v): c[k][v] * sum(D.get(z, 0) for z in zellen_je_k[k]) for (k, v) in je_kv}
        weg |= _duenne(je_kv, erwartet2)
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
