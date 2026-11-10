# SPDX-License-Identifier: MIT
"""Tests fuer einsaetze.py (Teile den Messungen zuordnen, Einsaetze bilden, Brueche erklaeren).  Aufruf: python3 -m unittest -v"""
import datetime as dt
import os
import tempfile
import unittest

import bewegungen as B
import einsaetze as E
import test_bewegungen as TB

TAG = dt.timedelta(days=1)


def messung(mid, geraet="G", limit=50, brueche=()):
    """Messung wie einsaetze.messungen_lesen; brueche: Bruchtage (date)."""
    return {"id": mid, "rel": mid, "datei": mid + ".dsd", "geraet": geraet, "limit": limit, "seite": mid, "name": mid, "fahrtrichtung": "",
            "brueche": [(i + 2, d, 1.0) for i, d in enumerate(brueche)], "aussen": False, "zeile": None, "ort": (51.2, 6.7)}


def tz(i, h=0):
    return dt.datetime.combine(TB.tag(i), dt.time(h))


def teil(von, bis, dateien, hist, fz_h=50.0):
    """Teil eines Aufenthalts (von, bis: Tagesindizes ab TB.BASIS); dateien: {Messung: Tage}, die Dateien in dieser Reihenfolge nacheinander."""
    tage = bis - von + 1
    info, ab = {}, von
    for mid, n in dateien.items():
        info[mid] = {"fahrzeuge": 1000 * n, "tage": n, "von": tz(ab).isoformat(), "bis": tz(ab + n - 1, 23).isoformat(), "rekonstruiert": 0}
        ab += n
    return {"von": tz(von).isoformat(), "bis": tz(bis, 23).isoformat(), "tage": tage, "fahrzeuge": 1000 * tage, "dateien": info,
            "merkmal": {"hist": hist, "fz_h": fz_h, "v85": 40, "n": 1000, "tage": tage}}


def aufenthalt(nr, teile, beginn=None):
    return {"nr": nr, "von": teile[0]["von"], "bis": teile[-1]["bis"], "beginn": beginn, "ende": None, "konfidenz": "ungeprueft",
            "brueche": [{"datum": t["von"][:10], "wahrscheinlichkeit": 1.0} for t in teile[1:]], "teile": teile, "zeilen": [],
            "voll_ohne_fahrzeuge": []}


HA, HB, HC = {"20": 50, "22": 50}, {"14": 60, "15": 40}, {"30": 100}


def synthetisch():
    """Auslesen, dann umhaengen: m-a (Standort A) bis zum Auslesen an Tag 20 um 9 Uhr; die Datei m-b beginnt dort, das Geraet haengt aber noch
    bis Tag 30 um 10 Uhr bei A und erst danach bei B."""
    x = TB.geraet([(TB.um(0, 0), TB.um(20, 9), TB.A, 0), (TB.um(20, 9, 5), TB.um(30, 10), TB.A, 1),
                   (TB.um(30, 10, 45), TB.um(60, 23, 59), TB.Bo, 1)], ["m-a", "m-b"])
    B.erkennen([x])
    return x, B._json({"aktionstage": {}, "geraete": [B.geraet_ausgabe(x)]})


class Zuordnung(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x, cls.bew = synthetisch()
        cls.ms = [messung("m-a"), messung("m-b", brueche=[TB.tag(31)])]
        cls.ein, cls.nicht, cls.ohne, cls.teile = E.einsaetze_bilden(cls.bew["geraete"], cls.ms, {})
        cls.von = {e["messung"]: e for e in cls.ein}

    def test_auslesen_dann_umhaengen(self):
        ea, eb = self.von["m-a"], self.von["m-b"]
        self.assertEqual(ea["status"], "abgeleitet")
        self.assertEqual([(t["messung"], t["herkunft"]) for t in ea["teile"]], [("m-a", "eigen"), ("m-b", "andere_messung")])
        self.assertEqual(eb["status"], "gekuerzt")
        self.assertEqual([a["an"] for a in eb["abgegeben"]], ["e-a"])
        self.assertEqual(eb["beginn"]["art"], "bewegung")
        self.assertEqual(eb["beginn"]["bewegung"]["stufe"], "umhaengen")
        self.assertEqual(ea["ende"]["bewegung"]["stufe"], "umhaengen")
        # minutengenau: der Einsatz an A endet vor der Luecke, der an B beginnt nach ihr
        self.assertLess(dt.datetime.fromisoformat(ea["bis_zeit"]), TB.um(30, 10, 5))
        self.assertGreater(dt.datetime.fromisoformat(eb["von_zeit"]), TB.um(30, 10, 40))
        self.assertEqual(self.nicht, [])
        self.assertEqual(self.ohne, [])

    def test_jedes_fahrzeug_in_genau_einem_einsatz(self):
        n = 0
        for e in self.ein:
            auftrag = E._auftrag(e, self.teile[e["id"]], None, (51.2, 6.7))
            n += sum(sum(z[4][1::2]) for a in auftrag["abschnitte"] for z in a["zeilen"])
        self.assertEqual(n, len(self.x["s"]))

    def test_bewegung_erklaert_den_bruch_der_messung(self):
        br = E.brueche_der_messungen(self.ms, self.bew["geraete"], [], {})
        self.assertEqual(len(br), 1)
        self.assertEqual((br[0]["zuordnung"]["art"], br[0]["zuordnung"]["stufe"]), ("bewegung", "belegt"))
        self.assertIn("Umhängen", br[0]["zuordnung"]["text"])

    def test_einsatz_rechnen(self):
        e = self.von["m-a"]
        auftrag = E._auftrag(e, self.teile[e["id"]], None, (51.2, 6.7))
        erg = E.einsatz_rechnen(auftrag)
        k = erg["kennzahlen"]
        n = sum(sum(z[4][1::2]) for a in auftrag["abschnitte"] for z in a["zeilen"])
        self.assertEqual(k["bereinigt"]["anzahl_fahrzeuge"] + k["rauschen"].get("abgezogen_fahrzeuge", 0), n)
        self.assertIn("raten", k["bereinigt"])
        self.assertEqual(sum(sum(z[6][1::2]) for z in erg["aggregat"]), k["bereinigt"]["anzahl_fahrzeuge"])
        with tempfile.TemporaryDirectory() as ordner:  # ueber den Zwischenspeicher: beim zweiten Mal aus dem Speicher, dasselbe Ergebnis
            _, erst, _ = E._arbeit((auftrag, ordner))
            _, zweit, benutzt = E._arbeit((auftrag, ordner))
            self.assertEqual(erst, zweit)
            self.assertIn("einsatz", {x[0] for x in benutzt})


class Teile(unittest.TestCase):
    def test_ortswechsel_ohne_bewegung(self):
        """Kein Umhaengen erkannt, aber ein Bruch im Aufenthalt, nach dem die Daten zur folgenden Messung passen: Schnitt am Bruch, Bruchtag
        und Vortag gehoeren zu keinem Einsatz."""
        g = {"geraet": "G", "aufenthalte": [aufenthalt(1, [teil(0, 29, {"m-a": 21, "m-b": 9}, HA), teil(30, 59, {"m-b": 30}, HB)])]}
        ein, nicht, ohne, _ = E.einsaetze_bilden([g], [messung("m-a"), messung("m-b")], {})
        von = {e["messung"]: e for e in ein}
        self.assertEqual(von["m-a"]["ende"]["art"], "ortswechsel_ohne_bewegung")
        self.assertEqual(von["m-b"]["beginn"]["art"], "ortswechsel_ohne_bewegung")
        self.assertEqual(von["m-a"]["ausgenommene_tage"], [TB.tag(29).isoformat(), TB.tag(30).isoformat()])
        self.assertEqual(von["m-a"]["bis"], TB.tag(28).isoformat())
        self.assertEqual(von["m-b"]["von"], TB.tag(31).isoformat())

    def test_bruch_im_einsatz_bleibt(self):
        """Ein Bruch, nach dem die Daten weiter zur selben Datei gehoeren: zwei Einsatz-Abschnitte, kein Schnitt."""
        g = {"geraet": "G", "aufenthalte": [aufenthalt(1, [teil(0, 29, {"m-a": 30}, HA), teil(30, 59, {"m-a": 30}, HB)])]}
        ein, _n, _o, _ = E.einsaetze_bilden([g], [messung("m-a")], {})
        self.assertEqual(len(ein[0]["abschnitte"]), 2)
        self.assertEqual(ein[0]["abschnitte"][1]["grenze_davor"]["art"], "bruch")
        self.assertEqual(ein[0]["ausgenommene_tage"], [])
        self.assertEqual(ein[0]["status"], "identisch")

    def test_kurzer_fremder_ort_ohne_messung(self):
        """Fuenf Tage an einem Ort ohne Messung zwischen zwei Messungen (anderer Verkehr, ausserhalb jedes Erfassungszeitraums): keine Messung."""
        g = {"geraet": "G", "aufenthalte": [aufenthalt(1, [teil(0, 30, {"m-a": 31}, HA)]), aufenthalt(2, [teil(31, 35, {"m-b": 5}, HC, 20.0)]),
                                            aufenthalt(3, [teil(36, 70, {"m-b": 35}, HB)])]}
        zr = {"m-a/m-a.dsd": [(TB.tag(0), TB.tag(30))], "m-b/m-b.dsd": [(TB.tag(36), TB.tag(70))]}
        ein, nicht, ohne, _ = E.einsaetze_bilden([g], [messung("m-a"), messung("m-b")], zr)
        self.assertEqual(len(nicht), 1)
        self.assertEqual(nicht[0]["von"][:10], TB.tag(31).isoformat())
        eb = next(e for e in ein if e["messung"] == "m-b")
        self.assertEqual(len(eb["nicht_beruecksichtigt"]), 1)
        self.assertEqual(eb["status"], "gekuerzt")

    def test_messung_ohne_daten(self):
        g = {"geraet": "G", "aufenthalte": [aufenthalt(1, [teil(0, 30, {"m-a": 31}, HA)])]}
        _e, _n, ohne, _ = E.einsaetze_bilden([g], [messung("m-a"), messung("m-c")], {})
        self.assertEqual([o["messung"] for o in ohne], ["m-c"])


class Brueche(unittest.TestCase):
    def test_bewegung_in_den_ferien_erklaert_den_bruch_am_ersten_schultag(self):
        # Osterferien 2025: 14.04. bis 26.04.; die Bruchsuche laesst Ferientage aus und findet den Bruch am 28.04.
        b = {"stufe": "umhaengen", "von": "2025-04-14T10:20:00", "bis": "2025-04-14T10:58:00", "z": 12.0}
        self.assertEqual(E.bewegung_vor(dt.date(2025, 4, 28), [b]), b)
        frueh = dict(b, von="2025-04-01T10:20:00", bis="2025-04-01T10:58:00")
        self.assertIsNone(E.bewegung_vor(dt.date(2025, 4, 28), [frueh]))
        self.assertIsNone(E.bewegung_vor(dt.date(2025, 4, 28), [dict(b, stufe="eingriff")]))

    def test_ferienende_erklaert_einen_bruch(self):
        # Herbstferien 2023 enden am 14.10. (Samstag), erster Schultag 16.10.
        zu, _ev, _v = E.erklaeren(dt.date(2023, 10, 16), "b", "m/m.dsd", [], {})
        self.assertEqual((zu["art"], zu["stufe"]), ("ereignis", "plausibel"))
        kurz = [{"von": "2023-08-25", "bis": "2023-08-29", "name": "Fest", "art": "kurz"}]
        self.assertEqual(E.ereignis_kandidaten(dt.date(2023, 8, 30), "b", kurz)[0]["erklaerung"], False)  # kurze Ereignisse nur als Hinweis

    def test_angabe_der_verwaltung_hat_vorrang(self):
        verw = {("m/m.dsd", "2023-10-16"): {"art": "ereignis", "erklaerung": "Baustelle"}}
        b = {"stufe": "umhaengen", "von": "2023-10-16T10:00:00", "bis": "2023-10-16T10:30:00", "z": 9.0}
        zu, _ev, _v = E.erklaeren(dt.date(2023, 10, 16), "b", "m/m.dsd", [], verw, b)
        self.assertEqual((zu["stufe"], zu["text"]), ("bestaetigt", "Baustelle"))


class Defekt(unittest.TestCase):
    def test_pdf_der_verwaltung(self):
        with tempfile.TemporaryDirectory() as w:
            for rel, f in (("01_A", "23_05_04_fehlerhaft_A.pdf"), ("01_A", "23_05_04_A.dsd"), ("02_B/sub", "23_05_04_B.dsd"),
                           ("02_B", "23_05_04_fehlerhaft_B.pdf"), ("03_C", "2023_07_C_defekt.pdf"), ("03_C", "_7.dsd"), ("04_D", "x.dsd"),
                           ("04_D", "2023_07_D.pdf"), ("05_E", "24_01_01_E.dsd"), ("05_E", "23_05_04_fehlerhaft_E.pdf")):
                os.makedirs(os.path.join(w, rel), exist_ok=True)
                open(os.path.join(w, rel, f), "w").close()
            ms = [dict(messung(i), rel=rel, datei=f) for i, rel, f in (("m-a", "01_A", "23_05_04_A.dsd"), ("m-b", "02_B/sub", "23_05_04_B.dsd"),
                                                                      ("m-c", "03_C", "_7.dsd"), ("m-d", "04_D", "x.dsd"), ("m-e", "05_E", "24_01_01_E.dsd"))]
            self.assertEqual(sorted(E.defekt(ms, w)), ["m-a", "m-b", "m-c"])


if __name__ == "__main__":
    unittest.main()
