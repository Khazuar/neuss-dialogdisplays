# SPDX-License-Identifier: MIT
"""Tests fuer standorte.py (Koordinaten und Unsicherheit der Messstellen).  Aufruf: python3 -m unittest -v"""
import json
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import standorte as s  # noqa: E402

HIER = os.path.dirname(os.path.abspath(__file__))


def haus(strasse, nr, ost, nord, zusatz=""):
    return s.Adresse("00001", strasse, nr, zusatz, float(ost), float(nord))


def verzeichnis():
    """Teststrasse von Sueden nach Norden bei Ost 1000 (ungerade Nummern westlich, gerade oestlich, alle 10 m je Nummer),
    Querstrasse nach Osten bei Nord 200, Nebenstrasse weit weg."""
    adr = []
    for i in range(1, 41):
        adr.append(haus("Teststraße", i, 990 if i % 2 else 1010, 10 * i))
    adr.append(haus("Teststraße", 13, 985, 135, "a"))
    for i in range(1, 29):
        adr.append(haus("Querstraße", i, 1030 + 10 * i, 190 if i % 2 else 210))
    for i in range(1, 9):
        adr.append(haus("Fernweg", i, 5000 + 15 * i, 5000))
    return s.Verzeichnis(adr)


class Koordinaten(unittest.TestCase):
    def test_bekannte_punkte(self):
        # auf dem Mittelmeridian ist Ost = 500000; 45° Nord liegen bei 0,9996 mal der Meridianbogenlaenge
        o, n = s.wgs84_zu_utm32(0.0, 9.0)
        self.assertAlmostEqual(o, 500000.0, 3)
        self.assertAlmostEqual(n, 0.0, 3)
        o, n = s.wgs84_zu_utm32(45.0, 9.0)
        self.assertAlmostEqual(o, 500000.0, 3)
        self.assertAlmostEqual(n, 4982950.40, 1)

    def test_hin_und_zurueck(self):
        for lat, lon in ((51.2042, 6.6879), (50.9413, 6.9583), (54.0, 10.5)):
            b, l_ = s.utm32_zu_wgs84(*s.wgs84_zu_utm32(lat, lon))
            self.assertAlmostEqual(b, lat, 7)
            self.assertAlmostEqual(l_, lon, 7)

    def test_neuss(self):
        b, l_ = s.utm32_zu_wgs84(338483.43, 5675073.65)
        self.assertAlmostEqual(b, 51.2042, 4)
        self.assertAlmostEqual(l_, 6.6879, 4)


class Verzeichnis(unittest.TestCase):
    def test_schreibweise_egal(self):
        v = verzeichnis()
        for name in ("Teststraße", "Teststrasse", "teststr.", "Test straße"):
            self.assertEqual(len(v.strasse(name)[0]), 41, name)

    def test_ein_buchstabe_abweichung_nur_bei_langen_namen_und_einem_treffer(self):
        v = s.Verzeichnis([haus("Eichendorffstraße", 1, 0, 0), haus("Eichendorffstraße", 2, 10, 0)])
        adr, name, abw = v.strasse("Eichendorfstraße")
        self.assertEqual(name, "Eichendorffstraße")
        self.assertIn("Buchstaben", abw)
        self.assertEqual(v.strasse("Eichendorfstrasse xyz")[0], [])
        kurz = s.Verzeichnis([haus("Am Hag", 1, 0, 0)])
        self.assertEqual(kurz.strasse("Am Hang")[0], [])

    def test_abschnitte(self):
        a = [haus("X", i, 10 * i, 0) for i in range(5)] + [haus("X", 9, 5000, 0)]
        g = s.abschnitte(a, 400)
        self.assertEqual([len(x) for x in g], [5, 1])


class Hinweise(unittest.TestCase):
    def setUp(self):
        self.v = verzeichnis()

    def test_adresse(self):
        e, _ = s.bewerte_adresse({"strasse": "Teststraße", "nr": "20"}, self.v)
        self.assertEqual((e["ost"], e["nord"]), (1010.0, 200.0))
        self.assertEqual(e["radius_m"], s.ANNAHMEN["adresse_m"])

    def test_gegenueber_ist_unsicherer(self):
        a, _ = s.bewerte_adresse({"strasse": "Teststraße", "nr": "20", "rolle": "hoehe"}, self.v)
        g, _ = s.bewerte_adresse({"strasse": "Teststraße", "nr": "20", "rolle": "gegenueber"}, self.v)
        self.assertEqual(g["radius_m"] - a["radius_m"], s.ANNAHMEN["gegenueber_zuschlag_m"])

    def test_zusatzbuchstabe(self):
        e, _ = s.bewerte_adresse({"strasse": "Teststraße", "nr": "13a"}, self.v)
        self.assertEqual((e["ost"], e["nord"]), (985.0, 135.0))

    def test_bereich_von_nummern(self):
        e, _ = s.bewerte_adresse({"strasse": "Teststraße", "nr": "20", "bis": "22"}, self.v)
        self.assertAlmostEqual(e["nord"], 210.0)
        self.assertGreater(e["radius_m"], s.ANNAHMEN["adresse_m"])
        self.assertIn("20–22", e["beschreibung"])

    def test_fehlende_nummer_nimmt_die_nachbarn(self):
        v = s.Verzeichnis([haus("Weg", 1, 0, 0), haus("Weg", 5, 0, 100), haus("Weg", 9, 0, 200)])
        e, _ = s.bewerte_adresse({"strasse": "Weg", "nr": "3"}, v)
        self.assertAlmostEqual(e["nord"], 50.0)
        # 30 m Grundwert + halber Abstand der Nachbarn (Mitte der beiden) + halber Abstand fuer die fehlende Nummer
        self.assertEqual(e["radius_m"], 30 + 50 + 50)
        self.assertIn("fehlt", e["beschreibung"])

    def test_unbekannte_strasse_und_nummer(self):
        e, grund = s.bewerte_adresse({"strasse": "Nirgendwo", "nr": "1"}, self.v)
        self.assertIsNone(e)
        self.assertIn("nicht im Adressverzeichnis", grund)
        e, grund = s.bewerte_adresse({"strasse": "Fernweg", "nr": "1"}, self.v)
        self.assertIsNotNone(e)

    def test_gleiche_nummer_in_getrennten_abschnitten_ist_mehrdeutig(self):
        v = s.Verzeichnis([haus("Dorfstraße", 5, 0, 0), haus("Dorfstraße", 5, 3000, 0), haus("Dorfstraße", 6, 10, 0)])
        e, _ = s.bewerte_adresse({"strasse": "Dorfstraße", "nr": "5"}, v)
        self.assertTrue(e["mehrdeutig"])
        self.assertGreater(e["radius_m"], 1000)

    def test_kreuzung(self):
        e, _ = s.bewerte_kreuzung({"strasse": "Teststraße", "quer": "Querstraße"}, self.v)
        self.assertLess(abs(e["nord"] - 200), 20)  # die Mitte des naechsten Haeuserpaars liegt bis zu einem Haus neben der Kreuzung
        self.assertLess(abs(e["ost"] - 1020), 15)
        self.assertGreaterEqual(e["radius_m"], s.ANNAHMEN["kreuzung_m"])

    def test_querstrasse_muss_anschliessen(self):
        e, grund = s.bewerte_kreuzung({"strasse": "Teststraße", "quer": "Fernweg"}, self.v)
        self.assertIsNone(e)
        self.assertIn("beginnt nicht an dieser Straße", grund)

    def test_zwischen_nummern(self):
        e, _ = s.bewerte_zwischen_nr({"strasse": "Teststraße", "von": 20, "bis": 30}, self.v)
        self.assertAlmostEqual(e["nord"], 250.0, delta=10)
        self.assertEqual(e["radius_m"], round(s.ANNAHMEN["zwischen_nr_m"] + 50))

    def test_zwischen_strassen(self):
        alt = verzeichnis().je_name
        v = s.Verzeichnis(list(alt["teststrasse"]) + list(alt["querstrasse"]) + [haus("Südweg", i, 1030 + 10 * i, 20 + (i % 2) * 20) for i in range(1, 6)])
        e, _ = s.bewerte_zwischen_strassen({"strasse": "Teststraße", "a": "Südweg", "b": "Querstraße"}, v)
        self.assertTrue(80 < e["nord"] < 140)
        self.assertGreater(e["radius_m"], s.ANNAHMEN["zwischen_strassen_m"])

    def test_strasse(self):
        e, _ = s.bewerte_strasse({"strasse": "Teststraße"}, self.v)
        self.assertTrue(150 < e["nord"] < 260)
        self.assertGreaterEqual(e["radius_m"], 150)
        self.assertEqual(e["abschnitte"], 1)
        self.assertEqual(len(e["punkte"]), 41)

    def test_kurze_strasse_hat_mindestradius(self):
        v = s.Verzeichnis([haus("Stich", 1, 0, 0), haus("Stich", 2, 10, 0)])
        e, _ = s.bewerte_strasse({"strasse": "Stich"}, v)
        self.assertGreaterEqual(e["radius_m"], 60)


class Namen(unittest.TestCase):
    def setUp(self):
        self.v = verzeichnis()

    def arten(self, text):
        h, unbekannt = s.hinweise_aus_text(text, self.v)
        return [(x["art"], x.get("nr"), x.get("bis"), x.get("rolle"), x.get("quer")) for x in h], unbekannt

    def test_hausnummer_mit_buchstabe(self):
        self.assertEqual(self.arten("Hauptstraße 13a")[0], [("adresse", "13a", None, "hoehe", None), ("strasse", None, None, None, None)])

    def test_nummernbereich(self):
        self.assertEqual(self.arten("Cyriakusstraße 86-88")[0][0], ("adresse", "86", "88", "hoehe", None))

    def test_gegenueber(self):
        h, _ = self.arten("Bauerbahn, ggü. Nr. 3")
        self.assertEqual(h[0], ("adresse", "3", None, "gegenueber", None))

    def test_ecke_und_hoehe(self):
        self.assertEqual(self.arten("Krokusstraße (Ecke Tulpenstraße)")[0][0], ("kreuzung", None, None, None, "Tulpenstraße"))
        self.assertEqual(self.arten("Kreitzweg (Höhe Ludgerusring)")[0][0], ("kreuzung", None, None, None, "Ludgerusring"))

    def test_zwischen(self):
        h, _ = s.hinweise_aus_text("Holzheimer Weg (zwischen Bergheimer Straße und Am Krausenbaum)", self.v)
        self.assertEqual((h[0]["art"], h[0]["a"], h[0]["b"]), ("zwischen_strassen", "Bergheimer Straße", "Am Krausenbaum"))

    def test_bekannte_querstrasse_in_klammern_ist_eine_kreuzung(self):
        h, unbekannt = s.hinweise_aus_text("Teststraße (Querstraße)", self.v)
        self.assertEqual(h[0]["art"], "kreuzung")
        self.assertEqual(unbekannt, [])

    def test_fahrtrichtung_und_messart_sind_keine_unbekannten(self):
        _, unbekannt = s.hinweise_aus_text("Teststraße, FR Kaarst (beidseitige Messung, Tempo 50)", self.v)
        self.assertEqual(unbekannt, [])
        _, unbekannt = s.hinweise_aus_text("Pomona (Eingang)", self.v)
        self.assertEqual(unbekannt, ["Eingang"])

    def test_ordnername_ohne_nummer_und_jahr(self):
        h, _ = s.hinweise_aus_ordner("07_2024_ Teststraße", self.v)
        self.assertEqual(h[-1]["strasse"], "Teststraße")
        h, _ = s.hinweise_aus_ordner("Stationär_Teststraße/FR Norf", self.v)
        self.assertEqual(h[-1]["strasse"], "Teststraße")
        self.assertEqual(h[-1]["quelle"]["typ"], "ordnername")

    def test_zwei_strassen_im_ordnernamen_sind_eine_kreuzung(self):
        h, _ = s.hinweise_aus_ordner("07_Test_Querstraße", self.v)
        self.assertEqual((h[0]["art"], h[0]["strasse"], h[0]["quer"]), ("kreuzung", "Teststraße", "Querstraße"))


class Entscheidung(unittest.TestCase):
    def setUp(self):
        self.v = verzeichnis()

    def test_nur_strasse(self):
        e = s.bestimme("05_Teststraße", self.v)
        self.assertEqual((e["methode"], e["sicherheit"]), ("strasse", "benannt"))
        self.assertAlmostEqual(e["utm32_ost"], 1000, delta=15)
        self.assertGreater(e["unsicherheit_m"], 100)
        self.assertEqual(e["belege"][0]["quelle"], {"typ": "ordnername", "name": "05_Teststraße"})

    def test_kleinster_kreis_gewinnt_und_die_strasse_widerspricht_nicht(self):
        e = s.bestimme("03_2024_Teststraße 20", self.v)
        self.assertEqual(e["methode"], "adresse")
        self.assertEqual(e["unsicherheit_m"], s.ANNAHMEN["adresse_m"])
        strasse = [b for b in e["belege"] if b["art"] == "strasse"][0]
        self.assertFalse(strasse["widerspricht"])
        self.assertFalse(strasse["verwendet"])

    def test_gleicher_hinweis_aus_name_und_mitteilung_zaehlt_einmal(self):
        e = s.bestimme("05_Teststraße", self.v, texte=["Teststraße"])
        self.assertEqual(len(e["belege"]), 1)

    def test_vorschlag_im_bereich_der_strasse_wird_vermutet(self):
        h = [{"art": "adresse", "strasse": "Teststraße", "nr": "30", "stufe": "vorschlag", "text": "Höhe Nr. 30",
              "quelle": {"typ": "ris"}}]
        e = s.bestimme("05_Teststraße", self.v, h)
        self.assertEqual((e["methode"], e["sicherheit"]), ("adresse", "vermutet"))
        self.assertEqual(e["unsicherheit_m"], s.ANNAHMEN["vorschlag_min_m"])
        self.assertEqual(e["utm32_nord"], 300)
        self.assertTrue([b for b in e["belege"] if b["stufe"] == "vorschlag"][0]["verwendet"])

    def test_manuelle_korrektur_geht_vor(self):
        h = [{"art": "adresse", "strasse": "Teststraße", "nr": "30", "stufe": "manuell", "text": "von Hand", "quelle": {"typ": "manuell"}},
             {"art": "adresse", "strasse": "Teststraße", "nr": "10", "stufe": "benannt", "text": "x", "quelle": {"typ": "ris"}},
             {"art": "adresse", "strasse": "Teststraße", "nr": "12", "stufe": "vorschlag", "text": "y", "quelle": {"typ": "ris"}}]
        e = s.bestimme("05_Teststraße", self.v, h)
        self.assertEqual(e["sicherheit"], "manuell korrigiert")
        self.assertEqual(e["utm32_nord"], 300)
        self.assertEqual(e["unsicherheit_m"], s.ANNAHMEN["adresse_m"])
        self.assertEqual([b["verwendet"] for b in e["belege"] if b["stufe"] == "manuell"], [True])

    def test_vorschlag_ausserhalb_wird_ignoriert(self):
        h = [{"art": "adresse", "strasse": "Fernweg", "nr": "3", "stufe": "vorschlag", "text": "x", "quelle": {"typ": "ris"}}]
        e = s.bestimme("05_Teststraße", self.v, h)
        self.assertEqual((e["methode"], e["sicherheit"]), ("strasse", "benannt"))
        self.assertTrue([b for b in e["belege"] if b["stufe"] == "vorschlag"][0]["widerspricht"])

    def test_vorschlag_ohne_belegte_angabe_bleibt_vermutet(self):
        h = [{"art": "adresse", "strasse": "Fernweg", "nr": "3", "stufe": "vorschlag", "text": "x", "quelle": {"typ": "ris"}}]
        v = s.Verzeichnis(list(self.v.je_name["fernweg"]))
        self.assertIsNone(s.bestimme("00_Ohneweg", v, []))
        e = s.bestimme("00_Fernweg", v, h)
        self.assertEqual(e["methode"], "adresse")

    def test_gleichrangige_widersprechende_angaben_ergeben_einen_gemeinsamen_kreis(self):
        v = s.Verzeichnis([haus("Nordweg", i, 100 + 10 * i, 0) for i in range(1, 6)] + [haus("Südweg", i, 100 + 10 * i, 1000) for i in range(1, 6)])
        e = s.bestimme("07_Nordweg", v, texte=["Südweg"])
        self.assertEqual(e["sicherheit"], "widersprüchlich")
        self.assertGreater(e["unsicherheit_m"], 500)
        self.assertAlmostEqual(e["utm32_nord"], 500, delta=5)
        self.assertEqual(sum(1 for b in e["belege"] if b["verwendet"]), 2)

    def test_fahrtrichtung_zeigt_zur_querstrasse(self):
        e = s.bestimme("08_Teststraße", self.v, fahrtrichtungen=["Querstraße"], texte=[])
        # Standort liegt in der Strassenmitte (Nord ~200), die Querstrasse bei Nord 200 -> Ziel zu nah, keine Peilung
        v = s.Verzeichnis(list(self.v.je_name["teststrasse"]) + [haus("Nordstraße", i, 985 + 10 * (i % 2) * 2, 450 + 10 * i) for i in range(1, 8)])
        e = s.bestimme("08_Teststraße", v, fahrtrichtungen=["Nordstraße"])
        self.assertIn("fahrtrichtung", e)
        self.assertLess(min(e["fahrtrichtung"]["peilung_grad"], 360 - e["fahrtrichtung"]["peilung_grad"]), 25)  # nach Norden
        sued = s.Verzeichnis(list(self.v.je_name["teststrasse"]) + [haus("Südstraße", i, 985 + 10 * (i % 2) * 2, -50 - 10 * i) for i in range(1, 8)])
        e = s.bestimme("08_Teststraße", sued, fahrtrichtungen=["Südstraße"])
        self.assertLess(abs(e["fahrtrichtung"]["peilung_grad"] - 180), 25)

    def test_beidseitige_messung_hat_keine_peilung(self):
        v = s.Verzeichnis(list(self.v.je_name["teststrasse"]) + [haus("Nordstraße", i, 985 + 10 * (i % 2) * 2, 450 + 10 * i) for i in range(1, 8)])
        e = s.bestimme("08_Teststraße", v, fahrtrichtungen=["Nordstraße"], texte=["Teststraße, FR Nordstraße (beidseitige Messung)"])
        self.assertNotIn("fahrtrichtung", e)
        self.assertTrue(e["beidseitige_messung"])

    def test_keine_strasse_im_verzeichnis(self):
        self.assertIsNone(s.bestimme("01_Gibtesnicht", self.v))

    def test_unbekannte_teile_und_verworfene_hinweise_stehen_im_ergebnis(self):
        e = s.bestimme("88_Teststraße (Eingang)", self.v, [{"art": "kreuzung", "strasse": "Teststraße", "quer": "Fernweg", "stufe": "benannt",
                                                           "text": "Fernweg", "quelle": {"typ": "x"}}])
        self.assertEqual(e["nicht_auswertbar"], ["Eingang"])
        self.assertEqual(e["nicht_verwendet"][0]["art"], "kreuzung")

    def test_vereinigung_zweier_kreise(self):
        a = {"ost": 0.0, "nord": 0.0, "radius_m": 10, "beschreibung": "a"}
        b = {"ost": 100.0, "nord": 0.0, "radius_m": 30, "beschreibung": "b"}
        u = s._vereinigung(a, b)
        self.assertEqual(u["radius_m"], 70)
        self.assertAlmostEqual(u["ost"], 60.0)  # der Kreis reicht von -10 bis 130
        self.assertIs(s._vereinigung(a, dict(b, radius_m=3, ost=2.0)), a)


class EchteDaten(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pfad = os.path.join(HIER, "belege", "neuss-adressen.csv")
        if not os.path.exists(cls.pfad):
            raise unittest.SkipTest("belege/neuss-adressen.csv fehlt (tools/adressen_laden.py)")
        cls.v = s.Verzeichnis.laden(cls.pfad)

    def test_alle_adressen_liegen_in_neuss(self):
        alle = [a for lst in self.v.je_name.values() for a in lst]
        self.assertGreater(len(alle), 30000)
        for a in alle[::97]:
            b, l_ = s.utm32_zu_wgs84(a.ost, a.nord)
            self.assertTrue(51.05 < b < 51.30 and 6.55 < l_ < 6.85, (a, b, l_))

    def test_bekannte_strasse_mit_umlaut_und_eszett(self):
        adr, name, _ = self.v.strasse("Cyriakusstr.")
        self.assertGreater(len(adr), 20)
        self.assertEqual(name, "Cyriakusstraße")

    @staticmethod
    def metadaten():
        with open(os.path.join(HIER, "belege", "metadaten.json"), encoding="utf-8") as fh:
            return json.load(fh)["standorte"]

    def test_hinweisdatei_hat_keine_doppelten_schluessel(self):
        def paare(p):
            schluessel = [k for k, _ in p]
            self.assertEqual(len(schluessel), len(set(schluessel)), schluessel)
            return dict(p)
        with open(os.path.join(HIER, "belege", "standort-hinweise.json"), encoding="utf-8") as fh:
            json.load(fh, object_pairs_hook=paare)

    def test_hinweise_gehoeren_zu_vorhandenen_ordnern_und_strassen(self):
        meta = self.metadaten()
        hinweise = s.lade_hinweise(os.path.join(HIER, "belege", "standort-hinweise.json"))
        self.assertGreater(len(hinweise), 10)
        for rel, liste in hinweise.items():
            self.assertIn(rel, meta, rel)
            for h in liste:
                self.assertIn(h["stufe"], s.BEWERTUNG, rel)
                self.assertTrue(h.get("quelle", {}).get("typ"), rel)
                if h["art"] == "fahrtrichtung":
                    continue
                self.assertIsNotNone(s.BEWERTER.get(h["art"]), (rel, h["art"]))
                self.assertTrue(self.v.strasse(h["strasse"])[0], (rel, h["strasse"]))

    def test_jeder_ordner_hat_einen_standort_im_stadtgebiet(self):
        for rel, st in self.metadaten().items():
            if "standort" not in st:
                self.fail("kein Standort: " + rel)
            self.assertTrue(51.05 < st["standort"]["breite"] < 51.30, rel)
            self.assertTrue(6.55 < st["standort"]["laenge"] < 6.85, rel)
            self.assertGreaterEqual(st["standort"]["unsicherheit_m"], s.ANNAHMEN["adresse_m"], rel)
            o, n = s.wgs84_zu_utm32(st["standort"]["breite"], st["standort"]["laenge"])
            self.assertLess(math.hypot(o - st["standort"]["utm32_ost"], n - st["standort"]["utm32_nord"]), 1.5, rel)


if __name__ == "__main__":
    unittest.main()
