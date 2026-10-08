# SPDX-License-Identifier: MIT
"""Tests fuer die Zeitumrechnung und Uhr-Auswertung in dsd2csv.py.  Aufruf: python3 -m unittest -v"""
import datetime as dt
import unittest

import dsd2csv as d


def zeit(*a):
    return dt.datetime(*a)


class Zeitumstellung(unittest.TestCase):
    def test_sommerzeit_grenzen_2024(self):
        # EU-Regel: letzter Sonntag im Maerz/Oktober, 01:00 UTC
        self.assertEqual(d._sommerzeit_utc(2024), (zeit(2024, 3, 31, 1), zeit(2024, 10, 27, 1)))
        self.assertEqual(d._sommerzeit_utc(2025), (zeit(2025, 3, 30, 1), zeit(2025, 10, 26, 1)))
        self.assertEqual(d._sommerzeit_utc(2026), (zeit(2026, 3, 29, 1), zeit(2026, 10, 25, 1)))

    def test_utc_versatz(self):
        self.assertEqual(d.utc_versatz_h(zeit(2024, 7, 1)), 2)
        self.assertEqual(d.utc_versatz_h(zeit(2024, 12, 1)), 1)
        self.assertEqual(d.utc_versatz_h(zeit(2024, 10, 27, 0, 59)), 2)
        self.assertEqual(d.utc_versatz_h(zeit(2024, 10, 27, 1, 0)), 1)

    def test_ortszeit_zu_utc(self):
        self.assertEqual(d.ortszeit_zu_utc(zeit(2024, 7, 24, 9, 0)), zeit(2024, 7, 24, 7, 0))
        self.assertEqual(d.ortszeit_zu_utc(zeit(2024, 12, 4, 9, 0)), zeit(2024, 12, 4, 8, 0))

    def test_uhr_in_sommerzeit_gestellt_laeuft_im_winter_eine_stunde_vor(self):
        f = d.geraet_zu_ortszeit(2)  # bei MESZ gestellt, nie umgestellt
        self.assertEqual(f(zeit(2024, 8, 1, 7, 30)), zeit(2024, 8, 1, 7, 30))
        self.assertEqual(f(zeit(2024, 11, 5, 7, 30)), zeit(2024, 11, 5, 6, 30))
        # Stichtag: Geraet 02:59 ist noch MESZ, 03:00 entspricht 02:00 MEZ (die Stunde wiederholt sich)
        self.assertEqual(f(zeit(2024, 10, 27, 2, 59)), zeit(2024, 10, 27, 2, 59))
        self.assertEqual(f(zeit(2024, 10, 27, 3, 0)), zeit(2024, 10, 27, 2, 0))

    def test_uhr_in_winterzeit_gestellt_laeuft_im_sommer_eine_stunde_nach(self):
        f = d.geraet_zu_ortszeit(1)  # bei MEZ gestellt, nie umgestellt
        self.assertEqual(f(zeit(2025, 3, 1, 7, 30)), zeit(2025, 3, 1, 7, 30))
        self.assertEqual(f(zeit(2025, 5, 5, 7, 30)), zeit(2025, 5, 5, 8, 30))
        # Stichtag: Geraet 01:59 ist noch MEZ, 02:00 entspricht 03:00 MESZ
        self.assertEqual(f(zeit(2025, 3, 30, 1, 59)), zeit(2025, 3, 30, 1, 59))
        self.assertEqual(f(zeit(2025, 3, 30, 2, 0)), zeit(2025, 3, 30, 3, 0))


class Teilzeitraeume(unittest.TestCase):
    def test_grenzen(self):
        tags = d.TEILZEITRAEUME["tags"][1]
        nachts = d.TEILZEITRAEUME["nachts"][1]
        schule = d.TEILZEITRAEUME["schulweg"][1]
        mo = zeit(2024, 11, 4)  # Montag
        for stunde, t, n in ((5, False, True), (6, True, False), (17, True, False), (18, False, True)):
            c = mo.replace(hour=stunde, minute=59 if stunde in (5, 17) else 0)
            self.assertEqual((tags(c), nachts(c)), (t, n), c)
        self.assertTrue(schule(mo.replace(hour=7, minute=0)))
        self.assertTrue(schule(mo.replace(hour=7, minute=59, second=59)))
        self.assertFalse(schule(mo.replace(hour=8)))
        self.assertFalse(schule(zeit(2024, 11, 9, 7, 30)))  # Samstag


class Uhrsegmente(unittest.TestCase):
    def aufzeichnung(self, zeiten):
        return [(z, 30) for z in zeiten], []

    def test_reset_auf_werksdatum_wird_erkannt(self):
        echte = [zeit(2023, 3, 15, 10, 0) + dt.timedelta(minutes=i) for i in range(50)]
        reset = [zeit(2020, 1, 1, 12, 0, 53) + dt.timedelta(minutes=i) for i in range(50)]
        veh, status = self.aufzeichnung(echte + reset)
        uhr, bereinigt, _ = d.analysiere_uhr(veh, status)
        self.assertEqual(len(bereinigt), 50)
        self.assertEqual(uhr["fahrzeuge_ohne_gueltige_zeit"], 50)
        self.assertEqual(uhr["bewertung"], "eingeschraenkt")  # genau die Haelfte der Fahrzeuge nutzbar
        self.assertTrue(any("zurückgesetzter Geräteuhr" in h for h in uhr["hinweise"]))

    def test_einzelner_ausreisser_zaehlt_nicht_als_segment(self):
        zeiten = [zeit(2024, 5, 6, 8, 0) + dt.timedelta(minutes=i) for i in range(200)]
        zeiten[100] = zeit(2055, 1, 1)
        veh, status = self.aufzeichnung(zeiten)
        uhr, bereinigt, _ = d.analysiere_uhr(veh, status)
        self.assertEqual(len(bereinigt), 199)
        self.assertEqual(uhr["segmente_mit_fahrzeugen"], 1)

    def test_luecke_ohne_aufzeichnung_behaelt_den_uhrversatz(self):
        # Geraet im Sommer gestellt, Luecke ueber die Zeitumstellung: danach weiter Sommerzeit-Uhr
        vor = [zeit(2024, 10, 20, 8, 0) + dt.timedelta(minutes=i) for i in range(100)]
        nach = [zeit(2024, 11, 5, 8, 0) + dt.timedelta(minutes=i) for i in range(100)]
        veh, status = self.aufzeichnung(vor + nach)
        _, bereinigt, _ = d.analysiere_uhr(veh, status)
        self.assertEqual(bereinigt[0][0], zeit(2024, 10, 20, 8, 0))
        self.assertEqual(bereinigt[100][0], zeit(2024, 11, 5, 7, 0))  # Geraet 08:00 = 07:00 MEZ


class Yaml(unittest.TestCase):
    def test_listen(self):
        z = d.yaml_zeilen({"a": [], "b": ["x", "y"], "c": [{"k": 1, "m": {"n": 2}}]})
        self.assertEqual(z, ["a: []", "b:", '  - "x"', '  - "y"', "c:", "  - k: 1", "    m:", "      n: 2"])


class Gefaehrdung(unittest.TestCase):
    def test_aufprall(self):
        self.assertAlmostEqual(d.aufprall_kmh(30, 30), 0.0, places=6)  # Fahrzeug mit dem Limit haelt gerade noch
        self.assertEqual(d.aufprall_kmh(20, 30), 0.0)
        self.assertAlmostEqual(d.aufprall_kmh(60, 50), 40.0, delta=0.2)  # nachgerechnet: 60 km/h in der 50er-Zone
        self.assertAlmostEqual(d.aufprall_kmh(55, 50), 27.9, delta=0.2)
        self.assertEqual(d.aufprall_kmh(100, 50), 100.0)  # Reaktionsstrecke laenger als die Anhaltestrecke bei 50: keine Bremsung
        self.assertGreater(d.aufprall_kmh(70, 50), d.aufprall_kmh(60, 50))

    def test_alle_fahren_das_limit(self):
        g = d.gefaehrdung([(None, 30)] * 100, 30)
        self.assertEqual(g["risikoindex_nilsson"], 1.0)
        self.assertEqual((g["aufprall_ueber_30_kmh_prozent"], g["aufprall_ueber_50_kmh_prozent"]), (0.0, 0.0))
        self.assertEqual((g["aufprall_anteil_prozent"], g["aufprall_mittel_kmh"], g["aufprall_p99_kmh"]), (0.0, 0.0, 0.0))
        self.assertNotIn("aufprall_mittel_der_aufprallenden_kmh", g)  # niemand trifft auf

    def test_anhaltestrecke(self):
        g = d.gefaehrdung([(None, 30)], 30)
        self.assertAlmostEqual(g["anhaltestrecke_bei_limit_m"], 13.3, delta=0.05)  # 8,33 m Reaktion + 4,96 m Bremsweg

    def test_aufprall_verteilung(self):
        # Limit 30: 90 Fahrzeuge halten, 10 fahren 40 km/h. Reaktionsstrecke 11,1 m, Rest 2,2 m zum Bremsen: Aufprall mit 35 km/h
        g = d.gefaehrdung([(None, 30)] * 90 + [(None, 40)] * 10, 30)
        auf40 = d.aufprall_kmh(40, 30)
        self.assertAlmostEqual(auf40, 34.7, delta=0.1)
        self.assertEqual(g["aufprall_anteil_prozent"], 10.0)
        self.assertAlmostEqual(g["aufprall_mittel_der_aufprallenden_kmh"], auf40, delta=0.1)
        self.assertAlmostEqual(g["aufprall_mittel_kmh"], 0.1 * auf40, delta=0.1)
        self.assertEqual(g["aufprall_p95_kmh"], round(auf40, 1))  # das schnellste Zehntel liegt ueber dem P95
        self.assertEqual(g["aufprall_p99_kmh"], round(auf40, 1))

    def test_ohne_bremsung_trifft_das_fahrzeug_mit_voller_geschwindigkeit_auf(self):
        self.assertEqual(d.aufprall_kmh(60, 30), 60.0)  # Reaktionsstrecke 16,7 m ist laenger als die Anhaltestrecke 13,3 m

    def test_aufprall_perzentile_sind_geordnet(self):
        v = [(None, x) for x in range(20, 90) for _ in range(5)]
        g = d.gefaehrdung(v, 50)
        self.assertLessEqual(g["aufprall_mittel_kmh"], g["aufprall_p95_kmh"])
        self.assertLessEqual(g["aufprall_p95_kmh"], g["aufprall_p99_kmh"])
        self.assertLessEqual(g["aufprall_p99_kmh"], d.aufprall_kmh(89, 50) + 0.1)
    def test_risikoindex_waechst_mit_der_vierten_potenz(self):
        self.assertEqual(d.gefaehrdung([(None, 60)], 30)["risikoindex_nilsson"], 16.0)
        # die Haelfte mit Limit, die Haelfte mit dem doppelten Tempo: (1 + 16) / 2
        self.assertEqual(d.gefaehrdung([(None, 30), (None, 60)], 30)["risikoindex_nilsson"], 8.5)

    def test_ohne_limit_oder_fahrzeuge(self):
        self.assertIsNone(d.gefaehrdung([(None, 30)], None))
        self.assertIsNone(d.gefaehrdung([], 30))
        self.assertIsNone(d.laerm([], 30))


class Laerm(unittest.TestCase):
    def test_pegel(self):
        self.assertAlmostEqual(d.pegel_pkw_db(50), 27.7 + 10 * __import__("math").log10(2), places=6)
        self.assertGreater(d.pegel_pkw_db(100), d.pegel_pkw_db(50) + 6)

    def test_alle_fahren_das_limit(self):
        l = d.laerm([(None, 50)] * 10, 50)
        self.assertEqual((l["mittelungspegel_gegenueber_limit_db"], l["spitzenpegel_p99_gegenueber_limit_db"]), (0.0, 0.0))
        self.assertEqual(l["anteil_mind_6_db_lauter_prozent"], 0.0)

    def test_schnelle_fahrzeuge_sind_lauter(self):
        l = d.laerm([(None, 50)] * 90 + [(None, 100)] * 10, 50)
        self.assertGreater(l["mittelungspegel_gegenueber_limit_db"], 0)
        self.assertGreater(l["spitzenpegel_p99_gegenueber_limit_db"], 6)
        self.assertEqual(l["anteil_mind_6_db_lauter_prozent"], 10.0)


class NachtEreignisse(unittest.TestCase):
    def test_grenzen_und_zuordnung_zur_nacht(self):
        spannen = [(dt.datetime(2025, 1, 1, 8, 0), dt.datetime(2025, 1, 4, 8, 0))]  # Naechte: 1.->2., 2.->3., 3.->4.
        fahrten = [
            (dt.datetime(2025, 1, 1, 21, 59), 130),  # noch Abend: zaehlt nicht
            (dt.datetime(2025, 1, 1, 22, 0), 105),   # Nacht vom 1.
            (dt.datetime(2025, 1, 2, 5, 59), 105),   # gehoert noch zur Nacht vom 1.
            (dt.datetime(2025, 1, 2, 6, 0), 130),    # Morgen: zaehlt nicht
            (dt.datetime(2025, 1, 3, 2, 0), 125),    # Nacht vom 2.
            (dt.datetime(2025, 1, 3, 23, 30), 60),   # Nacht vom 3., nur ab doppeltem Limit (50)
        ]
        e = d.nacht_ereignisse(fahrten, spannen, 30)
        self.assertEqual(e["naechte"], 3)
        s = {x["ab_kmh"]: x for x in e["schwellen"]}
        self.assertEqual(sorted(s), [60, 100, 120])
        self.assertTrue(s[60]["doppeltes_tempolimit"])
        self.assertEqual((s[100]["naechte_mit_fahrt"], s[100]["fahrten_gesamt"]), (2, 3))
        self.assertEqual((s[120]["naechte_mit_fahrt"], s[120]["fahrten_gesamt"]), (1, 1))
        self.assertEqual(s[60]["naechte_mit_fahrt"], 3)
        self.assertAlmostEqual(s[100]["fahrten_je_nacht"], 1.0)

    def test_unvollstaendige_naechte_zaehlen_nicht(self):
        spannen = [(dt.datetime(2025, 1, 1, 23, 0), dt.datetime(2025, 1, 2, 3, 0))]  # nur ein Teil einer Nacht
        e = d.nacht_ereignisse([(dt.datetime(2025, 1, 2, 1, 0), 130)], spannen, 50)
        self.assertEqual(e["naechte"], 0)
        self.assertNotIn("schwellen", e)

    def test_doppeltes_limit_bei_50_faellt_mit_100_zusammen(self):
        spannen = [(dt.datetime(2025, 1, 1, 8, 0), dt.datetime(2025, 1, 3, 8, 0))]
        e = d.nacht_ereignisse([], spannen, 50)
        self.assertEqual([x["ab_kmh"] for x in e["schwellen"]], [100, 120])
        self.assertTrue(e["schwellen"][0]["doppeltes_tempolimit"])

if __name__ == "__main__":
    unittest.main()
