# SPDX-License-Identifier: MIT
"""Einschwingen nach dem Beginn eines Einsatz-Abschnitts und Art der Aenderung an seiner Grenze.

Beginn eines Einsatz-Abschnitts ist eine Montage (Umhaengen, Inbetriebnahme), ein Bruch im Aufenthalt (verfeinerter Zeitpunkt) oder eine
ungepruefte Dateigrenze. Danach braucht der Verkehr womoeglich eine Weile, bis er sich eingespielt hat. Wir haben keine Daten vor der Montage;
messbar ist nur, wie sich der Verkehr nach dem Beginn bis zu seinem spaeteren Stand veraendert.

Schritte: ab der ersten vollen Stunde nach dem Beginn Fenster gleicher Laenge (1, 2, 3, 4 oder 7 Tage, je 24 Stunden, damit jede Tageszeit
gleich oft vorkommt). Die Laenge ist die kuerzeste, bei der ein Schritt im Mittel mindestens N_SCHRITT Fahrzeuge hat (ruhige Strassen:
laengere Schritte). Je Schritt mittleres Tempo, V85, V95 (aus den bereinigten Fahrzeugen des Einsatzes, nur vollstaendig aufgezeichnete
Stunden) bis HORIZONT Tage nach dem Beginn oder bis zum Ende des Abschnitts.
Tagtyp: An vielen Orten fahren Samstags und Sonntags andere Geschwindigkeiten. Damit Schritte von einem Tag (nur Werktag oder nur Sonntag) und
von sieben Tagen vergleichbar sind, wird jedes Fahrzeug um den Unterschied seines Tagtyps (Werktag, Samstag, Sonn- und Feiertag) zum Mittel
des Bezugsstands verschoben (mittleres Tempo im Bezugsstand je Tagtyp minus mittleres Tempo im Bezugsstand). Quantile mit Interpolation in
der km/h-Klasse (jede Klasse gleichmaessig von v - 0,5 bis v + 0,5), damit V85 und V95 nicht in ganzen km/h springen.
Bezugsstand (stabiler Stand): die Schritte ab Tag BEZUG_AB bis HORIZONT; Schwankung = Standardabweichung dieser Schritte um ihr Mittel
(Wetter, Wochen, Zufall). Ohne mindestens MIN_BEZUG Schritte dort gibt es kein Urteil (Abschnitt zu kurz).
Einschwingen: Modell Wert(t) = Stand + A * exp(-(t - t1) / tau) gegen konstant (BIC, Schritte bis HORIZONT, tau aus TAUS); belegt ab
dBIC >= DBIC_MIN. A ist die Abweichung im ersten Schritt vom spaeteren Stand. Stabil nach 3 tau (95 % der Anfangsabweichung abgebaut);
tau hoechstens 7 Tage, damit das Einschwingen vor dem Bezugsstand abgeschlossen ist.

Art der Aenderung (klassifizieren): Vergleich der Werktage (ohne Feiertage) bis VERGLEICH_TAGE vor und nach der Grenze, aus den Rohdaten der
Aufenthalte (bewegungen.py), ohne den Tag der Grenze selbst; ohne Ferien, wenn eine Seite dann noch MIN_VERGLEICH_TAGE hat. Liegen nur auf
einer Seite Ferientage, zaehlen Menge und Tagesgang nicht (Ferien aendern beides) und das Tempo erst ab der doppelten Schwelle:
  menge     ln(Fahrzeuge je Stunde danach / davor), ueber die Stunden des Tages, die auf beiden Seiten vorkommen
  profil    Gesamtvariation (TVD) der Tagesgaenge (Anteil der Fahrzeuge je Stunde) und Spitze = ln(Fahrzeuge 6-9 Uhr / 15-18 Uhr); eine
            andere Fahrtrichtung kehrt bei Pendlerverkehr die Spitze um (morgens in die Stadt, abends hinaus)
  tempo     Aenderung der Quantile q10 ... q90 (Fahrzeuge ab KMIN km/h; die Rohdaten enthalten langsame Stoerungen); additiv (alle gleich viel schneller) oder multiplikativ (alle um denselben Faktor; so wirkt
            ein anderer Messwinkel: das Radar misst v * cos(Winkel)); Streuung (q90 - q10)
  sofort    Anteil der Tempoaenderung, der im ersten Schritt nach der Grenze schon da ist (1 = sofort, darunter allmaehlich)
Klassen (Hinweise, keine Beweise; Schwellen in KLASSE_SCHWELLEN):
  standortwechsel   Montage zu Beginn eines Einsatzes: das Geraet kommt von einem anderen Ort (oder aus dem Lager); ebenso eine Bewegung
                    innerhalb einer Messung, nach der die Menge sich mehr als verdoppelt oder halbiert
  fahrtrichtung     Tagesgang deutlich anders und die Spitze kehrt sich um
  ausrichtung       Tempo um einen Faktor anders (multiplikativ passt deutlich besser als additiv), Menge und Tagesgang gleich
  ort_genau         Tempo sofort anders, Menge und Tagesgang gleich: anderer Mast, andere Hoehe oder Ausrichtung
  strasse           Tempo allmaehlich anders (etwa ein neues Schild) oder Menge anders bei gleichem Tagesgang (Baustelle, Umleitung)
  keine             keine deutliche Aenderung
  unklar            zu wenige Tage auf einer Seite, oder Ferien nur auf einer Seite und keine grosse Tempoaenderung
"""
import collections
import datetime as dt
import math

import kalender

STUNDE = dt.timedelta(hours=1)
TAG = dt.timedelta(days=1)
SCHRITTE = (1, 2, 3, 4, 7)          # moegliche Schrittlaengen in Tagen
N_SCHRITT = 1000                    # so viele Fahrzeuge soll ein Schritt im Mittel haben (V95 dann auf etwa 0,5 km/h genau)
HORIZONT = 63                       # Tage nach dem Beginn
BEZUG_AB = 21                       # ab diesem Tag gilt der Verkehr als eingespielt (Bezugsstand)
MIN_BEZUG = 3                       # mindestens so viele Schritte im Bezugsstand
MIN_ABDECKUNG = 0.5                 # Anteil vollstaendig aufgezeichneter Stunden je Schritt
TAUS = (1, 1.5, 2, 3, 4, 5, 7)    # 3 tau hoechstens BEZUG_AB: langsamere Veraenderungen sind Drift (Jahreszeit), kein Einschwingen
DBIC_MIN = 6.0
GROESSEN = ("mittel", "v85", "v95")
VERGLEICH_TAGE = 14
KMIN = 15
MIN_VERGLEICH_TAGE = 3
KLASSE_SCHWELLEN = {"tempo": 2.0, "menge": 0.3, "tvd": 0.2, "spitze": 0.5, "faktor_vorteil": 0.5, "sofort": 0.7, "menge_ort": math.log(2)}
KLASSE_TEXT = {"standortwechsel": "Standortwechsel", "fahrtrichtung": "andere Fahrtrichtung", "ausrichtung": "andere Ausrichtung (Messwinkel)",
               "ort_genau": "genauer Ort oder Ausrichtung geändert", "strasse": "Änderung an der Straße", "keine": "keine deutliche Änderung",
               "unklar": "nicht bestimmbar"}


def tagtyp(d):
    """0 Werktag, 1 Samstag, 2 Sonn- und Feiertag."""
    if kalender.feiertag(d) or d.weekday() == 6:
        return 2
    return 1 if d.weekday() == 5 else 0


def stunden_aus(zeilen, mit_abschnitt=None):
    """[(Beginn der Stunde, voll, Counter km/h)] aus Aggregat-Zeilen. Einsatz-Aggregat: [Datum, Stunde, Versatz, Abschnitt, voll, Regen,
    flach] (mit_abschnitt: nur dieser Abschnitt); Aufenthalt (bewegungen.py): [Datum, Stunde, Versatz, voll, flach]."""
    out = []
    for z in zeilen:
        if mit_abschnitt is not None:
            if z[3] != mit_abschnitt:
                continue
            voll, flach = z[4], z[6]
        else:
            voll, flach = z[3], z[4]
        d = dt.date.fromisoformat(z[0])
        out.append((dt.datetime(d.year, d.month, d.day, z[1]), bool(voll), collections.Counter(dict(zip(flach[0::2], flach[1::2])))))
    return out


def quantile(werte, ps):
    """Quantile aus [(km/h, Anzahl)] mit Interpolation in der Klasse (gleichmaessig von v - 0,5 bis v + 0,5)."""
    werte = sorted(werte)
    n = sum(c for _, c in werte)
    out, kum, i = [], 0, 0
    for p in ps:
        ziel = p * n
        while i < len(werte) and kum + werte[i][1] < ziel:
            kum += werte[i][1]
            i += 1
        if i >= len(werte):
            out.append(werte[-1][0] + 0.5)
            continue
        v, c = werte[i]
        out.append(v - 0.5 + (ziel - kum) / c)
    return out


def _kennwerte(werte):
    n = sum(c for _, c in werte)
    if not n:
        return None
    v85, v95 = quantile(werte, (0.85, 0.95))
    return {"mittel": sum(v * c for v, c in werte) / n, "v85": v85, "v95": v95, "fahrzeuge": n}


def anpassen(t, y):
    """(beste Einschwing-Kurve dict(tau, a, stand), dBIC gegen konstant) fuer Punkte (t, y)."""
    n = len(y)
    if n < 4:
        return None, 0.0
    m = sum(y) / n
    rss0 = sum((v - m) ** 2 for v in y)
    best = None
    t1 = min(t)
    for tau in TAUS:
        x = [math.exp(-(ti - t1) / tau) for ti in t]
        mx = sum(x) / n
        sxx = sum((xi - mx) ** 2 for xi in x)
        if sxx < 1e-9:
            continue
        a = sum((xi - mx) * (yi - m) for xi, yi in zip(x, y)) / sxx
        c = m - a * mx
        rss = sum((yi - c - a * xi) ** 2 for xi, yi in zip(x, y))
        if best is None or rss < best["rss"]:
            best = {"tau": tau, "a": a, "stand": c, "rss": rss}
    if not best or rss0 <= 1e-12:
        return best, 0.0
    bic0 = n * math.log(rss0 / n) + math.log(n)
    bic1 = n * math.log(max(best["rss"], 1e-12) / n) + 3 * math.log(n)
    return best, bic0 - bic1


def einschwingen(stunden, beginn, ende):
    """Schritte nach dem Beginn bis HORIZONT oder ende; Bezugsstand, Schwankung und Einschwingen je Groesse. None ohne Daten."""
    start = beginn.replace(minute=0, second=0, microsecond=0)
    if start < beginn:
        start += STUNDE
    bis = min(ende, start + HORIZONT * TAG)
    drin = [(t, c) for t, voll, c in stunden if voll and start <= t and t + STUNDE <= bis]
    if not drin:
        return None
    tage = (bis - start).total_seconds() / 86400
    je_tag = sum(sum(c.values()) for _, c in drin) / max(tage, 1e-9)
    laenge = next((s for s in SCHRITTE if je_tag * s >= N_SCHRITT), SCHRITTE[-1])
    # Tagtyp-Verschiebung aus dem Bezugsstand (Tag BEZUG_AB bis HORIZONT)
    ab = start + BEZUG_AB * TAG
    summe, anzahl = collections.Counter(), collections.Counter()
    for t, c in drin:
        if t >= ab:
            typ = tagtyp(t.date())
            summe[typ] += sum(v * k for v, k in c.items())
            anzahl[typ] += sum(c.values())
    gesamt = sum(summe.values()) / sum(anzahl.values()) if anzahl else None
    versatz = {typ: summe[typ] / anzahl[typ] - gesamt for typ in anzahl if anzahl[typ] >= 200} if gesamt is not None else {}
    schritte = []
    for k in range(max(1, int(tage // laenge))):  # nur ganze Schritte (ausser bei sehr kurzen Abschnitten)
        a, b = start + k * laenge * TAG, min(bis, start + (k + 1) * laenge * TAG)
        im =[(t, c) for t, c in drin if a <= t < b]
        moegliche = (b - a).total_seconds() / 3600
        if not im or len(im) < MIN_ABDECKUNG * moegliche:
            continue
        werte = collections.Counter()
        for t, c in im:
            off = versatz.get(tagtyp(t.date()), 0.0)
            for v, n in c.items():
                werte[v - off] += n
        kw = _kennwerte(list(werte.items()))
        if kw:
            schritte.append({"von_tag": round((a - start).total_seconds() / 86400, 2), "bis_tag": round((b - start).total_seconds() / 86400, 2),
                             "von": a.isoformat(), "bis": b.isoformat(), "abdeckung": round(len(im) / moegliche, 2),
                             **{g: round(kw[g], 2) for g in GROESSEN}, "fahrzeuge": kw["fahrzeuge"]})
    if not schritte:
        return None
    out = {"beginn": start.isoformat(), "schritt_tage": laenge, "fahrzeuge_je_tag": round(je_tag), "schritte": schritte,
           "tagtyp_versatz": {["werktag", "samstag", "sonntag"][typ]: round(v, 2) for typ, v in sorted(versatz.items())}}
    bezug = [s for s in schritte if s["von_tag"] >= BEZUG_AB]
    if len(bezug) < MIN_BEZUG:
        out["urteil"] = "zu_kurz"
        return out
    t = [(s["von_tag"] + s["bis_tag"]) / 2 for s in schritte]
    stabil = 0.0
    belegt = False
    for g in GROESSEN:
        werte = [s[g] for s in bezug]
        m = sum(werte) / len(werte)
        sd = math.sqrt(sum((w - m) ** 2 for w in werte) / (len(werte) - 1))
        kurve, dbic = anpassen(t, [s[g] for s in schritte])
        x = {"stand": round(m, 2), "schwankung": round(sd, 2), "erster": schritte[0][g], "abweichung_erster": round(schritte[0][g] - m, 2)}
        if kurve:
            x.update({"tau": kurve["tau"], "a": round(kurve["a"], 2), "dbic": round(dbic, 1), "belegt": dbic >= DBIC_MIN})
            if dbic >= DBIC_MIN and g in ("mittel", "v85"):
                belegt = True
                stabil = max(stabil, 3 * kurve["tau"])
        out[g] = x
    out["urteil"] = "einschwingen" if belegt else "sofort"
    out["stabil_tage"] = round(stabil, 1) if belegt else 0
    return out


# --- Art der Aenderung -------------------------------------------------------------------------------------------------------------------

def _werktage(stunden, von, bis, ohne_ferien):
    """{Datum: {Stunde: Counter}} der Werktage (ohne Feiertage) in [von, bis) mit mindestens 20 vollen Stunden."""
    je = collections.defaultdict(dict)
    for t, voll, c in stunden:
        if voll and von <= t < bis and t.weekday() < 5 and not kalender.feiertag(t.date()):
            if ohne_ferien and kalender.schulferien(t.date()):
                continue
            je[t.date()][t.hour] = c
    return {d: h for d, h in je.items() if len(h) >= 20}


def _seite(stunden, von, bis):
    """(Werktage einer Seite, mit Ferien): ohne Ferien, wenn dann noch genug Tage bleiben."""
    ohne = _werktage(stunden, von, bis, True)
    return (ohne, False) if len(ohne) >= MIN_VERGLEICH_TAGE else (_werktage(stunden, von, bis, False), True)


def _profil(tage):
    """Mittlere Fahrzeuge je Stunde des Tages {h: Rate}."""
    summe, n = collections.Counter(), collections.Counter()
    for h in tage.values():
        for s, c in h.items():
            summe[s] += sum(c.values())
            n[s] += 1
    return {s: summe[s] / n[s] for s in n}


def _tempo(tage):
    werte = collections.Counter()
    for h in tage.values():
        for c in h.values():
            werte.update({v: n for v, n in c.items() if v >= KMIN})
    return list(werte.items())


def merkmale(vor, nach):
    """Merkmale der Aenderung zwischen zwei Seiten {Datum: {Stunde: Counter}}."""
    pv, pn = _profil(vor), _profil(nach)
    gemeinsam = sorted(set(pv) & set(pn))
    sv, sn = sum(pv[s] for s in gemeinsam), sum(pn[s] for s in gemeinsam)
    if not sv or not sn:
        return None
    tvd = 0.5 * sum(abs(pv[s] / sv - pn[s] / sn) for s in gemeinsam)

    def spitze(p):
        morgens, abends = sum(p.get(s, 0) for s in range(6, 10)), sum(p.get(s, 0) for s in range(15, 19))
        return math.log(morgens / abends) if morgens and abends else None
    qv = quantile(_tempo(vor), (0.1, 0.25, 0.5, 0.75, 0.9))
    qn = quantile(_tempo(nach), (0.1, 0.25, 0.5, 0.75, 0.9))
    diff = [b - a for a, b in zip(qv, qn)]
    lnq = [math.log(b / a) for a, b in zip(qv, qn) if a > 0 and b > 0]
    faktor = math.exp(sorted(lnq)[len(lnq) // 2]) if lnq else None
    rest_add = max(diff) - min(diff)
    rest_mul = (max(lnq) - min(lnq)) * qv[2] if lnq else None  # in km/h beim Median
    sp_v, sp_n = spitze(pv), spitze(pn)
    return {"tage_vor": len(vor), "tage_nach": len(nach), "menge": round(math.log(sn / sv), 3), "tvd_profil": round(tvd, 3),
            "spitze_vor": round(sp_v, 2) if sp_v is not None else None, "spitze_nach": round(sp_n, 2) if sp_n is not None else None,
            "median_vor": round(qv[2], 1), "median_nach": round(qn[2], 1), "tempo": round(diff[2], 2), "q10_q90": [round(d, 2) for d in diff[::4]],
            "streuung": round((qn[4] - qn[0]) - (qv[4] - qv[0]), 2), "faktor": round(faktor, 3) if faktor else None,
            "rest_additiv": round(rest_add, 2), "rest_faktor": round(rest_mul, 2) if rest_mul is not None else None}


def klassifizieren(stunden_vor, stunden_nach, grenze_von, grenze_bis, montage_neu=False, es=None, vor_von=None, nach_bis=None, bewegung=False):
    """Art der Aenderung an einer Grenze. stunden_*: [(Beginn der Stunde, voll, Counter)] beider Seiten (Rohdaten); grenze_von/bis: Ende der
    Daten davor und Beginn danach (bei einem Bruch derselbe Zeitpunkt); montage_neu: Beginn eines Einsatzes mit einer Montage;
    es: Einschwingen danach (einschwingen()) fuer "sofort"; vor_von, nach_bis: andere Grenzen, die die Fenster begrenzen; bewegung: an der
    Grenze wurde eine Bewegung erkannt."""
    if montage_neu:
        return {"klasse": "standortwechsel"}
    tag_v = grenze_von.replace(hour=0, minute=0, second=0, microsecond=0)
    tag_n = grenze_bis.replace(hour=0, minute=0, second=0, microsecond=0) + TAG
    vor, ferien_v = _seite(stunden_vor, max(tag_v - VERGLEICH_TAGE * TAG, vor_von or dt.datetime.min), tag_v)
    nach, ferien_n = _seite(stunden_nach, tag_n, min(tag_n + VERGLEICH_TAGE * TAG, nach_bis or dt.datetime.max))
    if len(vor) < MIN_VERGLEICH_TAGE or len(nach) < MIN_VERGLEICH_TAGE:
        return {"klasse": "unklar", "tage_vor": len(vor), "tage_nach": len(nach)}
    m = merkmale(vor, nach)
    if m is None:
        return {"klasse": "unklar", "tage_vor": len(vor), "tage_nach": len(nach)}
    s = KLASSE_SCHWELLEN
    m["ferien"] = [ferien_v, ferien_n]
    gemischt = ferien_v != ferien_n  # Ferien nur auf einer Seite: Menge und Tagesgang sagen dann nichts, das Tempo nur bei grosser Aenderung
    if es and es.get("schritte") and abs(m["tempo"]) >= s["tempo"]:
        # erster Schritt gegen den Stand danach (ohne Bezugsstand: die Werktage danach), beides auf Werktage umgerechnet (Tagtyp-Versatz)
        w = es.get("tagtyp_versatz", {}).get("werktag", 0.0)
        tv = _tempo(vor)
        vor_mittel = sum(v * c for v, c in tv) / max(1, sum(c for _, c in tv))
        if es.get("mittel"):
            stand = es["mittel"]["stand"] + w
        else:
            tn = _tempo(nach)
            stand = sum(v * c for v, c in tn) / max(1, sum(c for _, c in tn))
        if abs(stand - vor_mittel) > 1e-6:
            m["sofort"] = round((es["schritte"][0]["mittel"] + w - vor_mittel) / (stand - vor_mittel), 2)
    flip = (m["spitze_vor"] is not None and m["spitze_nach"] is not None and m["spitze_vor"] * m["spitze_nach"] < 0
            and abs(m["spitze_nach"] - m["spitze_vor"]) >= s["spitze"])
    tempo = abs(m["tempo"]) >= s["tempo"] * (2 if gemischt else 1)
    menge = abs(m["menge"]) >= s["menge"] and not gemischt
    profil = m["tvd_profil"] >= s["tvd"] and not gemischt
    if bewegung and abs(m["menge"]) >= s["menge_ort"]:
        k = "standortwechsel"
    elif profil and flip:
        k = "fahrtrichtung"
    elif tempo and not menge and not profil and m["rest_faktor"] is not None and m["rest_faktor"] <= s["faktor_vorteil"] * m["rest_additiv"]:
        k = "ausrichtung"
    elif tempo and m.get("sofort") is not None and m["sofort"] < s["sofort"]:
        k = "strasse"
    elif tempo and not menge:
        k = "ort_genau"
    elif menge or profil:
        k = "strasse" if not tempo else "ort_genau"
    else:
        k = "unklar" if gemischt else "keine"  # mit Ferien auf einer Seite ist "keine Aenderung" nicht pruefbar
    return {"klasse": k, **m}
