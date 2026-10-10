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

    def test_vergleich_hat_zwei_linien_und_legende(self):
        tags, nachts = hist(5000), hist(800, 30)
        svg, _ = s.hist_svg([("Tags", "hist-tags", tags), ("Nachts", "hist-nachts", nachts)], 30)
        self.assertEqual(svg.count("<polyline"), 2)
        self.assertIn(f"Tags ({s.ganz(sum(tags['anzahl']))})", svg)  # Rundung der Testdaten: nicht exakt 5000
        self.assertIn(f"Nachts ({s.ganz(sum(nachts['anzahl']))})", svg)

    def test_abschnitt_auf_der_seite(self):
        row = zeile()
        row["histogramm"] = hist(5000)
        for k, n in (("vormittag", 2000), ("nachmittag", 2000), ("abend", 500)):
            row["teilzeitraeume"][k]["histogramm"] = hist(n)
        row["teilzeitraeume"]["nacht"]["histogramm"] = hist(400, 30)
        a = s.histogramm_abschnitt(row)
        self.assertIn("Verteilung der Geschwindigkeiten", a)
        self.assertIn("Tag und Nacht im Vergleich", a)
        self.assertIn(f"Tag ({s.ganz(sum(hist(2000)['anzahl']) * 2 + sum(hist(500)['anzahl']))})", a)  # Tag = Vormittag + Nachmittag + Abend
        self.assertEqual(a.count("<svg"), 2)
        row["teilzeitraeume"]["nacht"]["histogramm"] = hist(60, 30)  # zu wenige fuer den Vergleich
        self.assertEqual(s.histogramm_abschnitt(row).count("<svg"), 1)

    def test_hist_summe(self):
        h = s.hist_summe([{"ab_kmh": 10, "anzahl": [1, 2]}, None, {"ab_kmh": 11, "anzahl": [5, 5]}])
        self.assertEqual(h, {"ab_kmh": 10, "anzahl": [1, 7, 5]})
        self.assertIsNone(s.hist_summe([None]))
    def test_zu_wenige_fahrzeuge_oder_kein_histogramm(self):
        row = zeile()
        self.assertEqual(s.histogramm_abschnitt(row), "")
        row["histogramm"] = hist(s.HIST_MIN_FAHRZEUGE - 10)
        self.assertEqual(s.histogramm_abschnitt(row), "")


class FilterSeite(unittest.TestCase):
    def daten(self):
        import test_gruppen as tg
        fahrten, spannen = tg.fahrten_und_spannen(tage=28)
        block, daten = gruppen.analysiere(gruppen.zellen_bauen(fahrten, fahrten, spannen), 30, True)
        return block, daten

    def html(self, daten, block=None):
        row = zeile()
        row["gruppen"] = block or {"geprueft": False, "grund": "x"}
        return s.seite("07_2024_ Einsteinstraße", [row], {"messungen": []}, {}, {row["datei"]: daten})

    def test_abschnitt_daten_und_skript(self):
        block, daten = self.daten()
        h = self.html(daten, block)
        self.assertIn("Auswertung nach Zeit, Tagen und Gruppe", h)
        self.assertIn("<noscript>", h)
        self.assertIn('<section class="filter" data-filter hidden>', h)  # ohne JavaScript bleibt der Abschnitt verborgen
        self.assertIn('<script src="../filter.js" defer></script>', h)
        for name in ("Alle Daten", "Gruppe 1 (Modus", "Gruppe 2 (Modus", "Rest (nicht erklärt)", "Ganztägig", "Nacht (22–6 Uhr)", "Schulweg (7–8 Uhr)",
                     "Werktage (Mo–Fr)", "Sonn- und Feiertage", "Feiertage an Werktagen und Samstagen", ">Montag<"):
            self.assertIn(name, h, name)
        for nicht in ("Hauptmenge", "(langsam)", "Rauschboden (herausgerechnet)", "Unter "):
            self.assertNotIn(nicht, h, nicht)  # keine Auszeichnung "langsam" oder "Haupt-"; ohne abgezogenen Rauschboden keine solche Gruppe
        m = re.search(r'<script type="application/json" class="filter-daten">(.*?)</script>', h, re.S)
        self.assertEqual(json.loads(m.group(1)), daten)  # die Tabelle im Seitentext ist genau die Datentabelle
        d2 = dict(daten, r={"0|8": [10, 5]})
        self.assertIn("Rauschboden (herausgerechnet)", self.html(d2, block))
        d1 = dict(daten, gruppen=[])  # keine Zerlegung: kein Feld "Gruppe"
        h1 = self.html(d1)
        self.assertNotIn('data-feld="gruppe"', h1)
        self.assertIn('data-feld="zeit"', h1)
        self.assertIn('data-feld="tage"', h1)
    def test_json_kann_das_skript_nicht_beenden(self):
        self.assertNotIn("</script", s.json_in_html({"a": "</script><script>alert(1)</script>", "b": "<!--"}))
        self.assertEqual(json.loads(s.json_in_html({"a": "</x>"})), {"a": "</x>"})

    def test_ohne_zellen_kein_abschnitt_und_kein_skript(self):
        h = self.html(None)
        self.assertNotIn("Auswertung nach Zeit, Tagen und Gruppe", h)
        self.assertNotIn("filter.js", h)
        self.assertNotIn("<noscript>", h)

    def test_gruppen_tabelle(self):
        block, _ = self.daten()
        h = s.gruppen_abschnitt({"gruppen": block})
        self.assertIn("Gruppen in der Verteilung", h)
        self.assertIn(">Gruppe 1<", h)
        self.assertIn("Rest (nicht erklärt)", h)
        for nicht in ("(langsam)", "Hauptmenge", "nächst schnelleren"):
            self.assertNotIn(nicht, h, nicht)
        self.assertIn("keine Fahrzeugarten", h)
        self.assertIn("Fahrzeuge werden den Gruppen nicht zugeordnet", h)
        self.assertIn("müssen sich nicht zu 100", h)
        self.assertIn("2 Gruppen zusammen", h)
        self.assertIn("weichen von den Daten bei etwa", h)  # Passung des Modells
        self.assertIn("Nicht zerlegt", s.gruppen_abschnitt({"gruppen": {"geprueft": False, "grund": "zu klein"}}))
        self.assertIn("nicht stabil", s.gruppen_abschnitt({"gruppen": {"geprueft": True, "anzahl": 1}}))
        self.assertEqual(s.gruppen_abschnitt({}), "")
        self.assertNotIn("Kurven angepasst", h)  # eine Kurve je Gruppe: nichts zu erklaeren

    def test_gruppe_aus_mehreren_kurven(self):
        block, _ = self.daten()
        mehr = dict(block, kurven=3, gruppen=[dict(block["gruppen"][0]), dict(block["gruppen"][1], kurven=2)])
        h = s.gruppen_abschnitt({"gruppen": mehr})
        self.assertIn("Gruppe 2 <span", h)
        self.assertIn("(aus 2 Kurven)", h)
        self.assertNotIn("(aus 1 Kurven)", h)
        self.assertIn("aus 3 Kurven angepasst", h)
        self.assertIn("nicht belegt", h)  # die Aufteilung innerhalb einer Gruppe wird nicht ausgewiesen

    def test_warnung_bei_schlechter_passung(self):
        block, daten = self.daten()
        schlecht = dict(block, modellabweichung_prozent=15.5)
        self.assertIn("Das Modell passt hier schlecht", s.gruppen_abschnitt({"gruppen": schlecht}))
        self.assertIn("Das Modell passt hier schlecht", self.html(daten, schlecht))  # auch im Abschnitt mit der Auswahl
        gut = dict(block, modellabweichung_prozent=3.0)
        self.assertNotIn("Das Modell passt hier schlecht", s.gruppen_abschnitt({"gruppen": gut}))
        self.assertEqual(s.modell_warnung({}), "")
    def test_keine_externen_adressen_im_filter(self):
        h = self.html(*reversed(self.daten()))
        for url in re.findall(r'(?:href|src)="(https?://[^"]+)"', h):
            self.assertRegex(url, r"^https://(github\.com/Khazuar|ris-neuss\.itk-rheinland\.de|creativecommons\.org)")

    def test_bauen_liest_die_zellen(self):
        _, daten = self.daten()
        zl = zeile()
        with tempfile.TemporaryDirectory() as d:
            ordner = os.path.join(d, zl["standort"])
            os.makedirs(ordner)
            with open(os.path.join(ordner, "_15.zellen.json"), "w", encoding="utf-8") as fh:
                json.dump(daten, fh)
            s.bauen({"standorte": [zl]}, {"standorte": {}}, {"dateien": {}}, d, d)
            with open(os.path.join(d, "standorte", dsd2csv.standort_slug(zl["standort"]) + ".html"), encoding="utf-8") as fh:
                self.assertIn("filter-daten", fh.read())

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
