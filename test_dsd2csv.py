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


if __name__ == "__main__":
    unittest.main()
