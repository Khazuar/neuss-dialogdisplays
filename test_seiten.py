# SPDX-License-Identifier: MIT
"""Tests fuer seiten_bauen.py (Detailseiten).  Aufruf: python3 -m unittest -v"""
import json
import os
import re
import tempfile
import unittest

import dsd2csv
import gruppen
import seiten_bauen as s

HIER = os.path.dirname(os.path.abspath(__file__))


def zeile(rel="07_2024_ Einsteinstraße", datei="_15.dsd", n=1000):
    k = {"mittel": 21.4, "maximal": 90, "v85": 28, "v95": 32, "v99": 40}
    h = {"einhaltungsquote_prozent": 88.5, "qualifizierte_einhaltungsquote_prozent": 40.0}
    g = {"aufprall_mittel_der_aufprallenden_kmh": 33.6, "aufprall_p95_kmh": 51.6, "aufprall_p99_kmh": 69.2,
         "aufprall_ueber_30_kmh_je_stunde": 9.0, "aufprall_ueber_50_kmh_je_stunde": 2.2, "anhaltestrecke_bei_limit_m": 27.7}
    l = {"spitzenpegel_p99_gegenueber_limit_db": 3.7, "mind_3_db_lauter_je_stunde": 0.8, "mind_6_db_lauter_je_stunde": 0.1}
    r = {"stunden": 2400, "fahrzeuge_je_stunde": 41.7, "ueber_limit_je_stunde": 4.8,
         "ueber_limit_plus_toleranz_je_stunde": 2.5, "zusatzrisiko_je_stunde": 1.07}
    teil = {"anzahl_fahrzeuge": n, "geschwindigkeit_kmh": k, "einhaltung": h, "raten": r, "gefaehrdung": g, "laerm": l}
    return {"standort": rel, "datei": datei, "seite": f"standorte/{dsd2csv.standort_slug(rel)}.html", "tempolimit_kmh": 30,
            "anzahl_fahrzeuge": n, "messzeitraum": {"start": "2024-07-24 09:48:27", "ende": "2024-12-04 10:38:55"},
            "geschwindigkeit_kmh": k, "einhaltung": h, "raten": r, "gefaehrdung": g, "laerm": l,
            "nacht_ereignisse": {"definition": "22:00 bis 06:00 Uhr Ortszeit, nur vollständig aufgezeichnete Nächte", "naechte": 154,
                                 "schwellen": [{"ab_kmh": 100, "doppeltes_tempolimit": False, "naechte_mit_fahrt": 71,
                                                "anteil_naechte_prozent": 46.1, "fahrten_gesamt": 130, "fahrten_je_nacht": 0.84}]},
            "uhr": {"nutzbarkeit": "nutzbar", "fahrzeuge_mit_nutzbarer_zeit_prozent": 100.0, "hinweise": ["Hinweis <b>fett</b>"]},
            "bereinigt": {**teil, "messzeitraum": {"start": "2024-07-24 09:48:27", "ende": "2024-12-04 10:38:55"}},
            "teilzeitraeume": {"nacht": {"anzahl_fahrzeuge": 0}, "vormittag": dict(teil), "nachmittag": dict(teil), "abend": dict(teil), "schulweg": dict(teil)}}


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


def vg_beispiel():
    """verhaltensgruppen.json (stadtgruppen.py) mit zwei Abschnitten der Einsteinstraße, einer Stadtgruppe und einer MS-Gruppe."""
    def gruppe(name, klasse, modus, anteil, effekte=None, ms=None, korr=None):
        prof = [0.0] * 46
        prof[modus // 2] = 1.0
        return {"name": name, "kennung": "m-x/" + name, "klasse": klasse, "anteil": anteil, "fahrzeuge": 1000, "modus_kmh": modus, "mittel_kmh": modus,
                "streuung_kmh": 3, "profil": prof, "stabil": 0.99, "belastbar": True, "tagesgang": [1.0] * 24, "effekte_gegen_haupt": effekte,
                **({"stadt": "S-R1", "ms": ms, "korrelation_stadt": korr} if klasse != "haupt" else {})}
    eff = {"regen_2": {"faktor": 40.0, "z": 9.0}, "nacht": {"faktor": 1.1, "z": 0.5}, "dichte_log": {"faktor": 0.3, "z": -6.0}}
    s_r1 = {"id": "S-R1", "klasse": "rauschen", "art": "sehr langsam", "anzeige": "Regen<phantome> (S-R1)", "deutung": "Regen<phantome>",
            "stufe": "tragfähig", "kriterien": "k", "belege": ["b <1>"], "gefunden": True, "gruppen": 6, "abschnitte": 6, "placebo_gruppen": 2,
            "standorte": [{"seite": "einsteinstrasse", "name": "Einsteinstraße"}], "modus_median_kmh": 7, "anteil_median": 0.1, "anteil_spanne": [0.05, 0.2],
            "vorlagen_geprueft": 3, "vorlagen_nachgewiesen": 1,
            "effekte": {"regen_2": {"faktor": 40.0, "von": 20.0, "bis": 80.0, "placebo": 0.8, "gesichert": True}}}
    s_f1 = {"id": "S-F1", "klasse": "schnell", "art": "schneller", "anzeige": "S-F1 (Hypothese: Freie Fahrt)", "gefunden": True, "gruppen": 5,
            "abschnitte": 5, "standorte": [], "effekte": {}, "anteil_median": 0.12, "anteil_spanne": [0.08, 0.2]}
    return {"klassen_namen": {"haupt": "Hauptgruppe", "rauschen": "sehr langsam <x>", "schnell": "schneller"}, "merkmale": {"regen_2": "Regen ab 2 mm"},
            "uebersicht": {"abschnitte": 12, "mit_modell": 10, "mit_mehreren_gruppen": 6, "placebo_mit_mehreren_gruppen": 3},
            "stadt": [s_r1, s_f1],
            "standorte": {"07-2024-einsteinstrasse": [{"id": "MS-07-2024-einsteinstrasse-R1", "klasse": "rauschen", "stadt": "S-R1",
                                                       "mitglieder": ["m-x/A1·1", "m-x/A2·1"], "messungen": 1, "abschnitte": 2, "modus_kmh": 9,
                                                       "anteil_median": 0.045, "korrelation_stadt": 0.81}]},
            "abschnitte": {"07_2024_ Einsteinstraße/_15.dsd": [
                {"nr": 1, "geprueft": True, "tage": 50, "fahrzeuge": 20000, "K": 2, "cv_gewinn": [0.0, 0.02],
                 "gruppen": [gruppe("A1·1", "rauschen", 8, 0.05, eff, "MS-07-2024-einsteinstrasse-R1", 0.62), gruppe("A1·2", "haupt", 30, 0.95)],
                 "stadtgruppen": [{"stadt": "S-F1", "klasse": "schnell", "stand": "nicht_nachweisbar", "gewinn": 0.0, "erwartet_anteil": 0.12,
                                   "erwartet_spanne": [0.08, 0.2]}]},
                {"nr": 2, "geprueft": True, "tage": 40, "fahrzeuge": 15000, "K": 2, "cv_gewinn": [0.0, 0.01],
                 "gruppen": [gruppe("A2·1", "rauschen", 8, 0.04, eff, "MS-07-2024-einsteinstrasse-R1", 0.7), gruppe("A2·2", "haupt", 32, 0.96)],
                 "stadtgruppen": [{"stadt": "S-F1", "klasse": "schnell", "stand": "nachgewiesen", "gewinn": 0.004, "anteil": 0.03,
                                   "erwartet_anteil": 0.12, "erwartet_spanne": [0.08, 0.2]}]},
                {"nr": 3, "geprueft": False, "grund": "zu <kurz>", "tage": 9, "fahrzeuge": 2000,
                 "stadtgruppen": [{"stadt": "S-R1", "klasse": "rauschen", "stand": "erwartet", "erwartet_anteil": 0.1, "erwartet_spanne": [0.05, 0.2]}]}]}}


class Verhaltensgruppen(unittest.TestCase):
    def test_reiter_gruppen(self):
        h = s.seite("07_2024_ Einsteinstraße", [zeile()], {"messungen": [{"datei": "_15.dsd", "geraet": {}, "verwaltung": []}]}, {}, vg=vg_beispiel())
        self.assertIn('id="r-gruppen"', h)
        self.assertIn("Abschnitt 2 (40 Tage mit Wetterdaten", h)
        self.assertIn("Regen&lt;phantome&gt; (S-R1)", h)  # tragfähige Deutung statt Name, maskiert
        self.assertIn("Regen ab 2 mm ×40,00", h)
        self.assertIn('assoziiert mit <a href="#MS-07-2024-einsteinstrasse-R1">', h)
        self.assertIn('korreliert mit <a href="../verhaltensgruppen.html#S-R1">S-R1</a> (62&nbsp;%)', h)
        self.assertIn('<tr id="MS-07-2024-einsteinstrasse-R1">', h)  # MS-Gruppen einmal je Seite
        self.assertIn("A1·1, A2·1", h)
        self.assertIn("lokal nachgewiesen</strong>: Anteil 3,0&nbsp;%", h)
        self.assertIn("hier nicht nachweisbar", h)
        self.assertIn("das ist keine Messung", h)  # nur erwartet
        self.assertIn("zu &lt;kurz&gt;", h)
        self.assertEqual(h.count("Verhaltensgruppen sind Teile des Verkehrs"), 1)
        self.assertNotIn("Stadtweit</h3>", h)  # die Stadtgruppen stehen auf der Übersichtsseite
        ohne = s.seite("01_Anders", [zeile("01_Anders", "x.dsd")], {"messungen": []}, {}, vg=vg_beispiel())
        self.assertIn("kein Verhaltensmodell", ohne)
        self.assertIn("Keine Gruppe kehrt an diesem Standort", ohne)

    def test_forschungsstand_ist_im_labor_modus_versteckt(self):
        h = s.seite("07_2024_ Einsteinstraße", [zeile()], {"messungen": [{"datei": "_15.dsd", "geraet": {}, "verwaltung": []}]}, {}, vg=vg_beispiel())
        self.assertIn('<script src="../labor.js"></script>', h)
        self.assertIn('data-ziel="gruppen" class="labor"', h)  # der Reiter
        self.assertIn('class="reiter-inhalt labor" id="r-gruppen"', h)  # und sein Inhalt
        for rid in ("allgemein", "messung", "analyse", "vergleich"):
            self.assertNotIn(f'data-ziel="{rid}" class="labor"', h)
        self.assertNotIn('id="r-analyse" role="tabpanel" aria-labelledby="t-analyse" data-reiter="analyse"><h2>Analyse</h2><p class="muted labor', h)
        sv = s.verhaltensgruppen_seite(vg_beispiel())
        self.assertIn('<script src="labor.js"></script>', sv)
        self.assertIn('<div class="labor">', sv)
        self.assertIn('class="kein-labor"', sv)
        self.assertIn('name="robots" content="noindex"', sv)

    def test_namen_in_der_auswahl(self):
        namen = s.vg_namen(vg_beispiel(), "07_2024_ Einsteinstraße", "_15.dsd")
        self.assertEqual(sorted(namen), [1, 2])
        self.assertEqual(namen[1][0], "A1·1 · Regen<phantome> (S-R1) · Modus 8 km/h · 5 %")
        self.assertEqual(namen[1][1], "A1·2 · Hauptgruppe · Modus 30 km/h · 95 %")

    def test_uebersichtsseite(self):
        h = s.verhaltensgruppen_seite(vg_beispiel())
        self.assertIn('id="S-R1"', h)
        self.assertIn("Regen&lt;phantome&gt; (S-R1)", h)
        self.assertIn("b &lt;1&gt;", h)
        self.assertIn("in 6 von 10 Abschnitten", h.replace("\n", " "))
        self.assertIn('<a href="standorte/einsteinstrasse.html">Einsteinstraße</a>', h)
        self.assertIn("lokal nachgewiesen in 1", h)
        self.assertIn("×0,80", h)  # Placebo
        kurz = s.verhaltensgruppen_kurz(vg_beispiel())
        self.assertEqual(kurz[0], {"id": "S-R1", "anzeige": "Regen<phantome> (S-R1)", "stufe": "tragfähig", "standorte": 1, "gefunden": True})


class V85Farben(unittest.TestCase):
    def test_stufen_der_verwaltung(self):
        # Tempolimit 30: bis +4 unauffällig, +5..+8 unkritisch (gelb), +9..+10 noch akzeptabel (orange), ab +11 rot
        erwartet = {20: "", 30: "", 34: "", 35: " v85-gelb", 38: " v85-gelb", 39: " v85-orange", 40: " v85-orange", 41: " v85-rot", 60: " v85-rot"}
        for v, k in erwartet.items():
            self.assertEqual(s.klasse_v85(v, 30), k, v)
        self.assertEqual(s.klasse_v85(None, 30), "")
        self.assertEqual(s.klasse_v85(50, None), "")  # ohne Tempolimit keine Färbung

    def test_kennwerttabelle_faerbt_den_v85(self):
        z = zeile()
        z["geschwindigkeit_kmh"] = dict(z["geschwindigkeit_kmh"], v85=41)
        z["teilzeitraeume"]["vormittag"]["geschwindigkeit_kmh"] = dict(z["teilzeitraeume"]["vormittag"]["geschwindigkeit_kmh"], v85=36)
        t = s.kennzahlen_tabelle(z)
        self.assertIn('<td class="num v85-rot">41</td>', t)
        self.assertIn('<td class="num v85-gelb">36</td>', t)
        self.assertIn("ab +11 km/h rot", t)  # Legende

    def test_abschnitte_einzeln_stehen_mit_auswahl_im_noscript(self):
        a = {"nr": 1, "von": "2024-07-24", "bis": "2024-09-03", "tage": 30, "anzahl_fahrzeuge": 0}
        row = dict(zeile(), abschnitte={"geprueft": True, "liste": [a, dict(a, nr=2, von="2024-09-04", bis="2024-12-04")]})
        mit = s.analyse_teil(row, {"v": 1, "limit": 30, "tage": {"0|7": 1}, "z": {"0|7": [30, 5]}, "r": {}, "abschnitte": [
            {"nr": 1, "von": "2024-07-24", "bis": "2024-09-03"}, {"nr": 2, "von": "2024-09-04", "bis": "2024-12-04"}]}, "m-x")
        m = re.search(r"<noscript>((?:(?!</noscript>).)*Abschnitte einzeln.*?)</noscript>", mit, re.S)
        self.assertIsNotNone(m)
        self.assertNotIn("Mit JavaScript", mit)
        ohne = s.analyse_teil(row, None, "m-x")  # ohne Zellen keine Auswahl: die Blöcke stehen offen
        self.assertIn("Abschnitte einzeln", ohne)
        self.assertNotIn("<noscript>", ohne)


class AbschnitteUebersicht(unittest.TestCase):
    def test_eine_zeile_je_abschnitt_und_je_messung_ohne_bruch(self):
        z = zeile()
        k = {"mittel": 18.0, "maximal": 70, "v85": 25, "v95": 30, "v99": 38}
        h = {"einhaltungsquote_prozent": 91.0, "qualifizierte_einhaltungsquote_prozent": 50.0}

        def abschnitt(nr, von, bis, beginn):
            return {"nr": nr, "von": von, "bis": bis, "tage": 40, "anzahl_fahrzeuge": 3000, "beginn": beginn, "geschwindigkeit_kmh": k,
                    "einhaltung": h, "teilzeitraeume": {"nacht": {"anzahl_fahrzeuge": 10, "geschwindigkeit_kmh": k, "einhaltung": h}}}
        mit = dict(z, abschnitte={"geprueft": True, "liste": [abschnitt(1, "2024-07-24", "2024-09-01", {"art": "Beginn der Messung"}),
                                                              abschnitt(2, "2024-09-02", "2024-12-04", {"art": "Bruch", "wahrscheinlichkeit": 0.97})]})
        ohne = dict(zeile("01_Anders", "x.dsd"), abschnitte={"geprueft": True, "liste": []})
        nicht = dict(zeile("02_Kurz", "y.dsd"), abschnitte={"geprueft": False, "grund": "zu kurz"})
        ueb = {"07_2024_ Einsteinstraße/_15.dsd": {"seite": "standorte/einstein.html#m-x", "standort": "Einsteinstraße", "verwaltung": ["V <1>"]}}
        a = s.abschnitte_uebersicht({"standorte": [mit, ohne, nicht]}, ueb)
        self.assertEqual([(x["datei"], x["nr"], x["anzahl"]) for x in a], [("_15.dsd", 1, 2), ("_15.dsd", 2, 2), ("x.dsd", 1, 1), ("y.dsd", 1, 1)])
        self.assertEqual(a[1]["bruch"], 0.97)
        self.assertEqual(a[1]["seite"], "standorte/einstein.html#m-x/messung")
        self.assertEqual(a[1]["metriken"]["roh"]["quote"], 91.0)
        self.assertEqual(a[1]["metriken"]["nacht"]["n"], 10)
        self.assertEqual(a[2]["hinweis"], "kein Bruch erkannt")
        self.assertEqual(a[3]["hinweis"], "")  # nicht prüfbar: kein Hinweis auf „kein Bruch“
        self.assertEqual(a[2]["metriken"]["roh"]["n"], 1000)  # ohne Bruch: roh wie die Datei
        self.assertEqual(a[2]["tage"], 134)  # 24.07. bis 04.12.2024


class Einsatz(unittest.TestCase):
    def test_einsatz_und_messung_waehlbar(self):
        """Ein zusammengesetzter Einsatz steht vor seiner Messung; die Messung nennt, welcher Abschnitt zu einem anderen Einsatz gehört."""
        rel = "07_2024_ Einsteinstraße"
        m = s.messung_eintrag(rel, zeile(), {"standorte": {rel: {"messungen": []}}}, {}, {})
        teil = {"messung": m["id"], "abschnitt": 2, "von": "2024-09-05", "bis": "2024-12-04", "herkunft": "eigen", "stufe": None}
        fremd = {"messung": "m-79-rosmarinstrasse-16", "abschnitt": 1, "von": "2024-12-04", "bis": "2024-12-11", "herkunft": "vorgaenger", "stufe": "belegt",
                 "beleg": {"bruchtag": "2024-12-13", "bruch_wahrscheinlichkeit": 1.0, "score": 0.59, "p_nulltest": 0.012, "nulltest_abschnitte": 85,
                           "verhaeltnis_fahrzeuge": 1.09, "gegenprobe_score": 15.0, "naht": {"stetig": True}}}
        ein = {"id": "e-07-2024-einsteinstrasse-15", "messung": m["id"], "seite": "einsteinstrasse", "name": "Einsteinstraße", "fahrtrichtung": "",
               "geraet": "G", "limit": 30, "status": "abgeleitet", "von": "2024-09-05", "bis": "2024-12-11", "teile": [teil, fremd],
               "abgegeben": [{"abschnitt": 1, "an": "e-76-daimlerstrasse"}], "ausgenommene_tage": ["2024-09-04"],
               "kennzahlen": {"bereinigt": {"anzahl_fahrzeuge": 1000, "geschwindigkeit_kmh": zeile()["geschwindigkeit_kmh"]}, "teilzeitraeume": {}}}
        m["einsatz_info"], m["einsatz_eintrag"] = ein, s.einsatz_eintrag(ein, m, {})
        index = {m["id"]: {"slug": "einsteinstrasse", "name": "Einsteinstraße", "datei": "_15.dsd", "einsatz": ein["id"]},
                 "m-76-daimlerstrasse": {"slug": "daimlerstrasse", "name": "Daimlerstraße", "datei": "x.dsd", "einsatz": "e-76-daimlerstrasse"},
                 "m-79-rosmarinstrasse-16": {"slug": "rosmarinstrasse", "name": "Rosmarinstraße", "datei": "_16.dsd", "einsatz": None}}
        h = s.standortseite("Einsteinstraße", [m], index=index)
        self.assertIn('<optgroup label="Einsätze (unsere Zuordnung)">', h)
        self.assertLess(h.index('value="e-07-2024-einsteinstrasse-15"'), h.index(f'value="{m["id"]}"'))  # Einsatz zuerst
        self.assertIn("aus mehreren Messungen zusammengesetzt (abgeleitet, nicht bestätigt)", h)
        self.assertIn("Zeitraum der Verwaltung umfasst Daten eines anderen Standorts", h)  # Hinweis an der Messung
        self.assertIn('href="daimlerstrasse.html#e-76-daimlerstrasse"', h)
        self.assertIn("Belege der Zuordnung", h)
        self.assertIn('href="rosmarinstrasse.html#m-79-rosmarinstrasse-16"', h)
        ein["status"] = "bestaetigt"
        self.assertIn("von der Verwaltung als unzutreffend bestätigt", s.messung_hinweis(m, index))


class Seite(unittest.TestCase):
    def test_reiter_und_abschnittsauswahl(self):
        z = zeile()
        daten = {"v": 1, "limit": 30, "tage": {"0|7": 1}, "z": {"0|7": "30:5"}, "r": {},
                 "abschnitte": [{"nr": 1, "von": "2024-07-24", "bis": "2024-09-03", "tage": {}, "z": {}, "r": {}},
                                {"nr": 2, "von": "2024-09-04", "bis": "2024-12-04", "tage": {}, "z": {}, "r": {}}]}
        h = s.seite("07_2024_ Einsteinstraße", [z], {"messungen": [{"datei": "_15.dsd", "geraet": {}, "verwaltung": []}]}, {}, {"_15.dsd": daten})
        self.assertIn('data-feld="abschnitt"', h)
        self.assertIn("Abschnitt 2 (04.09.2024 bis 04.12.2024)", h)
        self.assertLess(h.index('data-feld="abschnitt"'), h.index('class="filter-ergebnis"'))
        self.assertIn('role="tablist"', h)
        self.assertNotIn("data-messwahl", h)  # nur eine Messung: keine Auswahl

    def html(self, eintraege=None, rows=None):
        meta = {"messungen": [{"datei": "_15.dsd", "geraet": {"konfiguration": "ABC 123", "erfassung_ab_kmh": 9},
                               "verwaltung": eintraege or []}]}
        uhr = {"07_2024_ Einsteinstraße/_15.dsd": {"abschnitte": [
            {"start": "2024-07-24 09:48:27", "ende": "2024-12-04 10:38:55", "fahrzeuge": 5000, "urteil": "plausibel", "begruendung": ["x <i>y</i>"]},
            {"start": "2024-12-05 00:00:00", "ende": "2024-12-05 01:00:00", "fahrzeuge": 10, "urteil": "unbrauchbar", "begruendung": []}]}}
        return s.seite("07_2024_ Einsteinstraße", rows or [zeile()], meta, uhr)

    def test_einschaetzung_und_massnahmen_stehen_im_wortlaut_auf_der_seite(self):
        h = self.html([eintrag()])
        self.assertIn('id="r-verwaltung"', h)
        self.assertIn("völlig unkritisch", h)
        self.assertIn("Verkehrslenkende Maßnahmen sind nicht erforderlich.", h)
        self.assertIn("Einsteinstraße, FR Hertzstraße (beidseitige Messung)", h)
        self.assertIn("69/338/2025", h)
        self.assertIn("https://ris-neuss.itk-rheinland.de/x?id=1&amp;type=do", h)  # Link maskiert

    def test_ohne_verwaltung_steht_ein_hinweis_da(self):
        h = self.html([])
        self.assertIn("keine Einschätzung veröffentlicht", h)
        self.assertIn("keine Angaben der Verwaltung vor, mit denen sich vergleichen ließe", h)

    def test_daten_werden_maskiert(self):
        h = self.html([eintrag(bezeichnung='<script>alert(1)</script>', stellungnahme_verwaltung=["a <b>b</b> & c."])])
        self.assertNotIn("<script>alert", h)
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
        self.assertIn("Vergleich mit der Verwaltung", h)
        self.assertIn("430 (kommend) + 423 (gehend)", h)
        self.assertIn("Diese Auswertung", h)
        self.assertIn("nur über Straßenname und Sitzungsdatum", h)

    def test_aufprall_laerm_und_naechte(self):
        h = self.html([])
        self.assertIn("nicht mit ihrem Anteil am Verkehr", h)
        self.assertIn("Anhaltestrecke 27,7 m", h)
        self.assertIn('<td class="num">33,6</td>', h)  # Ø Aufprall der Fahrzeuge, die auftreffen
        self.assertIn('<td class="num">69,2</td>', h)  # Aufprall am schnellsten Prozent
        self.assertIn('<td class="num">4,8</td><td class="num">2,5</td><td class="num">1,07</td><td class="num">9,0</td><td class="num">2,2</td>', h)  # je Stunde
        self.assertNotIn("Risikoindex", h)  # Anteile und Mittelwerte ueber alle Fahrzeuge gibt es nicht mehr
        self.assertNotIn("Mittelungspegel</th>", h)
        self.assertIn('<td class="num">0,8</td><td class="num">0,1</td>', h)  # lautere Vorbeifahrten je Stunde
        self.assertNotIn("die auftreffen, je", h)  # gleich der Zahl der Fahrzeuge ueber dem Limit, daher keine eigene Spalte
        self.assertIn("So rechnet das Modell", h)
        self.assertIn("Bei Tempolimit 30&nbsp;km/h", h)  # Umrechnungstabelle fuer das Limit der Datei
        self.assertIn("Lärm (grobe Schätzung)", h)
        self.assertIn("Spitzenpegel", h)
        self.assertIn("Ereignisse pro Nacht", h)
        self.assertIn("In 71 von 154 Nächten (46&nbsp;%) fuhr mindestens ein Fahrzeug mit 100&nbsp;km/h oder mehr", h)

    def test_zusaetzliche_mindestgeschwindigkeit_steht_auf_der_seite(self):
        row = zeile()
        row["auswertung_ab_kmh"], row["fahrzeuge_unter_auswertung_ab"] = 5, 1234
        h = self.html([], rows=[row])
        self.assertIn("Ausgewertet ab", h)
        self.assertIn("5&nbsp;km/h (1.234 langsamere Fahrzeuge in der Datei sind nicht berücksichtigt)", h)
        self.assertNotIn("Ausgewertet ab", self.html([]))  # ohne Angabe keine Zeile

    def rauschzeile(self, **kw):
        row = zeile()
        row["fahrzeuge_in_datei"] = 1200
        row["rauschen"] = {"geprueft": True, "belegt": True, "abgezogen_fahrzeuge": 200, "anteil_prozent": 16.7, "mittel_kmh": 4.9,
                           "obergrenze_kmh": 9, "stabil": True,
                           "spektrum": {"ab_kmh": 3, "rausch": [2040, 1590, 970, 590], "alle": [3130, 2270, 1610, 980]}, **kw}
        return row

    def test_regenanteil_mit_quellenvermerk(self):
        zl = self.rauschzeile()
        zl["rauschen"]["regen"] = {"belegt": True, "regenstunden": 240, "zusatz_je_regenstunde": 12.4, "obergrenze_kmh": 11,
                                   "abgezogen_fahrzeuge": 2976, "stabil": True}
        h = s.rauschen_abschnitt(zl)
        self.assertIn("Bei Regen kommen weitere langsame Datensätze hinzu", h)
        self.assertIn("In den 240 Regenstunden", h)
        self.assertIn("im Mittel 12,4 je Stunde", h)
        self.assertIn("unter 11&nbsp;km/h", h)
        self.assertIn("2.976 Fahrzeuge", h)
        self.assertIn("Quelle: Deutscher Wetterdienst", h)  # Quellenvermerk des DWD (CC BY 4.0) an der Information
        self.assertIn("Die Verkehrsmenge in Regenstunden bleibt unsicher", h)
        zl["rauschen"]["regen"] = {"belegt": False, "regenstunden": 5, "grund": "weniger als 12 Regenstunden in der Datei"}
        h = s.rauschen_abschnitt(zl)
        self.assertIn("Ein Regenanteil ist nicht belegt (weniger als 12 Regenstunden in der Datei)", h)
        self.assertIn("Quelle: Deutscher Wetterdienst", h)
        zl["rauschen"]["regen"] = {"belegt": False, "regenstunden": 0, "grund": "x"}  # kein Regen in der Messung: nichts sagen
        self.assertNotIn("Regenanteil", s.rauschen_abschnitt(zl))
        self.assertNotIn("Regenanteil", s.rauschen_abschnitt(self.rauschzeile()))  # ohne Wetterdaten

    def test_rauschboden_belegt_mit_bild(self):
        h = self.html([], rows=[self.rauschzeile()])
        self.assertIn("Rauschboden (verkehrsunabhängige Messwerte)", h)
        self.assertIn("Bei 16,7&nbsp;% der Messwerte dieser Datei (200 Fahrzeuge)", h)
        self.assertIn("im Mittel bei 4,9&nbsp;km/h, 95&nbsp;% davon unter 9&nbsp;km/h", h)
        self.assertIn("herausgerechnet", h)
        self.assertIn('class="rausch-rot"', h)  # roter Teil im Bild
        self.assertEqual(h.count('class="rausch-alle"'), 4)  # eine graue Saeule je km/h
        self.assertIn("Fahrzeuge in der Datei</dt><dd>1.200", h)
        self.assertNotIn("Ausgewertet ab", h)  # keine Mindestgeschwindigkeit mehr

    def test_rauschbild_nur_im_noscript_wenn_die_auswahl_den_rauschboden_zeigt(self):
        zl = self.rauschzeile()
        offen = s.rauschen_abschnitt(zl)
        self.assertIn("<svg", offen)
        self.assertNotIn("<noscript>", offen)
        mit = s.rauschen_abschnitt(zl, mit_filter=True)
        m = re.search(r"<noscript>(.*?)</noscript>", mit, re.S)
        self.assertEqual(m.group(1).count("<svg"), 1)
        self.assertNotIn("<svg", mit.replace(m.group(0), ""))
        self.assertIn("Bei 16,7&nbsp;% der Messwerte", mit.replace(m.group(0), ""))  # der Text bleibt sichtbar

    def test_rauschboden_nicht_belegt_oder_nicht_nachweisbar_oder_nicht_geprueft(self):
        h = s.rauschen_abschnitt(self.rauschzeile(belegt=False, grund="Anteil in den Haelften nicht stabil"))
        self.assertIn("nicht belegt", h)
        self.assertIn("Es wurde nichts herausgerechnet", h)
        h = s.rauschen_abschnitt({"rauschen": {"geprueft": True, "belegt": False, "grund": "kein verkehrsunabhaengiger Rauschboden nachweisbar",
                                               "anteil_prozent": 0.0}})
        self.assertIn("nicht nachweisen", h)
        self.assertNotIn("<svg", h)
        h = s.rauschen_abschnitt({"rauschen": {"geprueft": False, "grund": "weniger als 3000 Fahrzeuge"}})
        self.assertIn("Nicht geprüft: weniger als 3000 Fahrzeuge", h)
        self.assertEqual(s.rauschen_abschnitt(zeile()), "")  # Altdaten ohne Block

    def test_hinweis_zu_fehlern_steht_oben_und_unten(self):
        h = self.html([])
        self.assertEqual(h.count("Fehler in der Auswertung"), 2)  # Hinweis oben und im Fuss
        self.assertIn("Schätzungen und kein Gutachten", h)
        self.assertIn('class="notice"', h)
    def test_widersprueche_stehen_auf_der_seite(self):
        e = eintrag(tempolimit_widerspruch={"dsd_kmh": 10, "mitteilung_kmh": 30, "verwendet_kmh": 30, "grund": "g"})
        e["abgleich_dsd"]["ausserhalb_des_erfassungszeitraums"] = {
            "davor": {"fahrzeuge": 19198, "v85_kmh": 32, "mittel_kmh": 20.6, "von": "2023-07-19", "bis": "2023-09-12"}}
        meta = {"messungen": [{"datei": "_15.dsd", "geraet": {}, "verwaltung": [e],
                               "doppelte_daten": [{"datei": "48_Lanzerather Dorfstraße/_7.dsd", "anteil_dieser_datei_prozent": 100.0}]}]}
        row = zeile()
        row["tempolimit_quelle"], row["tempolimit_dsd_kmh"] = "mitteilung_verwaltung", 10
        h = s.seite("07_2024_ Einsteinstraße", [row], meta, {})
        self.assertIn("Widersprüche und Auffälligkeiten zwischen DSD und Mitteilung", h)
        self.assertIn("Die Mitteilung nennt 30&nbsp;km/h, die Anzeige-Schwelle in der DSD-Konfiguration steht auf 10&nbsp;km/h", h)
        self.assertIn("Für die Einhaltungsquoten gilt 30&nbsp;km/h", h)
        self.assertIn("laut Mitteilung der Verwaltung; DSD-Konfiguration 10 km/h", h)
        self.assertIn("19.198 Fahrzeuge davor dem Erfassungszeitraum", h)
        self.assertIn("Diese Datei enthält dieselben Fahrzeugdaten wie 48_Lanzerather Dorfstraße/_7.dsd", h)
        self.assertIn("etwa so viel wie eine Richtung", h)  # 430 + 423 gegenueber 522 je Tag

    def test_ohne_widerspruch_kein_hinweisblock(self):
        h = self.html([eintrag(abgleich_dsd={"fahrzeuge_je_tag": 840, "v85_kmh": 31, "mittel_kmh": 25,
                                             "abweichung_dsd_minus_verwaltung": {}})])
        self.assertNotIn("Widersprüche und Auffälligkeiten", h)
    def test_kurze_abschnitte_werden_zusammengefasst(self):
        h = self.html([])
        self.assertIn("1 weitere kurze Abschnitte", h)

    def test_uhr_urteil_kommt_aus_den_belegen_nicht_aus_der_nutzbarkeit(self):
        row = zeile()  # Zeitstempel zu 100 % nutzbar
        abschnitt = {"start": "2024-04-25 18:14:59", "ende": "2024-07-24 06:43:18", "fahrzeuge": 47453, "urteil": "eingeschraenkt",
                     "art": "widerspruch", "begruendung": ["tagesgang: um +90 Minuten verschoben"]}
        h = s.uhr_abschnitt(row, [abschnitt], "x")
        self.assertIn("Uhr eingeschränkt", h)
        self.assertNotIn("Uhr plausibel", h)  # frueher stand hier trotz Widerspruch "plausibel"
        self.assertIn("<strong>nutzbar</strong> (100,0&nbsp;% der Fahrzeuge", h)
        self.assertIn("sagt nicht, dass die Uhrzeit stimmt", h)
        self.assertIn("Widerspruch in den Belegen", h)
        plausibel = dict(abschnitt, urteil="plausibel", art=None)
        self.assertIn("Uhr plausibel", s.uhr_abschnitt(row, [plausibel], "x"))

    def test_uhr_ohne_belege_und_teilweise_nutzbar(self):
        row = zeile()
        row["uhr"] = {"nutzbarkeit": "teilweise_nutzbar", "fahrzeuge_mit_nutzbarer_zeit_prozent": 62.5}
        h = s.uhr_abschnitt(row, [], "x")
        self.assertIn("keine Prüfung der Uhr anhand von Belegen", h)
        self.assertNotIn('class="badge', h)
        self.assertIn("<strong>teilweise nutzbar</strong> (62,5&nbsp;%", h)

    def test_leere_datei(self):
        h = self.html([], rows=[zeile(n=0)])
        self.assertIn("keine Fahrzeugdaten", h)

    def test_abschnitte_mit_begruendung_wahrscheinlichkeit_und_gleichzeitigen_bruechen(self):
        def abschnitt(nr, von, bis, beginn):
            z = zeile()
            return {"nr": nr, "von": von, "bis": bis, "tage": 30, "anzahl_fahrzeuge": 5000, "beginn": beginn,
                    "geschwindigkeit_kmh": z["geschwindigkeit_kmh"], "einhaltung": z["einhaltung"], "teilzeitraeume": z["teilzeitraeume"],
                    "tempolimit_kmh": 30}
        bruch = {"art": "Bruch", "datum": "2025-04-14", "vorher_bis": "2025-04-13", "wahrscheinlichkeit": 0.9995, "luecke_tage": 0,
                 "unterschied_der_verteilungen": 0.4, "begruendung": ["Die Verteilung unterscheidet sich <um> 40 %."]}
        row = dict(zeile(), abschnitte={"geprueft": True, "tage": 60, "anzahl": 2, "brueche": 1, "ausschlaege": [{"von": "2025-03-01", "bis": "2025-03-05"}],
                                        "liste": [abschnitt(1, "2025-03-01", "2025-04-13", {"art": "Beginn der Messung"}),
                                                  abschnitt(2, "2025-04-14", "2025-05-30", bruch)]})
        meta = {"messungen": [{"datei": "_15.dsd", "geraet": {}, "verwaltung": [eintrag(zeitraum=["2025-04-15", "2025-06-30"], bezeichnung="Test")]}]}
        gleich = {("andere Strasse", "x.dsd"): ["2025-04-15"], ("07_2024_ Einsteinstraße", "_15.dsd"): ["2025-04-14"]}
        h = s.seite("07_2024_ Einsteinstraße", [row], meta, {}, None, None, gleich)
        self.assertIn("Abschnitte der Messung", h)
        self.assertIn("Abschnitt 2: 14.04.2025 bis 30.05.2025", h)
        self.assertIn("Bruch vor Abschnitt 2 am 14.04.2025", h)
        self.assertIn("über 99,9&nbsp;%", h)
        self.assertIn("Die Verteilung unterscheidet sich &lt;um&gt; 40 %.", h)
        self.assertIn("Erfassungszeitraum 15.04.2025 bis 30.06.2025", h)
        self.assertIn("von 1 anderen Standorten", h)  # nur der andere Standort zaehlt
        self.assertIn("Kurze Ausschläge", h)
        self.assertNotIn("Gruppen in der Verteilung", h)  # die Formgruppen stehen nur noch in der YAML
        self.assertIn('data-abschnitt="2"', h)  # Gefährdung und Lärm je Abschnitt
        ohne = s.seite("07_2024_ Einsteinstraße", [zeile()], {"messungen": [{"datei": "_15.dsd", "geraet": {}, "verwaltung": []}]}, {})
        self.assertNotIn("Abschnitt 2:", ohne)
        kein = dict(zeile(), abschnitte={"geprueft": True, "tage": 60, "anzahl": 1, "brueche": 0, "liste": [], "ausschlaege": []})
        self.assertIn("kein Bruch erkannt", s.seite("07_2024_ Einsteinstraße", [kein], meta, {}))

    def test_geschaetzte_lage_mit_skizze_und_belegen(self):
        import standorte
        verz = standorte.Verzeichnis([standorte.Adresse("1", "Einsteinstraße", i, "", 1000.0 + (i % 2) * 20, 2000.0 + 10 * i) for i in range(1, 30)])
        st = {"breite": 51.2, "laenge": 6.69, "utm32_ost": 1010, "utm32_nord": 2150, "unsicherheit_m": 90, "methode": "strasse",
              "sicherheit": "manuell korrigiert", "strasse": "Einsteinstraße", "beschreibung": "Mitte <der> Straße",
              "mehrdeutig": "Straße besteht aus getrennten Abschnitten",
              "fahrtrichtung": {"ziel": "Hertzstraße", "peilung_grad": 197, "unsicherheit_grad": 26},
              "belege": [{"art": "strasse", "text": "Einsteinstraße", "stufe": "benannt", "quelle": {"typ": "ordnername"}, "ort": "x",
                          "radius_m": 90, "abstand_zum_ergebnis_m": 0, "verwendet": True, "widerspricht": False},
                         {"art": "adresse", "text": "Nr. 3", "stufe": "vorschlag", "ort": "y", "radius_m": 30, "abstand_zum_ergebnis_m": 400,
                          "quelle": {"typ": "ris", "vorlage": "69/1/2024", "sitzung": "2024-06-26", "dokument": "https://ris-neuss.itk-rheinland.de/x?id=2&type=do"},
                          "verwendet": False, "widerspricht": True}]}
        meta = {"standort": st, "messungen": [{"datei": "_15.dsd", "geraet": {}, "verwaltung": []}]}
        h = s.seite("07_2024_ Einsteinstraße", [zeile()], meta, {}, None, verz)
        self.assertIn("Geschätzte Lage", h)
        self.assertIn("±90 m", h)
        self.assertIn("manuell korrigiert", h)
        self.assertIn('class="hist karte"', h)
        self.assertIn("karte-kreis", h)
        self.assertTrue(0 < h.count('class="karte-haus karte-eigene"') < 29)  # nur Häuser im Ausschnitt
        self.assertIn("Kompassrichtung etwa 197°", h)
        self.assertIn("widerspricht", h)
        self.assertIn("Mitte &lt;der&gt; Straße", h)
        self.assertIn("openstreetmap.org/?mlat=51.2&amp;mlon=6.69", h)
        ohne = s.seite("07_2024_ Einsteinstraße", [zeile()], meta, {}, None, None)
        self.assertNotIn("karte-kreis", ohne)
        self.assertIn("Geschätzte Lage", ohne)
        for url in re.findall(r'(?:href|src)="(https?://[^"]+)"', h):
            self.assertRegex(url, r"^https://(github\.com/Khazuar|ris-neuss\.itk-rheinland\.de|creativecommons\.org|www\.openstreetmap\.org)")

    def test_keine_externen_adressen_ausser_github_und_ris(self):
        h = self.html([eintrag()])
        for url in re.findall(r'(?:href|src)="(https?://[^"]+)"', h):
            self.assertRegex(url, r"^https://(github\.com/Khazuar|ris-neuss\.itk-rheinland\.de|creativecommons\.org)")


def hist(n, mitte=25, streuung=6):
    """Glockenfoermige Zaehlliste von 0 bis 80 km/h mit n Fahrzeugen (ganzzahlig)."""
    gew = [2.718281828 ** (-((v - mitte) / streuung) ** 2 / 2) for v in range(0, 81)]
    anzahl = [int(round(n * g / sum(gew))) for g in gew]
    return {"ab_kmh": 0, "anzahl": anzahl}


class Histogramme(unittest.TestCase):
    def test_klassenbreite_waechst_mit_kleinerem_n(self):
        breiten = [s.klassenbreite(**{"anzahl": h["anzahl"], "ab": 0}) for h in (hist(200000), hist(20000), hist(2000), hist(300), hist(60))]
        self.assertEqual(breiten[0], 1)
        self.assertEqual(breiten[1], 1)
        self.assertEqual(breiten, sorted(breiten))
        self.assertGreaterEqual(breiten[-1], 3)
        self.assertLessEqual(max(breiten), s.HIST_BREITE_MAX)

    def test_klassen_beginnen_bei_limit_plus_eins(self):
        h = hist(5000)
        for breite in (1, 2, 3, 5):
            kl = s.hist_klassen(h["anzahl"], 0, breite, 30, 0, 60)
            starts = [a for a, _, _ in kl]
            self.assertIn(31, starts)
            self.assertTrue(all(b - a == breite - 1 for a, b, _ in kl))
            self.assertTrue(all(not (a <= 30 < b) for a, b, _ in kl))  # keine Klasse ueber dem Limit
            self.assertEqual(sum(c for _, _, c in kl), sum(h["anzahl"][:61]))  # nichts geht verloren

    def test_svg_enthaelt_saeulen_limit_und_v85(self):
        svg, text = s.hist_svg([("alle", "", hist(20000))], 30, 33)
        self.assertGreater(svg.count("<rect"), 30)  # eine Saeule je km/h mit Fahrzeugen
        self.assertIn("hist-ueber", svg)
        self.assertIn("hist-ok", svg)
        self.assertIn("Limit 30", svg)
        self.assertIn("V85 33", svg)
        self.assertIn("Klassenbreite 1&nbsp;km/h (Auflösung der Geräte)", text)
        self.assertNotIn("xmlns", svg)  # Inline-SVG braucht keinen Namensraum, und keine fremde Adresse

    def test_wenige_fahrzeuge_werden_zusammengefasst_und_erklaert(self):
        svg, text = s.hist_svg([("alle", "", hist(120))], 30, 33)
        self.assertNotIn("Auflösung der Geräte", text)
        self.assertIn("zusammengefasst, weil nur 120 Fahrzeuge vorliegen", text)

    def test_ausreisser_werden_abgeschnitten_aber_genannt(self):
        h = hist(10000)
        h["anzahl"] += [0] * 150 + [1]  # ein Fahrzeug mit 231 km/h
        svg, text = s.hist_svg([("alle", "", h)], 30, 30)
        self.assertIn("1 Fahrzeug über", text)
        self.assertIn("schnellstes: 231", text)

    def test_abschnitt_auf_der_seite(self):
        row = zeile()
        row["histogramm"] = hist(5000)
        for k, n in (("vormittag", 2000), ("nachmittag", 2000), ("abend", 500)):
            row["teilzeitraeume"][k]["histogramm"] = hist(n)
        row["teilzeitraeume"]["nacht"]["histogramm"] = hist(400, 30)
        a = s.histogramm_abschnitt(row)
        self.assertIn("Verteilung der Geschwindigkeiten", a)
        self.assertNotIn("Tag und Nacht im Vergleich", a)  # Tag gegen Nacht zeigt die Auswahl
        self.assertEqual(a.count("<svg"), 1)

    def test_mit_filter_steht_das_feste_histogramm_nur_im_noscript(self):
        row = zeile()
        row["histogramm"] = hist(5000)
        a = s.histogramm_abschnitt(row, mit_filter=True)
        m = re.search(r"<noscript>(.*?)</noscript>", a, re.S)
        self.assertIn("Verteilung der Geschwindigkeiten", m.group(1))
        self.assertEqual(m.group(1).count("<svg"), 1)
        self.assertEqual(a.replace(m.group(0), ""), "")  # ausserhalb des noscript-Blocks steht nichts

    def test_zu_wenige_fahrzeuge_oder_kein_histogramm(self):
        row = zeile()
        self.assertEqual(s.histogramm_abschnitt(row), "")
        row["histogramm"] = hist(s.HIST_MIN_FAHRZEUGE - 10)
        self.assertEqual(s.histogramm_abschnitt(row), "")


class FilterSeite(unittest.TestCase):
    _zerlegung = None

    def daten(self):
        """Datentabelle der Testdaten (einmal gerechnet; die Tests veraendern die Rueckgabe nicht, sondern kopieren sie)."""
        import copy
        if FilterSeite._zerlegung is None:
            import test_gruppen as tg
            fahrten, spannen = tg.fahrten_und_spannen(tage=28)
            FilterSeite._zerlegung = gruppen.datentabelle(gruppen.zellen_bauen(fahrten, fahrten, spannen), 30)
        return copy.deepcopy(FilterSeite._zerlegung)

    def html(self, daten):
        row = zeile()
        return s.seite("07_2024_ Einsteinstraße", [row], {"messungen": []}, {}, {row["datei"]: daten})

    def test_abschnitt_daten_und_skript(self):
        daten = self.daten()
        daten["verhalten"] = {"profile": [[0.5, 0.5] + [0.0] * 44, [0.0] * 15 + [1.0] + [0.0] * 30], "klassen": ["rauschen", "haupt"],
                              "raten": {"0|7": [1.0, 20.0]}}
        h = self.html(daten)
        self.assertIn("Auswertung nach Zeit, Tagen, Abschnitt und Gruppe", h)
        self.assertIn("<noscript>", h)
        self.assertIn('<section class="filter" data-filter hidden>', h)  # ohne JavaScript bleibt der Abschnitt verborgen
        self.assertIn('<input type="checkbox" data-isoliert>', h)  # Auswahl isoliert darstellen (Standard aus)
        self.assertNotIn('data-isoliert checked', h)
        self.assertIn('<script src="../filter.js" defer></script>', h)
        for name in ("Alle Daten", 'value="v1">Gruppe 1<', 'value="v2">Gruppe 2<', "Ganztägig", "Nacht (22–6 Uhr)", "Schulweg (7–8 Uhr)",
                     "Werktage (Mo–Fr)", "Sonn- und Feiertage", "Feiertage an Werktagen und Samstagen", ">Montag<", "Verhaltensgruppen des Abschnitts"):
            self.assertIn(name, h, name)
        for nicht in ("Rest (nicht erklärt)", "Rauschboden (herausgerechnet)", "nachgepasst"):
            self.assertNotIn(nicht, h, nicht)  # keine Formgruppen; ohne abgezogenen Rauschboden keine solche Auswahl
        m = re.search(r'<script type="application/json" class="filter-daten">(.*?)</script>', h, re.S)
        eingebettet = json.loads(m.group(1))
        self.assertEqual(eingebettet, s.filter_daten(daten))  # die Tabelle im Seitentext ist die Datentabelle
        self.assertEqual(eingebettet["verhalten"], daten["verhalten"])
        d2 = dict(daten, r={"0|8": [10, 5]})
        self.assertIn("Rauschboden (herausgerechnet)", self.html(d2))
        d1 = {k: v for k, v in daten.items() if k != "verhalten"}  # keine Verhaltensgruppen, kein Rauschboden: kein Feld "Gruppe"
        h1 = self.html(d1)
        self.assertNotIn('data-feld="gruppe"', h1)
        self.assertIn('data-feld="zeit"', h1)
        self.assertIn('data-feld="tage"', h1)

    def test_auswahl_nur_trockene_stunden(self):
        daten = self.daten()
        self.assertNotIn('data-feld="wetter"', self.html(daten))  # ohne Zellen fuer trockene Stunden keine Auswahl
        daten["trocken"] = {"tage": {"0|7": 1}, "z": {"0|7": [30, 1]}, "r": {}}
        h = self.html(daten)
        self.assertIn('data-feld="wetter"', h)
        self.assertIn(">Nur trockene Stunden<", h)
        self.assertIn("docs/totzeit.md", h)
        m = re.search(r'<script type="application/json" class="filter-daten">(.*?)</script>', h, re.S)
        self.assertEqual(json.loads(m.group(1))["trocken"], daten["trocken"])  # die Zellen kommen mit in die Datentabelle

    def test_namen_kommen_in_die_datentabelle(self):
        daten = self.daten()
        daten["abschnitte"] = [{"nr": 1, "von": "2024-07-24", "bis": "2024-09-03", "tage": {}, "z": {}, "r": {},
                                "verhalten": {"profile": [[1.0] + [0.0] * 45], "klassen": ["haupt"], "raten": {}}},
                               {"nr": 2, "von": "2024-09-04", "bis": "2024-12-04", "tage": {}, "z": {}, "r": {}}]
        d = s.filter_daten(daten, {1: ["A1·1 · Hauptgruppe"]})
        self.assertEqual(d["abschnitte"][0]["verhalten"]["namen"], ["A1·1 · Hauptgruppe"])
        self.assertNotIn("verhalten", d["abschnitte"][1])
        self.assertNotIn("namen", daten["abschnitte"][0]["verhalten"])  # die Eingabe bleibt unveraendert

    def test_feste_kennzahlentabelle_steht_mit_auswahl_nur_im_noscript(self):
        daten = self.daten()
        h = self.html(daten)
        self.assertEqual(h.count("Kennzahlen dieser Messung nach Zeitraum"), 1)
        m = re.search(r"<noscript>((?:(?!</noscript>).)*Kennzahlen dieser Messung nach Zeitraum.*?)</noscript>", h, re.S)
        self.assertIsNotNone(m)  # die Tabelle steht im noscript-Block
        self.assertIn("<th>Zeitraum</th>", m.group(1))
        ohne = self.html(None)  # ohne Zellen keine Auswahl: die Tabelle steht offen
        self.assertEqual(ohne.count("Kennzahlen dieser Messung nach Zeitraum"), 1)
        self.assertNotIn("<noscript>", ohne)

    def test_seite_zeigt_das_histogramm_nur_einmal_mit_javascript(self):
        daten = self.daten()
        row = zeile()
        row["histogramm"] = hist(5000)
        h = s.seite("07_2024_ Einsteinstraße", [row], {"messungen": []}, {}, {row["datei"]: daten})
        self.assertEqual(h.count("Verteilung der Geschwindigkeiten"), 1)
        self.assertLess(h.index("<noscript><h4>Verteilung der Geschwindigkeiten"), h.index("</noscript>", h.index("<noscript><h4>Verteilung")))
        ohne = s.seite("07_2024_ Einsteinstraße", [row], {"messungen": []}, {}, {})  # ohne Zellen: kein Filter, das Histogramm steht offen
        self.assertEqual(ohne.count("Verteilung der Geschwindigkeiten"), 1)
        self.assertNotIn("<noscript>", ohne)

    def test_json_kann_das_skript_nicht_beenden(self):
        self.assertNotIn("</script", s.json_in_html({"a": "</script><script>alert(1)</script>", "b": "<!--"}))
        self.assertEqual(json.loads(s.json_in_html({"a": "</x>"})), {"a": "</x>"})

    def test_ohne_zellen_kein_abschnitt_und_kein_skript(self):
        h = self.html(None)
        self.assertNotIn("Auswertung nach Zeit, Tagen und Gruppe", h)
        self.assertNotIn("filter.js", h)
        self.assertNotIn("<noscript>", h)

    def test_keine_externen_adressen_im_filter(self):
        h = self.html(self.daten())
        for url in re.findall(r'(?:href|src)="(https?://[^"]+)"', h):
            self.assertRegex(url, r"^https://(github\.com/Khazuar|ris-neuss\.itk-rheinland\.de|creativecommons\.org)")

    def test_bauen_liest_die_zellen(self):
        daten = self.daten()
        zl = zeile()
        with tempfile.TemporaryDirectory() as d:
            ordner = os.path.join(d, zl["standort"])
            os.makedirs(ordner)
            with open(os.path.join(ordner, "_15.zellen.json"), "w", encoding="utf-8") as fh:
                json.dump(daten, fh)
            seiten = s.bauen({"standorte": [zl]}, {"standorte": {}}, {"dateien": {}}, d, d)
            with open(os.path.join(d, "standorte", list(seiten)[0] + ".html"), encoding="utf-8") as fh:
                self.assertIn("filter-daten", fh.read())

class Bauen(unittest.TestCase):
    def test_alle_seiten_werden_geschrieben(self):
        auswertung = {"standorte": [zeile(), zeile("Stationär_Villestraße/FR GV", "a.dsd")]}
        meta = {"standorte": {}}
        uhr = {"dateien": {}}
        with tempfile.TemporaryDirectory() as d:
            slugs = s.bauen(auswertung, meta, uhr, d)
            self.assertEqual(sorted(slugs), ["einsteinstrasse", "stationaer-villestrasse-fr-gv"])
            for slug in slugs:
                with open(os.path.join(d, "standorte", slug + ".html"), encoding="utf-8") as fh:
                    self.assertIn("<h1>", fh.read())
            # alte Adresse je Ordner leitet weiter
            with open(os.path.join(d, "standorte", "07-2024-einsteinstrasse.html"), encoding="utf-8") as fh:
                self.assertIn('url=einsteinstrasse.html#m-07-2024-einsteinstrasse-15', fh.read())
            with open(os.path.join(d, "uebersicht.json"), encoding="utf-8") as fh:
                ueb = json.load(fh)
            self.assertEqual(ueb["07_2024_ Einsteinstraße/_15.dsd"]["seite"], "standorte/einsteinstrasse.html#m-07-2024-einsteinstrasse-15")

    def test_messungen_derselben_strasse_auf_einer_seite(self):
        def st(ost):
            return {"standort": {"strasse": "Teststraße", "utm32_ost": ost, "utm32_nord": 0, "unsicherheit_m": 100, "breite": 51.2, "laenge": 6.7,
                                 "methode": "strasse", "sicherheit": "benannt", "beschreibung": "x", "belege": []}, "messungen": []}
        auswertung = {"standorte": [zeile("01_Teststraße", "a.dsd"), zeile("02_Teststraße", "b.dsd"), zeile("03_Teststraße", "c.dsd")]}
        meta = {"standorte": {"01_Teststraße": st(0), "02_Teststraße": st(150), "03_Teststraße": st(5000)}}
        gr = s.standortgruppen(auswertung, meta)
        self.assertEqual([(g[0], g[2]) for g in gr], [("teststrasse", ["01_Teststraße", "02_Teststraße"]), ("teststrasse-2", ["03_Teststraße"])])
        with tempfile.TemporaryDirectory() as d:
            s.bauen(auswertung, meta, {"dateien": {}}, d)
            with open(os.path.join(d, "standorte", "teststrasse.html"), encoding="utf-8") as fh:
                h = fh.read()
        self.assertIn("data-messwahl", h)
        self.assertEqual(h.count('<option value="m-'), 2)
        self.assertIn('data-messung="m-01-teststrasse-a"', h)
        for rid, _ in s.REITER:
            self.assertIn(f'id="r-{rid}"', h)
        self.assertIn('src="../seite.js"', h)


if __name__ == "__main__":
    unittest.main()
