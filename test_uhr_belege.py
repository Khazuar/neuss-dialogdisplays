# SPDX-License-Identifier: MIT
"""Tests fuer uhr_belege.py.  Aufruf: python3 -m unittest -v"""
import datetime as dt
import unittest

import dsd2csv as d
import uhr_belege as u

# Typische Woche Mo..So (Sonntag am schwaechsten, Samstag danach)
WOCHE = [1.04, 1.06, 1.08, 1.06, 1.09, 0.94, 0.72]


def tagesverlauf(stunde):
    """Einfacher Werktagsverlauf: Morgen- und Abendspitze, nachts fast leer."""
    gewicht = {range(0, 5): 1, range(5, 7): 6, range(7, 9): 20, range(9, 16): 12, range(16, 19): 22, range(19, 22): 8, range(22, 24): 3}
    return next(w for r, w in gewicht.items() if stunde in r)


def verkehr(tage, start, verschiebung_min=0, ab=None, nach_min=0):
    """Fahrzeugzeiten ueber mehrere Tage; ab dem Datum 'ab' um nach_min Minuten verschoben (wie Zeitumstellung)."""
    zeiten = []
    for k in range(tage):
        tag = start + dt.timedelta(days=k)
        faktor = WOCHE[tag.weekday()]
        versatz = verschiebung_min + (nach_min if ab and tag >= ab else 0)
        for stunde in range(24):
            for viertel in range(4):
                for n in range(round(tagesverlauf(stunde) * faktor * 2)):
                    t = dt.datetime(tag.year, tag.month, tag.day, stunde, viertel * 15, n % 60) + dt.timedelta(minutes=versatz)
                    zeiten.append(t)
    return sorted(zeiten)


class Namen(unittest.TestCase):
    def test_schluessel(self):
        self.assertEqual(u.schluessel("Rosellener Kirchstraße"), u.schluessel("Rosellener Kirchstr."))
        self.assertEqual(u.schluessel("St.Antoniusstraße"), "stantoniusstrasse")

    def test_messort_namen(self):
        self.assertEqual(u.messort_namen("07_2024_ Einsteinstraße"), ["Einsteinstraße"])
        self.assertEqual(u.messort_namen("Stationär_Villestraße/FR GV"), ["Villestraße"])
        self.assertEqual(u.messort_namen("03_2024_Hauptstraße 13a"), ["Hauptstraße"])
        self.assertEqual(u.messort_namen("34_Holzheimer Weg (zwischen Bergheimer Straße und Am Krausenbaum)"), ["Holzheimer Weg"])
        self.assertEqual(u.messort_namen("02_2024_Bauerbahn, ggü. Nr. 3"), ["Bauerbahn"])


class Wochenrhythmus(unittest.TestCase):
    def test_richtige_wochentage(self):
        z = verkehr(70, dt.date(2024, 5, 6))
        v, tage = u.wochenvektor(z, z[0], z[-1])
        r, korr, abstand, _ = u.beste_drehung(v, WOCHE)
        self.assertEqual(r, 0)
        self.assertGreater(korr, 0.99)

    def test_um_einen_tag_verschobene_uhr(self):
        z = verkehr(70, dt.date(2024, 5, 6))
        z = [t + dt.timedelta(days=1) for t in z]  # Uhr geht einen Tag vor
        v, _ = u.wochenvektor(z, z[0], z[-1])
        self.assertEqual(u.beste_drehung(v, WOCHE)[0], 1)

    def test_zu_kurz(self):
        z = verkehr(10, dt.date(2024, 5, 6))
        self.assertIsNone(u.wochenvektor(z, z[0], z[-1])[0])


class Tagesgang(unittest.TestCase):
    def profil(self, z):
        return d.tagesgang(z)[0]

    def test_vorzeichen_der_verschiebung(self):
        ref = self.profil(verkehr(40, dt.date(2024, 5, 6)))
        spaet = self.profil(verkehr(40, dt.date(2024, 5, 6), verschiebung_min=60))  # Verkehr spaeter: Uhr geht vor
        self.assertEqual(u.tagesgang_verschiebung(spaet, ref)[0], 60)
        frueh = self.profil(verkehr(40, dt.date(2024, 5, 6), verschiebung_min=-120))
        self.assertEqual(u.tagesgang_verschiebung(frueh, ref)[0], -120)

    def test_verstellte_uhr_um_stunden_bleibt_erkennbar(self):
        ref = self.profil(verkehr(40, dt.date(2024, 5, 6)))
        spaet = self.profil(verkehr(40, dt.date(2024, 5, 6), verschiebung_min=-8 * 60))
        minuten, korr = u.tagesgang_verschiebung(spaet, ref)
        self.assertEqual(minuten, -480)
        self.assertGreater(korr, 0.99)


class Zeitumstellung(unittest.TestCase):
    def test_stufe_liegt_am_amtlichen_tag(self):
        # Uhr im Sommer gestellt und nie umgestellt: ab dem 27.10.2024 zeigt sie den Verkehr eine Stunde spaeter
        z = verkehr(100, dt.date(2024, 9, 1), ab=dt.date(2024, 10, 27), nach_min=60)
        anker = u.zeitumstellung_anker(z, z[0], z[-1])
        self.assertEqual(len(anker), 1)
        self.assertEqual(anker[0]["datum"], "2024-10-27")
        self.assertLessEqual(abs(anker[0]["tage_abweichung"]), 1)
        self.assertGreaterEqual(anker[0]["trefferquote"], 0.9)

    def test_datum_um_eine_woche_verschoben_wird_erkannt(self):
        # Stufe im Verkehr liegt 7 Tage neben dem amtlichen Umstellungstag: das Datum der Uhr geht 7 Tage nach
        z = verkehr(100, dt.date(2024, 9, 1), ab=dt.date(2024, 11, 3), nach_min=60)
        anker = u.zeitumstellung_anker(z, z[0], z[-1])
        self.assertEqual(len(anker), 1)
        self.assertGreaterEqual(abs(anker[0]["tage_abweichung"]), 6)

    def test_ohne_stufe_kein_zuverlaessiger_anker(self):
        z = verkehr(100, dt.date(2024, 9, 1))
        for a in u.zeitumstellung_anker(z, z[0], z[-1]):
            self.assertLess(a["trefferquote"], 0.9)


class Urteil(unittest.TestCase):
    def seg(self, **kw):
        s = {"idx": list(range(5000)), "bewertung": "gueltig", "start": dt.datetime(2024, 5, 6), "ende": dt.datetime(2024, 8, 1)}
        s.update(kw)
        return s

    def belege(self, **status):
        namen = ("datum", "wochenrhythmus", "tagesgang", "zeitumstellung", "ris", "kontinuitaet")
        return {k: {"status": status.get(k, "offen"), "text": k} for k in namen}

    def test_plausibel_braucht_zwei_belege(self):
        self.assertEqual(u.urteil(self.seg(), self.belege(wochenrhythmus="bestaetigt", tagesgang="bestaetigt"), {})[0], "plausibel")
        self.assertEqual(u.urteil(self.seg(), self.belege(wochenrhythmus="bestaetigt"), {})[0], "eingeschraenkt")
        self.assertEqual(u.urteil(self.seg(), self.belege(), {})[0], "eingeschraenkt")

    def test_art_der_einschraenkung(self):
        self.assertEqual(u.urteil(self.seg(), self.belege(wochenrhythmus="bestaetigt"), {})[2], "unzureichend_belegt")
        self.assertEqual(u.urteil(self.seg(), self.belege(tagesgang="widerspricht"), {})[2], "widerspruch")
        self.assertEqual(u.urteil(self.seg(bewertung="werksdatum"), self.belege(), {})[2], "zurueckgesetzt")
        self.assertIsNone(u.urteil(self.seg(), self.belege(wochenrhythmus="bestaetigt", tagesgang="bestaetigt"), {})[2])

    def test_widerspruch_verhindert_plausibel(self):
        b = self.belege(wochenrhythmus="bestaetigt", tagesgang="bestaetigt", ris="widerspricht")
        self.assertEqual(u.urteil(self.seg(), b, {})[0], "eingeschraenkt")

    def test_unmoegliches_datum_ist_unbrauchbar(self):
        s = self.seg(bewertung="ungueltiges_datum", grund="Zeitstempel im Jahr 2255")
        self.assertEqual(u.urteil(s, self.belege(), {})[0], "unbrauchbar")

    def test_reset_ist_eingeschraenkt_wenn_lang_genug(self):
        self.assertEqual(u.urteil(self.seg(bewertung="werksdatum"), self.belege(), {})[0], "eingeschraenkt")
        kurz = self.seg(bewertung="werksdatum", idx=list(range(100)))
        self.assertEqual(u.urteil(kurz, self.belege(), {})[0], "unbrauchbar")

    def test_kein_tagesgang_ist_unbrauchbar(self):
        b = self.belege()
        b["tagesgang"] = {"status": "widerspricht", "text": "kein erkennbarer Tagesgang (Korrelation 0.20)"}
        self.assertEqual(u.urteil(self.seg(), b, {})[0], "unbrauchbar")


class Gesamturteil(unittest.TestCase):
    def a(self, **je_urteil):
        return [{"fahrzeuge": n, "urteil": urt} for urt, n in je_urteil.items()]

    def test_regeln(self):
        self.assertEqual(u.gesamturteil(self.a(plausibel=1000))[0], "plausibel")
        self.assertEqual(u.gesamturteil(self.a(plausibel=990, eingeschraenkt=10))[0], "plausibel")  # genau 99 %
        self.assertEqual(u.gesamturteil(self.a(plausibel=980, eingeschraenkt=20))[0], "eingeschraenkt")
        self.assertEqual(u.gesamturteil(self.a(plausibel=400, unbrauchbar=500, eingeschraenkt=100))[0], "unbrauchbar")
        self.assertEqual(u.gesamturteil(self.a(eingeschraenkt=1000))[0], "eingeschraenkt")

    def test_anteil_plausibel_und_ohne_fahrzeuge(self):
        self.assertAlmostEqual(u.gesamturteil(self.a(plausibel=600, eingeschraenkt=400))[1], 0.6)
        self.assertIsNone(u.gesamturteil([]))


class Ris(unittest.TestCase):
    def ris(self):
        return {"dokumente": [{"vorlage": "69/1/2024", "betreff": "x", "gremium": "BA I", "sitzung": "2024-06-01",
                               "dokument": "http://x", "_orte": {u.schluessel("Pomona")},
                               "_zeitraeume": [(dt.date(2025, 3, 19), dt.date(2025, 7, 6))]}]}

    def seg(self, start, ende):
        return {"start": dt.datetime.fromisoformat(start), "ende": dt.datetime.fromisoformat(ende)}

    def test_treffer(self):
        b = u.beleg_ris(["Pomona"], self.seg("2025-03-19 08:00", "2025-07-06 07:30"), self.ris())
        self.assertEqual(b["status"], "bestaetigt")
        self.assertIn("Beginn und Ende", b["text"])

    def test_nur_ende_passt(self):
        b = u.beleg_ris(["Pomona"], self.seg("2025-05-01 08:00", "2025-07-06 07:30"), self.ris())
        self.assertEqual(b["status"], "bestaetigt")
        self.assertIn("Ende", b["text"])

    def test_falscher_zeitraum_und_unbekannter_ort(self):
        self.assertEqual(u.beleg_ris(["Pomona"], self.seg("2024-01-01 00:00", "2024-02-01 00:00"), self.ris())["status"], "offen")
        self.assertEqual(u.beleg_ris(["Nirgendwo"], self.seg("2025-03-19 08:00", "2025-07-06 07:30"), self.ris())["status"], "offen")


if __name__ == "__main__":
    unittest.main()
