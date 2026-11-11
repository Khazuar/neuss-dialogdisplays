# SPDX-License-Identifier: MIT
"""Tests fuer einschwingen.py an synthetischen Stunden.  Aufruf: python3 -m unittest -v"""
import collections
import datetime as dt
import math
import random
import unittest

import einschwingen as E

BASIS = dt.datetime(2024, 1, 15, 10)  # Montag; bis Mitte Maerz keine Ferien und Feiertage in NRW
STUNDE = dt.timedelta(hours=1)


def stunden(von, tage, tempo, menge=60.0, spitze=8, rnd=None, faktor=1.0):
    """[(Beginn der Stunde, voll, Counter)]: tempo(t in Tagen seit von) -> mittleres Tempo, menge Fahrzeuge je Stunde in der Spitze."""
    rnd = rnd or random.Random(1)
    out = []
    for i in range(int(tage * 24)):
        t = von + i * STUNDE
        tage_seit = i / 24
        lam = menge * (0.3 + 0.7 * math.exp(-((t.hour - spitze) / 3.0) ** 2))
        c = collections.Counter()
        for _ in range(int(round(lam))):
            c[max(5, int(round(faktor * rnd.gauss(tempo(tage_seit), 6))))] += 1
        out.append((t, True, c))
    return out


class Quantile(unittest.TestCase):
    def test_interpolation_in_der_klasse(self):
        self.assertAlmostEqual(E.quantile([(10, 2), (11, 2)], (0.5,))[0], 10.5)
        self.assertAlmostEqual(E.quantile([(30, 4)], (0.25, 0.75))[0], 29.75)


class Einschwingen(unittest.TestCase):
    def test_abklingender_anfang(self):
        st = stunden(BASIS, 56, lambda t: 40 + 5 * math.exp(-t / 3), menge=100)
        es = E.einschwingen(st, BASIS, BASIS + dt.timedelta(days=56))
        self.assertEqual(es["schritt_tage"], 1)
        self.assertEqual(es["urteil"], "einschwingen")
        self.assertGreater(es["mittel"]["a"], 3)
        self.assertTrue(6 <= es["stabil_tage"] <= 15)

    def test_gleichbleibend(self):
        st = stunden(BASIS, 56, lambda t: 40)
        es = E.einschwingen(st, BASIS, BASIS + dt.timedelta(days=56))
        self.assertEqual(es["urteil"], "sofort")
        self.assertLess(abs(es["mittel"]["abweichung_erster"]), 1)

    def test_ruhige_strasse_laengere_schritte(self):
        st = stunden(BASIS, 56, lambda t: 30, menge=5)
        es = E.einschwingen(st, BASIS, BASIS + dt.timedelta(days=56))
        self.assertEqual(es["schritt_tage"], 7)

    def test_zu_kurz(self):
        st = stunden(BASIS, 20, lambda t: 40)
        es = E.einschwingen(st, BASIS, BASIS + dt.timedelta(days=20))
        self.assertEqual(es["urteil"], "zu_kurz")

    def test_beginn_mitten_in_der_stunde(self):
        st = stunden(BASIS, 30, lambda t: 40)
        es = E.einschwingen(st, BASIS + dt.timedelta(minutes=20), BASIS + dt.timedelta(days=30))
        self.assertEqual(es["beginn"], (BASIS + STUNDE).isoformat())


class Klassifizieren(unittest.TestCase):
    GRENZE = BASIS + dt.timedelta(days=21)

    def seiten(self, vorher, nachher):
        return stunden(BASIS, 21, **vorher), stunden(self.GRENZE, 21, rnd=random.Random(2), **nachher)

    def klasse(self, vorher, nachher, **kw):
        vor, nach = self.seiten(vorher, nachher)
        return E.klassifizieren(vor, nach, self.GRENZE, self.GRENZE, **kw)

    def test_montage_ist_standortwechsel(self):
        self.assertEqual(E.klassifizieren([], [], self.GRENZE, self.GRENZE, montage_neu=True)["klasse"], "standortwechsel")

    def test_keine_aenderung(self):
        self.assertEqual(self.klasse({"tempo": lambda t: 40}, {"tempo": lambda t: 40})["klasse"], "keine")

    def test_anderer_ort_tempo_sofort(self):
        self.assertEqual(self.klasse({"tempo": lambda t: 40}, {"tempo": lambda t: 45})["klasse"], "ort_genau")

    def test_messwinkel_faktor(self):
        r = self.klasse({"tempo": lambda t: 50}, {"tempo": lambda t: 50, "faktor": 0.88})
        self.assertEqual(r["klasse"], "ausrichtung")
        self.assertAlmostEqual(r["faktor"], 0.88, delta=0.02)

    def test_fahrtrichtung_spitze_kehrt_sich_um(self):
        self.assertEqual(self.klasse({"tempo": lambda t: 40, "spitze": 8}, {"tempo": lambda t: 40, "spitze": 17})["klasse"], "fahrtrichtung")

    def test_schild_allmaehlich(self):
        vor, nach = self.seiten({"tempo": lambda t: 45}, {"tempo": lambda t: 38 + 5 * math.exp(-t / 5)})
        es = E.einschwingen(nach, self.GRENZE, self.GRENZE + dt.timedelta(days=21))
        es["mittel"] = {"stand": 38.0}  # spaeterer Stand (der kurze Abschnitt hat keinen eigenen)
        r = E.klassifizieren(vor, nach, self.GRENZE, self.GRENZE, es=es)
        self.assertEqual(r["klasse"], "strasse")
        self.assertLess(r["sofort"], 0.7)

    def test_bewegung_mit_halber_menge_ist_standortwechsel(self):
        r = self.klasse({"tempo": lambda t: 40, "menge": 80}, {"tempo": lambda t: 40, "menge": 30}, bewegung=True)
        self.assertEqual(r["klasse"], "standortwechsel")

    def test_zu_wenige_tage(self):
        vor = stunden(self.GRENZE - dt.timedelta(days=2), 2, lambda t: 40)
        nach = stunden(self.GRENZE, 21, lambda t: 40)
        self.assertEqual(E.klassifizieren(vor, nach, self.GRENZE, self.GRENZE)["klasse"], "unklar")


if __name__ == "__main__":
    unittest.main()
