# SPDX-License-Identifier: MIT
"""Tests fuer tools/ris_messstellen.py (Zerlegen der Mitteilungen) und metadaten.py (Zuordnung).
Aufruf: python3 -m unittest -v"""
import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import metadaten as m  # noqa: E402
import ris_messstellen as r  # noqa: E402

# Ausschnitte aus echten Mitteilungen (Wortlaut inklusive der Trennfehler aus dem PDF-Text)
NEU = ("Inhalt der Mitteilung: Der Erfassungszeitraum war vom 26.10.2025 bis 29.03.2026. Rosellener Kirchstraße (Tempo 30): "
       "Der maßgebliche V85-Wert mit 41 km/h ist, bei vorgeschriebenen 30 km/h, überdurchschnittlich hoch. Im Erfassungszeitraum "
       "gab es ca. 320 Fahrzeugbewegungen (kommend) pro Tag bzw. 466 Fahrzeugbewegungen (gehend) pro Tag. Der überwiegende Anteil "
       "der Kraftfahrer, nämlich ca. 83%, fuhr unter 40 km/h. Das durchschnittliche Tempo betrug 34 km/h. "
       "Hier muss mit der Kreispolizeibehörde Neuss über geeignete Maßnahmen gesprochen werden.")
ALT = ("Inhalt der Mitteilung: Folgende Ergebnisse haben die Geschwindigkeitsmessungen auf der Villestraße im Zeitraum vom "
       "15.03.2023 bis 11.01.2024 ergeben: Fahrtrichtung Grevenbroich Im Zeitraum vom 15.03.2023 bis 11.01.2024 wurden insgesamt "
       "702.354 Fahrzeugbewegungen erfasst. Die durchschnittliche Geschwindigkeit betrug genau 50 km/h. Der maßgebliche V 85-Wert, "
       "der sich aus der Geschwindigkeit ergibt, die von 85 Prozent der erfassten Fahrzeuge nicht überschritten wird, betrug 56 km/h. "
       "Im Zeitraum vom 11.01.2024 bis 19.03.2024 wurden insgesamt 152.300 Fahrzeugbewegen erfasst. Die durchschnittliche "
       "Geschwindigkeit betrug 49 km/h. Fahrtrichtung Norf Im Zeitraum vom 15.03.2023 bis 11.01.2024 wurden insgesamt 899.118 "
       "Fahrzeugbewegungen erfasst. Der maßgebliche V85 -Wert betrug 57 km/h.")
DEFEKT = ("Inhalt der Mitteilung: Quinheimer Straße: Bei vorgeschriebenen 30 km/h betrug der maßgebliche V85 -Wert , der sich aus "
          "der Geschwindigkeit ergibt, die von 85 Prozent der erfassten Fahrzeuge nicht überschritten wird, 32 km/h. Im "
          "Erfassungsz eitraum vom 19.03.2024 bis 24.07.2024 gab es 669 Fahrzeu gbewegungen (ko mmend) und 723 Fahrzeugbewegungen "
          "(gehend) täglich. Das durchschnittlic he Tempo be trug 23 km/h. Es sollte berücksichtigt werden, dass hier ein hoher "
          "Prozentsatz von Radfahrer*innen erfasst ist.")


class Zerlegen(unittest.TestCase):
    def test_neues_format_mit_zeitraum_satz(self):
        bloecke, offen = r.zerlege(NEU)
        self.assertEqual(len(bloecke), 1)
        b = bloecke[0]
        self.assertEqual((b["strasse"], b["zeitraum"], b["tempolimit_kmh"]), ("Rosellener Kirchstraße", ["2025-10-26", "2026-03-29"], 30))
        self.assertEqual((b["v85_kmh"], b["mittel_kmh"]), (41, 34))
        self.assertEqual(b["fahrzeuge_je_tag"], {"kommend": 320, "gehend": 466})
        self.assertEqual(b["anteil_unter"], {"prozent": 83.0, "kmh": 40})
        self.assertEqual(b["einstufung_verwaltung"], "ueberdurchschnittlich_hoch")
        self.assertIn("Kreispolizeibehörde", b["massnahmen_verwaltung"])

    def test_aelteres_format_mit_richtungen_und_zeitraeumen(self):
        bloecke, _ = r.zerlege(ALT)
        werte = [(b["fahrtrichtung"], tuple(b["zeitraum"]), b.get("v85_kmh"), b["fahrzeuge_im_zeitraum"]["gesamt"]) for b in bloecke]
        self.assertEqual(werte, [
            ("Grevenbroich", ("2023-03-15", "2024-01-11"), 56, 702354),
            ("Grevenbroich", ("2024-01-11", "2024-03-19"), None, 152300),
            ("Norf", ("2023-03-15", "2024-01-11"), 57, 899118)])

    def test_trennfehler_aus_dem_pdf(self):
        b = r.zerlege(DEFEKT)[0][0]
        self.assertEqual((b["tempolimit_kmh"], b["v85_kmh"], b["mittel_kmh"]), (30, 32, 23))
        self.assertEqual(b["fahrzeuge_je_tag"], {"kommend": 669, "gehend": 723})
        self.assertEqual(b["zeitraum"], ["2024-03-19", "2024-07-24"])
        self.assertIn("Hoher Anteil Radfahrende erfasst, die Geräte unterscheiden nicht zwischen Rad und Kfz", b["hinweise_verwaltung"])

    def test_zwei_doppelpunkte_im_kopf(self):
        t = ("Inhalt der Mitteilung: Daimlerstraße: Folgende Messungen hat es im Bereich der Daimlerstraße 140 gegeben: "
             "Der maßgebliche V85 -Wert ist mit 34 km/h bei vorgeschriebenen 30 km/h unkritisch.")
        bloecke, _ = r.zerlege(t)
        self.assertEqual([(b["strasse"], b["v85_kmh"]) for b in bloecke], [("Daimlerstraße", 34)])

    def test_ohne_messwerte_geht_nicht_verloren(self):
        t = "Inhalt der Mitteilung: Für die Messstelle Further Straße liegen aufgrund eines technischen Defektes keine Daten vor."
        bloecke, offen = r.zerlege(t)
        self.assertEqual(bloecke, [])
        self.assertEqual(offen[0]["kopf"], "Further Straße")

    def test_datum_ohne_jahr_im_ersten_datum(self):
        self.assertEqual(r.zeitraum("16.09.", "04.12.2024"), ["2024-09-16", "2024-12-04"])
        self.assertEqual(r.zeitraum("16.11.", "19.03.2024"), ["2023-11-16", "2024-03-19"])

    def test_kopf(self):
        k = r.kopf_zerlegen("Am alten Bach, FR Supermarkt Rewe, beidseitige Messung")
        self.assertEqual((k["strasse"], k["fahrtrichtung"], k.get("beidseitig")), ("Am alten Bach", "Supermarkt Rewe", True))
        self.assertEqual(r.kopf_zerlegen("Villestraße (FR Speck)")["fahrtrichtung"], "Speck")
        self.assertEqual(r.kopf_zerlegen("Neukirchener Straße, FR Aller heiligen")["fahrtrichtung"], "Allerheiligen")


def datei(rel, name, tage, v85=30, mittel=25, n=50000, ende=None):
    """Kuenstliche DSD-Datei mit einem Fahrzeug je Tag (nur Tage und Kennzahlen zaehlen) und konstanter Geschwindigkeit."""
    start = dt.date.fromisoformat(tage[0])
    zeiten = [dt.datetime.combine(start + dt.timedelta(days=i), dt.time(12)) for i in range((dt.date.fromisoformat(tage[1]) - start).days + 1)]
    gueltig = [(t, v85) for t in zeiten]
    return {"rel": rel, "datei": name, "meta": {}, "alle": gueltig, "gueltig": gueltig, "tage": {t.date() for t in zeiten},
            "namen": [m.schluessel(n) for n in m.messort_namen(rel)], "richtungen": m.richtungen(f"{rel} {name}")}


def block(strasse, v85, zeitraum=None, sitzung="2025-06-01", **kw):
    b = {"bezeichnung": strasse, "strasse": strasse, "zeitraum": zeitraum, "v85_kmh": v85,
         "quellen": [{"vorlage": "69/1/2025", "sitzung": sitzung, "gremium": "x", "dokument": "http://x"}]}
    b.update(kw)
    return b


class Zuordnung(unittest.TestCase):
    def test_name(self):
        self.assertTrue(m.passt_name("Lupinenstraße", [m.schluessel("Lupinen")]))
        self.assertTrue(m.passt_name("Eingang Pomona", [m.schluessel("Pomona")]))
        self.assertTrue(m.passt_name("Im Tal", [m.schluessel(n) for n in m.messort_namen("23-2023_Im_Tal")]))
        self.assertFalse(m.passt_name("Martinusstraße", [m.schluessel("Martinstraße")]))

    def test_richtung(self):
        norf = datei("Stationär_Villestraße/FR Norf", "Ville Norf_3.dsd", ("2024-01-01", "2024-02-01"))
        gv = datei("Stationär_Villestraße/FR GV", "L 142 FR Speck20_3.dsd", ("2024-01-01", "2024-02-01"))
        self.assertTrue(m.passt_richtung({"fahrtrichtung": "Norf"}, norf))
        self.assertFalse(m.passt_richtung({"fahrtrichtung": "Norf"}, gv))
        self.assertTrue(m.passt_richtung({"fahrtrichtung": "Grevenbroich"}, datei("S/FR GV", "a.dsd", ("2024-01-01", "2024-02-01"))))
        self.assertTrue(m.passt_richtung({"fahrtrichtung": "Speck"}, gv))  # Richtung steht im Dateinamen
        self.assertFalse(m.passt_richtung({"fahrtrichtung": "Speck"}, norf))
        self.assertTrue(m.passt_richtung({}, norf))

    def test_zeitraum_waehlt_die_richtige_von_zwei_gleichnamigen_strassen(self):
        a = datei("94_Ruhrstraße", "a.dsd", ("2025-04-17", "2025-07-06"))
        b = datei("109_Ruhrstraße", "b.dsd", ("2025-10-26", "2026-03-23"))
        zu, offen = m.zuordnen([block("Ruhrstraße", 36, ["2025-10-26", "2026-03-29"], sitzung="2026-07-02")], [a, b])
        self.assertEqual(list(zu), [("109_Ruhrstraße", "b.dsd")])
        self.assertEqual(offen, [])
        self.assertEqual(zu[("109_Ruhrstraße", "b.dsd")][0][1]["methode"], "name_zeitraum")

    def test_ohne_zeitraum_entscheiden_werte_und_sitzung(self):
        alt = datei("60_Mühlenstraße", "a.dsd", ("2023-12-12", "2024-02-13"), v85=24)
        neu = datei("87_Mühlenstraße", "b.dsd", ("2024-12-04", "2025-02-21"), v85=24)
        zu, offen = m.zuordnen([block("Mühlenstraße", 24, None, sitzung="2025-06-24")], [alt, neu])
        self.assertEqual(list(zu), [("87_Mühlenstraße", "b.dsd")])  # die alte Messung liegt mehr als 15 Monate vor der Sitzung

    def test_mehrdeutig_bleibt_offen(self):
        a = datei("12_Berghäuschensweg", "a.dsd", ("2025-01-15", "2025-03-19"), v85=50)
        b = datei("85_Berghäuschensweg", "b.dsd", ("2025-01-20", "2025-03-25"), v85=50)
        zu, offen = m.zuordnen([block("Berghäuschensweg", 50, None, sitzung="2025-06-11")], [a, b])
        self.assertEqual(dict(zu), {})
        self.assertIn("mehrdeutig", offen[0]["grund"])

    def test_einzige_datei_auch_bei_abweichenden_werten(self):
        f = datei("07_2024_ Einsteinstraße", "_15.dsd", ("2024-07-24", "2024-12-04"), v85=28)
        zu, offen = m.zuordnen([block("Einsteinstraße", 31, None, sitzung="2025-02-26")], [f])
        self.assertEqual(zu[("07_2024_ Einsteinstraße", "_15.dsd")][0][1]["methode"], "name_einzige_datei")

    def test_zeitraum_nach_der_sitzung_wird_nicht_verwendet(self):
        j = [{"vorlage": "69/251/2024", "gremium": "Bezirksausschuss V", "sitzung": "2024-02-27", "dokument": "http://x",
              "messstellen": [{"strasse": "Norfer Kirchstraße", "bezeichnung": "Norfer Kirchstraße", "v85_kmh": 20,
                               "zeitraum": ["2023-09-13", "2024-11-16"]}], "nicht_ausgewertet": []}]
        pfad = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_test_messstellen.json")
        try:
            with open(pfad, "w", encoding="utf-8") as fh:
                import json
                json.dump({"dokumente": j}, fh)
            bloecke, _ = m.lade_bloecke(pfad)
        finally:
            os.remove(pfad)
        self.assertIsNone(bloecke[0]["zeitraum"])
        self.assertEqual(bloecke[0]["zeitraum_in_mitteilung"], ["2023-09-13", "2024-11-16"])

    def test_tage_wie_die_verwaltung(self):
        self.assertEqual(m.block_tage({"zeitraum": ["2024-04-25", "2024-07-24"]}), 90)  # 47453 Fahrzeuge / 90 = 527 je Tag


if __name__ == "__main__":
    unittest.main()
