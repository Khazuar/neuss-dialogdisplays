# SPDX-License-Identifier: MIT
"""Tests fuer rauschen.py (Rauschbodenschaetzer).  Aufruf: python3 -m unittest -v"""
import collections
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


def regen_mm(modulo=3, nur_ungerade_tage=False):
    """Regenfunktion der Testdaten: jeder modulo-te Tag regnet von 9 bis 14 Uhr mit 0,3 / 0,8 / 1,5 / 3,0 / 1,5 / 0,8 mm."""
    def f(datum, h):
        tag = (datum - START.date()).days
        if tag % modulo == 1 and 9 <= h <= 14 and not (nur_ungerade_tage and tag % 2 == 0):
            return (0.3, 0.8, 1.5, 3.0, 1.5, 0.8)[h - 9]
        return 0.0
    return f


STOERUNG = {8: 8, 9: 20, 10: 20, 11: 30, 12: 30, 13: 30, 14: 20, 15: 8}  # zusaetzliche langsame Datensaetze je Regenstunde


def mit_regenstoerung(fahrten, tage=40, regen=None, faktor=1.0, seed=7):
    """Fuegt zu den Fahrten in den Regenstunden langsame Datensaetze (3 bis 10 km/h) hinzu: Gibt (fahrten, Zahl) zurueck."""
    rnd = random.Random(seed)
    regen = regen or regen_mm()
    neu, n = list(fahrten), 0
    for tag in range(tage):
        datum = (START + dt.timedelta(days=tag)).date()
        for h, rate in STOERUNG.items():
            if regen(datum, h - 0) is None:
                continue
            klassen = regenklassen_der_stunde(regen, datum, h)
            if klassen == 0:
                continue
            for _ in range(poisson(rnd, rate * faktor)):
                v = min(3 + int(rnd.expovariate(0.6)), 10)
                neu.append((START + dt.timedelta(days=tag, hours=h, seconds=rnd.randrange(3600)), v))
                n += 1
    neu.sort()
    return neu, n


def regenklassen_der_stunde(regen, datum, h):
    return r.regenklassen(regen, [(datum, h)])[(datum, h)]


class Regenklassen(unittest.TestCase):
    def test_klassen_nach_intensitaet_mit_nachbarstunden(self):
        regen = regen_mm()
        tag = (START + dt.timedelta(days=1)).date()  # tag % 3 == 1: Regentag
        k = r.regenklassen(regen, [(tag, h) for h in range(24)])
        erwartet = {7: r.TROCKEN, 8: 1, 9: 2, 10: 2, 11: 3, 12: 3, 13: 3, 14: 2, 15: 1, 16: r.UNKLAR, 17: r.UNKLAR, 18: r.TROCKEN}
        for h, x in erwartet.items():
            self.assertEqual(k[(tag, h)], x, h)
        trocken_tag = (START + dt.timedelta(days=2)).date()
        self.assertEqual(r.regenklassen(regen, [(trocken_tag, 12)])[(trocken_tag, 12)], r.TROCKEN)

    def test_ohne_wert_ist_die_stunde_unklar(self):
        k = r.regenklassen(lambda d, h: None if h == 12 else 0.0, [(START.date(), 12), (START.date(), 13), (START.date(), 20)])
        self.assertEqual(k[(START.date(), 12)], r.UNKLAR)
        self.assertEqual(k[(START.date(), 13)], r.UNKLAR)  # die Vorstunde fehlt
        self.assertEqual(k[(START.date(), 20)], r.TROCKEN)

    def test_zellen_trennen_die_klassen(self):
        fahrten, spannen, _ = synthetisch(tage=10, rausch_je_stunde=0)
        klassen = r.regenklassen(regen_mm(), r.abgedeckte_stunden(spannen))
        counts, D = r.zellen(fahrten, spannen, klassen=klassen)
        self.assertEqual({k[2] for k in D}, {r.TROCKEN, 1, 2, 3, r.UNKLAR})
        self.assertEqual(sum(sum(c.values()) for c in counts.values()), len(fahrten))
        c0, d0 = r.zellen(fahrten, spannen)  # ohne Klassen: alles trocken
        self.assertEqual({k[2] for k in d0}, {r.TROCKEN})


class Regenanteil(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        basis, cls.spannen, _ = synthetisch(rausch_je_stunde=0)
        cls.fahrten, cls.echt = mit_regenstoerung(basis)
        cls.rb = r.pruefen(cls.fahrten, cls.spannen, 30, regen=regen_mm())

    def test_nur_regenstoerung_wird_gefunden_und_belegt(self):
        self.assertFalse(self.rb["belegt"])  # trockener Rauschboden: keiner
        regen = self.rb["regen"]
        self.assertTrue(regen["belegt"], regen["grund"])
        self.assertTrue(self.rb["abzug"])
        self.assertLessEqual(regen["obergrenze_kmh"], 10)
        self.assertTrue(regen["stabil"])
        z = regen["zusatz_je_klasse"]  # Datensaetze je Regenstunde: wachsen mit der Klasse (8 / 20 / 28)
        self.assertLess(z["1"], z["2"])
        self.assertLess(z["2"], z["3"] + 1)
        self.assertAlmostEqual(z["1"], 8, delta=3)
        self.assertAlmostEqual(z["3"], 30, delta=7)

    def test_abzug_entfernt_die_stoerung_und_keine_fahrzeuge(self):
        neu = r.ohne_rauschen(self.fahrten, self.rb["_modell"])
        entfernt = len(self.fahrten) - len(neu)
        self.assertAlmostEqual(entfernt, self.echt, delta=0.25 * self.echt)
        bleibt = {id(f) for f in neu}
        weg = [f for f in self.fahrten if id(f) not in bleibt]
        self.assertTrue(all(v <= 11 for _, v in weg))
        klassen = self.rb["_modell"]["klassen"]
        self.assertTrue(all(klassen[(t.date(), t.hour)] in (1, 2, 3) for t, _ in weg))  # nur in Regenstunden

    def test_abzug_trifft_die_menge_auch_bei_stark_schwankender_stoerung(self):
        """Die Stoerung ist in einer Klasse mal 0,2-fach, mal 1,8-fach: je Zelle wuerde dort gekappt und hier Rest bleiben."""
        basis, spannen, _ = synthetisch(rausch_je_stunde=0)
        rnd = random.Random(11)
        regen = regen_mm()
        neu, echt = list(basis), 0
        for tag in range(40):
            datum = (START + dt.timedelta(days=tag)).date()
            for h, rate in STOERUNG.items():
                if regenklassen_der_stunde(regen, datum, h) == 0:
                    continue
                faktor = 0.2 if rnd.random() < 0.5 else 1.8
                for _ in range(poisson(rnd, rate * faktor)):
                    neu.append((START + dt.timedelta(days=tag, hours=h, seconds=rnd.randrange(3600)), min(3 + int(rnd.expovariate(0.6)), 10)))
                    echt += 1
        neu.sort()
        rb = r.pruefen(neu, spannen, 30, regen=regen)
        self.assertTrue(rb["regen"]["belegt"], rb["regen"]["grund"])
        sauber = r.ohne_rauschen(neu, rb["_modell"])
        self.assertAlmostEqual(len(neu) - len(sauber), echt, delta=0.1 * echt)

    def test_abzug_je_v_ohne_uhrzeit_kennt_den_regen_nicht(self):
        self.assertEqual(r.ohne_rauschen_je_v(self.fahrten, self.rb["_modell"]), self.fahrten)  # kein trockener Rauschboden: nichts

    def test_ohne_wetterdaten_gibt_es_keinen_regenanteil(self):
        rb = r.pruefen(self.fahrten, self.spannen, 30)
        self.assertIsNone(rb["regen"])
        self.assertFalse(rb["abzug"])

    def test_trockener_rauschboden_wird_nicht_vom_regen_aufgeblaeht(self):
        basis, spannen, echt_trocken = synthetisch(rausch_je_stunde=4.0)
        fahrten, echt_regen = mit_regenstoerung(basis)
        wahr = 4.0 / (sum(1 for _ in range(1)) or 1)  # 4 Datensaetze je Stunde
        rb = r.pruefen(fahrten, spannen, 30, regen=regen_mm())
        self.assertTrue(rb["belegt"], rb["grund"])
        self.assertTrue(rb["regen"]["belegt"], rb["regen"]["grund"])
        summe_a = sum(rb["_modell"]["est"]["a"].values())
        self.assertAlmostEqual(summe_a, wahr, delta=0.25 * wahr)  # nur trockene Stunden: etwa 4 je Stunde
        # ohne Regenfunktion zieht der Schaetzer die Regenstoerung in a(v) hinein: deutlich mehr
        rb0 = r.pruefen(fahrten, spannen, 30)
        self.assertGreater(sum(rb0["_modell"]["est"]["a"].values()), 1.15 * summe_a)
        neu = r.ohne_rauschen(fahrten, rb["_modell"])
        self.assertAlmostEqual(len(fahrten) - len(neu), echt_trocken + echt_regen, delta=0.25 * (echt_trocken + echt_regen))

    def test_regen_nur_an_tagen_einer_haelfte_ist_nicht_stabil(self):
        basis, spannen, _ = synthetisch(rausch_je_stunde=0)
        regen = regen_mm(modulo=4)  # jeder vierte Tag: alle in einer Haelfte der Tage (gerade/ungerade)
        fahrten, _ = mit_regenstoerung(basis, regen=regen)
        rb = r.pruefen(fahrten, spannen, 30, regen=regen)
        self.assertFalse(rb["regen"]["belegt"])
        self.assertFalse(rb["regen"]["stabil"])
        self.assertIn("stabil", rb["regen"]["grund"])
        self.assertFalse(rb["abzug"])

    def test_zu_wenige_regenstunden(self):
        basis, spannen, _ = synthetisch(tage=40, rausch_je_stunde=0)
        regen = regen_mm(modulo=40)  # ein einziger Regentag
        fahrten, _ = mit_regenstoerung(basis, regen=regen)
        rb = r.pruefen(fahrten, spannen, 30, regen=regen)
        self.assertFalse(rb["regen"]["belegt"])
        self.assertFalse(rb["abzug"])

    def test_ohne_stoerung_bei_regen_nichts_nachweisbar(self):
        fahrten, spannen, _ = synthetisch(rausch_je_stunde=0)
        rb = r.pruefen(fahrten, spannen, 30, regen=regen_mm())
        self.assertFalse(rb["regen"]["belegt"])
        self.assertIn("nachweisbar", rb["regen"]["grund"])
        self.assertFalse(rb["abzug"])

    def test_klassen_mit_zu_wenigen_stunden_borgen_von_der_naechsten(self):
        ue, st = r.regen_ueberschuss(
            {"vT": 21, "ab": {}, "a": {}},
            {(0, 9, 1): collections.Counter({4: 100, 5: 100, 6: 100}), (0, 10, 3): collections.Counter({4: 100, 5: 100, 6: 100})},
            collections.Counter({(0, 9, 1): 2, (0, 10, 3): 20}))
        self.assertEqual(st[1], 2)
        self.assertEqual(ue[1], ue[2])  # beide uebernehmen die einzige Klasse mit genug Stunden (3)
        self.assertEqual(ue[2], ue[3])
        self.assertAlmostEqual(ue[3][5], 5.0)

    def test_einzelne_ausreisser_zaehlen_nicht_nur_zusammenhaengende_laeufe(self):
        k = lambda *vs: {v: (30.0, 40) for v in vs}  # noqa: E731  (Ueberschuss 30 bei 40 Datensaetzen: 4,7 Standardfehler je Wert)
        self.assertEqual(r._laeufe(k(5), 10), {})
        self.assertEqual(r._laeufe(k(5, 6), 10), {})
        self.assertEqual(sorted(r._laeufe(k(5, 6, 7, 19), 10)), [5, 6, 7])
        self.assertEqual(sorted(r._laeufe(k(5, 7, 9), 10)), [5, 7, 9])  # Luecken bis 1 km/h
        self.assertEqual(r._laeufe(k(5, 8, 11), 10), {})  # Abstand 3: kein Lauf
        self.assertEqual(r._laeufe(k(5, 6, 7), 10)[5], 3.0)  # Ueberschuss je Stunde

    def test_signifikanz_gilt_fuer_den_ganzen_lauf(self):
        # je Wert nur 1,6 Standardfehler (Ueberschuss 8 bei 25 Datensaetzen), zusammen 2,8 bei drei Werten: nicht genug (SIGMA 3) ...
        self.assertEqual(r._laeufe({5: (8.0, 25), 6: (8.0, 25), 7: (8.0, 25)}, 10), {})
        # ... mit vier Werten 3,2: genug, obwohl kein einzelner Wert den Test von 3 Sigma bestuende
        self.assertEqual(sorted(r._laeufe({5: (8.0, 25), 6: (8.0, 25), 7: (8.0, 25), 8: (8.0, 25)}, 10)), [5, 6, 7, 8])

    def test_dateien_mit_duenner_stoerung_je_geschwindigkeit_werden_gefunden(self):
        """Wenige Datensaetze je Geschwindigkeit (hier 0,3 je Stunde und km/h bei 9 bis 14 km/h), aber zusammenhaengend und ein Vielfaches."""
        rnd = random.Random(3)
        basis, spannen, _ = synthetisch(rausch_je_stunde=0, langsam_anteil=0.0)
        regen = regen_mm()
        neu, echt = list(basis), 0
        for tag in range(40):
            datum = (START + dt.timedelta(days=tag)).date()
            for h in STOERUNG:
                if regenklassen_der_stunde(regen, datum, h) == 0:
                    continue
                for v in range(9, 15):
                    for _ in range(poisson(rnd, 0.3)):
                        neu.append((START + dt.timedelta(days=tag, hours=h, seconds=rnd.randrange(3600)), v))
                        echt += 1
        neu.sort()
        rb = r.pruefen(neu, spannen, 50, regen=regen)  # Limit 50: Verkehrsschwelle 35, die Stoerung liegt weit darunter
        self.assertTrue(rb["regen"]["belegt"], rb["regen"])
        self.assertAlmostEqual(len(neu) - len(r.ohne_rauschen(neu, rb["_modell"])), echt, delta=0.3 * echt)


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
        self.assertNotIn("regen", b)  # ohne Wetterdaten kein Regenblock

    def test_regenblock(self):
        basis, spannen, _ = synthetisch(rausch_je_stunde=0)
        fahrten, _ = mit_regenstoerung(basis)
        rb = r.pruefen(fahrten, spannen, 30, regen=regen_mm())
        b = d.rauschen_block(rb, 0, len(fahrten), regen_abgezogen=1500)
        self.assertFalse(b["belegt"])  # trockener Rauschboden
        rg = b["regen"]
        self.assertTrue(rg["belegt"])
        self.assertEqual(rg["abgezogen_fahrzeuge"], 1500)
        self.assertGreater(rg["regenstunden"], 90)
        self.assertEqual(sorted(rg["stunden_je_klasse"]), ["1", "2", "3"])
        self.assertLessEqual(rg["obergrenze_kmh"], 10)
        self.assertNotIn("grund", rg)
        self.assertTrue(any(z.strip().startswith("zusatz_je_klasse:") for z in d.yaml_zeilen({"rauschen": b})))

    def test_regenfunktion_aus_der_wettertabelle(self):
        import json
        import tempfile
        tabelle = {"tage": {"2025-05-01": {"st": "x", "mm": 0.0}, "2025-05-02": {"st": "x", "mm": 1.1, "std": [0.0] * 8 + [1.1] + [0.0] * 14 + [None]}}}
        with tempfile.TemporaryDirectory() as ordner:
            pfad = os.path.join(ordner, "wetter.json")
            with open(pfad, "w", encoding="utf-8") as fh:
                json.dump(tabelle, fh)
            f = d.regenfunktion(pfad)
        self.assertEqual(f(dt.date(2025, 5, 1), 12), 0.0)  # Tag unter 0,1 mm
        self.assertEqual(f(dt.date(2025, 5, 2), 8), 1.1)
        self.assertEqual(f(dt.date(2025, 5, 2), 9), 0.0)
        self.assertIsNone(f(dt.date(2025, 5, 2), 23))  # fehlende Stunde
        self.assertIsNone(f(dt.date(2025, 5, 3), 12))  # Tag ohne Eintrag
        self.assertIsNone(d.regenfunktion(os.path.join(os.path.dirname(__file__), "gibt-es-nicht.json")))


if __name__ == "__main__":
    unittest.main()
