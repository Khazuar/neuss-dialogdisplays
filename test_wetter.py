# SPDX-License-Identifier: MIT
"""Tests fuer wetter.py (DWD-Wetterdaten) und tageslicht.py.  Aufruf: python3 -m unittest -v"""
import datetime as dt
import io
import math
import os
import sys
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tageslicht as tl  # noqa: E402
import wetter as w  # noqa: E402

STATIONEN = """Stations_id von_datum bis_datum Stationshoehe geoBreite geoLaenge Stationsname Bundesland Abgabe
----------- --------- --------- ------------- --------- --------- ----------------------------------------- ---------- ------
01078 19950901 20261012             37     51.2960    6.7686 Düsseldorf                               Nordrhein-Westfalen                      Frei
19839 20240802 20261012             41     51.2000    6.7000 Neuss (Steinhausstraße)                  Nordrhein-Westfalen                      Frei
00003 19950901 20110401            202     50.7827    6.0941 Aachen                                   Nordrhein-Westfalen                      Frei
"""


def zip_mit(name, zeilen, weitere=()):
    puffer = io.BytesIO()
    with zipfile.ZipFile(puffer, "w") as zf:
        for n, inhalt in weitere:
            zf.writestr(n, inhalt)
        zf.writestr(name, "\n".join(zeilen))
    return puffer.getvalue()


class Einlesen(unittest.TestCase):
    def test_abstand(self):
        d = w.km(w.BEZUG, (51.2960, 6.7686))  # Duesseldorf
        self.assertTrue(10 < d < 14, d)
        self.assertEqual(w.km(w.BEZUG, w.BEZUG), 0)

    def test_stationsliste_mit_leerzeichen_im_namen(self):
        st = w.lies_stationen(STATIONEN)
        self.assertEqual([s["id"] for s in st], ["01078", "19839", "00003"])
        self.assertEqual(st[1]["name"], "Neuss (Steinhausstraße)")
        self.assertEqual((st[0]["von"], st[0]["bis"]), ("19950901", "20261012"))
        self.assertAlmostEqual(st[0]["breite"], 51.296)

    def test_stundenwerte_und_fehlwerte(self):
        z = ["STATIONS_ID;MESS_DATUM;QN_8;  R1;RS_IND;WRTR;eor",
             "      1078;2025070100;    3;   0.0;   0;   0;eor",
             "      1078;2025070101;    3;   1.2;   1;   6;eor",
             "      1078;2025070102;    3;-999.0;-999;-999;eor"]
        self.assertEqual(w.stundenwerte(z), {"2025070100": 0.0, "2025070101": 1.2, "2025070102": None})

    def test_tageswerte(self):
        kopf = "STATIONS_ID;MESS_DATUM;QN_3;  FX;  FM;QN_4; RSK;RSKF; SDK;SHK_TAG;  NM; VPM;  PM; TMK; UPM; TXK; TNK; TGK;eor"
        z = [kopf, "       1078;20251231;    3;  10.5;   3.5;    9;   0.2;   6;-999;   0;   6.4;   5.9; 1019.40;    0.2;   93.00;    3.6;   -4.9;-999;eor"]
        t = w.tageswerte(z)[dt.date(2025, 12, 31)]
        self.assertEqual((t["fx"], t["fm"], t["tmk"], t["txk"], t["tnk"], t["shk"]), (10.5, 3.5, 0.2, 3.6, -4.9, 0.0))
        self.assertIsNone(t["tgk"])  # Fehlwert

    def test_zip_liest_nur_die_produktdatei(self):
        z = zip_mit("produkt_rr_stunde_x.txt", ["a;b", "c;d"], weitere=[("Metadaten_Geographie_01078.txt", "nicht lesen")])
        self.assertEqual(w.lies_zip(z), ["a;b", "c;d"])
        self.assertEqual(w.lies_zip(zip_mit("andere.txt", ["x"])), [])


class Ortszeit(unittest.TestCase):
    def werte(self):
        """Ein Wert je UTC-Stunde (Zeitstempel = Ende der Stunde), der Wert ist die Nummer der Stunde seit 2025-01-01 00 UTC."""
        out, t = {}, dt.datetime(2025, 1, 1, 0)
        for i in range(24 * 400):
            out[t.strftime("%Y%m%d%H")] = float(i)
            t += dt.timedelta(hours=1)
        return out

    def test_winter_stunde_null_ist_der_zeitstempel_utc_ende(self):
        # Ortszeit 00:00 bis 01:00 am 15.1. (MEZ) = 23:00 bis 00:00 UTC; Zeitstempel = Ende = 15.1. 00 UTC
        std = w.ortszeit_stunden(dt.date(2025, 1, 15), self.werte())
        erwartet = 14 * 24 + 0  # Stundennummer des Zeitstempels 2025011500
        self.assertEqual(std[0], float(erwartet))
        self.assertEqual(std[23], float(erwartet + 23))

    def test_sommer_ist_zwei_stunden_vor_utc(self):
        std = w.ortszeit_stunden(dt.date(2025, 7, 1), self.werte())
        t = dt.datetime(2025, 7, 1, 0) - dt.timedelta(hours=2) + dt.timedelta(hours=1)  # Ortszeit 00 Uhr: 22 UTC am Vortag, Ende 23 UTC
        n = int((t - dt.datetime(2025, 1, 1)).total_seconds() // 3600)
        self.assertEqual(std[0], float(n))

    def test_station_wird_nach_gueltigen_stunden_gewaehlt(self):
        voll = self.werte()
        luecke = dict(voll)
        for h in range(0, 18):  # an dem Tag fehlen 18 Stunden
            luecke[(dt.datetime(2025, 3, 10, 0) + dt.timedelta(hours=h)).strftime("%Y%m%d%H")] = None
        sid, std = w.waehle_station(dt.date(2025, 3, 10), [("nah", luecke), ("fern", voll)])
        self.assertEqual(sid, "fern")
        self.assertEqual(len(std), 24)
        sid, _ = w.waehle_station(dt.date(2025, 3, 10), [("nah", voll), ("fern", luecke)])
        self.assertEqual(sid, "nah")
        self.assertEqual(w.waehle_station(dt.date(2025, 3, 10), [("nah", luecke)]), (None, None))
        self.assertEqual(w.waehle_station(dt.date(2025, 3, 10), []), (None, None))


class Tabelle(unittest.TestCase):
    def test_bauen(self):
        def werte(wert_je_stunde, tage):
            out = {}
            t = dt.datetime(2025, 5, 1, 0)
            for i in range(24 * tage + 6):
                out[(t + dt.timedelta(hours=i)).strftime("%Y%m%d%H")] = wert_je_stunde(i)
            return out
        nah = werte(lambda i: 0.0 if i < 24 * 1 + 6 else (0.5 if i % 5 == 0 else 0.0), 3)  # Tag 1 trocken, ab Tag 2 Regen
        for k in [k for k in nah if k >= "2025050400"]:
            nah[k] = None  # ab dem 4.5. keine Werte
        fern = werte(lambda i: 0.1 if i % 12 == 0 else 0.0, 5)
        klima = {dt.date(2025, 5, 1): {"tmk": 12.3, "tnk": None, "fx": 8.0, "shk": 0.0}}
        info = {"nah": {"id": "nah", "name": "Nah", "km": 1.0}, "fern": {"id": "fern", "name": "Fern", "km": 9.0}, "01078": {"id": "01078", "name": "K", "km": 12.0}}
        t = w.bauen(dt.date(2025, 5, 1), dt.date(2025, 5, 5), [("nah", nah), ("fern", fern)], klima, info)
        tage = t["tage"]
        self.assertEqual(sorted(tage), ["2025-05-01", "2025-05-02", "2025-05-03", "2025-05-04", "2025-05-05"])
        self.assertEqual(tage["2025-05-01"]["st"], "nah")
        self.assertEqual(tage["2025-05-01"]["mm"], 0.0)
        self.assertNotIn("std", tage["2025-05-01"])  # nur an Tagen mit mindestens 0,1 mm
        self.assertEqual((tage["2025-05-01"]["tmk"], tage["2025-05-01"]["fx"]), (12.3, 8.0))
        self.assertNotIn("tnk", tage["2025-05-01"])  # Fehlwerte stehen nicht in der Tabelle
        self.assertEqual(tage["2025-05-02"]["st"], "nah")
        self.assertIn("std", tage["2025-05-02"])
        self.assertEqual(len(tage["2025-05-02"]["std"]), 24)
        self.assertEqual(tage["2025-05-04"]["st"], "fern")  # die naechste Station hat keine Werte: Rueckfall
        self.assertEqual(t["stationswechsel"], 1)
        self.assertEqual(sorted(t["stationen"]), ["fern", "nah"])  # nur Stationen, die gebraucht wurden
        self.assertIn("CC BY 4.0", t["lizenz"])
        self.assertEqual(t["quellenvermerk"], "Quelle: Deutscher Wetterdienst")
        self.assertIn("Deutscher Wetterdienst", t["aenderungen"])

    def test_tage_ohne_jede_station_haben_nur_klimawerte_oder_fehlen(self):
        klima = {dt.date(2025, 5, 2): {"tmk": 5.0}}
        t = w.bauen(dt.date(2025, 5, 1), dt.date(2025, 5, 3), [], klima, {})
        self.assertEqual(list(t["tage"]), ["2025-05-02"])
        self.assertEqual(t["tage"]["2025-05-02"], {"tmk": 5.0})


class Tageslicht(unittest.TestCase):
    def test_tageslaenge_bei_neuss(self):
        sommer = tl.sonnenzeiten(dt.date(2025, 6, 21))["tageslaenge_h"]
        winter = tl.sonnenzeiten(dt.date(2025, 12, 21))["tageslaenge_h"]
        tagundnacht = tl.sonnenzeiten(dt.date(2025, 3, 20))["tageslaenge_h"]
        self.assertAlmostEqual(sommer, 16 + 35 / 60, delta=4 / 60)  # 16 h 35 min
        self.assertAlmostEqual(winter, 7 + 53 / 60, delta=4 / 60)  # 7 h 53 min
        self.assertAlmostEqual(tagundnacht, 12 + 7 / 60, delta=5 / 60)  # etwas ueber 12 h wegen Refraktion

    def test_mittag_liegt_bei_der_laengenabhaengigen_zeit(self):
        z = tl.sonnenzeiten(dt.date(2025, 6, 21))
        mitte = z["aufgang"] + (z["untergang"] - z["aufgang"]) / 2
        erwartet = dt.datetime(2025, 6, 21, 12) - dt.timedelta(minutes=4 * tl.BEZUG[1])  # ohne Zeitgleichung (unter 2 Minuten im Juni)
        self.assertLess(abs((mitte - erwartet).total_seconds()), 5 * 60)

    def test_reihenfolge_und_lichtart(self):
        z = tl.sonnenzeiten(dt.date(2025, 10, 26))
        self.assertLess(z["daemmerung_beginn"], z["aufgang"])
        self.assertLess(z["aufgang"], z["untergang"])
        self.assertLess(z["untergang"], z["daemmerung_ende"])
        self.assertEqual(tl.lichtart(dt.datetime(2025, 10, 26, 11)), "tag")
        self.assertEqual(tl.lichtart(dt.datetime(2025, 10, 26, 23, 30)), "nacht")
        self.assertEqual(tl.lichtart(z["untergang"] + dt.timedelta(minutes=10)), "daemmerung")

    def test_tage_werden_im_herbst_schnell_kuerzer(self):
        a = tl.sonnenzeiten(dt.date(2025, 9, 20))["tageslaenge_h"]
        b = tl.sonnenzeiten(dt.date(2025, 10, 20))["tageslaenge_h"]
        self.assertGreater(a - b, 1.8)  # gut zwei Stunden in einem Monat


if __name__ == "__main__":
    unittest.main()
