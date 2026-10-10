# SPDX-License-Identifier: MIT
"""Zerlegung der Geschwindigkeitsverteilung in Gruppen und die Zellen fuer die Filter der Detailseiten.

Je Datei wird die Verteilung der Fahrzeuge (nach Abzug des Rauschbodens, rauschen.py) als Mischung von Lognormal-Verteilungen
angepasst. Die Zahl der Gruppen K bestimmt die Datei selbst: Eine weitere Gruppe zaehlt nur, wenn sie die Likelihood auf den
jeweils anderen Messtagen (gerade gegen ungerade Tage) spuerbar verbessert, in beiden Haelften wiederkehrt, nicht winzig ist
und von den anderen getrennt liegt. Laesst sich keine Zerlegung belegen, bleibt K = 1. Verfahren und Grenzen: docs/gruppen.md.

Die Zerlegung ist fuer alle Stunden und Tage gleich. Der Anteil einer Gruppe an einer Geschwindigkeit haengt dann nur von der
Geschwindigkeit ab, und die Detailseiten koennen jede Auswahl (Tageszeit, Wochentag, Gruppe) im Browser aus den Zellen rechnen.

Nur Standardbibliothek. Die Anpassung ist deterministisch (feste Startwerte).
"""
import collections
import datetime as dt
import math
import random

import rauschen

K_MAX = 8  # Obergrenze der Suche; sie endet meist frueher (siehe waehle_k)
MIN_FAHRZEUGE = 5000  # kleinere Dateien werden nicht zerlegt
MIN_ANTEIL = 0.03  # eine Gruppe unter 3 % in einer Haelfte der Messtage gilt als zu klein
CV_GEWINN_MIN = 0.005  # mindestens so viel nats je Fahrzeug Gewinn auf den jeweils anderen Tagen, sonst keine weitere Gruppe
D_MIN = 1.0  # Ashman-Abstand zwischen Gruppen (getrennt ab 1)
CV_GEWINN_STARK = 0.02  # so viel Gewinn belegt eine Struktur auch dort, wo sich die Gruppen stark ueberlappen (breite Gruppe neben einem schmalen Gipfel)
MODUS_ABSTAND_MIN = 0.15  # dann muessen die beiden langsamsten Gruppen aber um mindestens 15 % im haeufigsten Tempo auseinanderliegen (sonst Form, nicht Gruppe)
SICHTBAR_MIN = 0.25  # von jeder Gruppe muss mindestens so viel ihrer Flaeche im erfassten Bereich liegen
TOL_LAGE = 0.07  # Haelften stimmen ueberein: Modus (Logarithmus), mindestens, bei breiten Gruppen 0,25 x Streuung ...
TOL_ANTEIL = 0.06  # ... und Anteil
LANGSAM_FAKTOR = 0.6  # langsame Gruppe: Modus hoechstens 0,6 x Tempolimit
LANGSAM_MAX_ANTEIL = 0.5

# Zeitscheiben (Ortszeit): Name, von, bis (Stunde, bis exklusiv); der Schulweg (7-8 Uhr, Mo-Fr) steht in dsd2csv.TEILZEITRAEUME
ZEITSCHEIBEN = [("nacht", 22, 6), ("vormittag", 6, 12), ("nachmittag", 12, 19), ("abend", 19, 22)]
TAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag", "Feiertag"]  # Schluessel 0-7

SQ2PI = math.sqrt(2 * math.pi)


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


def zellen_bauen(vorher, nachher, spannen):
    """Zellen (Tagschluessel, Stunde) mit Histogrammen der Fahrzeuge in vollstaendig aufgezeichneten Stunden.

    vorher: [(Ortszeit, v)] mit nutzbarer Zeit vor dem Abzug des Rauschbodens, nachher: dieselbe Liste danach (gleiche Objekte,
    Teilmenge). Gibt dict mit D (abgedeckte Stunden je Zelle), z (Fahrzeuge je Zelle und Geschwindigkeit), r (der herausgerechnete
    Rauschboden) und haelften (zwei Counter ueber gerade bzw. ungerade Messtage) zurueck.
    """
    abgedeckt = rauschen.abgedeckte_stunden(spannen)
    behalten = {id(f) for f in nachher}
    D = collections.Counter()
    for datum, h in abgedeckt:
        D[(tagschluessel(dt.datetime(datum.year, datum.month, datum.day)), h)] += 1
    z = collections.defaultdict(collections.Counter)
    r = collections.defaultdict(collections.Counter)
    tage = sorted({t.date() for t, _ in nachher})
    gerade = {t for i, t in enumerate(tage) if i % 2 == 0}
    haelften = (collections.Counter(), collections.Counter())
    for f in vorher:
        t, v = f
        if (t.date(), t.hour) not in abgedeckt:
            continue
        zelle = (tagschluessel(t), t.hour)
        if id(f) in behalten:
            z[zelle][v] += 1
            haelften[0 if t.date() in gerade else 1][v] += 1
        else:
            r[zelle][v] += 1
    return {"D": D, "z": z, "r": r, "haelften": haelften}


def zelle_kodiert(c):
    """Counter -> [v, n, v, n, ...] aufsteigend."""
    out = []
    for v in sorted(c):
        out += [v, c[v]]
    return out


# ------------------------------------------------------------------ Mischung von Lognormal-Verteilungen

class Mischung:
    """Mischung von Lognormal-Verteilungen: Anteile w, Mittel mu und Streuung s des Logarithmus der Geschwindigkeit.

    xa: Logarithmus der Geschwindigkeit, ab der Fahrzeuge erfasst sind (links davon ist nichts bekannt, nicht null).
    Die Dichte der erfassten Werte ist die Mischung geteilt durch den erfassten Anteil z() der Gesamtfläche.
    """

    def __init__(self, w, mu, s, ll=0.0, xa=None):
        self.w, self.mu, self.s, self.ll, self.xa = list(w), list(mu), list(s), ll, xa

    @property
    def k(self):
        return len(self.w)

    def sichtbar(self, j):
        """Anteil der Flaeche von Gruppe j im erfassten Bereich (1 ohne Abschneidung)."""
        return 1.0 if self.xa is None else _ueberleben((self.xa - self.mu[j]) / self.s[j])

    def z(self):
        return sum(self.w[j] * self.sichtbar(j) for j in range(self.k))

    def anteile(self):
        """Anteil jeder Gruppe an den erfassten Fahrzeugen."""
        z = self.z()
        return [self.w[j] * self.sichtbar(j) / z for j in range(self.k)]

    def pdf(self, j, v):
        z = (math.log(v) - self.mu[j]) / self.s[j]
        return math.exp(-0.5 * z * z) / (SQ2PI * self.s[j] * v)

    def dichte(self, v):
        """Dichte der erfassten Fahrzeuge bei Geschwindigkeit v (auf den erfassten Bereich normiert)."""
        return sum(self.w[j] * self.pdf(j, v) for j in range(self.k)) / self.z()

    def modus(self, j):
        return math.exp(self.mu[j] - self.s[j] ** 2)

    def antworten(self, v):
        """Anteil jeder Gruppe an Fahrzeugen mit Geschwindigkeit v (Summe 1)."""
        p = [self.w[j] * self.pdf(j, v) for j in range(self.k)]
        s = sum(p)
        if s <= 0:  # weit ausserhalb aller Gruppen: der naechsten zuordnen
            j = min(range(self.k), key=lambda i: abs(math.log(v) - self.mu[i]))
            return [1.0 if i == j else 0.0 for i in range(self.k)]
        return [x / s for x in p]

    def sortiert(self):
        return sorted(range(self.k), key=self.modus)

    def als_dict(self):
        return {"w": self.w, "mu": self.mu, "s": self.s, "xa": self.xa}


def _ueberleben(a):
    """Anteil der Standardnormalverteilung oberhalb von a."""
    return 0.5 * math.erfc(a / math.sqrt(2))


def _verhaeltnis(a):
    """phi(a) / Phi(a) (Kehrwert des Mills-Verhaeltnisses fuer den linken Rand), auch weit im Rand stabil."""
    if a < -30:
        return -a + 1.0 / -a
    phi = math.exp(-0.5 * a * a) / SQ2PI
    return phi / (0.5 * math.erfc(-a / math.sqrt(2)))


def em(werte, anzahl, w, mu, s, xa=None, iterationen=400, tol=1e-9):
    """EM fuer eine Lognormal-Mischung auf Zaehlwerten (werte >= 1 km/h), links bei xa abgeschnitten.

    Fehlende Fahrzeuge links von xa werden als unbeobachtet behandelt: Die Anpassung nutzt die Flanke, die im erfassten Bereich
    liegt, und ergaenzt die abgeschnittene Flaeche im Erwartungsschritt (Momente der abgeschnittenen Normalverteilung).
    Eine Gruppe muss zu mindestens SICHTBAR_MIN im erfassten Bereich liegen, sonst ist ihre Lage nicht bestimmbar.
    Gibt Mischung mit Log-Likelihood der erfassten Werte (Geschwindigkeitsraum) zurueck.
    """
    k = len(w)
    xs = [math.log(v) for v in werte]
    n = sum(anzahl)
    smin = [max(0.03, 0.8 / max(werte[0], 1))] * k if xa is not None else [0.03] * k
    schranke = 0.8416  # Phi^-1(1 - SICHTBAR_MIN)
    w, mu, s = list(w), list(mu), list(s)
    alt = None
    for _ in range(iterationen):
        obs, s1, s2, ll = [0.0] * k, [0.0] * k, [0.0] * k, 0.0
        for x, c in zip(xs, anzahl):
            p = [w[j] * math.exp(-0.5 * ((x - mu[j]) / s[j]) ** 2) / s[j] for j in range(k)]
            den = sum(p)
            if den <= 0:
                continue
            ll += c * math.log(den)
            for j in range(k):
                r = c * p[j] / den
                obs[j] += r
                s1[j] += r * x
                s2[j] += r * x * x
        fehl = [0.0] * k
        if xa is not None:
            z = sum(w[j] * _ueberleben((xa - mu[j]) / s[j]) for j in range(k))
            for j in range(k):
                a = (xa - mu[j]) / s[j]
                fehl[j] = n / z * w[j] * (1 - _ueberleben(a))  # erwartete Fahrzeuge dieser Gruppe links von xa
                lam = _verhaeltnis(a)
                m1 = mu[j] - s[j] * lam  # E[x | x < xa]
                var = max(s[j] ** 2 * (1 - a * lam - lam * lam), 1e-12)
                s1[j] += fehl[j] * m1
                s2[j] += fehl[j] * (var + m1 * m1)
        gesamt = [obs[j] + fehl[j] for j in range(k)]
        summe = sum(gesamt)
        w = [max(g / summe, 1e-6) for g in gesamt]
        mu = [s1[j] / max(gesamt[j], 1e-9) for j in range(k)]
        s = [max(math.sqrt(max(s2[j] / max(gesamt[j], 1e-9) - mu[j] ** 2, 0.0)), smin[j]) for j in range(k)]
        if xa is not None:  # nicht weiter in den abgeschnittenen Bereich wandern
            mu = [max(mu[j], xa - schranke * s[j]) for j in range(k)]
        if alt is not None and abs(ll - alt) < tol * abs(ll):
            break
        alt = ll
    m = Mischung(w, mu, s, 0.0, xa)
    z = m.z()
    ll = 0.0
    for x, c in zip(xs, anzahl):
        den = sum(w[j] * math.exp(-0.5 * ((x - mu[j]) / s[j]) ** 2) / s[j] for j in range(k))
        if den > 0:
            ll += c * (math.log(den / SQ2PI / z) - x)
    m.ll = ll
    return m


def anpassen(werte, anzahl, k, versuche=3, seed=3, ab=None):
    """Beste Anpassung mit k Gruppen aus mehreren Startwerten (Quantile, dann zufaellig mit festem Startwert).

    ab: kleinste erfasste Geschwindigkeit; links davon gilt die Verteilung als nicht erfasst (nicht als null).
    """
    xs = [math.log(v) for v in werte]
    xa = None if ab is None else math.log(ab - 0.5)
    n = sum(anzahl)
    mittel = sum(x * c for x, c in zip(xs, anzahl)) / n
    sd = math.sqrt(sum(c * (x - mittel) ** 2 for x, c in zip(xs, anzahl)) / n)
    rnd = random.Random(seed)
    beste = None
    for t in range(versuche):
        if t == 0:
            mus, kum, i = [], 0, 0
            for j in range(k):
                ziel = (j + 0.5) / k * n
                while kum + anzahl[i] < ziel:
                    kum += anzahl[i]
                    i += 1
                mus.append(xs[i])
        elif t == 1 and xa is not None:  # eine Gruppe darf zuerst am Rand beginnen
            mus = sorted([xa] + [rnd.uniform(xs[0], xs[-1]) for _ in range(k - 1)])
        else:
            mus = sorted(rnd.uniform(xs[0], xs[-1]) for _ in range(k))
        m = em(werte, anzahl, [1.0 / k] * k, mus, [max(sd / (k + 1), 0.1)] * k, xa)
        if beste is None or m.ll > beste.ll:
            beste = m
    return beste


def ll_je_fahrzeug(m, werte, anzahl):
    n = sum(anzahl)
    return sum(c * math.log(max(m.dichte(v), 1e-300)) for v, c in zip(werte, anzahl)) / n


def trennschaerfen(m):
    """(D_unten, D_alle): Ashman-Abstand D = sqrt(2) |mu_i - mu_j| / sqrt(s_i^2 + s_j^2) im Logarithmus.

    D_unten: langsamste Gruppe gegen die naechste, D_alle: kleinster Abstand aller Paare (Gruppen mit Anteil >= MIN_ANTEIL).
    """
    anteile = m.anteile()
    idx = sorted((j for j in range(m.k) if anteile[j] >= MIN_ANTEIL), key=m.modus)
    if len(idx) < 2:
        return None, None

    def dd(i, j):
        return math.sqrt(2) * abs(m.mu[i] - m.mu[j]) / math.sqrt(m.s[i] ** 2 + m.s[j] ** 2)

    paare = [dd(i, j) for a, i in enumerate(idx) for j in idx[a + 1:]]
    return dd(idx[0], idx[1]), min(paare)


def modus_abstand(m):
    """Logarithmus des Verhaeltnisses der haeufigsten Tempi der beiden langsamsten Gruppen (Anteil >= MIN_ANTEIL)."""
    anteile = m.anteile()
    idx = sorted((j for j in range(m.k) if anteile[j] >= MIN_ANTEIL), key=m.modus)
    return math.log(m.modus(idx[1]) / m.modus(idx[0])) if len(idx) >= 2 else None


def vergleichbar(a, b):
    """Die Gruppen zweier Anpassungen (nach Modus sortiert) stimmen in Lage und Anteil ueberein."""
    aa, ab = a.anteile(), b.anteile()  # Anteile an den erfassten Fahrzeugen
    for ja, jb in zip(a.sortiert(), b.sortiert()):
        tol = max(TOL_LAGE, 0.25 * 0.5 * (a.s[ja] + b.s[jb]))  # die Lage einer breiten Gruppe ist ungenauer
        if abs(math.log(a.modus(ja)) - math.log(b.modus(jb))) > tol or abs(aa[ja] - ab[jb]) > TOL_ANTEIL:
            return False
    return True


def tabelle(zaehler, ab):
    werte = sorted(v for v in zaehler if v >= max(ab, 1))
    return werte, [zaehler[v] for v in werte]


def waehle_k(gerade, ungerade, ab):
    """Bestimmt die Zahl der Gruppen. gerade/ungerade: Counter der Haelften der Messtage, ab: kleinste angepasste Geschwindigkeit.

    Links von ab ist die Verteilung nicht erfasst (nicht null): die Anpassung nutzt die Flanke im erfassten Bereich.
    Gibt dict mit k, obere_gruppen_ueberlappen, auswahl (je K: stabil, klein, sichtbar_min, d_unten, d_alle, cv_gewinn) und mischung zurueck.
    """
    gesamt = collections.Counter(gerade)
    gesamt.update(ungerade)
    tw, ta = tabelle(gesamt, ab)
    aw, aa = tabelle(gerade, ab)
    bw, ba = tabelle(ungerade, ab)
    vorher = (anpassen(aw, aa, 1, 2, ab=ab), anpassen(bw, ba, 1, 2, ab=ab))
    auswahl, mischungen, fehl = [], {}, 0
    for k in range(2, K_MAX + 1):
        ma, mb, mt = anpassen(aw, aa, k, ab=ab), anpassen(bw, ba, k, ab=ab), anpassen(tw, ta, k, 4, ab=ab)
        gewinn = 0.5 * (ll_je_fahrzeug(ma, bw, ba) - ll_je_fahrzeug(vorher[0], bw, ba)
                        + ll_je_fahrzeug(mb, aw, aa) - ll_je_fahrzeug(vorher[1], aw, aa))
        du, da = trennschaerfen(mt)
        abst = modus_abstand(mt)
        sichtbar = min(mt.sichtbar(j) for j in range(k))  # kleinster Teil einer Gruppe im erfassten Bereich
        e = {"k": k, "stabil": vergleichbar(ma, mb), "klein": min(min(ma.anteile()), min(mb.anteile())) < MIN_ANTEIL,
             "sichtbar_min": round(sichtbar, 2),
             "d_unten": None if du is None else round(du, 2), "d_alle": None if da is None else round(da, 2),
             "modus_abstand": None if abst is None else round(abst, 2), "cv_gewinn": round(gewinn, 4)}
        auswahl.append(e)
        mischungen[k] = mt
        vorher = (ma, mb)
        if gewinn < CV_GEWINN_MIN:
            break
        fehl = 0 if (e["stabil"] and not e["klein"] and sichtbar >= SICHTBAR_MIN) else fehl + 1
        if fehl >= 2:
            break
    ok = [e for e in auswahl if e["stabil"] and not e["klein"] and e["sichtbar_min"] >= SICHTBAR_MIN and e["cv_gewinn"] >= CV_GEWINN_MIN]
    getrennt = [e["k"] for e in ok if e["d_alle"] is not None and e["d_alle"] >= D_MIN]
    unten = [e["k"] for e in ok if e["d_unten"] is not None and e["d_unten"] >= D_MIN]
    stark = [e["k"] for e in ok if e["cv_gewinn"] >= CV_GEWINN_STARK and (e["modus_abstand"] or 0) >= MODUS_ABSTAND_MIN]
    if getrennt:
        k, ueberlappend = max(getrennt), False
    elif unten:
        k, ueberlappend = max(unten), True
    elif stark:
        k, ueberlappend = max(stark), True
    else:
        k, ueberlappend = 1, False
    return {"k": k, "obere_gruppen_ueberlappen": ueberlappend, "auswahl": auswahl,
            "mischung": mischungen[k].als_dict() if k > 1 else None}


# ------------------------------------------------------------------ Kennzahlen

def toleranz(v):
    return 3 if v < 100 else math.ceil(0.03 * v)


def kennzahlen(hist, limit):
    """Kennzahlen eines (gewichteten) Histogramms {v: Anzahl}: Fahrzeuge, Mittel, V85/V95/V99, Einhaltung, qualifizierte Einhaltung."""
    n = sum(hist.values())
    if n <= 0:
        return None
    erg = {"fahrzeuge": round(n), "mittel_kmh": round(sum(v * c for v, c in hist.items()) / n, 2)}
    kum, ziele = 0.0, {85: None, 95: None, 99: None}
    for v in sorted(hist):
        kum += hist[v]
        for q in ziele:
            if ziele[q] is None and kum >= q / 100 * n - 1e-9:
                ziele[q] = v
    for q, v in ziele.items():
        erg[f"v{q}_kmh"] = v
    if limit:
        erg["einhaltungsquote_prozent"] = round(100 * sum(c for v, c in hist.items() if v <= limit) / n, 2)
        erg["qualifizierte_einhaltungsquote_prozent"] = round(100 * sum(c for v, c in hist.items() if v - toleranz(v) <= limit) / n, 2)
    return erg


def abschneiden(zaehler):
    """Kleinste Geschwindigkeit, ab der angepasst wird: ein Haufen am unteren Rand (Sensorgrenze) bleibt ausserhalb.

    Das erste lokale Minimum der geglaetteten Verteilung unterhalb von 30 km/h, wenn der Rand deutlich hoeher liegt. Wo der
    Rauschboden belegt und abgezogen ist, wird nicht abgeschnitten.
    """
    lo, hi = min(zaehler), max(zaehler)
    werte = list(range(lo, hi + 1))
    anzahl = [zaehler.get(v, 0) for v in werte]
    glatt = [sum(anzahl[max(0, i - 1):i + 2]) / len(anzahl[max(0, i - 1):i + 2]) for i in range(len(anzahl))]
    for i in range(2, min(len(glatt) - 2, 30)):
        if glatt[i] <= glatt[i - 1] and glatt[i] < glatt[i + 1] and glatt[i + 1] <= glatt[i + 2] * 1.3:
            # ein Haufen am Rand faellt von der ersten Klasse an; steigt die Kurve zuerst, ist es eine echte Gruppe
            if glatt[0] > 1.3 * glatt[i] and all(glatt[j] <= 1.1 * glatt[j - 1] for j in range(1, i + 1)):
                return werte[i]
            break
    return lo


# ------------------------------------------------------------------ Analyse einer Datei

def _hash_schluessel(*teile):
    import hashlib
    h = hashlib.sha256()
    for t in teile:
        h.update(repr(t).encode("utf-8"))
    return h.hexdigest()[:24]


def analysiere(zd, limit, rauschen_belegt, speicher=None, code_hash="", rausch_obergrenze=None):
    """Zerlegung und Zellendaten einer Datei. zd: Ergebnis von zellen_bauen.

    rausch_obergrenze: Geschwindigkeit, bis zu der 95 % des abgezogenen Rauschbodens liegen (Fahrzeuge bis dahin werden nicht zerlegt).
    Gibt (block, daten) zurueck. block: YAML-Block 'gruppen'. daten: Zellen und Gewichte fuer die Detailseite (None ohne Fahrzeuge).
    """
    gerade, ungerade = zd["haelften"]
    gesamt = collections.Counter(gerade)
    gesamt.update(ungerade)
    n = sum(gesamt.values())
    if not n:
        return {"geprueft": False, "grund": "keine Fahrzeuge in vollständig aufgezeichneten Stunden mit nutzbarer Zeit"}, None
    daten = {"v": 1, "limit": limit,
             "tage": {f"{d}|{h}": c for (d, h), c in sorted(zd["D"].items()) if c},
             "z": {f"{d}|{h}": zelle_kodiert(c) for (d, h), c in sorted(zd["z"].items())},
             "r": {f"{d}|{h}": zelle_kodiert(c) for (d, h), c in sorted(zd["r"].items()) if c}, "gruppen": []}
    if not limit or n < MIN_FAHRZEUGE:
        return {"geprueft": False, "grund": f"weniger als {MIN_FAHRZEUGE} Fahrzeuge oder kein Tempolimit"}, daten
    if rauschen_belegt:  # was der Abzug uebrig laesst, liegt im Bereich des Rauschbodens: nicht zerlegen
        ab = max(min(gesamt), (rausch_obergrenze or 0) + 1, 1)
    else:
        ab = max(abschneiden(gesamt), 1)
    schluessel = _hash_schluessel(sorted(gerade.items()), sorted(ungerade.items()), ab, code_hash)
    erg = speicher.holen("gruppen", schluessel) if speicher else None
    if erg is None:
        erg = waehle_k(gerade, ungerade, ab)
        if speicher:
            speicher.speichern("gruppen", schluessel, erg)
    k = erg["k"]
    block = {"geprueft": True, "anzahl": k, "obere_gruppen_ueberlappen": erg["obere_gruppen_ueberlappen"], "angepasst_ab_kmh": ab,
             "fahrzeuge": n, "fahrzeuge_unter_grenze": sum(c for v, c in gesamt.items() if v < ab)}
    if k == 1:
        block["grund"] = "keine stabile, voneinander getrennte Zerlegung nachweisbar"
    block["auswahl"] = erg["auswahl"]
    if k == 1:
        return block, daten
    m = Mischung(**erg["mischung"])
    vmax = max(gesamt)
    antw = {v: m.antworten(v) for v in range(ab, vmax + 1)}
    rang = m.sortiert()  # Gruppe 1 ist die langsamste
    nutz = sum(c for v, c in gesamt.items() if v >= ab)
    gruppen, histe = [], []
    for nr, j in enumerate(rang, 1):
        h = {v: c * antw[v][j] for v, c in gesamt.items() if v >= ab}
        histe.append(h)
        kz = kennzahlen(h, limit)
        gruppen.append({"nr": nr, "anteil_prozent": round(100 * sum(h.values()) / nutz, 2), "modus_kmh": round(m.modus(j), 1),
                        "streuung_log": round(m.s[j], 3), "sichtbar_prozent": round(100 * m.sichtbar(j)), "mittel_kmh": kz["mittel_kmh"], "v85_kmh": kz["v85_kmh"],
                        "einhaltungsquote_prozent": kz.get("einhaltungsquote_prozent"),
                        "qualifizierte_einhaltungsquote_prozent": kz.get("qualifizierte_einhaltungsquote_prozent")})
    langsam = [g["nr"] for g in gruppen if g["modus_kmh"] <= LANGSAM_FAKTOR * limit]
    if langsam and len(langsam) < k and sum(gruppen[i - 1]["anteil_prozent"] for i in langsam) <= 100 * LANGSAM_MAX_ANTEIL:
        for g in gruppen:
            g["langsam"] = g["nr"] in langsam
        haupt = {v: c * (1 - sum(antw[v][rang[i - 1]] for i in langsam)) for v, c in gesamt.items() if v >= ab}
        kz = kennzahlen(haupt, limit)
        block["hauptmenge_ohne_langsame"] = {"gruppen": [g["nr"] for g in gruppen if not g["langsam"]],
                                              "anteil_prozent": round(100 * sum(haupt.values()) / nutz, 2), **kz}
    else:
        langsam = []
    block["gruppen"] = gruppen
    daten["rand"] = ab if ab > min(gesamt) else 0
    daten["w0"] = ab
    daten["langsam"] = langsam
    for g, j in zip(gruppen, rang):
        daten["gruppen"].append({"nr": g["nr"], "anteil": g["anteil_prozent"], "modus": g["modus_kmh"], "mittel": g["mittel_kmh"],
                                 "w": [round(antw[v][j], 3) for v in range(ab, vmax + 1)]})
    return block, daten
