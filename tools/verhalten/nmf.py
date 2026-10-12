# SPDX-License-Identifier: MIT
"""Je Abschnitt: Poisson-NMF der Stundenmatrix (Stunden x 2-km/h-Klassen), Zahl der Komponenten per Kreuzvalidierung mit
Ausduennung (jede Zaehlung zufaellig halbiert: zwei unabhaengige Poisson-Haelften), Stabilitaet zwischen geraden/ungeraden Wochen,
und Verhaltenssignatur jeder Komponente (Tagesgang, Wochenende, Licht, Regen, Temperatur, Wind, Schnee, Ferien, Feiertag).
Aufruf: python3 -I tools/verhalten/nmf.py [--jobs N]  -> v2_komp.json"""
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

EPS = 1e-9
KMAX = 6
MIN_TAGE = 14
MIN_FAHRZEUGE = 5000
KOV = ["daemmerung", "tiefe_sonne", "nacht", "regen_0_1", "regen_0_5", "regen_2", "nach_regen", "temp_10c", "frost", "wind_10ms",
       "schnee", "ferien", "feiertag"]


def nmf(M, K, iters=300, seed=0, H=None, nur_w=False):
    rng = np.random.RandomState(seed)
    n, B = M.shape
    if H is None:
        H = rng.rand(K, B) + 0.1
        H /= H.sum(1, keepdims=True)
    else:
        H = H.copy()
    W = (M.sum(1, keepdims=True) / K + 0.1) * (rng.rand(n, K) + 0.5)
    for _ in range(iters):
        R = M / (W @ H + EPS)
        W *= (R @ H.T) / (H.sum(1)[None, :] + EPS)
        if not nur_w:
            R = M / (W @ H + EPS)
            H *= (W.T @ R) / (W.sum(0)[:, None] + EPS)
            s = H.sum(1, keepdims=True) + EPS
            H /= s
            W *= s.T
    return W, H


def loglik(M, mu):
    mu = mu + EPS
    return float((M * np.log(mu) - mu).sum())


def beste(M, K, restarts=2, iters=300):
    best = None
    for s in range(restarts):
        W, H = nmf(M, K, iters, seed=s)
        ll = loglik(M, W @ H)
        if best is None or ll > best[0]:
            best = (ll, W, H)
    return best


def cv_ll(M, K, rng):
    """Ausduennung: M1 ~ Bin(M, 1/2), M2 = M - M1; anpassen auf M1, bewerten auf M2 (und umgekehrt)."""
    M1 = rng.binomial(M.astype(np.int32), 0.5).astype(float)
    M2 = M - M1
    out = 0.0
    for a, b in ((M1, M2), (M2, M1)):
        _, W, H = beste(a, K)
        out += loglik(b, W @ H)
    return out


def kosinus(a, b):
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + EPS))


def zuordnen(H1, H2):
    """Gierige Zuordnung der Profile zweier Anpassungen nach Kosinus."""
    K = len(H1)
    frei = list(range(K))
    paare = []
    for i in np.argsort([-H1[k].max() for k in range(K)]):
        j = max(frei, key=lambda x: kosinus(H1[i], H2[x]))
        frei.remove(j)
        paare.append((i, j, kosinus(H1[i], H2[j])))
    return paare


def poisson(X, y, iters=40):
    b = np.zeros(X.shape[1])
    mu = np.full(len(y), max(y.mean(), 1e-3))
    eta = np.log(mu)
    for _ in range(iters):
        z = eta + (y - mu) / mu
        A = X.T @ (X * mu[:, None]) + 1e-4 * np.eye(X.shape[1])
        bn = np.linalg.solve(A, X.T @ (mu * z))
        eta = np.clip(X @ bn, -30, 30)
        mu = np.exp(eta)
        if np.max(np.abs(bn - b)) < 1e-6:
            b = bn
            break
        b = bn
    return b


def entwurf(c):
    r0, rp, rn, tmk, tnk, fx, shk, ele, wd, hr, tag, fer, fei = [c[:, i] for i in range(13)]
    r = r0 + 0.5 * (rp + rn)
    typ = np.where(fei > 0, 2, np.where(wd <= 4, 0, np.where(wd == 5, 1, 2)))
    zelle = (typ * 24 + hr).astype(int)
    cols = [(zelle == k).astype(float) for k in range(72) if (zelle == k).any()]
    nfix = len(cols)
    kov = [(ele > -6) & (ele <= 0), (ele > 0) & (ele <= 15), ele <= -6,
           (r >= 0.1) & (r < 0.5), (r >= 0.5) & (r < 2), r >= 2, (r < 0.1) & (rp >= 0.1),
           (tmk - 10) / 10.0, tnk < 0, fx / 10.0 - 1, shk > 0, fer > 0, fei > 0]
    cols += [np.asarray(x, dtype=float) for x in kov]
    w = ((tag - tag.min()) // 7).astype(int)
    for k in np.unique(w)[1:]:
        cols.append((w == k).astype(float))
    X = np.stack(cols, axis=1)
    keep = X.std(0) > 0
    keep[:nfix] = True
    return X, nfix, keep


def signatur(Wk, c, X, nfix, keep):
    """Verhaltenssignatur einer Komponente: Effekte (log-Rate) der Kovariaten, Tagesgang (Werktag), Wochenende/Werktag, Nachtanteil."""
    b = np.full(len(KOV), np.nan)
    Xk = X[:, keep]
    bk = poisson(Xk, Wk)
    idx = np.where(keep)[0]
    for j, col in enumerate(idx):
        if nfix <= col < nfix + len(KOV):
            b[col - nfix] = bk[j]
    wd, hr, fer, fei = c[:, 8], c[:, 9], c[:, 11], c[:, 12]
    werk = (wd <= 4) & (fer == 0) & (fei == 0)
    gang = np.array([Wk[werk & (hr == h)].mean() if (werk & (hr == h)).any() else np.nan for h in range(24)])
    gang = gang / np.nanmean(gang)
    tagw = Wk[werk].mean() * 24
    sa = Wk[(wd == 5) & (fei == 0)].mean() * 24 if ((wd == 5) & (fei == 0)).any() else np.nan
    so = Wk[(wd == 6) | (fei > 0)].mean() * 24 if ((wd == 6) | (fei > 0)).any() else np.nan
    nacht = Wk[(hr >= 22) | (hr < 6)].sum() / Wk.sum()
    return b, gang, sa / tagw, so / tagw, nacht


def segment(pfad):
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
        rng = np.random.RandomState(7)
        lls = [cv_ll(M, K, rng) for K in range(1, KMAX + 1)]
        # kleinste Zahl, deren Kreuzvalidierungs-Wert innerhalb 0,1 % (bezogen auf die Fahrzeugzahl) des besten liegt
        best = max(lls)
        K = next(k + 1 for k, v in enumerate(lls) if best - v <= 0.001 * M.sum())
        _, W, H = beste(M, K, restarts=3, iters=500)
        mitte = np.arange(M.shape[1]) * 2 + 1.0
        mitte[-1] = 92
        order = np.argsort([(H[k] * mitte).sum() for k in range(K)])
        W, H = W[:, order], H[order]
        # Stabilitaet: gerade/ungerade Wochen
        wo = ((c[:, 10] - c[:, 10].min()) // 7).astype(int)
        stab = [np.nan] * K
        if K > 1 and len(np.unique(wo)) >= 4:
            _, _, Ha = beste(M[wo % 2 == 0], K)
            _, _, Hb = beste(M[wo % 2 == 1], K)
            for k in range(K):
                stab[k] = min(max(kosinus(H[k], Ha[j]) for j in range(K)), max(kosinus(H[k], Hb[j]) for j in range(K)))
        X, nfix, keep = entwurf(c)
        for k in range(K):
            p = H[k]
            mu = (p * mitte).sum()
            sd = np.sqrt((p * (mitte - mu) ** 2).sum())
            modus = mitte[np.argmax(p)]
            b, gang, sa, so, nacht = signatur(W[:, k], c, X, nfix, keep)
            out.append({"datei": os.path.basename(pfad)[:-4], "rel": str(z["rel"]), "abschnitt": int(s), "tage": int(tage), "limit": lim,
                        "ort": [float(x) for x in z["ort"]], "K": K, "k": k, "anteil": float(W[:, k].sum() / W.sum()),
                        "fahrzeuge": float(W[:, k].sum()), "mittel": float(mu), "sd": float(sd), "modus": float(modus),
                        "profil": [float(x) for x in p], "stabil": None if np.isnan(stab[k]) else float(stab[k]),
                        "effekte": {n: (None if np.isnan(v) else float(v)) for n, v in zip(KOV, b)},
                        "tagesgang": [None if np.isnan(x) else float(x) for x in gang], "samstag": float(sa), "sonntag": float(so),
                        "nacht": float(nacht), "cv": [float(x - lls[0]) for x in lls], "von_tag": float(c[:, 10].min()), "bis_tag": float(c[:, 10].max())})
    return out


def main():
    jobs = int(sys.argv[sys.argv.index("--jobs") + 1]) if "--jobs" in sys.argv else 6
    dateien = sorted(glob.glob(os.path.join(SC, "stunden", "*.npz")))
    alle = []
    with multiprocessing.Pool(jobs) as pool:
        for erg in pool.imap_unordered(segment, dateien):
            alle += erg
            if erg:
                print(erg[0]["datei"].encode("ascii", "replace").decode()[:50], "Abschnitte", len({e["abschnitt"] for e in erg}),
                      "K", sorted({(e["abschnitt"], e["K"]) for e in erg}), flush=True)
    json.dump(alle, open(os.path.join(SC, "nmf_frei.json"), "w", encoding="utf-8"))
    print(len(alle), "Komponenten")


if __name__ == "__main__":
    main()
