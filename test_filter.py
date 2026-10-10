# SPDX-License-Identifier: MIT
"""Tests fuer site/filter.js (Auswahl nach Zeit, Tagen und Gruppe) mit Node.  Ohne Node werden sie uebersprungen."""
import json
import math
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
  const r = f.waehle(daten, a.zeit, a.tage, a.gruppe === "rausch");
  const kz = f.kennzahlen(r.hist, daten.limit);
  const modell = /^g\d+$/.test(a.gruppe) || a.gruppe === "rest" ? f.zerlege(daten, r.hist) : null;
  return { hist: r.hist, stunden: r.stunden, kz: kz, html: f.ergebnisHtml(daten, a), modell: modell };
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


def zelle_hist(daten, quelle, tage, stunden):
    h, std = {}, 0
    for t in tage:
        for st in stunden:
            key = f"{t}|{st}"
            std += daten["tage"].get(key, 0)
            z = daten[quelle].get(key, [])
            for i in range(0, len(z), 2):
                h[z[i]] = h.get(z[i], 0) + z[i + 1]
    return h, std


def kurvenform(x, w0):
    """Anteil je km/h einer Gruppe ab w0 (Summe 1), wie site/filter.js: die Kurven der Gruppe, je auf 1 normiert, mal ihr Gewicht."""
    summe = {v: 0.0 for v in range(w0, gruppen.VMAX_GRUPPEN + 1)}
    for k in x["kurven"]:
        p = {v: math.exp(-0.5 * ((math.log(v) - k["mu"]) / k["s"]) ** 2) / (k["s"] * v) for v in summe}
        s = sum(p.values())
        for v, q in p.items():
            summe[v] += k["c"] * q / s
    return summe


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
        self.assertEqual(round(kz["n"]), self.block["fahrzeuge"])

    def test_zeit_und_tage(self):
        auswahl = [{"zeit": "nacht", "tage": "werktag", "gruppe": "alle"}, {"zeit": "vormittag", "tage": "samstag", "gruppe": "alle"},
                   {"zeit": "schulweg", "tage": "sonn", "gruppe": "alle"}, {"zeit": "abend", "tage": "3", "gruppe": "alle"}]
        erwartet = [(range(5), [22, 23, 0, 1, 2, 3, 4, 5]), ([5], range(6, 12)), ([6, 7], [7]), ([3], [19, 20, 21])]
        for r, (tage, stunden) in zip(laufe(self.daten, auswahl), erwartet):
            h, std = zelle_hist(self.daten, "z", tage, stunden)
            self.assertEqual({int(k): v for k, v in r["hist"].items()}, h)
            self.assertEqual(r["stunden"], std)

    def test_gruppen_sind_kurven_und_rest_ist_der_unterschied(self):
        (g1, g2, rest) = laufe(self.daten, [{"zeit": "alle", "tage": "alle", "gruppe": "g1"}, {"zeit": "alle", "tage": "alle", "gruppe": "g2"},
                                            {"zeit": "alle", "tage": "alle", "gruppe": "rest"}])
        m = g1["modell"]
        n = sum(g1["hist"].values())
        self.assertAlmostEqual(sum(m["pi"]), 1.0, places=6)
        self.assertAlmostEqual(m["nfit"], n, delta=0.5)  # nichts liegt unter der Anpassungsgrenze
        w0 = self.daten["w0"]
        for j, x in enumerate(self.daten["gruppen"]):  # die Kurve einer Gruppe: Zahl der Fahrzeuge mal Anteil mal Form
            p = kurvenform(x, w0)
            for v in (20, 30, 45):
                self.assertAlmostEqual(m["gruppen"][j][str(v)], m["nfit"] * m["pi"][j] * p[v], delta=1e-6 * n)
            self.assertAlmostEqual(m["pi"][j], x["pi"], delta=0.01)  # ganztaegig stimmt die Schaetzung mit der Anpassung ueberein
        ges = {int(v): c for v, c in g1["hist"].items()}
        mod = m["gruppen"]
        for v, c in ges.items():  # Kurven plus Rest decken die Daten ab; der Rest ist nie negativ
            r = m["rest"].get(str(v), 0.0)
            self.assertGreaterEqual(r, 0.0)
            self.assertGreaterEqual(sum(h.get(str(v), 0.0) for h in mod) + r + 1e-6, c)
        self.assertLess(sum(m["rest"].values()) / n, 0.08)
        self.assertEqual(rest["modell"]["rest"], m["rest"])
        mittel = [sum(int(v) * c for v, c in h.items()) / sum(h.values()) for h in mod]  # die Kurven der beiden Gruppen
        self.assertLess(mittel[0], 22)
        self.assertGreater(mittel[1], 35)
        self.assertAlmostEqual(sum(sum(h.values()) for h in mod), n, delta=0.5)
        self.assertEqual(g1["modell"]["pi"], g2["modell"]["pi"])  # beide Gruppen derselben Auswahl: dieselbe Zerlegung

    def test_gruppe_aus_mehreren_kurven(self):
        """Besteht eine Gruppe aus zwei Kurven, ist ihre Form die gewichtete Summe der beiden (auf je 1 normiert)."""
        import copy
        daten = copy.deepcopy(self.daten)
        k = daten["gruppen"][1]["kurven"][0]
        daten["gruppen"][1]["kurven"] = [{"mu": k["mu"] - 0.08, "s": k["s"] * 0.8, "c": 0.4}, {"mu": k["mu"] + 0.05, "s": k["s"], "c": 0.6}]
        (g2,) = laufe(daten, [{"zeit": "alle", "tage": "alle", "gruppe": "g2"}])
        m = g2["modell"]
        w0, n = daten["w0"], sum(g2["hist"].values())
        p = kurvenform(daten["gruppen"][1], w0)
        self.assertAlmostEqual(sum(p.values()), 1.0, places=9)
        for v in (20, 30, 40, 50):
            self.assertAlmostEqual(m["gruppen"][1][str(v)], m["nfit"] * m["pi"][1] * p[v], delta=1e-6 * n)
        self.assertAlmostEqual(sum(m["pi"]), 1.0, places=6)

    def test_anteile_der_gruppen_je_auswahl(self):
        """Nachts andere Anteile als tagsueber: Die Anteile werden je Auswahl neu geschaetzt, die Kurven bleiben."""
        nacht, tag = laufe(self.daten, [{"zeit": "nacht", "tage": "alle", "gruppe": "g1"}, {"zeit": "nachmittag", "tage": "alle", "gruppe": "g1"}])
        for r in (nacht, tag):
            self.assertAlmostEqual(sum(r["modell"]["pi"]), 1.0, places=6)
        # die Testdaten haben ueber den Tag gleiche Anteile: beide nahe der Anpassung
        for r in (nacht, tag):
            for pi, x in zip(r["modell"]["pi"], self.daten["gruppen"]):
                self.assertAlmostEqual(pi, x["pi"], delta=0.05)

    def test_ausgabe_html(self):
        (alle,) = laufe(self.daten, [{"zeit": "alle", "tage": "alle", "gruppe": "alle"}])
        self.assertIn("<table>", alle["html"])
        self.assertIn('<svg class="hist"', alle["html"])
        self.assertIn("hist-limit", alle["html"])
        self.assertIn("Klassenbreite", alle["html"])
        self.assertNotIn("hist-grau", alle["html"])  # ohne Gruppe keine ausgegrauten Saeulen
        self.assertNotIn("hist-modell", alle["html"])
        (g1,) = laufe(self.daten, [{"zeit": "alle", "tage": "alle", "gruppe": "g1"}])
        self.assertIn("hist-grau", g1["html"])  # alle Fahrzeuge bleiben grau sichtbar
        self.assertIn("hist-ok", g1["html"])  # der Teil der Gruppe ist farbig
        self.assertIn("hist-modell", g1["html"])  # und die Kurve der Gruppe liegt als Linie darueber
        self.assertIn("Anteil an allen", g1["html"])
        self.assertIn("Gruppe 1", g1["html"])
        self.assertIn("nicht zu 100", g1["html"])
        (rest,) = laufe(self.daten, [{"zeit": "alle", "tage": "alle", "gruppe": "rest"}])
        self.assertIn("Rest", rest["html"])
        self.assertIn("hist-grau", rest["html"])
        self.assertNotIn("hist-modell", rest["html"])
        (klein,) = laufe(self.daten, [{"zeit": "schulweg", "tage": "samstag", "gruppe": "g1"}])
        self.assertIn("<table>", klein["html"])
        self.assertIn("Wenige Fahrzeuge", klein["html"])  # Anteile bei kleinen Auswahlen sind unsicher

    def test_farbige_saeule_ist_nie_hoeher_als_die_graue(self):
        (g1,) = laufe(self.daten, [{"zeit": "alle", "tage": "alle", "gruppe": "g2"}])
        import re
        grau = [float(m.group(1)) for m in re.finditer(r'class="hist-grau" x="[\d.]+" y="[\d.]+" width="[\d.]+" height="([\d.]+)"', g1["html"])]
        farbig = [float(m.group(1)) for m in re.finditer(r'class="hist-(?:ok|ueber)" x="[\d.]+" y="[\d.]+" width="[\d.]+" height="([\d.]+)"', g1["html"])]
        self.assertTrue(grau)
        self.assertTrue(farbig)
        self.assertLessEqual(max(farbig), max(grau) + 0.11)  # gerundet auf eine Nachkommastelle


if __name__ == "__main__":
    unittest.main()
