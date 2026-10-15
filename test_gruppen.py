# SPDX-License-Identifier: MIT
"""Tests fuer gruppen.py (Zellen der Detailseiten) und zwischenspeicher.py.  Aufruf: python3 -m unittest -v"""
import collections
import datetime as dt
import math
import os
import random
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gruppen as g  # noqa: E402
import zwischenspeicher as zs  # noqa: E402


class Hilfen(unittest.TestCase):
    def test_stunden(self):
        self.assertEqual(g.stunden(22, 6), [22, 23, 0, 1, 2, 3, 4, 5])
        self.assertEqual(g.stunden(6, 12), [6, 7, 8, 9, 10, 11])
        self.assertEqual(sum(len(g.stunden(a, b)) for _, a, b in g.ZEITSCHEIBEN), 24)  # die vier Scheiben decken den Tag ohne Luecke

    def test_tagschluessel(self):
        z = lambda *a: dt.datetime(*a)
        self.assertEqual(g.tagschluessel(z(2025, 10, 6, 12)), 0)  # Montag
        self.assertEqual(g.tagschluessel(z(2025, 10, 11, 12)), 5)  # Samstag
        self.assertEqual(g.tagschluessel(z(2025, 10, 12, 12)), 6)  # Sonntag
        self.assertEqual(g.tagschluessel(z(2025, 10, 3, 12)), 7)  # Tag der Deutschen Einheit (Freitag)
        self.assertEqual(g.tagschluessel(z(2025, 12, 25, 12)), 7)  # 1. Weihnachtstag (Donnerstag)
        self.assertEqual(g.tagschluessel(z(2025, 4, 18, 12)), 7)  # Karfreitag
        self.assertEqual(g.tagschluessel(z(2025, 10, 31, 12)), 4)  # Reformationstag ist in NRW kein Feiertag


def fahrten_und_spannen(tage=14, seed=1, rausch=False):
    """Zwei Wochen Verkehr: Fahrzeuge (Ortszeit, v), alle in einem durchgehenden Abschnitt."""
    rnd = random.Random(seed)
    start = dt.datetime(2025, 3, 3)  # Montag
    fahrten = []
    for tag in range(tage):
        for h in range(24):
            n = 6 + int(60 * math.exp(-((h - 8) / 3.0) ** 2))
            for _ in range(n):
                v = rnd.gauss(16, 2) if rnd.random() < 0.25 else rnd.gauss(40, 4)
                fahrten.append((start + dt.timedelta(days=tag, hours=h, seconds=rnd.randrange(3600)), max(5, int(round(v)))))
    return fahrten, [(start, start + dt.timedelta(days=tage))]


class Zellen(unittest.TestCase):
    def test_zellen_summen(self):
        fahrten, spannen = fahrten_und_spannen()
        behalten = [f for f in fahrten if f[1] >= 8]  # "Rauschen": Fahrten unter 8 km/h entfernt
        zd = g.zellen_bauen(fahrten, behalten, spannen)
        n_z = sum(sum(c.values()) for c in zd["z"].values())
        n_r = sum(sum(c.values()) for c in zd["r"].values())
        self.assertEqual(n_z, len(behalten))
        self.assertEqual(n_z + n_r, len(fahrten))
        self.assertEqual(sum(zd["D"].values()), 14 * 24)  # jede Stunde war aufgezeichnet
        self.assertEqual(zd["D"][(0, 8)], 2)  # zwei Montage
        self.assertTrue(all(v < 8 for c in zd["r"].values() for v in c))

    def test_teilstunden_am_rand_zaehlen_nicht(self):
        fahrten, _ = fahrten_und_spannen(tage=2)
        start = dt.datetime(2025, 3, 3, 0, 30)
        zd = g.zellen_bauen(fahrten, fahrten, [(start, start + dt.timedelta(hours=10, minutes=15))])
        self.assertEqual(sum(zd["D"].values()), 9)  # 1:00 bis 10:00 vollstaendig
        self.assertNotIn((0, 0), zd["z"])

    def test_kodierung(self):
        self.assertEqual(g.zelle_kodiert(collections.Counter({30: 5, 12: 2})), [12, 2, 30, 5])

    def test_datentabelle(self):
        fahrten, spannen = fahrten_und_spannen(tage=2)
        d = g.datentabelle(g.zellen_bauen(fahrten, fahrten, spannen), 30)
        self.assertEqual((d["v"], d["limit"]), (1, 30))
        self.assertEqual(sum(d["tage"].values()), 48)
        self.assertEqual(sum(sum(z[1::2]) for z in d["z"].values()), len(fahrten))
        self.assertEqual(d["r"], {})
        self.assertIsNone(g.datentabelle(g.zellen_bauen([], [], []), 30))  # ohne Fahrzeuge keine Tabelle


class Speicher(unittest.TestCase):
    def test_holen_speichern_aufraeumen(self):
        with tempfile.TemporaryDirectory() as ordner:
            s = zs.Zwischenspeicher(ordner)
            self.assertIsNone(s.holen("datei", "abc"))
            s.speichern("datei", "abc", {"a": [1, 2.5, None], "b": "ä"})
            s.speichern("datei", "alt", {"x": 1})
            s2 = zs.Zwischenspeicher(ordner)
            self.assertEqual(s2.holen("datei", "abc"), {"a": [1, 2.5, None], "b": "ä"})
            self.assertEqual(s2.aufraeumen(s2.benutzt), 1)  # "alt" wurde nicht benutzt
            self.assertIsNone(zs.Zwischenspeicher(ordner).holen("datei", "alt"))
            self.assertIsNotNone(zs.Zwischenspeicher(ordner).holen("datei", "abc"))

    def test_kaputte_datei_ist_ein_fehlschlag(self):
        with tempfile.TemporaryDirectory() as ordner:
            s = zs.Zwischenspeicher(ordner)
            s.speichern("datei", "k", {"a": 1})
            with open(os.path.join(ordner, "datei", "k.json"), "w") as fh:
                fh.write("{kaputt")
            self.assertIsNone(zs.Zwischenspeicher(ordner).holen("datei", "k"))

    def test_hashes(self):
        self.assertEqual(zs.inhalts_hash(b"a", 1), zs.inhalts_hash(b"a", 1))
        self.assertNotEqual(zs.inhalts_hash(b"a", 1), zs.inhalts_hash(b"a", 2))
        self.assertNotEqual(zs.inhalts_hash(b"a", 1), zs.inhalts_hash(b"b", 1))


if __name__ == "__main__":
    unittest.main()
