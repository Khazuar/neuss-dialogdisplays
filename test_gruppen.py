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


_K_MAX = g.K_MAX


def setUpModule():
    g.K_MAX = 5  # die Suche geht immer bis K_MAX (8); fuer schnelle Tests genuegt 5


def tearDownModule():
    g.K_MAX = _K_MAX


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



def modus_mischung(*komponenten):
    """Mischung aus (Anteil, haeufigstes Tempo, s); die Kurven stehen in der Reihenfolge der Angabe."""
    return g.Mischung([w for w, _, _ in komponenten], [math.log(m) + s * s for _, m, s in komponenten], [s for _, _, s in komponenten])


class Gruppenbildung(unittest.TestCase):
    def test_zusammenfassen_nach_ueberlappenden_kernbereichen(self):
        # nicht nach Tempo geordnet; Kerne in ln v: Mitte mu = ln(Modus) + s^2, Kern mu +- s
        m = modus_mischung((0.5, 33, 0.1), (0.2, 15, 0.15), (0.3, 30, 0.05))
        # 33/s 0,10 und 30/s 0,05: |Delta mu| = 0,095 <= 0,15 -> eine Gruppe; 15 liegt weit ab
        self.assertEqual(g.zusammenfassen(m), [[0], [1, 2]])  # Raenge: 15 | 30 und 33
        self.assertEqual(g.kurven_von(m, [[0], [1, 2]]), [[1], [2, 0]])  # Raenge -> Kurvennummern der Anpassung
        m2 = modus_mischung((0.5, 40, 0.1), (0.5, 20, 0.1))
        self.assertEqual(g.zusammenfassen(m2), [[0], [1]])

    def test_breite_kurve_zieht_den_huegel_in_ihren_kern(self):
        """Beide Streuungen zaehlen: Eine schmale Spitze und ein Huegel daneben bilden eine Gruppe, wenn sich ihre Kerne beruehren."""
        spitze_huegel = modus_mischung((0.6, 30, 0.10), (0.4, 34, 0.15))  # |Delta mu| = 0,12 <= 0,25
        self.assertEqual(len(g.zusammenfassen(spitze_huegel)), 1)
        getrennt = modus_mischung((0.6, 30, 0.10), (0.4, 45, 0.15))  # |Delta mu| = 0,41 > 0,25
        self.assertEqual(len(g.zusammenfassen(getrennt)), 2)
        gleich_hoch = modus_mischung((0.6, 50, 0.11), (0.4, 50, 0.22))  # dasselbe Tempo, aber stabil: eine Gruppe, nicht zwei
        self.assertEqual(g.zusammenfassen(gleich_hoch), [[0, 1]])

    def test_kleine_kurve_kommt_zur_gruppe_mit_dem_besten_kern(self):
        # 40 und 52 (je s 0,1) liegen zu weit auseinander (|Delta mu| = 0,26 > 0,2): zwei Gruppen. Die kleine Kurve bei 46 (s 0,15) liegt
        # im Kern beider (|Delta mu| 0,15 bzw. 0,11 <= 0,25) und kommt zu der mit der besseren Ueberlappung, hier 52.
        m = modus_mischung((0.5, 40, 0.1), (0.4, 52, 0.1), (0.1, 46, 0.15))
        self.assertEqual(g.zusammenfassen(m), [[0], [1, 2]])  # Raenge: 40 | 46 und 52
    def test_summe_der_kurven_einer_gruppe(self):
        m = modus_mischung((0.2, 15, 0.1), (0.3, 30, 0.05), (0.5, 33, 0.1))
        self.assertAlmostEqual(g.gruppen_anteil(m, [1, 2]), 0.8, places=9)
        mittel, streuung = g.gruppen_moment(m, [1, 2])
        self.assertAlmostEqual(mittel, 0.3 / 0.8 * m.mu[1] + 0.5 / 0.8 * m.mu[2], places=9)
        w1, w2 = 0.3 / 0.8, 0.5 / 0.8  # Varianz einer Mischung: mittlere Varianz plus Varianz der Mittel
        erwartet = w1 * m.s[1] ** 2 + w2 * m.s[2] ** 2 + w1 * w2 * (m.mu[1] - m.mu[2]) ** 2
        self.assertAlmostEqual(streuung ** 2, erwartet, places=9)
        self.assertEqual(g.gruppen_modus(m, [0]), m.modus(0))
        self.assertTrue(30 <= g.gruppen_modus(m, [1, 2]) <= 36)

    def test_ueberdeckung_und_zusammenlegen(self):
        """Eine instabile Gruppe geht in die Gruppe mit der groessten Ueberlappung auf, nicht in die mit dem naechsten Tempo."""
        # Kurve 1: breit bei 26; Kurve 0: schmal bei 10 (weit weg); Kurve 2: schmale Spitze bei 30 neben dem breiten Hintergrund
        m = modus_mischung((0.3, 10, 0.1), (0.1, 26, 0.25), (0.6, 30, 0.05))
        teile = [[0], [1], [2]]
        u_klein_gross = g.ueberdeckung(m, [1], [2])
        u_klein_weit = g.ueberdeckung(m, [1], [0])
        self.assertGreater(u_klein_gross, u_klein_weit)
        self.assertTrue(0.0 <= u_klein_weit <= u_klein_gross <= 1.0)
        self.assertEqual(g.zusammenlegen(m, teile, 1), [[0], [1, 2]])
        # die Partnerin muss nicht benachbart sein: schmale Kurve bei 20 sitzt im Hintergrund der breiten bei 24, nicht bei 40
        m2 = modus_mischung((0.05, 20, 0.1), (0.35, 24, 0.25), (0.6, 40, 0.1))
        self.assertEqual(g.zusammenlegen(m2, [[0], [1], [2]], 0), [[0, 1], [2]])
    def test_stabilitaet_gilt_fuer_die_gruppen_nicht_fuer_die_kurven(self):
        a = modus_mischung((0.3, 15, 0.1), (0.3, 30, 0.05), (0.4, 33, 0.1))
        b = modus_mischung((0.3, 15, 0.1), (0.1, 30, 0.05), (0.6, 33, 0.1))  # die beiden oberen Kurven tauschen Masse (Summe gleich)
        teile = [[0], [1, 2]]
        self.assertTrue(g.vergleichbar(a, teile, b, teile))
        self.assertFalse(g.vergleichbar(a, [[0], [1], [2]], b, [[0], [1], [2]]))  # als einzelne Gruppen waeren sie instabil
        c = modus_mischung((0.5, 15, 0.1), (0.2, 30, 0.05), (0.3, 33, 0.1))  # Masse wandert zwischen den Gruppen
        self.assertFalse(g.vergleichbar(a, teile, c, teile))
        self.assertFalse(g.vergleichbar(a, teile, b, [[0, 1, 2]]))  # andere Zahl von Gruppen


class Problemgruppen(unittest.TestCase):
    def test_kleine_gruppe_ist_ein_problem(self):
        a = modus_mischung((0.01, 8, 0.2), (0.25, 28, 0.3), (0.74, 46, 0.1))
        b = modus_mischung((0.015, 9, 0.25), (0.25, 28, 0.3), (0.735, 46, 0.1))
        teile = [[0], [1], [2]]
        self.assertEqual(g.problemgruppen(a, teile, b, teile), [0])  # nur die winzige Gruppe (unter 3 %)
        self.assertEqual(g.problemgruppen(a, [[0, 1], [2]], b, [[0, 1], [2]]), [])

    def test_instabile_gruppe_ist_ein_problem(self):
        a = modus_mischung((0.3, 15, 0.1), (0.7, 40, 0.1))
        b = modus_mischung((0.3, 22, 0.1), (0.7, 40, 0.1))  # die langsame Gruppe wandert um 38 %
        teile = [[0], [1]]
        self.assertEqual(g.problemgruppen(a, teile, b, teile), [0])
        self.assertFalse(g.gruppen_gleich(a, [0], b, [0]))
        self.assertTrue(g.gruppen_gleich(a, [1], b, [1]))

    def test_schmale_kurve_weit_vom_rand_der_erfassung(self):
        """Die Untergrenze der Streuung gilt am Tempo der Kurve, nicht am Rand der Erfassung: Ein schmaler Gipfel bei 46 km/h
        bleibt schmal, auch wenn die Erfassung bei 4 km/h beginnt."""
        c = mischung_ab([(0.2, 24, 0.4), (0.8, 46, 0.10)], 60000, 7, 4)
        w, a = g.tabelle(c, 4)
        m = g.anpassen(w, a, 2, 3, ab=4)
        oben = max(range(2), key=lambda j: m.modus(j))
        self.assertAlmostEqual(m.modus(oben), 46, delta=1.5)
        self.assertLess(m.s[oben], 0.13)
        self.assertGreaterEqual(min(m.s), g.S_MIN)

    def test_obergrenze_der_streuung_haelt_den_ausflaeufer_kurz(self):
        """Eine breite Schulter wird aus mehreren Kurven gebaut (jede mit s <= S_MAX); ihr rechter Ausflaeufer geht nicht
        weit ueber die schnelle Gruppe hinaus, die langsame Gruppe hat nicht das groesste V99."""
        c = mischung_ab([(0.3, 22, 0.45), (0.7, 50, 0.10)], 100000, 9, 10)
        w, a = g.tabelle(c, 10)
        m = g.anpassen(w, a, 4, 3, ab=10)
        self.assertLessEqual(max(m.s), g.S_MAX + 1e-9)
        # V99 der langsamsten (Summen-)Kurve gegen V99 der schnellsten Kurve
        vs = list(range(10, g.VMAX_GRUPPEN + 1))

        def v99(j):
            p = {x: m.pdf(j, x) for x in vs}
            s, kum = sum(p.values()), 0.0
            for x in vs:
                kum += p[x] / s
                if kum >= 0.99:
                    return x

        schnell = max(range(m.k), key=lambda j: m.modus(j) * m.w[j])
        langsam = min(range(m.k), key=lambda j: m.modus(j))
        self.assertLess(v99(langsam), v99(schnell) + 20)

    def test_untergrenze_der_streuung_waechst_zum_niedrigen_tempo(self):
        c = collections.Counter({5: 4000, 6: 100, 7: 100, 40: 1000, 41: 1000})  # Haufen auf einer Klasse bei 5 km/h
        w, a = g.tabelle(c, 3)
        m = g.anpassen(w, a, 2, 3, ab=3)
        for j in range(2):
            self.assertGreaterEqual(m.s[j] + 1e-9, min(g.S_KLASSE / math.exp(m.mu[j]), 0.2) if m.mu[j] > 0 else 0)
            self.assertGreaterEqual(m.s[j] + 1e-9, g.S_MIN)


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

    def test_drei_getrennte_gruppen_ohne_vorzeitigen_abbruch(self):
        erg = self.waehlen([(0.15, 8, 0.1), (0.25, 20, 0.12), (0.6, 45, 0.1)])
        self.assertEqual(erg["k"], 3)
        self.assertEqual([e["k"] for e in erg["auswahl"]], list(range(2, g.K_MAX + 1)))  # kein Abbruch: auch ein groesseres K kann besser sein
        for e in erg["auswahl"]:
            self.assertIn("cv_gewinn", e)

    def test_gewinn_gegen_die_letzte_gueltige_anpassung(self):
        """cv_gewinn eines K gilt gegenueber der letzten gueltigen Anpassung (gegen_k), nicht gegenueber K - 1."""
        erg = self.waehlen([(0.15, 8, 0.1), (0.25, 20, 0.12), (0.6, 45, 0.1)])
        basis = 1
        for e in erg["auswahl"]:
            self.assertEqual(e["gegen_k"], basis)
            if g._gueltig(e):
                basis = e["k"]
        self.assertEqual(erg["auswahl"][0]["gegen_k"], 1)

    def test_gruppen_nach_kernbereichen_sind_getrennt(self):
        """Gruppen, deren Kerne (mu +- s) sich nicht ueberlappen, haben einen Ashman-Abstand von mindestens sqrt(2); ueberlappende
        Kerne bilden eine Gruppe. Das Trennkriterium ist damit durch die Einteilung erfuellt."""
        for komponenten in ([(0.4, 30, 0.25), (0.6, 38, 0.2)], [(0.4, 28, 0.3), (0.6, 40, 0.22)], [(0.3, 15, 0.2), (0.7, 45, 0.12)]):
            m = modus_mischung(*komponenten)
            teile = g.kurven_von(m, g.zusammenfassen(m))
            if len(teile) == 2:
                du, da = g.trennschaerfen(m, teile)
                self.assertGreaterEqual(da, math.sqrt(2) - 1e-9, komponenten)
            else:
                self.assertEqual(len(teile), 1, komponenten)  # Kerne ueberlappen: eine Gruppe
        # (0,4, 30, 0,25) und (0,6, 38, 0,2): |Delta mu| = 0,21 <= 0,45, also eine Gruppe; (0,3, 15, 0,2) und (0,7, 45, 0,12): zwei
        self.assertEqual(len(g.zusammenfassen(modus_mischung((0.4, 30, 0.25), (0.6, 38, 0.2)))), 1)
        self.assertEqual(len(g.zusammenfassen(modus_mischung((0.3, 15, 0.2), (0.7, 45, 0.12)))), 2)
    def test_zu_kleine_gruppe_in_der_gesamtanpassung_wird_aufgenommen(self):
        """Eine Gruppe, die nur in der Gesamtanpassung (nicht in den Haelften) zu klein ist, bleibt nicht als eigene Gruppe stehen."""
        gesamt = modus_mischung((0.002, 70, 0.1), (0.25, 28, 0.3), (0.748, 46, 0.1))
        halb = modus_mischung((0.05, 70, 0.1), (0.25, 28, 0.3), (0.70, 46, 0.1))
        gesamt.n, halb.n = 40000, 20000
        teile = [[0], [1], [2]]
        self.assertEqual(g.kleine_gruppen((gesamt,), teile), [2])  # Rang 2 ist die schnellste Kurve: 0,2 % = 80 Fahrzeuge
        self.assertEqual(g.kleine_gruppen((halb,), teile), [])
        self.assertEqual(g.kleine_gruppen((halb, gesamt), teile), [2])

    def test_mindestgroesse_waechst_bei_kleinen_dateien(self):
        """Mindestens MIN_ANTEIL der Fahrzeuge und mindestens MIN_GRUPPE Fahrzeuge: 0,6 % von 10 000 sind zu wenig, 0,6 % von 48 000 genug."""
        m = modus_mischung((0.006, 9, 0.2), (0.994, 46, 0.1))
        teile = [[0], [1]]
        m.n = 10000
        self.assertGreater(m.mindestanteil(), 0.006)
        self.assertEqual(g.kleine_gruppen((m,), teile), [0])
        m.n = 48000
        self.assertEqual(m.mindestanteil(), g.MIN_ANTEIL)
        self.assertEqual(g.kleine_gruppen((m,), teile), [])
        m.n = None  # ohne Zahl der Fahrzeuge gilt nur der Mindestanteil
        self.assertEqual(m.mindestanteil(), g.MIN_ANTEIL)

    def test_wenige_fahrzeuge_zerlegen_nicht_stabil(self):
        """Mit wenig Daten schwanken die Haelften: keine belegte Zerlegung statt einer zufaelligen."""
        erg = g.waehle_k(mischung([(1.0, 30, 0.2)], 400, 3), mischung([(1.0, 30, 0.2)], 400, 4), 3)
        self.assertEqual(erg["k"], 1)

    def test_gruppe_aus_mehreren_kurven(self):
        """Ein schmaler Gipfel neben einer breiten Glocke gehoert zu einer Gruppe: die Teile zaehlen als Kurven einer Gruppe."""
        erg = self.waehlen([(0.2, 20, 0.15), (0.1, 29.5, 0.04), (0.7, 36, 0.12)], n=120000)
        self.assertGreaterEqual(erg["k"], 2)
        teile = erg["teile"]
        self.assertEqual(sorted(j for t in teile for j in t), list(range(erg["k"])))  # jede Kurve gehoert zu genau einer Gruppe
        m = g.Mischung(**erg["mischung"])
        self.assertAlmostEqual(g.gruppen_modus(m, teile[0]), 20, delta=3)  # teile: Kurvennummern je Gruppe, langsamste Gruppe zuerst
        self.assertAlmostEqual(sum(g.gruppen_anteil(m, t) for t in teile), 1.0, places=6)
        self.assertLessEqual(len(teile), erg["k"])

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
    def test_gruppen_nach_gewicht_nummeriert(self):
        fahrten, spannen = fahrten_und_spannen(tage=28)
        zd = g.zellen_bauen(fahrten, fahrten, spannen)
        block, daten = g.analysiere(zd, 30, True)
        anteile = [x["anteil_prozent"] for x in block["gruppen"]]
        self.assertEqual(anteile, sorted(anteile, reverse=True))
        self.assertEqual([x["nr"] for x in daten["gruppen"]], list(range(1, len(anteile) + 1)))
        self.assertEqual([x["anteil"] for x in daten["gruppen"]], anteile)  # YAML und Datentabelle in derselben Reihenfolge

    def test_rand_der_anpassung_ist_das_kleinste_gemessene_tempo(self):
        fahrten, spannen = fahrten_und_spannen(tage=28)
        zd = g.zellen_bauen(fahrten, fahrten, spannen)
        kleinste = min(v for c in zd["z"].values() for v in c)
        block, _ = g.analysiere(zd, 30, False)  # kein Rauschboden belegt: kein Abschneiden eines Haufens am Rand
        self.assertEqual(block["angepasst_ab_kmh"], max(kleinste, 1))
        self.assertEqual(block["fahrzeuge_unter_grenze"], 0)

    def test_block_und_daten(self):
        fahrten, spannen = fahrten_und_spannen(tage=28)
        zd = g.zellen_bauen(fahrten, fahrten, spannen)
        block, daten = g.analysiere(zd, 30, True)
        self.assertTrue(block["geprueft"])
        self.assertEqual(block["anzahl"], 2)
        gr = block["gruppen"]
        self.assertEqual([x["nr"] for x in gr], [1, 2])
        self.assertGreater(gr[0]["anteil_prozent"], gr[1]["anteil_prozent"])  # Gruppe 1 ist die groesste (die Hauptgruppe), nicht die langsamste
        self.assertGreater(gr[0]["modus_kmh"], gr[1]["modus_kmh"])  # in den Testdaten ist die grosse Gruppe die schnelle
        self.assertAlmostEqual(gr[0]["anteil_prozent"] + gr[1]["anteil_prozent"], 100.0, delta=0.05)  # alle Fahrzeuge sind angepasst
        for x in gr:  # keine Auszeichnung "langsam"/"Hauptmenge" mehr, keine Zuordnung von Fahrzeugen
            for schluessel in ("langsam", "zugeordnet_bis_kmh"):
                self.assertNotIn(schluessel, x)
        self.assertNotIn("hauptmenge_ohne_langsame", block)
        self.assertEqual(len(daten["gruppen"]), 2)
        for x in daten["gruppen"]:
            self.assertEqual(sorted(x), ["anteil", "kurven", "modus", "nr", "pi"])
            self.assertAlmostEqual(sum(c["c"] for c in x["kurven"]), 1.0, delta=0.001)  # Gewichte der Kurven einer Gruppe
            for c in x["kurven"]:
                self.assertEqual(sorted(c), ["c", "mu", "s"])
            self.assertNotIn("w", x)
            self.assertNotIn("bis", x)
        self.assertAlmostEqual(sum(x["pi"] for x in daten["gruppen"]), 1.0, delta=0.001)
        self.assertNotIn("langsam", daten)
        self.assertNotIn("rand", daten)
        n = sum(sum(c for c in z[1::2]) for z in daten["z"].values())  # Zellen: Summe der Zaehlwerte = Fahrzeuge
        self.assertEqual(n, block["fahrzeuge"])

    def test_gruppen_sind_kurven_und_der_rest_ist_der_unterschied(self):
        fahrten, spannen = fahrten_und_spannen(tage=28)
        zd = g.zellen_bauen(fahrten, fahrten, spannen)
        block, daten = g.analysiere(zd, 30, True)
        gesamt = collections.Counter()
        for c in zd["z"].values():
            gesamt.update(c)
        # die Kurven der Gruppen aus den Parametern der Datentabelle nachrechnen (wie site/filter.js)
        w0 = daten["w0"]
        kurven = []
        for x in daten["gruppen"]:
            h = collections.Counter()
            for c in x["kurven"]:  # die Gruppe ist die gewichtete Summe ihrer Kurven
                p = {v: math.exp(-0.5 * ((math.log(v) - c["mu"]) / c["s"]) ** 2) / (c["s"] * v) for v in range(w0, g.VMAX_GRUPPEN + 1)}
                s = sum(p.values())
                for v, q in p.items():
                    h[v] += block["fahrzeuge"] * x["pi"] * c["c"] * q / s
            kurven.append(h)
        for x, h in zip(block["gruppen"], kurven):  # YAML und Datentabelle beschreiben dieselben Kurven
            self.assertAlmostEqual(100 * sum(h.values()) / block["fahrzeuge"], x["anteil_prozent"], delta=0.05)
            self.assertAlmostEqual(g.kennzahlen(h, 30)["mittel_kmh"], x["mittel_kmh"], delta=0.02)
        rest = {v: max(0.0, gesamt.get(v, 0) - sum(h.get(v, 0.0) for h in kurven)) for v in set(gesamt)}
        rest = {v: c for v, c in rest.items() if c > 0}
        for v, c in gesamt.items():  # Kurven plus Rest decken die Daten ab
            self.assertGreaterEqual(sum(h.get(v, 0.0) for h in kurven) + rest.get(v, 0.0) + 1e-6, c)
        self.assertAlmostEqual(block["rest"]["anteil_prozent"], 100 * sum(rest.values()) / block["fahrzeuge"], delta=0.05)
        self.assertLess(block["rest"]["anteil_prozent"], 8.0)  # lognormale Testdaten: wenig bleibt uebrig
        self.assertLess(block["modellabweichung_prozent"], 8.0)

    def test_schlecht_passende_daten_haben_einen_grossen_rest(self):
        c = collections.Counter()
        for v in range(10, 60):  # flaches Plateau: keine Glocke
            c[v] = 400
        for v in range(30, 40):
            c[v] += 1200  # dazu ein Gipfel
        zd = {"haelften": (collections.Counter({v: n // 2 for v, n in c.items()}), collections.Counter({v: n - n // 2 for v, n in c.items()})),
              "D": collections.Counter({(0, 8): 1}), "z": {(0, 8): c}, "r": {}}
        block, daten = g.analysiere(zd, 30, True)
        if block.get("anzahl", 1) > 1:
            self.assertGreater(block["rest"]["anteil_prozent"], 2.0)
            self.assertGreater(block["modellabweichung_prozent"], 2.0)
    def test_rauschgrenze_begrenzt_die_anpassung(self):
        fahrten, spannen = fahrten_und_spannen(tage=28)
        zd = g.zellen_bauen(fahrten, fahrten, spannen)
        block, daten = g.analysiere(zd, 30, True, rausch_obergrenze=10)
        self.assertEqual(block["angepasst_ab_kmh"], 11)
        self.assertGreater(block["fahrzeuge_unter_grenze"], 0)
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
