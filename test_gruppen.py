# SPDX-License-Identifier: MIT
"""Tests fuer gruppen.py (Zerlegung in Gruppen, Zellen) und zwischenspeicher.py.  Aufruf: python3 -m unittest -v"""
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


def cdf(v, modus, s):
    mu = math.log(modus) + s * s
    return 0.5 * (1 + math.erf((math.log(v) - mu) / (s * math.sqrt(2))))


def mischung(komponenten, n, seed):
    """Counter aus einer Lognormal-Mischung [(Anteil, Modus, s)] mit n Fahrzeugen und Zufallsrauschen."""
    rnd = random.Random(seed)
    c = collections.Counter()
    for v in range(3, 140):
        erwartet = n * sum(w * (cdf(v + 0.5, m, s) - cdf(v - 0.5, m, s)) for w, m, s in komponenten)
        k = int(round(erwartet + rnd.gauss(0, math.sqrt(max(erwartet, 0)))))
        if k > 0:
            c[v] = k
    return c


def mischung_ab(komponenten, n, seed, ab):
    """Wie mischung(), aber nur Geschwindigkeiten ab 'ab' (links davon ist nichts erfasst)."""
    return collections.Counter({v: c for v, c in mischung(komponenten, n, seed).items() if v >= ab})

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

    def test_kennzahlen(self):
        k = g.kennzahlen({20: 50, 30: 30, 40: 20}, 30)
        self.assertEqual(k["fahrzeuge"], 100)
        self.assertEqual(k["mittel_kmh"], 27.0)
        self.assertEqual((k["v85_kmh"], k["v95_kmh"], k["v99_kmh"]), (40, 40, 40))
        self.assertEqual(k["einhaltungsquote_prozent"], 80.0)
        self.assertEqual(k["qualifizierte_einhaltungsquote_prozent"], 80.0)  # 40 - 3 = 37 > 30: bleibt Ueberschreiter
        self.assertIsNone(g.kennzahlen({}, 30))
        self.assertNotIn("einhaltungsquote_prozent", g.kennzahlen({20: 1}, None))
        k = g.kennzahlen({20: 0.5, 25: 0.5}, 30)  # gewichtete Histogramme
        self.assertEqual(k["fahrzeuge"], 1)

    def test_abschneiden_findet_den_haufen_am_rand(self):
        c = collections.Counter({3: 900, 4: 700, 5: 500, 6: 250, 7: 120, 8: 100, 9: 130, 10: 200, 11: 400, 12: 800, 13: 1200, 14: 1500, 15: 1200, 16: 800})
        self.assertEqual(g.abschneiden(c), 8)
        glatt = collections.Counter({v: 100 + 10 * v for v in range(5, 40)})
        self.assertEqual(g.abschneiden(glatt), 5)  # kein Haufen: alles zaehlt


class Zerlegung(unittest.TestCase):
    def waehlen(self, komponenten, n=60000):
        return g.waehle_k(mischung(komponenten, n, 1), mischung(komponenten, n, 2), 3)

    def test_eine_gruppe_bleibt_eine(self):
        erg = self.waehlen([(1.0, 30, 0.2)])
        self.assertEqual(erg["k"], 1)
        self.assertIsNone(erg["mischung"])

    def test_zwei_getrennte_gruppen(self):
        erg = self.waehlen([(0.25, 15, 0.18), (0.75, 40, 0.12)])
        self.assertEqual(erg["k"], 2)
        self.assertFalse(erg["obere_gruppen_ueberlappen"])
        m = g.Mischung(**erg["mischung"])
        modi = sorted(m.modus(j) for j in range(2))
        self.assertAlmostEqual(modi[0], 15, delta=1.5)
        self.assertAlmostEqual(modi[1], 40, delta=1.5)
        self.assertAlmostEqual(sorted(m.w)[0], 0.25, delta=0.03)

    def test_drei_getrennte_gruppen_und_abbruch_danach(self):
        erg = self.waehlen([(0.15, 8, 0.1), (0.25, 20, 0.12), (0.6, 45, 0.1)])
        self.assertEqual(erg["k"], 3)
        ks = [e["k"] for e in erg["auswahl"]]
        self.assertLessEqual(len(ks), 5)  # die Suche endet, bevor K_MAX erreicht ist
        for e in erg["auswahl"]:
            self.assertIn("cv_gewinn", e)

    def test_wenige_fahrzeuge_zerlegen_nicht_stabil(self):
        """Mit wenig Daten schwanken die Haelften: keine belegte Zerlegung statt einer zufaelligen."""
        erg = g.waehle_k(mischung([(1.0, 30, 0.2)], 400, 3), mischung([(1.0, 30, 0.2)], 400, 4), 3)
        self.assertEqual(erg["k"], 1)

    def test_antworten_summieren_zu_eins(self):
        m = g.Mischung([0.3, 0.7], [math.log(15) + 0.03, math.log(40) + 0.01], [0.2, 0.1])
        for v in (3, 15, 27, 40, 90, 200):
            a = m.antworten(v)
            self.assertAlmostEqual(sum(a), 1.0, places=9)
        self.assertGreater(m.antworten(14)[0], 0.9)
        self.assertGreater(m.antworten(41)[1], 0.9)

    def test_anpassung_ist_deterministisch(self):
        c = mischung([(0.3, 15, 0.18), (0.7, 40, 0.12)], 30000, 5)
        w, a = g.tabelle(c, 3)
        m1, m2 = g.anpassen(w, a, 2), g.anpassen(w, a, 2)
        self.assertEqual((m1.w, m1.mu, m1.s), (m2.w, m2.mu, m2.s))


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
        self.assertEqual(sum(sum(c.values()) for c in zd["haelften"]), n_z)
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


class Analyse(unittest.TestCase):
    def test_block_und_daten(self):
        fahrten, spannen = fahrten_und_spannen(tage=28)
        zd = g.zellen_bauen(fahrten, fahrten, spannen)
        block, daten = g.analysiere(zd, 30, True)
        self.assertTrue(block["geprueft"])
        self.assertEqual(block["anzahl"], 2)
        gr = block["gruppen"]
        self.assertEqual([x["nr"] for x in gr], [1, 2])
        self.assertLess(gr[0]["modus_kmh"], gr[1]["modus_kmh"])  # Gruppe 1 ist die langsamste
        self.assertAlmostEqual(gr[0]["anteil_prozent"] + gr[1]["anteil_prozent"], 100.0, delta=0.05)
        self.assertTrue(gr[0]["langsam"])  # Modus 16 <= 0,6 * 30 = 18
        self.assertFalse(gr[1]["langsam"])
        self.assertEqual(block["hauptmenge_ohne_langsame"]["gruppen"], [2])
        self.assertEqual(daten["langsam"], [1])
        self.assertEqual(len(daten["gruppen"]), 2)
        # Gewichte: je Geschwindigkeit liefern alle Gruppen zusammen 1
        for i in range(len(daten["gruppen"][0]["w"])):
            self.assertAlmostEqual(sum(x["w"][i] for x in daten["gruppen"]), 1.0, delta=0.002)
        # Zellen: Summe der Zaehlwerte = Fahrzeuge
        n = sum(sum(c for c in z[1::2]) for z in daten["z"].values())
        self.assertEqual(n, block["fahrzeuge"])

    def test_rauschgrenze_begrenzt_die_anpassung(self):
        fahrten, spannen = fahrten_und_spannen(tage=28)
        zd = g.zellen_bauen(fahrten, fahrten, spannen)
        block, daten = g.analysiere(zd, 30, True, rausch_obergrenze=10)
        self.assertEqual(block["angepasst_ab_kmh"], 11)
        self.assertGreater(block["fahrzeuge_unter_grenze"], 0)
        self.assertEqual(daten["rand"], 11)
        self.assertEqual(daten["w0"], 11)
        # ohne Rauschboden entscheidet die Form des unteren Rands; eine echte langsame Gruppe (Modus 16) bleibt in der Anpassung
        block, _ = g.analysiere(zd, 30, False)
        self.assertLess(block["angepasst_ab_kmh"], 14)
        self.assertEqual(block["anzahl"], 2)

    def test_abgeschnittene_gruppe_wird_aus_der_flanke_gefunden(self):
        """Die Verteilung links vom Datenrand ist nicht erfasst (nicht null): eine halb abgeschnittene Gruppe bleibt eine Gruppe."""
        wahrheit = [(0.30, 15, 0.25), (0.70, 31, 0.17)]
        c = mischung_ab(wahrheit, 60000, 1, 15)
        erg = g.waehle_k(c, mischung_ab(wahrheit, 60000, 2, 15), 15)
        self.assertEqual(erg["k"], 2)
        m = g.Mischung(**erg["mischung"])
        langsam = m.sortiert()[0]
        self.assertAlmostEqual(m.modus(langsam), 15, delta=1.0)
        self.assertAlmostEqual(m.anteile()[langsam], 0.3 * 0.67 / (0.3 * 0.67 + 0.7), delta=0.03)  # Anteil der erfassten Fahrzeuge
        self.assertGreater(m.sichtbar(langsam), 0.55)  # etwa zwei Drittel der Glocke liegen im erfassten Bereich
        # die naive Anpassung (links null) liegt weiter daneben und erfindet eine schmale Gruppe
        w, a = g.tabelle(c, 15)
        naiv = g.anpassen(w, a, 2, 4)
        j = naiv.sortiert()[0]
        self.assertLess(abs(m.modus(langsam) - 15), abs(naiv.modus(j) - 15))
        self.assertLess(naiv.s[j], 0.15)

    def test_abgeschnittene_hauptgruppe_bleibt_eine_gruppe(self):
        c1 = mischung_ab([(1.0, 31, 0.2)], 60000, 1, 25)
        c2 = mischung_ab([(1.0, 31, 0.2)], 60000, 2, 25)
        self.assertEqual(g.waehle_k(c1, c2, 25)["k"], 1)

    def test_dichte_der_erfassten_werte_ist_normiert(self):
        m = g.anpassen(*g.tabelle(mischung_ab([(0.3, 15, 0.25), (0.7, 31, 0.17)], 60000, 1, 15), 15), 2, 3, ab=15)
        self.assertAlmostEqual(sum(m.dichte(v) for v in range(15, 400)), 1.0, delta=0.03)
        self.assertAlmostEqual(sum(m.anteile()), 1.0, places=9)
        self.assertAlmostEqual(g.Mischung([1.0], [3.0], [0.2]).z(), 1.0)  # ohne Abschneidung ist alles sichtbar
    def test_zu_wenige_fahrzeuge_und_kein_limit(self):
        fahrten, spannen = fahrten_und_spannen(tage=2)
        zd = g.zellen_bauen(fahrten, fahrten, spannen)
        block, daten = g.analysiere(zd, 30, True)
        self.assertFalse(block["geprueft"])
        self.assertTrue(daten["z"])  # die Zellen fuer die Auswahl gibt es trotzdem
        fahrten, spannen = fahrten_und_spannen(tage=14)
        block, daten = g.analysiere(g.zellen_bauen(fahrten, fahrten, spannen), None, True)
        self.assertFalse(block["geprueft"])
        self.assertEqual(g.analysiere(g.zellen_bauen([], [], []), 30, True), ({"geprueft": False, "grund": "keine Fahrzeuge in vollständig aufgezeichneten Stunden mit nutzbarer Zeit"}, None))

    def test_zwischenspeicher_liefert_dasselbe(self):
        fahrten, spannen = fahrten_und_spannen(tage=28)
        zd = g.zellen_bauen(fahrten, fahrten, spannen)
        with tempfile.TemporaryDirectory() as ordner:
            s1 = zs.Zwischenspeicher(ordner)
            b1, d1 = g.analysiere(zd, 30, True, s1, "x")
            self.assertEqual(len(s1.benutzt), 1)
            s2 = zs.Zwischenspeicher(ordner)
            b2, d2 = g.analysiere(zd, 30, True, s2, "x")
            self.assertEqual((b1, d1), (b2, d2))
            s3 = zs.Zwischenspeicher(ordner)
            g.analysiere(zd, 30, True, s3, "anderer Code")  # anderer Code-Hash: neu gerechnet, neuer Eintrag
            self.assertNotEqual(s3.benutzt, s2.benutzt)


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
