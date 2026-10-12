# SPDX-License-Identifier: MIT
"""Verhaltensgruppen-Modell je Abschnitt:  lambda[h, v] = sum_k exp(X[h] . beta_k) * H[k, v]
K Gruppen mit festem Geschwindigkeitsprofil H_k, deren Menge je Stunde von Tageszeit/Tagtyp, Licht, Wetter, Ferien und einem Trend
abhaengt. Pruefung: Vorhersage ungesehener Wochen (Anpassung auf geraden, Bewertung auf ungeraden Wochen und umgekehrt).
K=1 heisst: eine Verteilung, nur die Menge aendert sich. K>1 besser vorhergesagt = Gruppen mit eigenem Verhalten.
Aufruf: python3 -I tools/verhalten/modell.py [--jobs N] [--nur MUSTER]  -> v3_modell.json"""
import glob
import json
import multiprocessing
import os
import sys


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I nimmt das Skriptverzeichnis nicht auf
import gemeinsam  # noqa: E402  (Pfade, numpy)
SC = gemeinsam.DATEN
W = gemeinsam.WURZEL
import numpy as np  # noqa: E402
from nmf import nmf, kosinus  # noqa: E402

EPS = 1e-9
KMAX = 5
MIN_TAGE = 14
MIN_FAHRZEUGE = 5000
KOV = ["daemmerung", "tiefe_sonne", "nacht", "regen_0_1", "regen_0_5", "regen_2", "nach_regen", "temp_10c", "frost", "wind_10ms",
       "schnee", "ferien", "feiertag"]


PLACEBO = os.environ.get("VERHALTEN_PLACEBO") == "1"
ORDNER = "modell_placebo" if PLACEBO else "modell"


def entwurf(c):
    r0, rp, rn, tmk, tnk, fx, shk, ele, wd, hr, tag, fer, fei = [c[:, i] for i in range(13)]
    if PLACEBO:  # Wetter, Licht und Ferien gegen die Stunden verschieben: echte Zusammenhaenge brechen, Selbstaehnlichkeit bleibt
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
    t = (tag - tag.mean()) / 30.0
    cols += [t, t * t]  # langsamer Trend (Jahreszeit, Bauzustand)
    return np.stack(cols, axis=1)


def irls_schritt(X, y, b, ridge):
    eta = np.clip(X @ b, -30, 30)
    mu = np.exp(eta)
    z = eta + (y - mu) / np.maximum(mu, 1e-6)
    A = X.T @ (X * mu[:, None]) + ridge
    return np.linalg.solve(A, X.T @ (mu * z))


def anpassen(M, X, K, iters=120, seed=0):
    """Gibt (beta [K, p], H [K, B]) zurueck."""
    n, B = M.shape
    p = X.shape[1]
    ridge = np.diag(np.r_[np.full(72, 1e-3), np.full(p - 72, 1e-2)])
    W0, H = nmf(M, K, 200, seed=seed)
    beta = np.zeros((K, p))
    for k in range(K):
        y = W0[:, k]
        beta[k, :72] = np.log(np.array([y[X[:, j] > 0].mean() if (X[:, j] > 0).any() else 1e-3 for j in range(72)]) + 1e-3)
        for _ in range(3):
            beta[k] = irls_schritt(X, y, beta[k], ridge)
    for _ in range(iters):
        L = np.exp(np.clip(X @ beta.T, -30, 30))  # n x K
        mu = L @ H + EPS
        R = M / mu
        # erwartete Zaehlungen je Gruppe und Stunde / je Gruppe und Klasse
        Y = L * (R @ H.T)  # n x K
        Hn = H * (L.T @ R)  # K x B
        H = Hn / (Hn.sum(1, keepdims=True) + EPS)
        for k in range(K):
            beta[k] = irls_schritt(X, Y[:, k], beta[k], ridge)
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
        out.append(np.sqrt(np.diag(np.linalg.inv(A)) * phi))
    return np.array(out), phi


def segment(pfad):
    ziel = os.path.join(SC, ORDNER, os.path.basename(pfad)[:-4] + ".json")
    if os.path.exists(ziel):
        return json.load(open(ziel, encoding="utf-8"))
    out = _segment(pfad)
    json.dump(out, open(ziel, "w", encoding="utf-8"))
    with open(os.path.join(SC, ORDNER + "_fortschritt.txt"), "a", encoding="utf-8") as fh:
        fh.write(os.path.basename(pfad) + "\n")
    return out


def _segment(pfad):
    z = np.load(pfad)
    M_all, c_all, lim = z["M"].astype(float), z["ctx"], float(z["lim"])
    ok = ~np.isnan(c_all[:, :8]).any(1)
    out = []
    for s in np.unique(c_all[:, 13][ok]).astype(int):
        m = ok & (c_all[:, 13] == s)
        M, c = M_all[m], c_all[m]
        tage = len(np.unique(c[:, 10]))
        if tage < MIN_TAGE or M.sum() < MIN_FAHRZEUGE:
            continue
        X = entwurf(c)
        wo = ((c[:, 10] - c[:, 10].min()) // 7).astype(int)
        gerade = wo % 2 == 0
        if gerade.sum() < 24 * 5 or (~gerade).sum() < 24 * 5:
            continue
        cv = []
        for K in range(1, KMAX + 1):
            ll = 0.0
            for tr in (gerade, ~gerade):
                beta, H = anpassen(M[tr], X[tr], K)
                ll += loglik(M[~tr], X[~tr], beta, H)
            cv.append(ll)
        n = M.sum()
        gewinn = [(v - cv[0]) / n for v in cv]  # nats je Fahrzeug gegen K=1
        # kleinste Zahl, die bis auf 0,002 nats je Fahrzeug an die beste Vorhersage herankommt
        K = 1 + next(i for i, g in enumerate(gewinn) if g >= max(gewinn) - 0.002)
        beta, H = anpassen(M, X, K, iters=200)
        se, phi = standardfehler(M, X, beta, H)
        mitte = np.arange(M.shape[1]) * 2 + 1.0
        mitte[-1] = 92
        order = np.argsort([(H[k] * mitte).sum() for k in range(K)])
        beta, H, se = beta[order], H[order], se[order]
        L = np.exp(np.clip(X @ beta.T, -30, 30))
        # Stabilitaet der Profile: getrennte Anpassung auf geraden und ungeraden Wochen
        stab = [None] * K
        if K > 1:
            _, Ha = anpassen(M[gerade], X[gerade], K)
            _, Hb = anpassen(M[~gerade], X[~gerade], K)
            for k in range(K):
                stab[k] = float(min(max(kosinus(H[k], Ha[j]) for j in range(K)), max(kosinus(H[k], Hb[j]) for j in range(K))))
        wd, hr, fer, fei = c[:, 8], c[:, 9], c[:, 11], c[:, 12]
        werk = (wd <= 4) & (fer == 0) & (fei == 0)
        for k in range(K):
            p = H[k]
            mu = float((p * mitte).sum())
            gang = [float(L[werk & (hr == h), k].mean()) if (werk & (hr == h)).any() else None for h in range(24)]
            out.append({"datei": os.path.basename(pfad)[:-4], "rel": str(z["rel"]), "abschnitt": int(s), "tage": int(tage), "limit": lim,
                        "ort": [float(x) for x in z["ort"]], "K": K, "k": k, "anteil": float(L[:, k].sum() / L.sum()), "fahrzeuge": float(L[:, k].sum()),
                        "mittel": mu, "sd": float(np.sqrt((p * (mitte - mu) ** 2).sum())), "modus": float(mitte[np.argmax(p)]),
                        "profil": [float(x) for x in p], "stabil": stab[k], "phi": phi,
                        "effekte": {nme: float(beta[k, 72 + j]) for j, nme in enumerate(KOV)},
                        "se": {nme: float(se[k, 72 + j]) for j, nme in enumerate(KOV)},
                        "tagesgang": gang, "cv_gewinn": [float(g) for g in gewinn], "von_tag": float(c[:, 10].min()), "bis_tag": float(c[:, 10].max())})
    return out


def main():
    jobs = int(sys.argv[sys.argv.index("--jobs") + 1]) if "--jobs" in sys.argv else 6
    muster = sys.argv[sys.argv.index("--nur") + 1] if "--nur" in sys.argv else ""
    os.makedirs(os.path.join(SC, ORDNER), exist_ok=True)
    dateien = sorted(f for f in glob.glob(os.path.join(SC, "stunden", "*.npz")) if muster in f)
    alle = []
    with multiprocessing.Pool(jobs) as pool:
        for erg in pool.imap_unordered(segment, dateien):
            alle += erg
            for a in sorted({e["abschnitt"] for e in erg}):
                ee = [e for e in erg if e["abschnitt"] == a]
                print(ee[0]["datei"].encode("ascii", "replace").decode()[:46], "A%d" % a, "K=%d" % ee[0]["K"],
                      "Gewinn", " ".join("%.4f" % g for g in ee[0]["cv_gewinn"][1:]), "|",
                      " ; ".join("m%.0f %.0f%%" % (e["modus"], 100 * e["anteil"]) for e in ee), flush=True)
    json.dump(alle, open(os.path.join(SC, ORDNER + ("_" + muster if muster else "") + ".json"), "w", encoding="utf-8"))
    print(len(alle), "Gruppen")


if __name__ == "__main__":
    main()
