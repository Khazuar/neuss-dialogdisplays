# SPDX-License-Identifier: MIT
"""Tests fuer einsaetze.py (Brueche zuordnen, Einsaetze bilden) an synthetischen Messreihen.  Aufruf: python3 -m unittest -v"""
import collections
import datetime as dt
import math
import random
import unittest

import einsaetze as E

BASIS = dt.date(2023, 8, 21)  # Montag, weit weg von Ferienanfang und -ende


def tag(i):
    return BASIS + dt.timedelta(days=i)


def standort(mittel, spitze, menge=15.0, sd=6.0):
    """Verkehr eines Standorts: mittleres Tempo, Stunde der Spitze, Fahrzeuge je Stunde im Mittel."""
    return {"mittel": mittel, "spitze": spitze, "menge": menge, "sd": sd}


def zeilen_fuer(tage, profil, rnd):
    """Aggregat-Zeilen (Datum, Stunde, voll, Regenklasse, Counter) und vollstaendig aufgezeichnete Stunden fuer eine Folge von Tagen."""
    zeilen, voll = [], []
    for d in tage:
        for h in range(24):
            faktor = 0.3 + 1.7 * math.exp(-((h - profil["spitze"]) / 3.0) ** 2) * (0.6 if d.weekday() >= 5 else 1.0)
            n = max(0, int(round(rnd.gauss(profil["menge"] * faktor, math.sqrt(profil["menge"] * faktor)))))
            c = collections.Counter(max(16, min(98, int(round(rnd.gauss(profil["mittel"], profil["sd"]))))) for _ in range(n))
            voll.append((d, h))
            if c:
                zeilen.append((d, h, 1, 0, c))
    return zeilen, voll


def messung(mid, seite, geraet, teile, brueche=(), limit=50, rnd=None):
    """Messung wie einsaetze.messungen_lesen: teile = [(erster Tag, letzter Tag, Standortprofil)] (Indizes ab BASIS)."""
    rnd = rnd or random.Random(hash(mid) % 1000)
    zeilen, voll = [], []
    for a, b, profil in teile:
        z, v = zeilen_fuer([tag(i) for i in range(a, b + 1)], profil, rnd)
        zeilen += z
        voll += v
    br = [(i + 2, tag(t), 1.0) for i, t in enumerate(brueche)]
    return {"id": mid, "rel": mid, "datei": mid + ".dsd", "geraet": geraet, "limit": limit, "seite": seite, "name": seite, "fahrtrichtung": "",
            "uhr_nutzbar": True, "brueche": br, "grenzen": [b[1] for b in br], "zeilen": zeilen, "voll": voll,
            "von": tag(teile[0][0]), "bis": tag(teile[-1][1])}


A, B, C, D = standort(45, 8), standort(30, 17, menge=12), standort(38, 12, sd=8), standort(52, 6)


def andere(n=22):
    """Vergleichsabschnitte anderer Standorte (gleiches Limit) fuer den Nulltest: andere Tempi und Tagesgaenge als A."""
    out = []
    for i in range(n):
        mittel = 33 + 1.3 * i
        if abs(mittel - 45) < 2:
            mittel += 4
        out.append(messung(f"m-z{i}", f"z{i}", f"G{i}", [(0, 29, standort(mittel, 6 + (i % 11) if (i % 11) != 2 else 3))]))
    return out


class Zuordnung(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vergleich = andere()

    def test_umhaengen_wird_belegt_und_der_einsatz_zusammengesetzt(self):
        y = messung("m-y", "a", "G", [(0, 59, A)])
        x = messung("m-x", "b", "G", [(60, 89, A), (90, 119, B)], brueche=[90])  # das Geraet hing nach dem Auslesen noch bei A
        brueche, umh = E.zuordnen([y, x] + self.vergleich)
        b = next(b for b in brueche if b["messung"] == "m-x")
        self.assertEqual((b["zuordnung"]["art"], b["zuordnung"]["stufe"]), ("umhaengen", "belegt"), b["umhaengen"])
        self.assertEqual(umh[0]["von_messung"], "m-y")
        ein = {e["messung"]: e for e in E.einsaetze_bilden([y, x] + self.vergleich, umh)}
        ey, ex = ein["m-y"], ein["m-x"]
        self.assertEqual(ey["status"], "abgeleitet")
        self.assertEqual([(t["messung"], t["abschnitt"]) for t in ey["teile"]], [("m-y", 1), ("m-x", 1)])
        self.assertEqual(ex["status"], "gekuerzt")
        self.assertEqual([(t["messung"], t["abschnitt"]) for t in ex["teile"]], [("m-x", 2)])
        # Bruchtag und Vortag gehoeren zu keinem Einsatz
        self.assertEqual(ey["teile"][1]["bis"], tag(88).isoformat())
        self.assertEqual(ex["teile"][0]["von"], tag(91).isoformat())
        self.assertEqual(sorted(set(ey["ausgenommene_tage"] + ex["ausgenommene_tage"])), [tag(89).isoformat(), tag(90).isoformat()])
        self.assertEqual(ex["abgegeben"], [{"abschnitt": 1, "an": "e-y"}])

    def test_anderer_standort_wird_nicht_zugeordnet(self):
        y = messung("m-y", "a", "G", [(0, 59, A)])
        x = messung("m-x", "b", "G", [(60, 89, C), (90, 119, B)], brueche=[90])  # Abschnitt 1 ist ein dritter Ort, nicht A
        brueche, umh = E.zuordnen([y, x] + self.vergleich)
        b = next(b for b in brueche if b["messung"] == "m-x")
        self.assertNotIn(b["zuordnung"]["stufe"], ("belegt", "bestaetigt"))
        self.assertEqual(umh, [])
        self.assertTrue(all(e["status"] == "identisch" for e in E.einsaetze_bilden([y, x], umh)))

    def test_kette_ueber_drei_messungen(self):
        y = messung("m-y", "a", "G", [(0, 59, A)])
        x = messung("m-x", "b", "G", [(60, 89, A), (90, 119, B)], brueche=[90])
        z = messung("m-z", "d", "G", [(120, 149, B), (150, 179, D)], brueche=[150])
        brueche, umh = E.zuordnen([y, x, z] + self.vergleich)
        ein = {e["messung"]: e for e in E.einsaetze_bilden([y, x, z] + self.vergleich, umh)}
        self.assertEqual([(t["messung"], t["abschnitt"]) for t in ein["m-y"]["teile"]], [("m-y", 1), ("m-x", 1)])
        self.assertEqual([(t["messung"], t["abschnitt"]) for t in ein["m-x"]["teile"]], [("m-x", 2), ("m-z", 1)])
        self.assertEqual([(t["messung"], t["abschnitt"]) for t in ein["m-z"]["teile"]], [("m-z", 2)])
        self.assertEqual(ein["m-x"]["status"], "abgeleitet")

    def test_angabe_der_verwaltung_hat_vorrang(self):
        y = messung("m-y", "a", "G", [(0, 59, A)])
        x = messung("m-x", "b", "G", [(60, 89, A), (90, 119, B)], brueche=[90])
        verw = {("m-x/m-x.dsd", tag(90).isoformat()): {"art": "umhaengen", "abschnitt_von": "m-y", "erklaerung": "Umhängeprotokoll",
                                                      "ausgenommen": [tag(90).isoformat()]}}
        brueche, umh = E.zuordnen([y, x] + self.vergleich, verwaltung=verw)
        b = next(b for b in brueche if b["messung"] == "m-x")
        self.assertEqual((b["zuordnung"]["stufe"], b["zuordnung"]["text"]), ("bestaetigt", "Umhängeprotokoll"))
        ein = {e["messung"]: e for e in E.einsaetze_bilden([y, x], umh)}
        self.assertEqual(ein["m-y"]["status"], "bestaetigt")
        self.assertEqual(ein["m-y"]["teile"][1]["bis"], tag(89).isoformat())  # nur der bestaetigte Tag faellt weg

    def test_ferienende_erklaert_einen_bruch(self):
        # Herbstferien 2023 enden am 14.10. (Samstag), erster Schultag 16.10.
        i = (dt.date(2023, 10, 16) - BASIS).days
        x = messung("m-x", "b", "G", [(0, i - 1, C), (i, i + 40, B)], brueche=[i])
        brueche, _ = E.zuordnen([x])
        self.assertEqual((brueche[0]["zuordnung"]["art"], brueche[0]["zuordnung"]["stufe"]), ("ereignis", "plausibel"))
        kurz = [{"von": "2023-08-25", "bis": "2023-08-29", "name": "Fest", "art": "kurz"}]
        self.assertEqual(E.ereignis_kandidaten(dt.date(2023, 8, 30), "b", kurz)[0]["erklaerung"], False)  # kurze Ereignisse nur als Hinweis

    def test_invarianten(self):
        y = messung("m-y", "a", "G", [(0, 59, A)])
        x = messung("m-x", "b", "G", [(60, 89, A), (90, 119, B)], brueche=[90])
        ms = [y, x]
        _, umh = E.zuordnen(ms + self.vergleich)
        ein = E.einsaetze_bilden(ms, umh)
        self.assertEqual({e["messung"] for e in ein}, {"m-y", "m-x"})  # zu jeder Messung ein Einsatz
        self.assertTrue(all(e["teile"] for e in ein))  # jeder Einsatz mit mindestens einem Abschnitt
        # jedes Fahrzeug genau einmal: in einem Einsatz oder an einem ausgenommenen Tag
        im_einsatz = collections.Counter()
        for e in ein:
            for t in e["teile"]:
                m = next(m for m in ms if m["id"] == t["messung"])
                von, bis = dt.date.fromisoformat(t["von"]), dt.date.fromisoformat(t["bis"])
                im_einsatz[t["messung"]] += sum(sum(c.values()) for d, h, v, k, c in m["zeilen"] if von <= d <= bis)
        aus = {dt.date.fromisoformat(d) for e in ein for d in e["ausgenommene_tage"]}
        for m in ms:
            gesamt = sum(sum(c.values()) for *_x, c in m["zeilen"])
            ausgenommen = sum(sum(c.values()) for d, h, v, k, c in m["zeilen"] if d in aus)
            self.assertEqual(im_einsatz[m["id"]] + ausgenommen, gesamt, m["id"])

    def test_kennzahlen_eines_einsatzes(self):
        y = messung("m-y", "a", "G", [(0, 59, A)])
        e = E.einsaetze_bilden([y], [])[0]
        self.assertEqual(e["status"], "identisch")
        k, daten = E.kennzahlen_einsatz(e, {"m-y": y})
        n = sum(sum(c.values()) for *_x, c in y["zeilen"])
        self.assertEqual(k["bereinigt"]["anzahl_fahrzeuge"], n)
        self.assertEqual(sum(daten["tage"].values()), len(y["voll"]))  # alle vollstaendig aufgezeichneten Stunden, auch ohne Fahrzeug
        self.assertEqual(sum(sum(z[1::2]) for z in daten["z"].values()), n)
        self.assertIn("raten", k["bereinigt"])
        self.assertEqual(set(k["teilzeitraeume"]), {"nacht", "vormittag", "nachmittag", "abend", "schulweg"})


if __name__ == "__main__":
    unittest.main()
