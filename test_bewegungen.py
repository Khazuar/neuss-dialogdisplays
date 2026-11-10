# SPDX-License-Identifier: MIT
"""Tests fuer bewegungen.py und uhr_rekonstruktion.py an synthetischen Datenstroemen.  Aufruf: python3 -m unittest -v"""
import datetime as dt
import math
import random
import unittest

import bewegungen as B
import dsd2csv
import uhr_rekonstruktion as U

BASIS = dt.date(2024, 1, 15)  # Montag; bis Mitte Maerz keine Ferien und Feiertage in NRW
TAG = dt.timedelta(days=1)


def tag(i):
    return BASIS + i * TAG


def standort(mittel, spitze, menge=120.0, sd=6.0):
    """Verkehr eines Standorts: mittleres Tempo, Stunde der Spitze, Fahrzeuge je Stunde in der Spitze."""
    return {"mittel": mittel, "spitze": spitze, "menge": menge, "sd": sd}


def verkehr(von, bis, profil, rnd):
    """Fahrzeuge [(Ortszeit, v)] zwischen den Zeitpunkten von und bis."""
    out = []
    d = von.date()
    while d <= bis.date():
        for h in range(24):
            faktor = 0.3 + 0.7 * math.exp(-((h - profil["spitze"]) / 3.0) ** 2) * (0.6 if d.weekday() >= 5 else 1.0)
            lam = profil["menge"] * faktor
            for _ in range(max(0, int(round(rnd.gauss(lam, math.sqrt(lam)))))):
                t = dt.datetime(d.year, d.month, d.day, h) + dt.timedelta(seconds=rnd.randrange(3600))
                if von <= t <= bis:
                    out.append((t, max(5, int(round(rnd.gauss(profil["mittel"], profil["sd"]))))))
        d += TAG
    return sorted(out)


A, Bo, C = standort(45, 8), standort(30, 17, menge=90), standort(38, 12, sd=8)


def geraet(abschnitte, dateien, rnd=None):
    """Synthetischer Gesamtstrom: abschnitte = [(von, bis, Profil, Datei-Index)] (datetime), dateien = [Messungs-ID]."""
    rnd = rnd or random.Random(7)
    s = []
    for von, bis, profil, i in abschnitte:
        s += [(t, v, i) for t, v in verkehr(von, bis, profil, rnd)]
    s.sort()
    return {"geraet": "G", "dateien": [{"id": d, "rel": d, "datei": d + ".dsd", "limit": 50} for d in dateien], "s": s,
            "spannen": [(von, bis) for von, bis, _p, _i in abschnitte], "rekon": []}


def um(i, h, m=0):
    return dt.datetime.combine(tag(i), dt.time(h, m))


class Bewegungen(unittest.TestCase):
    def test_umhaengen_mit_transportluecke(self):
        """Gerät hängt 30 Tage bei A, wird an einem Mittwoch 10:00 bis 10:45 umgehängt und hängt dann 30 Tage bei B."""
        x = geraet([(um(0, 0), um(30, 10), A, 0), (um(30, 10, 45), um(60, 23, 59), Bo, 0)], ["m-a"])
        B.erkennen([x])
        trennend = [k for k in x["kandidaten"] if k["stufe"] in B.TRENNEN]
        self.assertEqual(len(trennend), 1, x["kandidaten"])
        k = trennend[0]
        self.assertEqual(k["stufe"], "umhaengen")
        self.assertGreaterEqual(k["z"], B.Z_STARK)
        self.assertTrue(k["tagesprobe"]["stimmig"])
        self.assertLessEqual(abs((k["von"] - um(30, 10)).total_seconds()), 15 * 60)
        self.assertLessEqual(abs((k["bis"] - um(30, 10, 45)).total_seconds()), 15 * 60)
        auf = B.aufenthalte(x, {0: 50})
        self.assertEqual(len(auf), 2)
        self.assertEqual(auf[1]["beginn"]["stufe"], "umhaengen")
        self.assertEqual(auf[0]["ende"]["stufe"], "umhaengen")
        self.assertEqual(sum(a["fahrzeuge"] for a in auf), len(x["s"]))  # jedes Fahrzeug in genau einem Aufenthalt
        self.assertEqual(auf[0]["brueche"], [])  # die Bruchsuche findet im Aufenthalt keinen Ortswechsel mehr

    def test_pause_ohne_aenderung_trennt_nicht(self):
        """Drei Tage aus (Akku?), danach derselbe Verkehr: pause_gleicher_ort, ein Aufenthalt."""
        x = geraet([(um(0, 0), um(30, 9), A, 0), (um(33, 11), um(60, 23, 59), A, 0)], ["m-a"])
        B.erkennen([x])
        self.assertEqual([k["stufe"] for k in x["kandidaten"] if k["art"] == "pause" and k["stunden"] > B.PAUSE_LANG_H], ["pause_gleicher_ort"])
        self.assertEqual(len(B.aufenthalte(x, {0: 50})), 1)

    def test_stunden_und_teile(self):
        x = geraet([(um(0, 0), um(30, 10), A, 0), (um(30, 10, 45), um(60, 23, 59), Bo, 1)], ["m-a", "m-b"])
        B.erkennen([x])
        auf = B.aufenthalte(x, {0: 50, 1: 50})
        a = auf[1]
        self.assertEqual(sum(sum(z[4][1::2]) for z in a["zeilen"]), a["fahrzeuge"])
        # die Stunde des Umhaengens ist nicht vollstaendig aufgezeichnet
        self.assertEqual([z[3] for z in a["zeilen"] if z[0] == tag(30).isoformat() and z[1] == 10], [0])
        self.assertEqual(list(a["dateien"]), ["m-b"])
        self.assertEqual(a["teile"][0]["dateien"]["m-b"]["fahrzeuge"], a["fahrzeuge"])
        self.assertGreater(a["teile"][0]["merkmal"]["fz_h"], 0)

    def test_gesamtstrom_mit_rekonstruierter_uhr(self):
        """Gueltiges Segment, dann eines mit zurueckgesetzter Uhr; mit Entscheidung kommt es mit Geraetezeit + Delta in den Strom."""
        t0 = dt.datetime(2024, 1, 15, 8)
        werk = dsd2csv.WERKSDATUM
        veh = [(t0 + dt.timedelta(minutes=i), 40) for i in range(300)] + [(werk + dt.timedelta(minutes=i), 30) for i in range(300)]
        segs = [{"idx": list(range(300)), "bewertung": "gueltig", "ortszeit": [t for t, _ in veh[:300]]},
                {"idx": list(range(300, 600)), "bewertung": "werksdatum"}]
        delta = dt.datetime(2024, 1, 20, 9) - werk  # UTC
        fz, spannen, rekon = B.fahrzeuge_der_datei("r", "d.dsd", veh, segs, {}, dt.datetime(2030, 1, 1))
        self.assertEqual(len(fz), 300)  # ohne Entscheidung nur der gueltige Teil
        fz, spannen, rekon = B.fahrzeuge_der_datei("r", "d.dsd", veh, segs, {("r", "d.dsd", 1): (delta, "belegt")}, dt.datetime(2030, 1, 1))
        self.assertEqual(len(fz), 600)
        self.assertEqual(rekon[0][0], dt.datetime(2024, 1, 20, 10))  # 9 Uhr UTC = 10 Uhr Ortszeit (Winter)
        self.assertEqual(len(spannen), 2)
        # doppelte Fahrzeuge aus zwei Dateien zaehlen einmal
        s, _sp, _rk = B.strom([{"rel": "r", "datei": "d.dsd"}, {"rel": "r2", "datei": "d.dsd"}],
                              {("r", "d.dsd"): (veh[:300], segs[:1]), ("r2", "d.dsd"): (veh[:300], segs[:1])}, {}, dt.datetime(2030, 1, 1))
        self.assertEqual(len(s), 300)


class Rekonstruktion(unittest.TestCase):
    def test_lage_aus_ankern(self):
        """Ein Abschnitt mit zurueckgesetzter Uhr zwischen Abbau (gueltiger Teil derselben Datei) und naechster Aufzeichnung: belegt durch
        'Beginn an Montagetag' und 'Ende an naechster Aufzeichnung'."""
        rnd = random.Random(3)
        montage = dt.datetime(2024, 1, 17, 10)  # Ortszeit = UTC + 1
        ende = dt.datetime(2024, 2, 21, 15)
        echt = verkehr(montage, ende, A, rnd)
        vorlage = U.wochenvektor_normal([t for t, _ in echt])
        referenz = dsd2csv.tagesgang([t for t, _ in echt])[0]
        delta = (montage - dt.timedelta(hours=1)) - dsd2csv.WERKSDATUM
        geraetezeit = [t - dt.timedelta(hours=1) - delta for t, _ in echt]
        werk = {"rel": "r", "datei": "d.dsd", "nr": 1, "erster_index": 100, "n": len(echt), "bewertung": "werksdatum",
                "geraet_von": min(geraetezeit), "geraet_bis": max(geraetezeit), "zeiten": geraetezeit}
        vorher = {"rel": "r", "datei": "d.dsd", "nr": 0, "erster_index": 0, "n": 100, "bewertung": "gueltig",
                  "utc_von": dt.datetime(2023, 12, 1), "utc_bis": dt.datetime(2024, 1, 16, 9)}
        naechste_utc = max(echt)[0] - dt.timedelta(hours=1) + dt.timedelta(minutes=20)
        nachher = {"rel": "r2", "datei": "e.dsd", "nr": 0, "erster_index": 0, "n": 100, "bewertung": "gueltig",
                   "utc_von": naechste_utc, "utc_bis": naechste_utc + 30 * TAG}
        erg = U.rekonstruieren({"G": [vorher, werk, nachher]}, vorlage, referenz, {montage.date()})
        e = next(e for e in erg if e["abschnitt"] == 1)
        self.assertEqual(e["stufe"], "belegt", e)
        self.assertIn("Beginn an Montagetag", e["anker"])
        self.assertIn("Ende an nächster Aufzeichnung", e["anker"])
        self.assertLessEqual(abs(e["delta_s"] - delta.total_seconds()), 3 * 3600)

    def test_kurze_abschnitte_bleiben_draussen(self):
        werk = {"rel": "r", "datei": "d.dsd", "nr": 0, "erster_index": 0, "n": 50, "bewertung": "werksdatum",
                "geraet_von": dsd2csv.WERKSDATUM, "geraet_bis": dsd2csv.WERKSDATUM + dt.timedelta(hours=20), "zeiten": []}
        erg = U.rekonstruieren({"G": [werk]}, [1] * 7, [1] * 96, set())
        self.assertEqual(erg[0]["stufe"], "nicht_rekonstruiert")

    def test_dateidatum(self):
        self.assertEqual(U.dateidatum("23_05_04_Cyriakusstraße.dsd"), dt.date(2023, 5, 4))
        self.assertEqual(U.dateidatum("2023_07_19_x.dsd"), dt.date(2023, 7, 19))
        self.assertIsNone(U.dateidatum("_7.dsd"))


if __name__ == "__main__":
    unittest.main()
