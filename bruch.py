# SPDX-License-Identifier: MIT
"""Brueche in einer Messreihe: wo aendert sich das Verhalten des Verkehrs so stark, dass die Teile getrennt ausgewertet werden sollten?

Anlass: Die Geraete werden umgehaengt, neu eingestellt oder stehen nach einer Unterbrechung an anderer Stelle. Dann gehoeren Fahrzeuge vor und nach
dem Wechsel zu verschiedenen Messstellen. Das Verfahren (docs/abschnitte.md):

  1. Je vollstaendig aufgezeichnetem Tag werden aus den Fahrzeugen ab `ab` km/h fuenf Merkmale gebildet: mittleres Tempo, 15. und 85.
     Perzentil, Anteil ueber dem Tempolimit und der Logarithmus der Fahrzeugzahl. Der Unterschied zwischen Werktagen, Samstagen und Sonntagen
     (Mittel je Tagtyp) wird abgezogen.
  2. Die Tage werden optimal in Abschnitte zerlegt (dynamische Programmierung, Summe der quadrierten Abweichungen vom Abschnittsmittel in
     Einheiten der robust geschaetzten Streuung von Tag zu Tag, Strafe je Bruch nach dem BIC).
  3. Wahrscheinlichkeit je Bruch: BIC-Vergleich "ein Abschnitt" gegen "zwei Abschnitte" fuer die beiden angrenzenden Abschnitte,
     p = 1 / (1 + exp(-dBIC / 2)) bei gleicher Vorabwahrscheinlichkeit. Aufeinanderfolgende Tage sind aehnlich (Wetter, Ferien); das senkt
     die Zahl unabhaengiger Tage um den Faktor (1 - r) / (1 + r) mit der mittleren Autokorrelation r der Merkmale, und die Abweichungsquadrate
     werden damit gewichtet.
Die Wahrscheinlichkeit gilt unter diesen Annahmen (Normalverteilung der Tageswerte, gleichartige Streuung); sie ist ein Mass fuer die Staerke
des Befunds, keine Haeufigkeit.
"""
import collections
import datetime as dt
import math

import rauschen

MIN_TAG_FAHRZEUGE = 50      # Tage mit weniger Fahrzeugen ab `ab` bleiben ausser Betracht
MIN_ABSCHNITT_TAGE = 7      # kuerzere Abschnitte gibt es nicht
MAX_AUSSCHLAG_TAGE = 21     # ein kuerzerer Abschnitt, nach dem der Verkehr zum alten Niveau zurueckkehrt, ist ein Ausschlag
SPLIT_P = 0.9               # ab dieser Wahrscheinlichkeit wird getrennt
MOEGLICH_P = 0.5            # ab dieser Wahrscheinlichkeit wird ein Bruch als moeglich genannt
MIN_UNTERSCHIED = 0.15      # kleinster Unterschied (totale Variation) der Verteilungen vor und nach einem Bruch
FENSTER = 7                # Tage je Fenster fuer die Streuung von Woche zu Woche
MERKMALE = ("mittel_kmh", "p15_kmh", "p85_kmh", "anteil_ueber_limit", "log_fahrzeuge")
MIN_STREUUNG = (0.15, 0.3, 0.3, 0.01, 0.03)  # Untergrenzen der Streuung von Tag zu Tag je Merkmal
TAGTYP = lambda d: 0 if d.weekday() < 5 else d.weekday() - 4  # Werktag, Samstag, Sonntag  # noqa: E731


def perzentil(sortiert, p):
    return sortiert[min(len(sortiert) - 1, int(math.ceil(p / 100.0 * len(sortiert))) - 1)]


def tagesmerkmale(fahrzeuge, spannen, ab, limit):
    """[(Datum, [Merkmale], Fahrzeuge)] fuer vollstaendig aufgezeichnete Tage mit genug Fahrzeugen ab `ab` km/h."""
    zaehler = collections.Counter(d for d, _ in rauschen.abgedeckte_stunden(spannen))
    voll = {d for d, c in zaehler.items() if c == 24}
    je_tag = collections.defaultdict(list)
    for t, v in fahrzeuge:
        d = t.date()
        if d in voll and v >= ab:
            je_tag[d].append(v)
    out = []
    for d in sorted(je_tag):
        v = sorted(je_tag[d])
        if len(v) < MIN_TAG_FAHRZEUGE:
            continue
        n = len(v)
        ueber = sum(1 for x in v if x > limit) / n if limit else 0.0
        out.append((d, [sum(v) / n, perzentil(v, 15), perzentil(v, 85), ueber, math.log(n)], n))
    return out


def _histogramme_je_tag(fahrzeuge, tage, ab):
    """{Datum: Counter(ganze km/h ab `ab`)} fuer die Tage der Merkmale."""
    gesucht = set(tage)
    h = {t: collections.Counter() for t in tage}
    for t, v in fahrzeuge:
        d = t.date()
        if d in gesucht and v >= ab:
            h[d][int(v)] += 1
    return h


def _tv(histogramme, a, k, b, tage_liste=None):
    """Totale Variation (0..1) zwischen den zusammengefassten Verteilungen der Tage [a,k) und [k,b)."""
    tage = sorted(histogramme)
    links, rechts = collections.Counter(), collections.Counter()
    for t in tage[a:k]:
        links.update(histogramme[t])
    for t in tage[k:b]:
        rechts.update(histogramme[t])
    nl, nr = sum(links.values()), sum(rechts.values())
    if not nl or not nr:
        return 0.0
    return 0.5 * sum(abs(links[v] / nl - rechts[v] / nr) for v in set(links) | set(rechts))


def _bereinigt(werte, tage):
    """Tagtyp-Mittel abziehen: werte[tag][merkmal] -> Reste."""
    d = len(werte[0])
    mittel = {}
    for typ in (0, 1, 2):
        idx = [i for i, t in enumerate(tage) if TAGTYP(t) == typ]
        for j in range(d):
            x = sorted(werte[i][j] for i in idx)
            mittel[(typ, j)] = x[len(x) // 2] if x else 0.0
    return [[werte[i][j] - mittel[(TAGTYP(tage[i]), j)] for j in range(d)] for i in range(len(tage))]


def _mad_streuung(x):
    diff = sorted(abs(b - a) for a, b in zip(x, x[1:]))
    return (diff[len(diff) // 2] / 0.6745 / math.sqrt(2)) if diff else 0.0


def _autokorrelation(x):
    n = len(x)
    m = sum(x) / n
    num = sum((x[i] - m) * (x[i + 1] - m) for i in range(n - 1))
    den = sum((a - m) ** 2 for a in x) or 1.0
    return num / den


class _Summen:
    """Praefixsummen fuer Kosten Summe_j sum_i (y_ij - Mittel)^2 / s_j^2 (mal Gewicht f)."""

    def __init__(self, y, s, f):
        self.d = len(s)
        self.n = len(y)
        self.f = f
        self.w = [1.0 / (sj * sj) for sj in s]
        self.s1 = [[0.0] * self.d]
        self.s2 = [[0.0] * self.d]
        for row in y:
            self.s1.append([a + b for a, b in zip(self.s1[-1], row)])
            self.s2.append([a + b * b for a, b in zip(self.s2[-1], row)])

    def kosten(self, a, b):
        n = b - a
        if n <= 0:
            return 0.0
        c = 0.0
        for j in range(self.d):
            q = self.s1[b][j] - self.s1[a][j]
            c += self.w[j] * ((self.s2[b][j] - self.s2[a][j]) - q * q / n)
        return self.f * c


def zerlege(y, s, f, strafe):
    """Optimale Zerlegung in Abschnitte der Mindestlaenge; gibt die Anfangsindizes der Abschnitte nach dem ersten zurueck."""
    S = _Summen(y, s, f)
    n = len(y)
    inf = float("inf")
    F = [0.0] + [inf] * n
    vor = [0] * (n + 1)
    for t in range(MIN_ABSCHNITT_TAGE, n + 1):
        besser = (S.kosten(0, t), 0)  # ein Abschnitt von Anfang an
        for sidx in range(MIN_ABSCHNITT_TAGE, t - MIN_ABSCHNITT_TAGE + 1):
            if F[sidx] == inf:
                continue
            c = F[sidx] + S.kosten(sidx, t) + strafe
            if c < besser[0]:
                besser = (c, sidx)
        F[t], vor[t] = besser
    grenzen = []
    t = n
    while t > 0 and vor[t] > 0:
        grenzen.append(vor[t])
        t = vor[t]
    return sorted(grenzen), S


def bruchwahrscheinlichkeit(S, a, k, b, f):
    """BIC-Wahrscheinlichkeit, dass zwischen den Tagen k-1 und k ein Bruch liegt (Abschnitte [a,k) und [k,b))."""
    delta = S.kosten(a, b) - S.kosten(a, k) - S.kosten(k, b)
    bic = delta - (S.d + 1) * math.log(b - a)
    return 1.0 / (1.0 + math.exp(-max(-300.0, min(300.0, bic / 2.0)))), delta


def _de(x, stellen=1):
    return ("%.*f" % (stellen, x)).replace(".", ",")


def begruendung(b, ab):
    """Saetze zur Begruendung eines Bruchs (aus den Merkmalen vor und nach dem Bruch)."""
    v, n, sh = b["vorher"], b["nachher"], b["verschiebung_in_streuungen"]
    s = [f"Die Verteilung der Geschwindigkeiten (Fahrzeuge ab {ab} km/h) unterscheidet sich vor und nach dem {b['datum'][8:]}.{b['datum'][5:7]}.{b['datum'][:4]} "
         f"um {round(100 * b['unterschied_der_verteilungen'])} % (totale Variation der Verteilungen; ab {round(100 * MIN_UNTERSCHIED)} % wird getrennt)."]
    teile = [f"mittleres Tempo {_de(v['mittel_kmh'])} → {_de(n['mittel_kmh'])} km/h ({sh['mittel_kmh']:+.0f} Streuungen von Tag zu Tag)"]
    teile.append(f"85. Perzentil {_de(v['p85_kmh'], 0)} → {_de(n['p85_kmh'], 0)} km/h")
    teile.append(f"15. Perzentil {_de(v['p15_kmh'], 0)} → {_de(n['p15_kmh'], 0)} km/h")
    faktor = math.exp(n["log_fahrzeuge"] - v["log_fahrzeuge"])
    teile.append(f"Fahrzeuge je Tag ab {ab} km/h: Faktor {_de(faktor, 2)}")
    s.append("; ".join(teile) + ".")
    if b["luecke_tage"]:
        s.append(f"Davor fehlen {b['luecke_tage']} Tage ohne vollständige Aufzeichnung.")
    return s


def erkenne(fahrzeuge, spannen, ab, limit):
    """Brueche einer Messreihe.

    fahrzeuge: [(Ortszeit, v)] mit nutzbarer Zeit, spannen: [(erste, letzte Ortszeit)] je Uhr-Abschnitt.
    Gibt dict: geprueft (bool), grund, tage, abschnitte [{von, bis, tage}] und brueche [{datum, wahrscheinlichkeit, ...}] zurueck.
    """
    tm = tagesmerkmale(fahrzeuge, spannen, ab, limit)
    if len(tm) < 2 * MIN_ABSCHNITT_TAGE:
        return {"geprueft": False, "grund": f"weniger als {2 * MIN_ABSCHNITT_TAGE} vollständig aufgezeichnete Tage", "tage": len(tm)}
    tage = [t[0] for t in tm]
    roh = [t[1] for t in tm]
    y = _bereinigt(roh, tage)
    d = len(MERKMALE)
    s = [max(_mad_streuung([row[j] for row in y]), MIN_STREUUNG[j]) for j in range(d)]
    r = [_autokorrelation([row[j] for row in y]) for j in range(d)]
    rm = max(0.0, min(0.95, sum(r) / d))
    # Streuung von Woche zu Woche (Wetter, Ferien, Feiertage) im Vergleich zu reinem Tagesrauschen: die Streuung wird entsprechend aufgeblaeht
    aufblaehung = []
    for j in range(d):
        x = [row[j] for row in y]
        diffs = [sum(x[t:t + FENSTER]) / FENSTER - sum(x[t - FENSTER:t]) / FENSTER for t in range(FENSTER, len(x) - FENSTER + 1)]
        if len(diffs) >= 3:
            m = sorted(diffs)[len(diffs) // 2]
            sd = 1.4826 * sorted(abs(v - m) for v in diffs)[len(diffs) // 2]
            aufblaehung.append(max(1.0, sd / (s[j] * math.sqrt(2.0 / FENSTER))))
        else:
            aufblaehung.append(1.0)
    s = [s[j] * aufblaehung[j] for j in range(d)]
    f = 1.0
    grenzen, S = zerlege(y, s, f, (d + 1) * math.log(len(y)))
    pos = [0] + grenzen + [len(y)]
    brueche, moeglich = [], []
    # Wahrscheinlichkeit je Grenze gegen die beiden Nachbarabschnitte
    behalten = list(grenzen)
    wsk = {}
    for i, k in enumerate(grenzen):
        a, b = pos[i], pos[i + 2]
        p, delta = bruchwahrscheinlichkeit(S, a, k, b, f)
        wsk[k] = (p, a, b)
    # Grenzen unter der Schwelle verwerfen und Rest neu bewerten, bis alle ueber der Schwelle liegen
    while True:
        schwach = [k for k in behalten if wsk[k][0] < SPLIT_P]
        if not schwach:
            break
        k = min(schwach, key=lambda x: wsk[x][0])
        behalten.remove(k)
        moeglich.append((k, wsk[k][0]))
        pos2 = [0] + behalten + [len(y)]
        wsk = {kk: (bruchwahrscheinlichkeit(S, pos2[i], kk, pos2[i + 2], f)[0], pos2[i], pos2[i + 2]) for i, kk in enumerate(behalten)}
    kleine_verschiebungen = []
    # Kurze Ausschlaege (Feiertage, Ferienwoche, Unwetter), nach denen der Verkehr zum alten Niveau zurueckkehrt, sind keine Umstellung
    ausschlaege = []
    while True:
        pos = [0] + sorted(behalten) + [len(y)]
        gefunden = None
        for i in range(1, len(pos) - 2):
            a0, a1, b1, c1 = pos[i - 1], pos[i], pos[i + 1], pos[i + 2]
            if b1 - a1 > MAX_AUSSCHLAG_TAGE:
                continue

            def mittel(lo, hi):
                return [sum(y[x][j] for x in range(lo, hi)) / (hi - lo) for j in range(d)]
            A, B, C = mittel(a0, a1), mittel(a1, b1), mittel(b1, c1)
            hin = max(abs(B[j] - A[j]) / s[j] for j in range(d))
            netto = max(abs(C[j] - A[j]) / s[j] for j in range(d))
            if netto <= 0.5 * hin:
                gefunden = (a1, b1)
                break
        if not gefunden:
            break
        for k in gefunden:
            behalten.remove(k)
        ausschlaege.append((tage[gefunden[0]].isoformat(), tage[gefunden[1] - 1].isoformat()))
    # Nur Brueche, nach denen sich die Verteilung der Geschwindigkeiten deutlich unterscheidet (kleine Verschiebungen sind bei Tausenden
    # Fahrzeugen je Tag statistisch "sicher", aber keine neue Messstelle)
    histogramme = _histogramme_je_tag(fahrzeuge, tage, ab)
    while True:
        pos = [0] + sorted(behalten) + [len(y)]
        tv_wert = {k: _tv(histogramme, pos[i], k, pos[i + 2]) for i, k in enumerate(sorted(behalten))}
        klein = [k for k in behalten if tv_wert[k] < MIN_UNTERSCHIED]
        if not klein:
            break
        k = min(klein, key=lambda x: tv_wert[x])
        behalten.remove(k)
        kleine_verschiebungen.append(tage[k].isoformat())
    pos = [0] + sorted(behalten) + [len(y)]
    abschnitte = [{"von": tage[a].isoformat(), "bis": tage[b - 1].isoformat(), "tage": b - a} for a, b in zip(pos[:-1], pos[1:])]
    for i, k in enumerate(sorted(behalten)):
        a, b = pos[i], pos[i + 2]
        p, delta = bruchwahrscheinlichkeit(S, a, k, b, f)
        links = [sum(roh[x][j] for x in range(pos[i], k)) / (k - pos[i]) for j in range(d)]
        rechts = [sum(roh[x][j] for x in range(k, pos[i + 2] if i + 2 < len(pos) else len(y))) / ((pos[i + 2] if i + 2 < len(pos) else len(y)) - k) for j in range(d)]
        verschiebung = [(rechts[j] - links[j]) / s[j] for j in range(d)]
        luecke = (tage[k] - tage[k - 1]).days - 1
        brueche.append({"datum": tage[k].isoformat(), "vorher_bis": tage[k - 1].isoformat(), "wahrscheinlichkeit": round(p, 4),
                        "luecke_tage": max(luecke, 0), "unterschied_der_verteilungen": round(tv_wert[k], 3),
                        "vorher": {m: round(links[j], 3) for j, m in enumerate(MERKMALE)},
                        "nachher": {m: round(rechts[j], 3) for j, m in enumerate(MERKMALE)},
                        "verschiebung_in_streuungen": {m: round(verschiebung[j], 1) for j, m in enumerate(MERKMALE)}})
        brueche[-1]["begruendung"] = begruendung(brueche[-1], ab)
    return {"geprueft": True, "tage": len(tage), "ab_kmh": ab, "autokorrelation": round(rm, 2), "aufblaehung": {m: round(aufblaehung[j], 1) for j, m in enumerate(MERKMALE)}, "abschnitte": abschnitte, "brueche": brueche,
            "verworfen_kleiner_unterschied": kleine_verschiebungen,
            "ausschlaege": [{"von": a, "bis": b} for a, b in ausschlaege],
            "moegliche_brueche": [{"datum": tage[k].isoformat(), "wahrscheinlichkeit": round(p, 4)} for k, p in sorted(moeglich)],
            "streuung_von_tag_zu_tag": {m: round(s[j], 3) for j, m in enumerate(MERKMALE)}}
