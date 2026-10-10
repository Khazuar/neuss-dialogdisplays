# SPDX-License-Identifier: MIT
"""Tests fuer site/filter.js (Auswahl nach Zeit, Tagen und Gruppe) mit Node.  Ohne Node werden sie uebersprungen."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gruppen  # noqa: E402
import test_gruppen as tg  # noqa: E402

HIER = os.path.dirname(os.path.abspath(__file__))
NODE = shutil.which("node")

SKRIPT = r"""
const f = require(process.argv[2]);
const daten = JSON.parse(require("fs").readFileSync(process.argv[3], "utf8"));
const auswahlen = JSON.parse(process.argv[4]);
const aus = auswahlen.map(a => {
  const r = f.waehle(daten, a.zeit, a.tage, a.gruppe);
  const kz = f.kennzahlen(r.hist, daten.limit);
  return { hist: r.hist, stunden: r.stunden, kz: kz, html: f.ergebnisHtml(daten, a) };
});
console.log(JSON.stringify(aus));
"""


def laufe(daten, auswahlen):
    with tempfile.TemporaryDirectory() as d:
        pfad = os.path.join(d, "daten.json")
        with open(pfad, "w", encoding="utf-8") as fh:
            json.dump(daten, fh)
        skript = os.path.join(d, "t.js")
        with open(skript, "w", encoding="utf-8") as fh:
            fh.write(SKRIPT)
        out = subprocess.run([NODE, skript, os.path.join(HIER, "site", "filter.js"), pfad, json.dumps(auswahlen)],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=120)
    return json.loads(out.stdout.decode("utf-8"))


def zelle_hist(daten, quelle, tage, stunden, gewicht=lambda v: 1.0):
    h, std = {}, 0
    for t in tage:
        for st in stunden:
            key = f"{t}|{st}"
            std += daten["tage"].get(key, 0)
            z = daten[quelle].get(key, [])
            for i in range(0, len(z), 2):
                w = gewicht(z[i])
                if w > 0:
                    h[z[i]] = h.get(z[i], 0) + z[i + 1] * w
    return h, std


@unittest.skipUnless(NODE, "Node ist nicht installiert")
class FilterJs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fahrten, spannen = tg.fahrten_und_spannen(tage=28)
        cls.block, cls.daten = gruppen.analysiere(gruppen.zellen_bauen(fahrten, fahrten, spannen), 30, True)

    def test_alles_stimmt_mit_der_python_rechnung(self):
        (r,) = laufe(self.daten, [{"zeit": "alle", "tage": "alle", "gruppe": "alle"}])
        h, std = zelle_hist(self.daten, "z", range(8), range(24))
        self.assertEqual({int(k): v for k, v in r["hist"].items()}, h)
        self.assertEqual(r["stunden"], std)
        erwartet = gruppen.kennzahlen(h, 30)
        kz = r["kz"]
        self.assertEqual(round(kz["n"]), erwartet["fahrzeuge"])
        self.assertAlmostEqual(kz["mittel"], erwartet["mittel_kmh"], places=2)
        self.assertEqual((kz["v85"], kz["v95"], kz["v99"]), (erwartet["v85_kmh"], erwartet["v95_kmh"], erwartet["v99_kmh"]))
        self.assertAlmostEqual(kz["einhaltung"], erwartet["einhaltungsquote_prozent"], places=1)
        self.assertAlmostEqual(kz["qualifiziert"], erwartet["qualifizierte_einhaltungsquote_prozent"], places=1)
        # und mit der Kennzahl der Zerlegung: Gesamtzahl der Fahrzeuge
        self.assertEqual(round(kz["n"]), self.block["fahrzeuge"])

    def test_zeit_und_tage(self):
        auswahl = [{"zeit": "nacht", "tage": "werktag", "gruppe": "alle"}, {"zeit": "vormittag", "tage": "samstag", "gruppe": "alle"},
                   {"zeit": "schulweg", "tage": "sonn", "gruppe": "alle"}, {"zeit": "abend", "tage": "3", "gruppe": "alle"}]
        erwartet = [(range(5), [22, 23, 0, 1, 2, 3, 4, 5]), ([5], range(6, 12)), ([6, 7], [7]), ([3], [19, 20, 21])]
        for r, (tage, stunden) in zip(laufe(self.daten, auswahl), erwartet):
            h, std = zelle_hist(self.daten, "z", tage, stunden)
            self.assertEqual({int(k): v for k, v in r["hist"].items()}, h)
            self.assertEqual(r["stunden"], std)

    def test_gruppen_summieren_sich_zum_ganzen(self):
        auswahl = [{"zeit": "alle", "tage": "alle", "gruppe": g} for g in ("alle", "g1", "g2", "haupt", "rand")]
        alle, g1, g2, haupt, rand = laufe(self.daten, auswahl)
        n = alle["kz"]["n"]
        self.assertAlmostEqual(g1["kz"]["n"] + g2["kz"]["n"], n, delta=0.005 * n)  # Gewichte sind auf 3 Stellen gerundet
        self.assertAlmostEqual(haupt["kz"]["n"], g2["kz"]["n"], delta=0.005 * n)  # Gruppe 1 ist die einzige langsame
        self.assertLess(g1["kz"]["mittel"], 20)
        self.assertGreater(g2["kz"]["mittel"], 35)
        self.assertEqual(rand["kz"], None)  # nichts unterhalb der Grenze, wenn der Rauschboden abgezogen ist
        self.assertIn("keine Fahrzeuge", rand["html"])
        erw = {g["nr"]: g["anteil"] for g in self.daten["gruppen"]}
        self.assertAlmostEqual(100 * g1["kz"]["n"] / n, erw[1], delta=0.3)

    def test_kurve_der_gruppe(self):
        skript = (
            "const f = require(process.argv[1]); const d = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));"
            "const k = f.gruppenKurve(d, 'g1', 1000); const k2 = f.gruppenKurve(d, 'alle', 1000);"
            "let s = 0; const bis = Math.floor(d.gruppen[0].bis); for (let v = d.w0; v <= bis; v++) s += k(v);"
            "console.log(JSON.stringify({summe: s, davor: k(d.w0 - 1), alle: k2, jenseits: k(bis + 20) > 0}));")
        with tempfile.TemporaryDirectory() as t:
            pfad = os.path.join(t, "d.json")
            with open(pfad, "w", encoding="utf-8") as fh:
                json.dump(self.daten, fh)
            out = subprocess.run([NODE, "-e", skript, os.path.join(HIER, "site", "filter.js"), pfad], stdout=subprocess.PIPE, check=True, timeout=60)
        r = json.loads(out.stdout.decode())
        self.assertAlmostEqual(r["summe"], 1000, delta=0.5)  # die Kurve umfasst bis zur Zuordnungsgrenze so viele Fahrzeuge wie die Gruppe
        self.assertEqual(r["davor"], 0)
        self.assertIsNone(r["alle"])  # nur einzelne Gruppen haben eine Kurve
        self.assertTrue(r["jenseits"])  # sie läuft über die Grenze hinaus weiter und zeigt den Ausläufer
        (g1,) = laufe(self.daten, [{"zeit": "alle", "tage": "alle", "gruppe": "g1"}])
        self.assertIn("hist-modell", g1["html"])
        self.assertIn("angepasste Kurve der Gruppe", g1["html"])
        (alle,) = laufe(self.daten, [{"zeit": "alle", "tage": "alle", "gruppe": "alle"}])
        self.assertNotIn("hist-modell", alle["html"])
    def test_ausgabe_html(self):
        (r,) = laufe(self.daten, [{"zeit": "alle", "tage": "alle", "gruppe": "alle"}])
        self.assertIn("<table>", r["html"])
        self.assertIn('<svg class="hist"', r["html"])
        self.assertIn("hist-limit", r["html"])
        self.assertIn("Klassenbreite", r["html"])
        (r,) = laufe(self.daten, [{"zeit": "schulweg", "tage": "samstag", "gruppe": "g1"}])
        self.assertIn("<table>", r["html"])  # wenige Fahrzeuge: Tabelle, kein Histogramm noetig


if __name__ == "__main__":
    unittest.main()