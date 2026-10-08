# SPDX-License-Identifier: MIT
"""Tests fuer seiten_bauen.py (Detailseiten).  Aufruf: python3 -m unittest -v"""
import json
import os
import re
import tempfile
import unittest

import dsd2csv
import seiten_bauen as s

HIER = os.path.dirname(os.path.abspath(__file__))


def zeile(rel="07_2024_ Einsteinstraße", datei="_15.dsd", n=1000):
    k = {"mittel": 21.4, "maximal": 90, "v85": 28, "v95": 32, "v99": 40}
    h = {"einhaltungsquote_prozent": 88.5, "qualifizierte_einhaltungsquote_prozent": 40.0}
    g = {"risikoindex_nilsson": 1.07, "aufprall_anteil_prozent": 39.01, "aufprall_mittel_kmh": 13.1,
         "aufprall_mittel_der_aufprallenden_kmh": 33.6, "aufprall_p95_kmh": 51.6, "aufprall_p99_kmh": 69.2,
         "aufprall_ueber_30_kmh_prozent": 21.64, "aufprall_ueber_50_kmh_prozent": 5.18, "anhaltestrecke_bei_limit_m": 27.7}
    l = {"mittelungspegel_gegenueber_limit_db": -0.1, "spitzenpegel_p99_gegenueber_limit_db": 3.7,
         "anteil_mind_3_db_lauter_prozent": 1.86, "anteil_mind_6_db_lauter_prozent": 0.13}
    teil = {"anzahl_fahrzeuge": n, "geschwindigkeit_kmh": k, "einhaltung": h, "gefaehrdung": g, "laerm": l}
    return {"standort": rel, "datei": datei, "seite": f"standorte/{dsd2csv.standort_slug(rel)}.html", "tempolimit_kmh": 30,
            "anzahl_fahrzeuge": n, "messzeitraum": {"start": "2024-07-24 09:48:27", "ende": "2024-12-04 10:38:55"},
            "geschwindigkeit_kmh": k, "einhaltung": h, "gefaehrdung": g, "laerm": l,
            "nacht_ereignisse": {"definition": "22:00 bis 06:00 Uhr Ortszeit, nur vollständig aufgezeichnete Nächte", "naechte": 154,
                                 "schwellen": [{"ab_kmh": 100, "doppeltes_tempolimit": False, "naechte_mit_fahrt": 71,
                                                "anteil_naechte_prozent": 46.1, "fahrten_gesamt": 130, "fahrten_je_nacht": 0.84}]},
            "uhr": {"bewertung": "plausibel", "fahrzeuge_mit_gueltiger_zeit_prozent": 100.0, "hinweise": ["Hinweis <b>fett</b>"]},
            "bereinigt": {**teil, "messzeitraum": {"start": "2024-07-24 09:48:27", "ende": "2024-12-04 10:38:55"}},
            "teilzeitraeume": {"tags": teil, "nachts": {"anzahl_fahrzeuge": 0}, "schulweg": teil}}


def eintrag(**kw):
    e = {"bezeichnung": "Einsteinstraße, FR Hertzstraße (beidseitige Messung)", "v85_kmh": 31, "mittel_kmh": 25,
         "einstufung_verwaltung": "voellig_unkritisch", "massnahmen_verwaltung": "nicht erforderlich",
         "stellungnahme_verwaltung": ["Der maßgebliche V85-Wert mit 31 km/h ist völlig unkritisch.", "Verkehrslenkende Maßnahmen sind nicht erforderlich."],
         "fahrzeuge_je_tag": {"kommend": 430, "gehend": 423},
         "zuordnung": {"methode": "name_einzige_datei"},
         "abgleich_dsd": {"v85_kmh": 28, "mittel_kmh": 21.4, "fahrzeuge_je_tag": 520,
                          "abweichung_dsd_minus_verwaltung": {"v85_kmh": -3, "mittel_kmh": -3.6, "fahrzeuge_je_tag_prozent": -39}},
         "quellen": [{"vorlage": "69/338/2025", "gremium": "Bezirksausschuss I - Innenstadt", "sitzung": "2025-02-26",
                      "dokument": "https://ris-neuss.itk-rheinland.de/x?id=1&type=do", "ris_vorlage_id": 28262}]}
    e.update(kw)
    return e


class Hilfen(unittest.TestCase):
    def test_bereinige(self):
        self.assertEqual(s.bereinige("07_2024_ Einsteinstraße"), "Einsteinstraße")
        self.assertEqual(s.bereinige("Stationär_Villestraße/FR GV"), "Stationär Villestraße / FR GV")
        self.assertEqual(s.bereinige("02_Föhrenstraße/2023_FR Fliederstraße"), "Föhrenstraße / FR Fliederstraße")

    def test_formate(self):
        self.assertEqual((s.ganz(1234567), s.dez(21.46), s.dez(88.5, 2), s.iso_de("2025-10-26")), ("1.234.567", "21,5", "88,50", "26.10.2025"))
        self.assertEqual(s.zeit_de("2025-10-26 08:38:52"), "26.10.2025 08:38")
        self.assertEqual(s.ganz(None), "–")

    def test_slugs_aller_standorte_sind_eindeutig(self):
        rels = set()
        for ordner, _, dateien in os.walk(HIER):
            if any(d.lower().endswith(".dsd") for d in dateien):
                rels.add(os.path.relpath(ordner, HIER).replace(os.sep, "/"))
        self.assertGreater(len(rels), 50)
        slugs = {dsd2csv.standort_slug(r) for r in rels}
        self.assertEqual(len(slugs), len(rels))
        self.assertTrue(all(re.fullmatch(r"[a-z0-9-]+", x) for x in slugs))


class Seite(unittest.TestCase):
    def html(self, eintraege=None, rows=None):
        meta = {"messungen": [{"datei": "_15.dsd", "geraet": {"konfiguration": "ABC 123", "erfassung_ab_kmh": 9},
                               "verwaltung": eintraege or []}]}
        uhr = {"07_2024_ Einsteinstraße/_15.dsd": {"abschnitte": [
            {"start": "2024-07-24 09:48:27", "ende": "2024-12-04 10:38:55", "fahrzeuge": 5000, "urteil": "plausibel", "begruendung": ["x <i>y</i>"]},
            {"start": "2024-12-05 00:00:00", "ende": "2024-12-05 01:00:00", "fahrzeuge": 10, "urteil": "unbrauchbar", "begruendung": []}]}}
        return s.seite("07_2024_ Einsteinstraße", rows or [zeile()], meta, uhr)

    def test_einschaetzung_und_massnahmen_stehen_im_wortlaut_auf_der_seite(self):
        h = self.html([eintrag()])
        self.assertIn("Einschätzung und Maßnahmen der Verwaltung", h)
        self.assertIn("völlig unkritisch", h)
        self.assertIn("Verkehrslenkende Maßnahmen sind nicht erforderlich.", h)
        self.assertIn("Einsteinstraße, FR Hertzstraße (beidseitige Messung)", h)
        self.assertIn("69/338/2025", h)
        self.assertIn("https://ris-neuss.itk-rheinland.de/x?id=1&amp;type=do", h)  # Link maskiert

    def test_ohne_verwaltung_steht_ein_hinweis_da(self):
        h = self.html([])
        self.assertIn("keine Beschreibung der Verwaltung", h)
        self.assertIn("keine Einschätzung veröffentlicht", h)

    def test_daten_werden_maskiert(self):
        h = self.html([eintrag(bezeichnung='<script>alert(1)</script>', stellungnahme_verwaltung=["a <b>b</b> & c."])])
        self.assertNotIn("<script", h)
        self.assertNotIn("<b>b</b>", h)
        self.assertNotIn("<i>y</i>", h)
        self.assertNotIn("<b>fett</b>", h)
        self.assertIn("&lt;script&gt;", h)

    def test_kennzahlen_tabelle_und_farben(self):
        h = self.html([eintrag()])
        self.assertIn("Schulweg (Mo–Fr, 7–8 Uhr)", h)
        self.assertIn("keine Fahrzeuge", h)  # Nachts ohne Daten
        self.assertIn('class="num bad">40,00&nbsp;%', h)  # Quote unter 50 %
        self.assertIn('class="num">88,50&nbsp;%', h)  # ab 75 % keine Farbe
        self.assertIn("1.000", h)

    def test_abgleich_und_zuordnung(self):
        h = self.html([eintrag()])
        self.assertIn("Abgleich mit den Angaben der Verwaltung", h)
        self.assertIn("430 (kommend) + 423 (gehend)", h)
        self.assertIn("-39&nbsp;%", h)
        self.assertIn("nur über Straßenname und Sitzungsdatum", h)

    def test_aufprall_laerm_und_naechte(self):
        h = self.html([])
        self.assertIn("Mit wie viel km/h träfen die gemessenen Fahrzeuge auf ein Hindernis?", h)
        self.assertIn("Anhaltestrecke 27,7 m", h)
        self.assertIn('<td class="num">33,6</td>', h)  # Ø Aufprall der Fahrzeuge, die auftreffen
        self.assertIn('<td class="num">69,2</td>', h)  # Aufprall am schnellsten Prozent
        self.assertIn("39,0&nbsp;%", h)  # Anteil, der auftrifft
        self.assertNotIn("Anteil &gt; 30 km/h", h)  # keine Schwellenspalte mehr
        self.assertIn("So rechnet das Modell", h)
        self.assertIn("Bei Tempolimit 30&nbsp;km/h", h)  # Umrechnungstabelle fuer das Limit der Datei
        self.assertIn("Lärm (grobe Schätzung)", h)
        self.assertIn("Spitzenpegel", h)
        self.assertIn("Ereignisse pro Nacht", h)
        self.assertIn("In 71 von 154 Nächten (46&nbsp;%) fuhr mindestens ein Fahrzeug mit 100&nbsp;km/h oder mehr", h)

    def test_hinweis_zu_fehlern_steht_oben_und_unten(self):
        h = self.html([])
        self.assertEqual(h.count("Fehler in der Auswertung"), 2)  # Hinweis oben und im Fuss
        self.assertIn("Schätzungen und kein Gutachten", h)
        self.assertIn('class="notice"', h)
    def test_kurze_abschnitte_werden_zusammengefasst(self):
        h = self.html([])
        self.assertIn("1 weitere kurze Abschnitte", h)

    def test_leere_datei(self):
        h = self.html([], rows=[zeile(n=0)])
        self.assertIn("keine Fahrzeugdaten", h)

    def test_keine_externen_adressen_ausser_github_und_ris(self):
        h = self.html([eintrag()])
        for url in re.findall(r'(?:href|src)="(https?://[^"]+)"', h):
            self.assertRegex(url, r"^https://(github\.com/Khazuar|ris-neuss\.itk-rheinland\.de|creativecommons\.org)")


class Bauen(unittest.TestCase):
    def test_alle_seiten_werden_geschrieben(self):
        auswertung = {"standorte": [zeile(), zeile("Stationär_Villestraße/FR GV", "a.dsd")]}
        meta = {"standorte": {}}
        uhr = {"dateien": {}}
        with tempfile.TemporaryDirectory() as d:
            slugs = s.bauen(auswertung, meta, uhr, d)
            self.assertEqual(sorted(slugs), ["07-2024-einsteinstrasse", "stationaer-villestrasse-fr-gv"])
            for slug in slugs:
                with open(os.path.join(d, "standorte", slug + ".html"), encoding="utf-8") as fh:
                    self.assertIn("<h1>", fh.read())

    def test_falscher_seitenlink_wird_erkannt(self):
        zl = zeile()
        zl["seite"] = "standorte/anders.html"
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                s.bauen({"standorte": [zl]}, {"standorte": {}}, {"dateien": {}}, d)


if __name__ == "__main__":
    unittest.main()
