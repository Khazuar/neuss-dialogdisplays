# SPDX-License-Identifier: MIT
"""Tests fuer bruch.py (Brueche in Messreihen).  Aufruf: python3 -m unittest -v"""
import datetime as dt
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bruch as b  # noqa: E402

START = dt.date(2025, 3, 3)  # ein Montag


def reihe(tage, mittel_je_tag, n_je_tag=300, streuung=6.0, luecken=(), seed=1):
    """Fahrzeuge [(Ortszeit, v)] und Spannen fuer `tage` vollstaendige Tage; mittel_je_tag(i) -> mittleres Tempo."""
    rng = random.Random(seed)
    fz = []
    for i in range(tage):
        if i in luecken:
            continue
        tag = START + dt.timedelta(days=i)
        n = int(n_je_tag * (0.6 if tag.weekday() >= 5 else 1.0))  # Wochenende ruhiger
        for _ in range(n):
            t = dt.datetime(tag.year, tag.month, tag.day, rng.randrange(6, 22), rng.randrange(60), rng.randrange(60))
            fz.append((t, max(1, int(round(rng.gauss(mittel_je_tag(i), streuung))))))
    spannen = []
    i = 0
    while i < tage:  # zusammenhaengende Tage ergeben einen Abschnitt der Uhr
        if i in luecken:
            i += 1
            continue
        j = i
        while j + 1 < tage and (j + 1) not in luecken:
            j += 1
        spannen.append((dt.datetime.combine(START + dt.timedelta(days=i), dt.time()),
                        dt.datetime.combine(START + dt.timedelta(days=j + 1), dt.time())))  # bis Mitternacht: der letzte Tag ist vollstaendig
        i = j + 1
    return fz, spannen


class Erkennung(unittest.TestCase):
    def test_gleichmaessige_reihe_hat_keinen_bruch(self):
        fz, sp = reihe(60, lambda i: 40)
        r = b.erkenne(fz, sp, 20, 50)
        self.assertTrue(r["geprueft"])
        self.assertEqual(r["brueche"], [])
        self.assertEqual(len(r["abschnitte"]), 1)
        self.assertEqual(r["abschnitte"][0]["tage"], 60)

    def test_sprung_im_tempo_ist_ein_bruch(self):
        fz, sp = reihe(60, lambda i: 45 if i < 25 else 30)
        r = b.erkenne(fz, sp, 15, 50)
        self.assertEqual(len(r["brueche"]), 1)
        br = r["brueche"][0]
        self.assertEqual(br["datum"], (START + dt.timedelta(days=25)).isoformat())
        self.assertEqual(br["vorher_bis"], (START + dt.timedelta(days=24)).isoformat())
        self.assertGreaterEqual(br["wahrscheinlichkeit"], 0.99)
        self.assertGreater(br["unterschied_der_verteilungen"], 0.5)
        self.assertGreater(br["vorher"]["mittel_kmh"] - br["nachher"]["mittel_kmh"], 10)
        self.assertEqual([a["tage"] for a in r["abschnitte"]], [25, 35])
        text = " ".join(br["begruendung"])
        self.assertIn("mittleres Tempo", text)
        self.assertIn("totale Variation", text)

    def test_luecke_vor_dem_bruch_wird_genannt(self):
        fz, sp = reihe(60, lambda i: 45 if i < 25 else 30, luecken=range(25, 31))
        r = b.erkenne(fz, sp, 15, 50)
        self.assertEqual(len(r["brueche"]), 1)
        self.assertEqual(r["brueche"][0]["datum"], (START + dt.timedelta(days=31)).isoformat())
        self.assertEqual(r["brueche"][0]["luecke_tage"], 6)
        self.assertIn("6 Tage", " ".join(r["brueche"][0]["begruendung"]))

    def test_kurzer_ausschlag_mit_rueckkehr_ist_kein_bruch(self):
        fz, sp = reihe(70, lambda i: 30 if 30 <= i < 37 else 45)
        r = b.erkenne(fz, sp, 15, 50)
        self.assertEqual(r["brueche"], [])
        self.assertEqual(len(r["ausschlaege"]), 1)
        self.assertEqual(r["ausschlaege"][0]["von"], (START + dt.timedelta(days=30)).isoformat())

    def test_kleine_verschiebung_wird_nicht_getrennt(self):
        fz, sp = reihe(80, lambda i: 40 if i < 40 else 40.8)
        r = b.erkenne(fz, sp, 15, 50)
        self.assertEqual(r["brueche"], [])

    def test_zu_wenige_tage(self):
        fz, sp = reihe(8, lambda i: 40)
        r = b.erkenne(fz, sp, 15, 50)
        self.assertFalse(r["geprueft"])
        self.assertIn("vollständig aufgezeichnete Tage", r["grund"])

    def test_unvollstaendige_tage_zaehlen_nicht(self):
        fz, sp = reihe(30, lambda i: 40)
        # Ende der Aufzeichnung mitten am Tag 29: dieser Tag faellt aus den Tagesmerkmalen
        sp = [(sp[0][0], dt.datetime.combine(START + dt.timedelta(days=29), dt.time(12)))]
        tm = b.tagesmerkmale(fz, sp, 15, 50)
        self.assertEqual(len(tm), 29)

    def test_wochenende_fuehrt_nicht_zu_bruechen(self):
        # Werktage 300, Wochenende 180 Fahrzeuge: der Tagtyp wird abgezogen
        fz, sp = reihe(70, lambda i: 40, n_je_tag=500)
        self.assertEqual(b.erkenne(fz, sp, 15, 50)["brueche"], [])


class Ferien(unittest.TestCase):
    def test_kalender(self):
        import kalender
        self.assertEqual(kalender.schulferien(dt.date(2025, 4, 14)), "Osterferien")
        self.assertIsNone(kalender.schulferien(dt.date(2025, 4, 27)))
        self.assertEqual(kalender.besonderer_tag(dt.date(2025, 4, 21)), "feiertag")  # Ostermontag in den Ferien
        self.assertEqual(kalender.besonderer_tag(dt.date(2025, 4, 22)), "ferien")
        self.assertIsNone(kalender.besonderer_tag(dt.date(2025, 5, 6)))
        for von, bis, _ in kalender.SCHULFERIEN_NRW:
            self.assertLessEqual(von, bis)

    def test_ferien_sind_kein_bruch_aber_ein_wechsel_in_den_ferien_schon(self):
        ferien = set(range(30, 44))  # zwei Wochen mit anderem Verkehr
        aus = (lambda d: "ferien" if (d - START).days in ferien else None)
        fz, sp = reihe(80, lambda i: 32 if i in ferien else 40)
        self.assertEqual(b.erkenne(fz, sp, 15, 50, aus)["brueche"], [])
        # nach den Ferien bleibt es anders: ein Bruch am ersten Tag nach den Ferien, die Ferientage stehen in der Begruendung
        fz, sp = reihe(80, lambda i: 40 if i < 30 else 30)
        r = b.erkenne(fz, sp, 15, 50, aus)
        self.assertEqual(len(r["brueche"]), 1)
        self.assertEqual(r["brueche"][0]["datum"], (START + dt.timedelta(days=44)).isoformat())
        self.assertEqual(r["brueche"][0]["ausgenommene_tage_davor"], {"ferien": 14})
        self.assertEqual(r["brueche"][0]["luecke_tage"], 0)
        self.assertIn("14 Tage Schulferien", " ".join(r["brueche"][0]["begruendung"]))


class Auswertung(unittest.TestCase):
    def test_abschnitte_werden_einzeln_ausgewertet(self):
        import dsd2csv
        fz, sp = reihe(45, lambda i: 45 if i < 25 else 30, n_je_tag=100)
        br = b.erkenne(fz, sp, 15, 50)
        teil = {k: [] for k in dsd2csv.TEILZEITRAEUME}
        blk, _ = dsd2csv.abschnitte_auswerten(br, fz, fz, teil, sp, 50, 0, lambda v: {})
        self.assertEqual((blk["anzahl"], blk["brueche"]), (2, 1))
        a1, a2 = blk["liste"]
        self.assertEqual(a1["beginn"]["art"], "Beginn der Messung")
        self.assertEqual(a2["beginn"]["art"], "Bruch")
        self.assertEqual(a2["beginn"]["datum"], (START + dt.timedelta(days=25)).isoformat())
        self.assertEqual(a1["anzahl_fahrzeuge"] + a2["anzahl_fahrzeuge"], len(fz))
        self.assertGreater(a1["geschwindigkeit_kmh"]["mittel"] - a2["geschwindigkeit_kmh"]["mittel"], 10)
        self.assertEqual(a1["von"], START.isoformat())
        self.assertIn("teilzeitraeume", a2)
        # ohne Bruch: kein Abschnitt in der Liste
        fz2, sp2 = reihe(40, lambda i: 40)
        blk2, _ = dsd2csv.abschnitte_auswerten(b.erkenne(fz2, sp2, 15, 50), fz2, fz2, teil, sp2, 50, 0, lambda v: {})
        self.assertEqual((blk2["liste"], blk2["brueche"]), ([], 0))
        blk3, _ = dsd2csv.abschnitte_auswerten(b.erkenne(fz2[:50], sp2, 15, 50), fz2[:50], fz2[:50], teil, sp2, 50, 0, lambda v: {})
        self.assertFalse(blk3["geprueft"])


class Bausteine(unittest.TestCase):
    def test_wahrscheinlichkeit_waechst_mit_dem_sprung(self):
        y = [[0.0]] * 10 + [[1.0]] * 10
        S = b._Summen(y, [1.0], 1.0)
        p1, _ = b.bruchwahrscheinlichkeit(S, 0, 10, 20, 1.0)
        y2 = [[0.0]] * 10 + [[3.0]] * 10
        p2, _ = b.bruchwahrscheinlichkeit(b._Summen(y2, [1.0], 1.0), 0, 10, 20, 1.0)
        self.assertLess(p1, p2)
        self.assertGreater(p2, 0.999)
        y3 = [[0.1 * (i % 2)] for i in range(20)]
        p3, _ = b.bruchwahrscheinlichkeit(b._Summen(y3, [1.0], 1.0), 0, 10, 20, 1.0)
        self.assertLess(p3, 0.1)

    def test_tv(self):
        import collections
        h = {dt.date(2025, 1, 1): collections.Counter({30: 10, 31: 10}), dt.date(2025, 1, 2): collections.Counter({30: 10, 31: 10}),
             dt.date(2025, 1, 3): collections.Counter({50: 20})}
        self.assertAlmostEqual(b._tv(h, 0, 2, 3), 1.0)
        self.assertAlmostEqual(b._tv(h, 0, 1, 2), 0.0)

    def test_zerlegung_findet_die_grenze(self):
        y = [[0.0, 0.0]] * 12 + [[5.0, -4.0]] * 12
        grenzen, _ = b.zerlege(y, [1.0, 1.0], 1.0, 10.0)
        self.assertEqual(grenzen, [12])
        grenzen, _ = b.zerlege([[0.0, 0.0]] * 24, [1.0, 1.0], 1.0, 10.0)
        self.assertEqual(grenzen, [])


if __name__ == "__main__":
    unittest.main()
