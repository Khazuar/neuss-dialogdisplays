# SPDX-License-Identifier: MIT
"""Verhaltensgruppen je Abschnitt einer Messreihe (docs/verhalten.md).

Modell:  lambda[Stunde, Klasse] = sum_k exp(X[Stunde] . beta_k) * H[k, Klasse]
K Gruppen mit festem Geschwindigkeitsprofil H_k (2-km/h-Klassen von 0 bis 90 km/h), deren Menge je Stunde von Stunde x Tagtyp, Licht
(Sonnenhoehe), Regen, Temperatur, Frost, Wind, Schnee, Schulferien, Feiertagen, Verkehrsmenge und einem langsamen Trend abhaengt.
Die Zahl der Gruppen folgt aus der Vorhersage ungesehener Wochen (Anpassung auf geraden, Bewertung auf ungeraden Wochen und umgekehrt).
Der Placebo-Durchgang verschiebt Wetter, Licht und Ferien gegen die Stunden; er dient dem Vergleich auf Stadtebene (stadtgruppen.py).
Vorlagen: Profile der Stadtgruppen (belege/verhaltensgruppen-register.json) werden in Abschnitten ohne eigene Gruppe dieser Art als feste
Form eingesetzt; verbessert das die Vorhersage, gilt die Gruppe dort als mit Stadtprofil nachgewiesen.

numpy ist noetig (sonst verfuegbar() == False und die Pipeline laesst die Verhaltensgruppen aus). Wer numpy nicht installiert hat:
pip install --target <Ordner> numpy und NUMPY_PFAD=<Ordner> setzen. Jeder Abschnitt wird einzeln gerechnet und im Zwischenspeicher
abgelegt (Schluessel: Inhalt der Stundentabelle und dieses Skript), so dass meist nur neue Abschnitte gerechnet werden.
"""
import bisect
import datetime as dt
import math
import os
import sys

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")  # ein Rechenfaden je Prozess; dsd2csv rechnet mehrere Dateien gleichzeitig
if os.environ.get("NUMPY_PFAD"):
    sys.path.insert(0, os.environ["NUMPY_PFAD"])
try:
    import numpy as np
except ImportError:  # pragma: no cover - ohne numpy keine Verhaltensgruppen
    np = None

import json  # noqa: E402

import gruppen  # noqa: E402
import kalender  # noqa: E402
import rauschen  # noqa: E402
import zwischenspeicher  # noqa: E402

REGISTER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "belege", "verhaltensgruppen-register.json")
CODE = zwischenspeicher.code_hash(os.path.abspath(__file__))  # Teil der Schluessel im Zwischenspeicher (beim Laden, gilt fuer den ganzen Lauf)

EPOCHE = dt.datetime(2020, 1, 1)
BREITE = 2
NBIN = 46  # 0-2, 2-4, ..., 88-90, ab 90
EPS = 1e-9
KMAX = 5
MIN_TAGE = 14
MIN_FAHRZEUGE = 5000
VORLAGE_MIN_TAGE = 7
VORLAGE_MIN_FAHRZEUGE = 1000
GEWINN_SCHWELLE = 0.002  # nats je Fahrzeug: so viel muss eine weitere Gruppe die Vorhersage ungesehener Wochen verbessern
KOV = ["daemmerung", "tiefe_sonne", "nacht", "regen_0_1", "regen_0_5", "regen_2", "nach_regen", "temp_10c", "frost", "wind_10ms",
       "schnee", "ferien", "feiertag", "dichte_log"]
KLASSEN = {"haupt": "Hauptgruppe", "rauschen": "sehr langsam (unter 12 km/h)", "langsam": "langsam (12 bis 28 km/h)",
           "etwas_langsamer": "etwas langsamer als die Hauptgruppe", "schnell": "schneller als die Hauptgruppe"}
RIDGE_MERKMALE = float(os.environ.get("VERHALTEN_RIDGE", "1.0"))
MIN_ANTEIL = 0.02
MIN_STABIL = 0.9


def verfuegbar():
    return np is not None


def mitten():
    m = np.arange(NBIN) * BREITE + 1.0
    m[-1] = 92.0
    return m


def klasse(g, haupt):
    """Art einer Gruppe im Vergleich zur Hauptgruppe desselben Abschnitts (Dicts mit modus, mittel)."""
    if g is haupt:
        return "haupt"
    if g["modus_kmh"] < 12:
        return "rauschen"
    if g["modus_kmh"] <= 28 and g["mittel_kmh"] < haupt["mittel_kmh"] - 5:
        return "langsam"
    return "etwas_langsamer" if g["mittel_kmh"] < haupt["mittel_kmh"] else "schnell"


# ------------------------------------------------------------------ Stundentabelle

def sonnenhoehe(utc, breite, laenge):
    """Sonnenhoehe in Grad (NOAA/Spencer)."""
    doy = utc.timetuple().tm_yday
    h = utc.hour + utc.minute / 60.0
    g = 2 * math.pi / 365 * (doy - 1 + (h - 12) / 24)
    eq = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    dek = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g)
           - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    ha = math.radians((h * 60 + eq + 4 * laenge) / 4 - 180)
    la = math.radians(breite)
    c = math.sin(la) * math.sin(dek) + math.cos(la) * math.cos(dek) * math.cos(ha)
    return 90 - math.degrees(math.acos(max(-1.0, min(1.0, c))))


def stundentabelle(fahrzeuge, spannen, ort, regen, wetter_tage, utc_versatz_h, grenzen):
    """Vollstaendig aufgezeichnete Stunden mit Wetter: (Stunden [(Datum, Stunde)], M [n x NBIN], ctx [n x 14]).

    fahrzeuge: [(Ortszeit, v)] mit nutzbarer Zeit (vor Abzug des Rauschbodens: das Modell findet ihn als eigene Gruppe),
    grenzen: erste Tage der Abschnitte 2, 3, ... (bruch.py). ctx: r0, r(h-1), r(h+1), tmk, tnk, fx, shk, Sonnenhoehe, Wochentag, Stunde,
    Tag (seit 2020), Ferien, Feiertag, Abschnitt (0 = erster)."""
    abged = sorted(rauschen.abgedeckte_stunden(spannen))
    idx = {s: i for i, s in enumerate(abged)}
    M = np.zeros((len(abged), NBIN))
    for t, v in fahrzeuge:
        i = idx.get((t.date(), t.hour))
        if i is not None:
            M[i, min(int(v) // BREITE, NBIN - 1)] += 1
    ctx = np.full((len(abged), 14), np.nan)
    for i, (tag, h) in enumerate(abged):
        lok = dt.datetime(tag.year, tag.month, tag.day, h)
        w = wetter_tage.get(tag.isoformat(), {})
        p, n = lok - dt.timedelta(hours=1), lok + dt.timedelta(hours=1)
        r0, rp, rn = regen(tag, h), regen(p.date(), p.hour), regen(n.date(), n.hour)
        mitte = lok + dt.timedelta(minutes=30)
        utc = mitte - dt.timedelta(hours=utc_versatz_h(mitte - dt.timedelta(hours=1)))
        bt = kalender.besonderer_tag(tag)
        ctx[i] = [np.nan if r0 is None else r0, np.nan if rp is None else rp, np.nan if rn is None else rn,
                  w.get("tmk", np.nan), w.get("tnk", np.nan), w.get("fx", np.nan), w.get("shk") or 0.0,
                  sonnenhoehe(utc, ort[0], ort[1]), tag.weekday(), h, (tag - EPOCHE.date()).days,
                  1.0 if bt == "ferien" else 0.0, 1.0 if bt == "feiertag" else 0.0, bisect.bisect_right(grenzen, tag)]
    ok = ~np.isnan(ctx[:, :8]).any(1)
    return [s for s, k in zip(abged, ok) if k], M[ok], ctx[ok]


# ------------------------------------------------------------------ Modell

def entwurf(c, M, lim, placebo=False):
    r0, rp, rn, tmk, tnk, fx, shk, ele, wd, hr, tag, fer, fei = [c[:, i] for i in range(13)]
    if placebo:  # Wetter, Licht und Ferien gegen die Stunden verschieben: echte Zusammenhaenge brechen, Selbstaehnlichkeit bleibt
        r0, rp, rn, tmk, tnk, fx, shk = [np.roll(x, 24 * 37) for x in (r0, rp, rn, tmk, tnk, fx, shk)]
        ele = np.roll(ele, 24 * 45)
        fer, fei = np.roll(fer, 24 * 29), np.roll(fei, 24 * 29)
    r = r0 + 0.5 * (rp + rn)
    typ = np.where(fei > 0, 2, np.where(wd <= 4, 0, np.where(wd == 5, 1, 2)))
    zelle = (typ * 24 + hr).astype(int)
    cols = [(zelle == k).astype(float) for k in range(72)]
    kov = [(ele > -6) & (ele <= 0), (ele > 0) & (ele <= 15), ele <= -6,
           (r >= 0.1) & (r < 0.5), (r >= 0.5) & (r < 2), r >= 2, (r < 0.1) & (rp >= 0.1),
           (tmk - 10) / 10.0, tnk < 0, fx / 10.0 - 1, shk > 0, fer > 0, fei > 0]
    cols += [np.asarray(x, dtype=float) for x in kov]
    n = M[:, int(0.5 * lim) // BREITE:].sum(1)
    ln = np.log(n + 1.0)
    cols.append(ln - np.median(ln))  # Verkehrsmenge (Fahrzeuge ab halbem Tempolimit)
    t = (tag - tag.mean()) / 30.0
    cols += [t, t * t]  # langsamer Trend (Jahreszeit, Bauzustand)
    return np.stack(cols, axis=1)


def nmf(M, K, iters=200, seed=0):
    """Poisson-NMF (Kullback-Leibler) als Startwert: (W [n x K], H [K x B])."""
    rng = np.random.RandomState(seed)
    n, B = M.shape
    H = rng.rand(K, B) + 0.1
    H /= H.sum(1, keepdims=True)
    W = (M.sum(1, keepdims=True) / K + 0.1) * (rng.rand(n, K) + 0.5)
    for _ in range(iters):
        R = M / (W @ H + EPS)
        W *= (R @ H.T) / (H.sum(1)[None, :] + EPS)
        R = M / (W @ H + EPS)
        H *= (W.T @ R) / (W.sum(0)[:, None] + EPS)
        s = H.sum(1, keepdims=True) + EPS
        H /= s
        W *= s.T
    return W, H


def kosinus(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + EPS))


def irls_schritt(X, y, b, ridge):
    eta = np.clip(X @ b, -30, 30)
    mu = np.exp(eta)
    z = eta + (y - mu) / np.maximum(mu, 1e-6)
    A = X.T @ (X * mu[:, None]) + ridge
    return np.linalg.solve(A, X.T @ (mu * z))


def anpassen(M, X, K, iters=120, seed=0, fest=None, tol=1e-5):
    """(beta [K x p], H [K x B]). fest: {Gruppe: Profil} bleiben unveraendert (Vorlagen). Endet frueher, wenn sich nichts mehr tut."""
    n, B = M.shape
    p = X.shape[1]
    ridge = np.diag(np.r_[np.full(72, 1e-3), np.full(p - 72, RIDGE_MERKMALE)])
    W0, H = nmf(M, K, 200, seed=seed)
    for k, prof in (fest or {}).items():
        H[k] = prof
    beta = np.zeros((K, p))
    for k in range(K):
        y = W0[:, k]
        beta[k, :72] = np.log(np.array([y[X[:, j] > 0].mean() if (X[:, j] > 0).any() else 1e-3 for j in range(72)]) + 1e-3)
        for _ in range(3):
            beta[k] = irls_schritt(X, y, beta[k], ridge)
    alt = None
    for _ in range(iters):
        L = np.exp(np.clip(X @ beta.T, -30, 30))
        mu = L @ H + EPS
        R = M / mu
        Y = L * (R @ H.T)
        Hn = H * (L.T @ R)
        Hn = Hn / (Hn.sum(1, keepdims=True) + EPS)
        for k, prof in (fest or {}).items():
            Hn[k] = prof
        H = Hn
        for k in range(K):
            beta[k] = irls_schritt(X, Y[:, k], beta[k], ridge)
        ll = float((M * np.log(mu) - mu).sum())
        if alt is not None and abs(ll - alt) < tol * abs(alt):
            break
        alt = ll
    return beta, H


def loglik(M, X, beta, H):
    mu = np.exp(np.clip(X @ beta.T, -30, 30)) @ H + EPS
    return float((M * np.log(mu) - mu).sum())


def standardfehler(M, X, beta, H):
    """Naeherung: Poisson-Fisher-Information je Gruppe auf den erwarteten Zaehlungen, mal Ueberdispersion (Pearson)."""
    L = np.exp(np.clip(X @ beta.T, -30, 30))
    mu = L @ H + EPS
    phi = float((((M - mu) ** 2) / mu).sum() / max(M.size - beta.size - H.size, 1))
    out = []
    for k in range(len(beta)):
        A = X.T @ (X * L[:, k][:, None]) + 1e-6 * np.eye(X.shape[1])
        out.append(np.sqrt(np.clip(np.diag(np.linalg.inv(A)), 0, None) * phi))
    return np.array(out)


def _haelften(c):
    wo = ((c[:, 10] - c[:, 10].min()) // 7).astype(int)
    return wo % 2 == 0


def kreuzvalidierung(M, X, K, gerade, fest=None):
    ll = 0.0
    for tr in (gerade, ~gerade):
        beta, H = anpassen(M[tr], X[tr], K, fest=fest)
        ll += loglik(M[~tr], X[~tr], beta, H)
    return ll


def modell(M, c, lim, placebo=False):
    """Verhaltensgruppen eines Abschnitts. Gibt (Ergebnis, L [Stunden x K]) zurueck oder (None, None), wenn der Abschnitt zu klein ist."""
    tage = len(np.unique(c[:, 10]))
    gerade = _haelften(c)
    if tage < MIN_TAGE or M.sum() < MIN_FAHRZEUGE or gerade.sum() < 24 * 5 or (~gerade).sum() < 24 * 5:
        return None, None
    X = entwurf(c, M, lim, placebo)
    n = M.sum()
    cv = [kreuzvalidierung(M, X, 1, gerade)]
    K = 1
    while K < KMAX:  # Gruppe fuer Gruppe, solange jede weitere die Vorhersage ungesehener Wochen merklich verbessert
        cv.append(kreuzvalidierung(M, X, K + 1, gerade))
        if (cv[-1] - cv[-2]) / n < GEWINN_SCHWELLE:
            break
        K += 1
    beta, H = anpassen(M, X, K, iters=200)
    se = standardfehler(M, X, beta, H)
    mitte = mitten()
    order = np.argsort([(H[k] * mitte).sum() for k in range(K)])
    beta, H, se = beta[order], H[order], se[order]
    L = np.exp(np.clip(X @ beta.T, -30, 30))
    stab = [None] * K
    if K > 1:
        _, Ha = anpassen(M[gerade], X[gerade], K)
        _, Hb = anpassen(M[~gerade], X[~gerade], K)
        for k in range(K):
            stab[k] = round(min(max(kosinus(H[k], Ha[j]) for j in range(K)), max(kosinus(H[k], Hb[j]) for j in range(K))), 3)
    wd, hr, fer, fei = c[:, 8], c[:, 9], c[:, 11], c[:, 12]
    werk = (wd <= 4) & (fer == 0) & (fei == 0)
    gruppen_ = []
    for k in range(K):
        p = H[k]
        mu = float((p * mitte).sum())
        gang = [float(L[werk & (hr == h), k].mean()) if (werk & (hr == h)).any() else None for h in range(24)]
        g = {"anteil": round(float(L[:, k].sum() / L.sum()), 4), "fahrzeuge": int(round(float(L[:, k].sum()))),
             "modus_kmh": float(mitte[np.argmax(p)]), "mittel_kmh": round(mu, 1), "streuung_kmh": round(float(np.sqrt((p * (mitte - mu) ** 2).sum())), 1),
             "profil": [round(float(x), 5) for x in p], "stabil": stab[k],
             "effekte": {nme: round(float(beta[k, 72 + j]), 4) for j, nme in enumerate(KOV)},
             "se": {nme: round(float(se[k, 72 + j]), 4) for j, nme in enumerate(KOV)},
             "tagesgang": [None if x is None else round(x, 3) for x in gang]}
        gruppen_.append(g)
    haupt = max(gruppen_, key=lambda g: g["anteil"])
    for g in gruppen_:
        g["klasse"] = klasse(g, haupt)
        g["belastbar"] = g is haupt or (g["anteil"] >= MIN_ANTEIL and (g["stabil"] is None or g["stabil"] >= MIN_STABIL))
    return {"K": K, "tage": int(tage), "fahrzeuge": int(n), "cv_gewinn": [round((x - cv[0]) / n, 5) for x in cv], "gruppen": gruppen_}, L


def hauptmodus(M):
    """Klasse des haeufigsten Tempos ab 12 km/h (Hauptgruppe ohne Rauschen)."""
    s = M.sum(0)
    return 6 + int(np.argmax(s[6:]))


def vorlage_profil(v, M):
    """Profil einer Stadt-Vorlage fuer diesen Abschnitt: absolut oder um den Modus der Hauptgruppe verschoben."""
    if v["bezug"] == "absolut":
        p = np.array(v["profil"], dtype=float)
    else:
        rel, mitte_ = v["profil_relativ"], v["mitte"]
        m0 = hauptmodus(M)
        p = np.zeros(NBIN)
        for j in range(NBIN):
            k = j - m0 + mitte_
            if 0 <= k < len(rel):
                p[j] = rel[k]
    s = p.sum()
    return p / s if s > 0 else None


def vorlagen(M, c, lim, liste, eigene=None):
    """Stadt-Vorlagen in einem Abschnitt pruefen: die eigenen Gruppen (frei) plus die Vorlage (feste Form) gegen die eigenen Gruppen allein,
    beides an der Vorhersage ungesehener Wochen. eigene: Ergebnis von modell() oder None (dann eine freie Gruppe als Vergleich).

    liste: Vorlagen aus dem Register [{id, klasse, bezug, profil|profil_relativ, mitte}]; Arten, die der Abschnitt schon als belastbare
    eigene Gruppe hat, werden nicht geprueft."""
    tage = len(np.unique(c[:, 10]))
    gerade = _haelften(c)
    if tage < VORLAGE_MIN_TAGE or M.sum() < VORLAGE_MIN_FAHRZEUGE or gerade.sum() < 48 or (~gerade).sum() < 48:
        return None
    vorhanden = {g["klasse"] for g in eigene["gruppen"] if g["belastbar"]} if eigene else set()
    K = eigene["K"] if eigene else 1
    kandidaten = []
    for v in liste:
        p = None if v["klasse"] in vorhanden or v["klasse"] == "haupt" else vorlage_profil(v, M)
        if p is not None:
            kandidaten.append((v, p))
    if not kandidaten:
        return []
    X = entwurf(c, M, lim)
    n = M.sum()
    # Vorwaertsauswahl: die Vorlage mit dem groessten Gewinn zuerst aufnehmen, die uebrigen dann gegen das erweiterte Modell pruefen.
    # Sonst "gewinnt" jede Vorlage, nur weil sie aufnimmt, was eine andere, fehlende Gruppe erklaeren wuerde (z. B. Rauschen).
    fest, aktuell, erg, aufgenommen = {}, kreuzvalidierung(M, X, K, gerade), {}, []
    while kandidaten:
        bestes = None
        for v, p in kandidaten:
            f = dict(fest)
            f[K + len(fest)] = p
            ll = kreuzvalidierung(M, X, K + len(f), gerade, fest=f)
            erg[v["id"]] = {"id": v["id"], "klasse": v["klasse"], "gewinn": round(float((ll - aktuell) / n), 5), "nachgewiesen": False}
            if bestes is None or ll > bestes[2]:
                bestes = (v, p, ll)
        v, p, ll = bestes
        if (ll - aktuell) / n < GEWINN_SCHWELLE:
            break
        erg[v["id"]]["nachgewiesen"] = True
        aufgenommen.append(v["id"])
        fest[K + len(fest)] = p
        aktuell = ll
        kandidaten = [(w, q) for w, q in kandidaten if w is not v]
    if fest:  # Anteil und Verhalten nur, wo Vorlagen tragen; sonst gilt die Erwartung aus der Stadtebene
        beta, _ = anpassen(M, X, K + len(fest), fest=fest)
        L = np.exp(np.clip(X @ beta.T, -30, 30))
        for i, vid in zip(sorted(fest), aufgenommen):
            erg[vid]["anteil"] = round(float(L[:, i].sum() / L.sum()), 4)
            erg[vid]["effekte_gegen_haupt"] = _gegen_haupt(beta, L, i)
            erg[vid]["nachgewiesen"] = erg[vid]["anteil"] >= MIN_ANTEIL  # wie bei eigenen Gruppen: winzige Gruppen zaehlen nicht
    return [erg[v["id"]] for v in liste if v["id"] in erg]


def _gegen_haupt(beta, L, k):
    """Verhaltensunterschied (log-Faktor je Merkmal) der Gruppe k zur groessten Gruppe."""
    h = int(np.argmax(np.delete(L.sum(0), k))) if L.shape[1] > 1 else 0
    h = h if h < k else h + 1
    return {nme: round(float(beta[k, 72 + j] - beta[h, 72 + j]), 4) for j, nme in enumerate(KOV)}


def vorlagen_laden(pfad=REGISTER):
    """(Vorlagen der Stadtgruppen, Hash des Registers) aus belege/verhaltensgruppen-register.json; ([], '') ohne Register."""
    if not os.path.exists(pfad):
        return [], ""
    with open(pfad, encoding="utf-8") as fh:
        reg = json.load(fh)
    liste = [dict(g["vorlage"], id=g["id"], klasse=g["klasse"]) for g in reg.get("gruppen", [])
             if g.get("vorlage") and g.get("status", "aktiv") == "aktiv"]
    # nur die Vorlagen zaehlen: Aenderungen an Deutung oder Belegen rechnen nichts neu
    return liste, zwischenspeicher.inhalts_hash(json.dumps(liste, sort_keys=True).encode("utf-8")) if liste else ""


def _placebo_kurz(erg):
    if not erg:
        return None
    return {"K": erg["K"], "gruppen": [{k: g[k] for k in ("klasse", "anteil", "stabil", "belastbar", "effekte", "se")}
                                       for g in erg["gruppen"]]}


def auswerten(fahrzeuge, spannen, grenzen, lim, ort, regen, wetter_tage, utc_versatz_h, speicher=None, register=REGISTER):
    """Verhaltensgruppen aller Abschnitte einer Datei. Gibt (YAML-Block 'verhalten', {Abschnittsnummer: Zellendaten}) zurueck.

    Jeder Abschnitt hat eigene Eintraege im Zwischenspeicher: "verhalten" (Modell und Placebo) und "vorlagen" (Stadt-Vorlagen, haengt
    zusaetzlich vom Register ab). Schluessel ist der Inhalt der Stundentabelle des Abschnitts, nicht seine Nummer: aendert sich die Suche nach
    Bruechen anderswo in der Messreihe, bleibt der Eintrag gueltig."""
    if np is None:
        return {"geprueft": False, "grund": "numpy nicht installiert"}, {}
    if not lim:
        return {"geprueft": False, "grund": "kein Tempolimit"}, {}
    stunden, M_all, c_all = stundentabelle(fahrzeuge, spannen, ort, regen, wetter_tage, utc_versatz_h, grenzen)
    code = CODE
    liste, reg_hash = vorlagen_laden(register)
    blk = {"geprueft": True, "stunden_mit_wetter": len(stunden), "abschnitte": []}
    zellen = {}
    for nr in range(1, len(grenzen) + 2):
        m = c_all[:, 13] == nr - 1
        M, c = M_all[m], c_all[m]
        st = [s for s, k in zip(stunden, m) if k]
        e = {"nr": nr, "stunden": int(m.sum()), "tage": int(len(np.unique(c[:, 10]))), "fahrzeuge": int(M.sum())}
        if not m.any():
            blk["abschnitte"].append(dict(e, geprueft=False, grund="keine Stunden mit Wetterdaten"))
            continue
        inhalt = M.astype(np.float64).tobytes() + np.ascontiguousarray(c[:, :13]).tobytes()
        schl = zwischenspeicher.inhalts_hash(inhalt, lim, code) if speicher else None
        gesp = speicher.holen("verhalten", schl) if speicher else None
        if gesp is None:
            erg, L = modell(M, c, lim)
            plac, _ = modell(M, c, lim, placebo=True) if erg else (None, None)
            gesp = {"erg": erg, "placebo": _placebo_kurz(plac), "raten": zellen_raten(L, st) if erg else None}
            if speicher:
                speicher.speichern("verhalten", schl, gesp)
        if liste:
            schl_v = zwischenspeicher.inhalts_hash(inhalt, lim, code, reg_hash) if speicher else None
            vl = speicher.holen("vorlagen", schl_v) if speicher else None
            if vl is None:
                vl = {"vorlagen": vorlagen(M, c, lim, liste, gesp["erg"])}
                if speicher:
                    speicher.speichern("vorlagen", schl_v, vl)
            if vl["vorlagen"] is not None:
                e["vorlagen"] = vl["vorlagen"]
        if gesp["erg"] is None:
            e.update(geprueft=False, grund=f"weniger als {MIN_TAGE} Tage oder {MIN_FAHRZEUGE} Fahrzeuge in Stunden mit Wetterdaten")
        else:
            e.update(geprueft=True, **{k: x for k, x in gesp["erg"].items() if k not in ("tage", "fahrzeuge")})
            e["placebo"] = gesp["placebo"]
            zellen[nr] = {"profile": [g["profil"] for g in gesp["erg"]["gruppen"]],
                          "klassen": [g["klasse"] for g in gesp["erg"]["gruppen"]], "raten": gesp["raten"]}
        blk["abschnitte"].append(e)
    return blk, zellen


def zellen_raten(L, stunden):
    """Erwartete Fahrzeuge je Gruppe in den Zellen der Detailseite ('Tag|Stunde', Tag nach gruppen.tagschluessel)."""
    z = {}
    for (tag, h), werte in zip(stunden, L):
        k = f"{gruppen.tagschluessel(dt.datetime(tag.year, tag.month, tag.day, h))}|{h}"
        alt = z.get(k)
        z[k] = [a + float(b) for a, b in zip(alt, werte)] if alt else [float(b) for b in werte]
    return {k: [round(x, 2) for x in v] for k, v in sorted(z.items())}
