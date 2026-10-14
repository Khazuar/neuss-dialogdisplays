# SPDX-License-Identifier: MIT
"""Tests fuer verhalten.py (Verhaltensgruppen je Abschnitt) und stadtgruppen.py (Stadt- und Standortebene, Register)."""
import datetime as dt
import json
import os
import tempfile
import unittest

import stadtgruppen
import verhalten
import zwischenspeicher

np = verhalten.np


def kontext(tage, regen_alle=None, seed=1):
    """Stundenkontext wie verhalten.stundentabelle: r0, r-1, r+1, tmk, tnk, fx, shk, Sonne, Wochentag, Stunde, Tag, Ferien, Feiertag, Abschnitt."""
    rng = np.random.RandomState(seed)
    zeilen = []
    for d in range(tage):
        tag = dt.date(2024, 3, 4) + dt.timedelta(days=d)
        regentag = rng.rand() < 0.35
        for h in range(24):
            r = float(rng.choice([0.0, 0.3, 1.0, 3.0], p=[0.4, 0.3, 0.2, 0.1])) if regentag else 0.0
            zeilen.append([r, 0.0, 0.0, 10.0, 4.0, 10.0, 0.0, 40 * np.sin((h - 6) / 24 * 2 * np.pi), tag.weekday(), h,
                           (tag - verhalten.EPOCHE.date()).days, 0.0, 0.0, 0.0])
    c = np.array(zeilen)
    c[1:, 1] = c[:-1, 0]  # Regen der Stunde davor und danach
    c[:-1, 2] = c[1:, 0]
    return c


def zaehlungen(c, gruppen_, seed=2):
    """gruppen_: [(Modus km/h, Grundmenge je Stunde, Regenfaktor)]; die Menge folgt einem Tagesgang, Regen ab 0,5 mm wirkt als Faktor."""
    rng = np.random.RandomState(seed)
    mitte = verhalten.mitten()
    M = np.zeros((len(c), verhalten.NBIN))
    for modus, menge, regen in gruppen_:
        prof = np.exp(-0.5 * ((mitte - modus) / 3.0) ** 2)
        prof /= prof.sum()
        gang = 0.2 + np.clip(np.sin((c[:, 9] - 5) / 17 * np.pi), 0, None)
        r = c[:, 0] + 0.5 * (c[:, 1] + c[:, 2])
        lam = menge * gang * np.where(r >= 0.5, regen, 1.0)
        M += rng.poisson(lam[:, None] * prof[None, :])
    return M


@unittest.skipIf(np is None, "numpy nicht installiert")
class Modell(unittest.TestCase):
    def test_zwei_gruppen_mit_eigenem_regenverhalten(self):
        c = kontext(42)
        M = zaehlungen(c, [(30, 60, 1.0), (7, 4, 8.0)])
        erg, L = verhalten.modell(M, c, 30)
        self.assertGreaterEqual(erg["K"], 2)
        rausch = [g for g in erg["gruppen"] if g["klasse"] == "rauschen"]
        self.assertEqual(len(rausch), 1)
        haupt = next(g for g in erg["gruppen"] if g["klasse"] == "haupt")
        self.assertAlmostEqual(haupt["modus_kmh"], 31, delta=2)
        # Regen ab 2 mm vervielfacht die langsame Gruppe, nicht die Hauptgruppe
        self.assertGreater(rausch[0]["effekte"]["regen_2"] - haupt["effekte"]["regen_2"], 1.0)
        self.assertEqual(L.shape, (len(c), erg["K"]))

    def test_eine_gruppe_reicht(self):
        c = kontext(42)
        M = zaehlungen(c, [(30, 60, 1.0)])
        erg, _ = verhalten.modell(M, c, 30)
        self.assertEqual(erg["K"], 1)
        self.assertEqual(erg["gruppen"][0]["klasse"], "haupt")

    def test_zu_kurz(self):
        c = kontext(10)
        erg, L = verhalten.modell(zaehlungen(c, [(30, 60, 1.0)]), c, 30)
        self.assertIsNone(erg)
        self.assertIsNone(L)

    def test_vorlage_wird_lokal_nachgewiesen(self):
        c = kontext(21)
        M = zaehlungen(c, [(30, 30, 1.0), (7, 3, 8.0)])
        prof = np.exp(-0.5 * ((verhalten.mitten() - 7) / 3.0) ** 2)
        vl = [{"id": "S-R1", "klasse": "rauschen", "bezug": "absolut", "profil": list(prof / prof.sum())},
              {"id": "S-F1", "klasse": "schnell", "bezug": "relativ", "mitte": verhalten.NBIN - 1,
               "profil_relativ": [0.0] * (verhalten.NBIN + 4) + [1.0] + [0.0] * (verhalten.NBIN - 6)}]
        erg = {v["id"]: v for v in verhalten.vorlagen(M, c, 30, vl)}
        self.assertTrue(erg["S-R1"]["nachgewiesen"])
        self.assertGreater(erg["S-R1"]["anteil"], 0.02)
        self.assertFalse(erg["S-F1"]["nachgewiesen"])

    def test_relative_vorlage_folgt_der_hauptgruppe(self):
        M = np.zeros((1, verhalten.NBIN))
        M[0, 20] = 100  # Hauptgruppe bei 40-42 km/h
        rel = [0.0] * (2 * verhalten.NBIN - 1)
        rel[verhalten.NBIN - 1 + 3] = 1.0  # drei Klassen (6 km/h) schneller
        p = verhalten.vorlage_profil({"bezug": "relativ", "profil_relativ": rel, "mitte": verhalten.NBIN - 1}, M)
        self.assertEqual(int(np.argmax(p)), 23)

    def test_zellen_raten(self):
        stunden = [(dt.date(2024, 3, 4), 7), (dt.date(2024, 3, 11), 7), (dt.date(2024, 3, 10), 7)]  # Mo, Mo, So
        z = verhalten.zellen_raten(np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]), stunden)
        self.assertEqual(z, {"0|7": [4.0, 6.0], "6|7": [5.0, 6.0]})


@unittest.skipIf(np is None, "numpy nicht installiert")
class Ablauf(unittest.TestCase):
    def fahrzeuge(self, tage):
        c = kontext(tage)
        M = zaehlungen(c, [(30, 40, 1.0), (7, 3, 8.0)])
        start = dt.datetime(2024, 3, 4)
        veh = []
        for i in range(len(c)):
            t = start + dt.timedelta(hours=i)
            for b in range(verhalten.NBIN):
                veh += [(t + dt.timedelta(seconds=7 * j), 2 * b + 1) for j in range(int(M[i, b]))]
        return veh, [(start, start + dt.timedelta(days=tage))], c

    def test_zwischenspeicher_trifft(self):
        veh, spannen, c = self.fahrzeuge(28)
        tab = {(dt.date(2024, 3, 4) + dt.timedelta(days=int(i // 24)), int(i % 24)): c[i] for i in range(len(c))}

        def regen(tag, h):
            x = tab.get((tag, h))
            return None if x is None else float(x[0])
        wetter = {(dt.date(2024, 3, 4) + dt.timedelta(days=d)).isoformat(): {"tmk": 10.0, "tnk": 4.0, "fx": 10.0, "shk": 0.0} for d in range(30)}
        with tempfile.TemporaryDirectory() as tmp:
            sp = zwischenspeicher.Zwischenspeicher(tmp)
            blk, zellen = verhalten.auswerten(veh, spannen, [], 30, (51.2, 6.7), regen, wetter, lambda t: 1, sp, register=os.path.join(tmp, "x"))
            self.assertTrue(blk["abschnitte"][0]["geprueft"])
            self.assertIn(1, zellen)
            self.assertEqual(len(zellen[1]["profile"]), blk["abschnitte"][0]["K"])
            sp2 = zwischenspeicher.Zwischenspeicher(tmp)
            alt = verhalten.modell
            verhalten.modell = lambda *a, **k: self.fail("Zwischenspeicher nicht benutzt")
            try:
                blk2, _ = verhalten.auswerten(veh, spannen, [], 30, (51.2, 6.7), regen, wetter, lambda t: 1, sp2, register=os.path.join(tmp, "x"))
            finally:
                verhalten.modell = alt
            self.assertEqual(json.dumps(blk2, sort_keys=True), json.dumps(json.loads(json.dumps(blk)), sort_keys=True))
            self.assertIn("verhalten", {e for e, _ in sp2.benutzt})


def gruppe(klasse, modus, anteil, effekte, se=0.1, profil=None):
    prof = profil or [0.0] * stadtgruppen.NBIN
    if profil is None:
        prof[int(modus) // 2] = 1.0
    return {"klasse": klasse, "modus_kmh": modus, "mittel_kmh": modus, "streuung_kmh": 3.0, "anteil": anteil, "fahrzeuge": 1000, "profil": prof,
            "stabil": 0.99, "belastbar": True, "tagesgang": [1.0] * 24, "effekte": effekte, "se": {c: se for c in effekte}}


def effekte(**kw):
    e = {c: 0.0 for c in stadtgruppen.MERKMALE}
    e.update(kw)
    return e


def auswertung(n_standorte=4, placebo_k=1):
    rows = []
    for i in range(n_standorte):
        h = gruppe("haupt", 31, 0.9, effekte())
        r = gruppe("rauschen", 7, 0.1, effekte(regen_2=3.0 + 0.1 * i, regen_0_5=2.0, dichte_log=-1.0, nacht=0.1 * i, ferien=-0.05 * i))
        a = {"nr": 1, "geprueft": True, "K": 2, "tage": 30, "fahrzeuge": 10000, "cv_gewinn": [0, 0.01], "gruppen": [r, h],
             "placebo": {"K": placebo_k, "gruppen": [{"klasse": "haupt", "anteil": 1.0, "stabil": None, "belastbar": True, "effekte": effekte(),
                                                      "se": {c: 0.1 for c in stadtgruppen.MERKMALE}}]},
             "vorlagen": [{"id": "S-F1", "klasse": "schnell", "gewinn": 0.003 if i == 0 else 0.0, "nachgewiesen": i == 0,
                           **({"anteil": 0.05} if i == 0 else {})}]}
        rows.append({"standort": f"Ort {i}", "datei": "a.dsd", "verhalten": {"geprueft": True, "abschnitte": [a]}})
    # zweite Messung am ersten Ort: dieselbe sehr langsame Gruppe -> MS-Gruppe
    h = gruppe("haupt", 31, 0.9, effekte())
    r = gruppe("rauschen", 7, 0.08, effekte(regen_2=2.8, regen_0_5=1.9, dichte_log=-0.9, nacht=0.05, ferien=0.02))
    rows.append({"standort": "Ort 0", "datei": "b.dsd", "verhalten": {"geprueft": True, "abschnitte": [
        {"nr": 1, "geprueft": True, "K": 2, "tage": 30, "fahrzeuge": 10000, "cv_gewinn": [0, 0.01], "gruppen": [r, h], "placebo": None}]}})
    return {"standorte": rows}


class Stadtebene(unittest.TestCase):
    REG = {"naechste_nummer": {"R": 2, "L": 1, "M": 1, "F": 2}, "gruppen": [
        {"id": "S-R1", "klasse": "rauschen", "status": "aktiv", "deutung": "Regenphantome", "stufe": "tragfähig"},
        {"id": "S-F1", "klasse": "schnell", "status": "aktiv", "deutung": "Freie Fahrt", "stufe": "gestützt"}]}

    def test_namen_ebenen_und_beziehungen(self):
        out = stadtgruppen.ausgabe(auswertung(), {}, self.REG)
        s = {x["klasse"]: x for x in out["stadt"]}
        self.assertEqual(s["rauschen"]["id"], "S-R1")
        self.assertEqual(s["rauschen"]["anzeige"], "Regenphantome (S-R1)")
        self.assertTrue(s["rauschen"]["gefunden"])
        self.assertTrue(s["rauschen"]["effekte"]["regen_2"]["gesichert"])
        self.assertEqual(stadtgruppen.anzeige_s({"id": "S-F1", "deutung": "Freie Fahrt", "stufe": "gestützt"}), "S-F1 (gestützt: Freie Fahrt)")
        a = out["abschnitte"]["Ort 0/a.dsd"][0]
        self.assertEqual([g["name"] for g in a["gruppen"]], ["A1·1", "A1·2"])
        g = a["gruppen"][0]
        self.assertEqual(g["stadt"], "S-R1")
        self.assertTrue(g["ms"].startswith("MS-") and g["ms"].endswith("-R1"))
        self.assertGreater(g["korrelation_stadt"], 0.5)
        ms = out["standorte"][g["ms"][3:-3]]
        self.assertEqual(len(ms[0]["mitglieder"]), 2)
        self.assertEqual(out["uebersicht"]["mit_mehreren_gruppen"], 5)

    def test_unbekannte_art_ohne_register(self):
        out = stadtgruppen.ausgabe(auswertung(), {}, {"naechste_nummer": {}, "gruppen": []})
        s = {x["klasse"]: x for x in out["stadt"]}
        self.assertEqual(s["rauschen"]["id"], "S-R?")
        self.assertFalse(s["rauschen"]["im_register"])

    def test_register_vergibt_neue_ids_ohne_wiederverwendung(self):
        reg = json.loads(json.dumps(self.REG))
        reg["gruppen"][0]["status"] = "nicht mehr gefunden"  # S-R1 ist stillgelegt: die Art bekommt S-R2, nicht wieder S-R1
        out = stadtgruppen.ausgabe(auswertung(), {}, reg)
        with tempfile.TemporaryDirectory() as tmp:
            pfad = os.path.join(tmp, "reg.json")
            stadtgruppen.register_schreiben(pfad, reg, out["stadt"])
            with open(pfad, encoding="utf-8") as fh:
                neu = json.load(fh)
        ids = [g["id"] for g in neu["gruppen"]]
        self.assertEqual(ids, ["S-R1", "S-F1", "S-R2"])
        self.assertEqual(neu["naechste_nummer"]["R"], 3)
        self.assertEqual(neu["gruppen"][2]["vorlage"]["bezug"], "absolut")

    def test_stadtgruppen_im_abschnitt(self):
        reg = json.loads(json.dumps(self.REG))
        rows = auswertung()
        for r in rows["standorte"][:4]:  # schnelle Gruppen an vier Standorten machen S-F1 stadtweit
            a = r["verhalten"]["abschnitte"][0]
            a["gruppen"].append(gruppe("schnell", 41, 0.1, effekte(nacht=1.0, schnee=-0.5, daemmerung=-0.3)))
            a["vorlagen"] = []
        rows["standorte"].append({"standort": "Ort 9", "datei": "c.dsd", "verhalten": {"geprueft": True, "abschnitte": [
            {"nr": 1, "geprueft": False, "grund": "zu kurz", "tage": 9, "fahrzeuge": 3000,
             "vorlagen": [{"id": "S-R1", "klasse": "rauschen", "gewinn": 0.01, "nachgewiesen": True, "anteil": 0.04}]}]}})
        out = stadtgruppen.ausgabe(rows, {}, reg)
        stand = {v["stadt"]: v for v in out["abschnitte"]["Ort 9/c.dsd"][0]["stadtgruppen"]}
        self.assertEqual(stand["S-R1"]["stand"], "nachgewiesen")
        self.assertEqual(stand["S-F1"]["stand"], "erwartet")
        self.assertIsNotNone(stand["S-F1"]["erwartet_anteil"])


if __name__ == "__main__":
    unittest.main()
