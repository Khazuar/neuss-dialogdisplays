# SPDX-License-Identifier: MIT
"""Tests fuer aggregat.py und daten_bauen.py (bereinigte Daten, DATEN.md).  Aufruf: python3 -m unittest -v"""
import collections
import csv
import datetime as dt
import gzip
import json
import os
import tempfile
import unittest

import aggregat
import daten_bauen
import dsd2csv as d
import gruppen
import zwischenspeicher

HIER = os.path.dirname(os.path.abspath(__file__))


def fahrzeuge():
    """Zwei Tage in Ortszeit: Tag 1 mit Fahrzeugen um 7 und 8 Uhr (8 Uhr nur teilweise aufgezeichnet), Tag 2 um 23 Uhr."""
    t = dt.datetime
    return [(t(2025, 3, 3, 7, 5), 30), (t(2025, 3, 3, 7, 6), 30), (t(2025, 3, 3, 7, 40), 45), (t(2025, 3, 3, 8, 2), 32),
            (t(2025, 3, 4, 23, 10), 51), (t(2025, 3, 4, 23, 11), 28)]


SPANNEN = [(dt.datetime(2025, 3, 3, 6, 30), dt.datetime(2025, 3, 3, 8, 10)), (dt.datetime(2025, 3, 4, 22, 0), dt.datetime(2025, 3, 5, 0, 0))]
WINTER = dt.timedelta(hours=1)  # Winterzeit im Maerz vor der Umstellung: Ortszeit = UTC + 1


def bauen(veh, spannen, grenzen=(), limit=30):
    """aggregat.bauen fuer Fahrzeuge und Spannen in (Winter-)Ortszeit; die UTC-Zeit ist dann Ortszeit minus 1 Stunde."""
    utc = {id(f): f[0] - WINTER for f in veh}
    return aggregat.bauen(veh, utc, [(a - WINTER, b - WINTER) for a, b in spannen], lambda u: 1, list(grenzen), limit, d.stats)


class Bauen(unittest.TestCase):
    def setUp(self):
        self.agg = bauen(fahrzeuge(), SPANNEN, [dt.date(2025, 3, 4)])

    def test_stunden_je_tag_und_kmh(self):
        s = self.agg["stunden"]
        self.assertEqual(s, [["2025-03-03", 7, 1, 1, 1, [30, 2, 45, 1]], ["2025-03-03", 8, 1, 1, 0, [32, 1]], ["2025-03-04", 23, 1, 2, 1, [28, 1, 51, 1]]])
        self.assertEqual(sum(sum(z[5][1::2]) for z in s), len(fahrzeuge()))  # nichts geht verloren

    def test_abschnitt_nach_den_grenzen(self):
        self.assertEqual([z[3] for z in self.agg["stunden"]], [1, 1, 2])  # der Tag der Grenze gehoert schon zum neuen Abschnitt

    def test_tageskennzahlen_wie_stats(self):
        tag = [f for f in fahrzeuge() if f[0].date() == dt.date(2025, 3, 3)]
        s = d.stats(tag, 30)
        erwartet = [1, "2025-03-03", s["anzahl_fahrzeuge"], s["geschwindigkeit_kmh"]["mittel"], s["geschwindigkeit_kmh"]["v85"],
                    s["geschwindigkeit_kmh"]["v95"], s["geschwindigkeit_kmh"]["v99"], s["einhaltung"]["einhaltungsquote_prozent"],
                    s["einhaltung"]["qualifizierte_einhaltungsquote_prozent"]]
        self.assertEqual(self.agg["tage"][0], erwartet)
        self.assertEqual([t[:2] for t in self.agg["tage"]], [[1, "2025-03-03"], [2, "2025-03-04"]])

    def test_luecken_sind_die_nicht_vollstaendigen_stunden(self):
        # 7 Uhr ist voll (6:30 bis 8:10: 7:00 bis 8:00), 8 Uhr nur teilweise; Tag 2: 22 und 23 Uhr voll. Die Luecke ist in UTC angegeben (Ortszeit - 1)
        self.assertEqual(self.agg["luecken"], [["2025-03-03T07:00Z", "2025-03-04T20:00Z", 38]])

    def test_ohne_fahrzeuge(self):
        self.assertEqual(bauen([], []), {"stunden": [], "tage": [], "luecken": []})

    def test_zeitraeume_decken_alle_stunden_ab(self):
        z = aggregat.zeitraum_je_stunde(gruppen.ZEITSCHEIBEN)
        self.assertEqual(sorted(z), list(range(24)))
        self.assertEqual({h: z[h] for h in (22, 5, 6, 11, 12, 18, 19, 21)},
                         {22: "nacht", 5: "nacht", 6: "vormittag", 11: "vormittag", 12: "nachmittag", 18: "nachmittag", 19: "abend", 21: "abend"})


class Zeitumstellung(unittest.TestCase):
    """Gerätezeit über die Sommerzeitumstellung (die Geräte stellen nie um): Jede Stunde hat Datum, Ortszeit-Stunde und UTC-Versatz, auch die
    doppelte Stunde im Herbst ist in zwei Zeilen getrennt."""

    def aggregat(self, start, minuten):
        veh = [(start + dt.timedelta(minutes=i), 30) for i in range(minuten)]  # ein Fahrzeug je Minute
        uhr, bereinigt, teil, spannen, utc, spannen_utc = d.analysiere_uhr(veh, [], mit_utc=True)
        self.assertEqual(len(bereinigt), minuten)  # alle haben nutzbare Zeit
        agg = aggregat.bauen(bereinigt, utc, spannen_utc, d.utc_versatz_h, [], 30, d.stats)
        return [(z[0], z[1], z[2], sum(z[5][1::2]), z[4]) for z in agg["stunden"]]

    def test_fruehjahr_stunde_2_faellt_aus(self):
        # Geraet im Winter gestellt (MEZ), laeuft im Sommer eine Stunde nach: Geraet 02:00 ist 03:00 MESZ am 30.03.2025
        stunden = self.aggregat(dt.datetime(2025, 3, 30, 0, 0), 5 * 60)  # Geraet 00:00 bis 04:59
        self.assertEqual([(s[0], s[1], s[2], s[3]) for s in stunden],
                         [("2025-03-30", 0, 1, 60), ("2025-03-30", 1, 1, 60), ("2025-03-30", 3, 2, 60), ("2025-03-30", 4, 2, 60), ("2025-03-30", 5, 2, 60)])
        self.assertNotIn(("2025-03-30", 2), [(s[0], s[1]) for s in stunden])  # diese Ortszeit-Stunde gibt es an dem Tag nicht

    def test_herbst_die_doppelte_stunde_ist_in_zwei_zeilen_getrennt(self):
        # Geraet im Sommer gestellt (MESZ), nie umgestellt: Geraet 02:xx und 03:xx sind beide Ortszeit 02:xx am 27.10.2024 (2A und 2B)
        stunden = self.aggregat(dt.datetime(2024, 10, 26, 22, 0), 7 * 60)  # Geraet 22:00 bis 04:59
        self.assertEqual([(s[0], s[1], s[2], s[3]) for s in stunden],
                         [("2024-10-26", 22, 2, 60), ("2024-10-26", 23, 2, 60), ("2024-10-27", 0, 2, 60), ("2024-10-27", 1, 2, 60),
                          ("2024-10-27", 2, 2, 60), ("2024-10-27", 2, 1, 60), ("2024-10-27", 3, 1, 60)])  # 2A (Versatz 2) vor 2B (Versatz 1)
        self.assertEqual([s[4] for s in stunden], [1, 1, 1, 1, 1, 1, 0])  # die letzte Stunde endet schon um 04:59: angebrochen

    def test_utc_aus_datum_stunde_und_versatz(self):
        """datum, stunde und utc_versatz_h bestimmen die UTC-Stunde eindeutig und aufsteigend, auch ueber die Umstellung."""
        stunden = self.aggregat(dt.datetime(2024, 10, 26, 22, 0), 7 * 60)
        utc = [dt.datetime.strptime(s[0], "%Y-%m-%d") + dt.timedelta(hours=s[1] - s[2]) for s in stunden]
        self.assertEqual(utc, [dt.datetime(2024, 10, 26, 20) + dt.timedelta(hours=i) for i in range(7)])


class Gesamt(unittest.TestCase):
    """convert() und daten_bauen an einer echten DSD-Datei: dieselben Zahlen wie die YAML und die Zellen der Detailseite."""

    @classmethod
    def setUpClass(cls):
        # eine kleine Datei, bei der ein Regenanteil abgezogen wird (dort wichen die Zeitraeume frueher ab)
        datei = os.path.join(HIER, "15_Schluchenhausstraße", "_7.dsd")
        if not os.path.exists(datei):
            raise unittest.SkipTest("Testdatei fehlt")
        cls.tmp = tempfile.TemporaryDirectory()
        t = cls.tmp.name
        cls.ausgabe, cls.agg_ordner, cls.ziel = (os.path.join(t, x) for x in ("aus", "agg", "daten"))
        os.makedirs(cls.ausgabe)
        cls.res = d.convert(datei, cls.ausgabe, "01_Teststrasse", None, False, False, 0, {},
                            zwischenspeicher.Zwischenspeicher(os.path.join(t, "cache")), False, cls.agg_ordner)
        cls.auswertung = {"standorte": [json.loads(json.dumps(cls.res))]}
        cls.n = daten_bauen.bauen(cls.auswertung, {"standorte": {}}, {"dateien": {}}, cls.agg_ordner, cls.ziel)
        with open(os.path.join(cls.ausgabe, os.path.splitext(cls.res["datei"])[0] + ".zellen.json"), encoding="utf-8") as fh:
            cls.zellen = json.load(fh)
        cls.slug = d.standort_slug(cls.res["standort"].split("_", 1)[-1])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def stunden(self):
        pfade = os.listdir(os.path.join(self.ziel, "stunden"))
        self.assertEqual(len(pfade), 1)
        self.assertTrue(pfade[0].endswith(".csv.gz"))
        with gzip.open(os.path.join(self.ziel, "stunden", pfade[0]), "rt", encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))

    def test_dateien_und_spalten(self):
        for name in ("messungen.csv", "abschnitte.csv", "kennzahlen.csv", "tage.csv", "luecken.csv", "stunden.csv.gz"):
            self.assertTrue(os.path.exists(os.path.join(self.ziel, name)), name)
        z = self.stunden()
        self.assertEqual(list(z[0]), aggregat.SPALTEN_STUNDEN)
        with gzip.open(os.path.join(self.ziel, "stunden.csv.gz"), "rt", encoding="utf-8", newline="") as fh:
            gesamt = list(csv.DictReader(fh))
        self.assertEqual(gesamt, z)  # eine Standortdatei, also ist die Gesamtdatei dieselbe

    def test_summe_ist_die_zahl_der_fahrzeuge_mit_nutzbarer_zeit(self):
        z = self.stunden()
        self.assertEqual(sum(int(r["anzahl"]) for r in z), self.res["bereinigt"]["anzahl_fahrzeuge"])
        with open(os.path.join(self.ziel, "messungen.csv"), encoding="utf-8", newline="") as fh:
            m = list(csv.DictReader(fh))[0]
        self.assertEqual(int(m["fahrzeuge_im_aggregat"]), sum(int(r["anzahl"]) for r in z))
        self.assertEqual(int(m["fahrzeuge_in_datei"]), self.res["fahrzeuge_in_datei"])

    def test_kennzahlen_je_zeitraum_aus_dem_aggregat_wie_in_der_yaml(self):
        """V85 und Einhaltung je Zeitraum, aus den Stundenzeilen neu gerechnet, stimmen mit teilzeitraeume der YAML ueberein."""
        z = self.stunden()
        limit = self.res["tempolimit_kmh"]
        for name in ("nacht", "vormittag", "nachmittag", "abend"):
            v = []
            for r in z:
                if r["zeitraum"] == name:
                    v += [int(r["kmh"])] * int(r["anzahl"])
            yaml = self.res["teilzeitraeume"][name]
            self.assertEqual(len(v), yaml["anzahl_fahrzeuge"], name)
            if not v:
                continue
            v.sort()
            self.assertEqual(d.pct(v, 85), yaml["geschwindigkeit_kmh"]["v85"], name)
            self.assertEqual(round(sum(v) / len(v), 2), yaml["geschwindigkeit_kmh"]["mittel"], name)
            if limit:
                ok = sum(1 for x in v if x <= limit)
                self.assertEqual(round(100 * ok / len(v), 2), yaml["einhaltung"]["einhaltungsquote_prozent"], name)
        schulweg = sum(int(r["anzahl"]) for r in z if r["stunde"] == "7" and int(r["wochentag"]) <= 5)
        self.assertEqual(schulweg, self.res["teilzeitraeume"]["schulweg"]["anzahl_fahrzeuge"])

    def test_die_testdatei_hat_einen_regenabzug(self):
        """Der Vergleich oben ist nur etwas wert, wo ein Regenanteil abgezogen ist (dort wichen die Zeitraeume frueher ab)."""
        self.assertGreater(((self.res.get("rauschen") or {}).get("regen") or {}).get("abgezogen_fahrzeuge") or 0, 0)

    def test_zeitraeume_einer_kuenstlichen_messung(self):
        """Aggregat und Zeitraumlisten derselben Fahrzeuge (hier ohne Abzug)."""
        t = dt.datetime
        veh = [(t(2025, 3, 3 + i // 24, i % 24, i % 60), 25 + i % 30) for i in range(400)]
        teil = {k: [f for f in veh if in_zeitraum(f[0])] for k, (_, in_zeitraum) in d.TEILZEITRAEUME.items()}
        agg = bauen(veh, [(veh[0][0], veh[-1][0])])
        zeitraum = aggregat.zeitraum_je_stunde(gruppen.ZEITSCHEIBEN)
        for name in ("nacht", "vormittag", "nachmittag", "abend"):
            n = sum(sum(z[5][1::2]) for z in agg["stunden"] if zeitraum[z[1]] == name)
            self.assertEqual(n, len(teil[name]), name)

    def test_vollstaendige_stunden_sind_die_zellen_der_detailseite(self):
        """Die Zellen (Tagschluessel x Stunde) der Detailseite zaehlen nur vollstaendig aufgezeichnete Stunden; hier dasselbe aus den Zeilen."""
        je_zelle = collections.defaultdict(collections.Counter)
        for r in self.stunden():
            if r["voll"] == "1":
                dd = dt.datetime.strptime(r["datum"], "%Y-%m-%d")
                je_zelle["%d|%d" % (gruppen.tagschluessel(dd), int(r["stunde"]))][int(r["kmh"])] += int(r["anzahl"])
        z = self.zellen["z"]
        self.assertEqual(set(je_zelle), set(z))
        for k, zaehler in je_zelle.items():
            erwartet = {z[k][i]: z[k][i + 1] for i in range(0, len(z[k]), 2)}
            self.assertEqual(dict(zaehler), erwartet, k)

    def test_tage_und_abschnitte(self):
        with open(os.path.join(self.ziel, "tage.csv"), encoding="utf-8", newline="") as fh:
            tage = list(csv.DictReader(fh))
        self.assertEqual(sum(int(t["fahrzeuge"]) for t in tage), self.res["bereinigt"]["anzahl_fahrzeuge"])
        with open(os.path.join(self.ziel, "abschnitte.csv"), encoding="utf-8", newline="") as fh:
            ab = list(csv.DictReader(fh))
        self.assertEqual(len(ab), len(self.res["abschnitte"].get("liste") or []) or 1)
        for a in ab:  # die Tage eines Abschnitts summieren sich zu seinen Fahrzeugen
            self.assertEqual(sum(int(t["fahrzeuge"]) for t in tage if t["abschnitt_nr"] == a["abschnitt_nr"]), int(a["fahrzeuge"]), a)
        with open(os.path.join(self.ziel, "kennzahlen.csv"), encoding="utf-8", newline="") as fh:
            k = list(csv.DictReader(fh))
        alle = [r for r in k if r["bereich"] == "messung" and r["zeitraum"] == "alle"][0]
        self.assertEqual(int(alle["fahrzeuge"]), self.res["bereinigt"]["anzahl_fahrzeuge"])
        self.assertEqual(float(alle["v85_kmh"]), self.res["bereinigt"]["geschwindigkeit_kmh"]["v85"])

    def test_gleiche_eingabe_gleiche_bytes(self):
        ziel2 = os.path.join(self.tmp.name, "daten2")
        daten_bauen.bauen(self.auswertung, {"standorte": {}}, {"dateien": {}}, self.agg_ordner, ziel2)
        for pfad in ("messungen.csv", "kennzahlen.csv", "tage.csv", "stunden.csv.gz", os.path.join("stunden", os.listdir(os.path.join(self.ziel, "stunden"))[0])):
            with open(os.path.join(self.ziel, pfad), "rb") as a, open(os.path.join(ziel2, pfad), "rb") as b:
                self.assertEqual(a.read(), b.read(), pfad)

    def test_lage_und_fahrtrichtung_in_messungen(self):
        metadaten = {"standorte": {self.res["standort"]: {"standort": {
            "breite": 51.2, "laenge": 6.7, "unsicherheit_m": 250, "sicherheit": "benannt", "strasse": "Schluchenhausstraße", "beidseitige_messung": True},
            "messungen": [{"datei": self.res["datei"], "verwaltung": [{"bezeichnung": "Test, FR Hertzstraße", "fahrtrichtung": "Hertzstraße"}]}]}}}
        ziel = os.path.join(self.tmp.name, "daten_lage")
        daten_bauen.bauen(self.auswertung, metadaten, {"dateien": {}}, self.agg_ordner, ziel)
        with open(os.path.join(ziel, "messungen.csv"), encoding="utf-8", newline="") as fh:
            m = list(csv.DictReader(fh))[0]
        self.assertEqual((m["strasse"], m["lage_breite"], m["lage_laenge"], m["lage_unsicherheit_m"], m["lage_sicherheit"]),
                         ("Schluchenhausstraße", "51.2", "6.7", "250", "benannt"))
        self.assertEqual((m["fahrtrichtung"], m["beidseitige_messung"], m["bezeichnung_verwaltung"]), ("Hertzstraße", "1", "Test, FR Hertzstraße"))
        self.assertTrue(m["standort_name"])
        with open(os.path.join(self.ziel, "messungen.csv"), encoding="utf-8", newline="") as fh:
            leer = list(csv.DictReader(fh))[0]  # ohne Metadaten bleiben die Spalten leer, die Datei hat dieselben Spalten
        self.assertEqual(list(leer), list(m))
        self.assertEqual((leer["strasse"], leer["lage_breite"], leer["beidseitige_messung"]), ("", "", ""))

    def test_ohne_zwischenstand_nur_kennzahlen(self):
        """Fehlt der Zwischenstand einer Datei, entstehen Kennzahlen, aber keine Stundenzeilen."""
        leer = os.path.join(self.tmp.name, "leer")
        os.makedirs(leer)
        ziel3 = os.path.join(self.tmp.name, "daten3")
        n = daten_bauen.bauen(self.auswertung, {"standorte": {}}, {"dateien": {}}, leer, ziel3)
        self.assertEqual((n["messungen"], n["stunden"], n["tage"]), (1, 0, 0))


if __name__ == "__main__":
    unittest.main()
