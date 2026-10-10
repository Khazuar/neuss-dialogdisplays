# SPDX-License-Identifier: MIT
"""Tests fuer rauschen.py (Rauschbodenschaetzer).  Aufruf: python3 -m unittest -v"""
import datetime as dt
import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dsd2csv as d  # noqa: E402
import rauschen as r  # noqa: E402

START = dt.datetime(2025, 3, 3)  # ein Montag


def poisson(rnd, lam):
    if lam > 30:
        return max(0, int(round(rnd.gauss(lam, math.sqrt(lam)))))
    l, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rnd.random()
        if p <= l:
            return k
        k += 1


def synthetisch(tage=40, rausch_je_stunde=4.0, rausch_bis=10, langsam_anteil=0.2, rausch_tage=None, seed=1):
    """Verkehr mit Tagesgang (Lognormal um 30 km/h, 20 % davon langsam bei 16 km/h, verkehrsgebunden) plus konstantes Rauschen."""
    rnd = random.Random(seed)
    fahrten, echt_rausch = [], 0
    for tag in range(tage):
        for h in range(24):
            verkehr = 4 + 70 * math.exp(-((h - 8) / 3.0) ** 2) + 60 * math.exp(-((h - 17) / 3.0) ** 2)
            zeit = START + dt.timedelta(days=tag, hours=h)
            for _ in range(poisson(rnd, verkehr)):
                v = rnd.gauss(16, 2) if rnd.random() < langsam_anteil else rnd.gauss(31, 4.5)
                fahrten.append((zeit + dt.timedelta(seconds=rnd.randrange(3600)), max(1, int(round(v)))))
            if rausch_je_stunde and (rausch_tage is None or tag in rausch_tage):
                for _ in range(poisson(rnd, rausch_je_stunde)):
                    v = min(3 + int(rnd.expovariate(0.6)), rausch_bis)
                    fahrten.append((zeit + dt.timedelta(seconds=rnd.randrange(3600)), v))
                    echt_rausch += 1
    fahrten.sort()
    spannen = [(START, START + dt.timedelta(days=tage))]
    return fahrten, spannen, echt_rausch


class Tagtyp(unittest.TestCase):
    def test_wochentage_und_feiertage(self):
        self.assertEqual(r.tagtyp(dt.datetime(2025, 3, 3, 12)), "Werktag")
        self.assertEqual(r.tagtyp(dt.datetime(2025, 3, 8, 12)), "Samstag")
        self.assertEqual(r.tagtyp(dt.datetime(2025, 3, 9, 12)), "Sonn-/Feiertag")
        self.assertEqual(r.tagtyp(dt.datetime(2025, 10, 3, 12)), "Sonn-/Feiertag")  # Freitag, Tag der Deutschen Einheit
        self.assertEqual(r.tagtyp(dt.datetime(2025, 12, 25, 12)), "Sonn-/Feiertag")

    def test_ostern(self):
        self.assertEqual(r.ostern(2025), dt.date(2025, 4, 20))
        self.assertEqual(r.ostern(2024), dt.date(2024, 3, 31))
        self.assertEqual(r.tagtyp(dt.datetime(2025, 4, 18, 9)), "Sonn-/Feiertag")  # Karfreitag
        self.assertEqual(r.tagtyp(dt.datetime(2025, 4, 21, 9)), "Sonn-/Feiertag")  # Ostermontag
        self.assertEqual(r.tagtyp(dt.datetime(2025, 5, 29, 9)), "Sonn-/Feiertag")  # Christi Himmelfahrt


class Hilfen(unittest.TestCase):
    def test_nur_volle_stunden_im_abschnitt_zaehlen(self):
        s = r.abgedeckte_stunden([(dt.datetime(2025, 3, 3, 10, 30), dt.datetime(2025, 3, 3, 13, 0))])
        self.assertEqual(sorted(h for _, h in s), [11, 12])

    def test_wls_findet_achsenabschnitt_und_steigung(self):
        xs = [float(x) for x in range(1, 11)]
        a, b, se = r.wls(xs, [2 + 3 * x for x in xs], [10] * 10)
        self.assertAlmostEqual(a, 2, places=3)
        self.assertAlmostEqual(b, 3, places=3)

    def test_wls_haelt_a_und_b_nicht_negativ(self):
        xs = [float(x) for x in range(1, 11)]
        a, b, _ = r.wls(xs, [3 * x for x in xs], [10] * 10)  # kein Achsenabschnitt
        self.assertGreaterEqual(a, 0)
        self.assertAlmostEqual(a, 0, places=2)
        a, b, _ = r.wls(xs, [5.0] * 10, [10] * 10)  # konstant: nur Rauschen
        self.assertAlmostEqual(a, 5, places=2)
        self.assertAlmostEqual(b, 0, places=2)


class Schaetzer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fahrten, cls.spannen, cls.echt = synthetisch()
        cls.rb = r.pruefen(cls.fahrten, cls.spannen, 30)

    def test_findet_das_konstante_rauschen(self):
        wahr = self.echt / len(self.fahrten)
        self.assertTrue(self.rb["belegt"], self.rb["grund"])
        self.assertAlmostEqual(self.rb["anteil"], wahr, delta=0.3 * wahr)
        self.assertLessEqual(self.rb["obergrenze_kmh"], 10)
        self.assertTrue(self.rb["stabil"])

    def test_verkehrsgebundene_langsame_gruppe_ist_kein_rauschen(self):
        est = self.rb["_modell"]["est"]
        self.assertTrue(all(v <= 11 for v in est["a"]), sorted(est["a"]))  # nichts bei 12 bis 20 km/h (langsame Gruppe um 16)

    def test_abzug_entfernt_etwa_das_rauschen_und_nur_langsames(self):
        neu = r.ohne_rauschen(self.fahrten, self.rb["_modell"])
        entfernt = len(self.fahrten) - len(neu)
        self.assertAlmostEqual(entfernt, self.echt, delta=0.3 * self.echt)
        bleibt = {id(f) for f in neu}
        weg = [f for f in self.fahrten if id(f) not in bleibt]
        self.assertTrue(all(v <= 11 for _, v in weg))
        self.assertEqual([f for f in neu], sorted(neu))  # Reihenfolge bleibt

    def test_abzug_ist_deterministisch(self):
        a = r.ohne_rauschen(self.fahrten, self.rb["_modell"])
        b = r.ohne_rauschen(self.fahrten, self.rb["_modell"])
        self.assertEqual(a, b)

    def test_abzug_ohne_uhrzeit_nur_nach_geschwindigkeit(self):
        neu = r.ohne_rauschen_je_v(self.fahrten, self.rb["_modell"])
        mit_zeit = r.ohne_rauschen(self.fahrten, self.rb["_modell"])
        self.assertAlmostEqual(len(self.fahrten) - len(neu), self.echt, delta=0.3 * self.echt)
        # beide Abzuege entfernen gleich viel, damit "alle Fahrzeuge" nie kleiner ausfaellt als "mit nutzbarer Zeit"
        self.assertAlmostEqual(len(neu), len(mit_zeit), delta=0.01 * len(neu))

    def test_spektrum_ist_ganzzahlig_und_beginnt_beim_kleinsten_rauschwert(self):
        sp = self.rb["spektrum"]
        self.assertEqual(sp["ab_kmh"], min(self.rb["_modell"]["est"]["a"]))
        self.assertEqual(len(sp["rausch"]), len(sp["alle"]))
        self.assertTrue(all(isinstance(x, int) for x in sp["rausch"] + sp["alle"]))
        self.assertTrue(all(a <= b + 1 for a, b in zip(sp["rausch"], sp["alle"])))  # Rauschen <= alle (Rundung)

    def test_ohne_rauschen_nichts_nachweisbar(self):
        fahrten, spannen, _ = synthetisch(rausch_je_stunde=0)
        rb = r.pruefen(fahrten, spannen, 30)
        self.assertFalse(rb["belegt"])
        self.assertIn("nachweisbar", rb["grund"])
        self.assertLess(rb["anteil"], 0.005)

    def test_rauschen_bis_weit_ueber_langsamen_verkehr_ist_nicht_belegt(self):
        fahrten, spannen, _ = synthetisch(rausch_je_stunde=40, rausch_bis=25)
        # gleichverteiltes Rauschen bis 25 km/h: die Obergrenze liegt ueber der Grenze
        rnd = random.Random(5)
        fahrten = [(t, v if v > 10 else rnd.randrange(3, 21)) for t, v in fahrten]
        rb = r.pruefen(fahrten, spannen, 30)
        self.assertFalse(rb["belegt"])
        self.assertIn("reicht bis", rb["grund"])

    def test_rauschen_nur_in_einer_haelfte_der_tage_ist_nicht_stabil(self):
        gerade = set(range(0, 40, 2))
        fahrten, spannen, _ = synthetisch(rausch_je_stunde=6, rausch_tage=gerade)
        rb = r.pruefen(fahrten, spannen, 30)
        self.assertFalse(rb["stabil"])
        self.assertFalse(rb["belegt"])
        self.assertIn("stabil", rb["grund"])

    def test_zu_kleine_datei_wird_nicht_geprueft(self):
        self.assertIsNone(r.pruefen(self.fahrten[:100], self.spannen, 30))
        self.assertIsNone(r.pruefen(self.fahrten, self.spannen, None))


class Block(unittest.TestCase):
    def test_nicht_geprueft(self):
        b = d.rauschen_block(None, 0)
        self.assertFalse(b["geprueft"])
        self.assertIn("3000", b["grund"])

    def test_geprueft_und_belegt(self):
        fahrten, spannen, _ = synthetisch()
        rb = r.pruefen(fahrten, spannen, 30)
        b = d.rauschen_block(rb, 123, 1000)
        self.assertTrue(b["geprueft"] and b["belegt"])
        self.assertEqual(b["abgezogen_fahrzeuge"], 123)
        self.assertEqual(b["abgezogen_anteil_prozent"], 12.3)
        self.assertNotIn("_modell", b)
        self.assertIn("spektrum", b)
        self.assertNotIn("grund", b)
        zeilen = d.yaml_zeilen({"rauschen": b})
        self.assertTrue(any(z.strip().startswith("rausch: [") for z in zeilen))  # Zahlenlisten in einer Zeile


if __name__ == "__main__":
    unittest.main()
