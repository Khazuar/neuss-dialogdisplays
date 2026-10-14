# SPDX-License-Identifier: MIT
"""Tests fuer site/filter.js (Auswahl nach Zeit, Tagen und Verhaltensgruppe) mit Node.  Ohne Node werden sie uebersprungen."""
import copy
import json
import os
import re
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
_K_MAX = gruppen.K_MAX


def setUpModule():
    gruppen.K_MAX = 5  # die Suche geht immer bis K_MAX (8); fuer schnelle Tests genuegt 5


def tearDownModule():
    gruppen.K_MAX = _K_MAX

SKRIPT = r"""
const f = require(process.argv[2]);
const daten = JSON.parse(require("fs").readFileSync(process.argv[3], "utf8"));
const auswahlen = JSON.parse(process.argv[4]);
const aus = auswahlen.map(a => {
  const r = f.waehle(daten, a.zeit, a.tage, a.gruppe === "rausch");
  const kz = f.kennzahlen(r.hist, daten.limit);
  const vg = /^v\d+$/.test(a.gruppe) ? f.verhaltensgruppe(daten, a.zeit, a.tage, parseInt(a.gruppe.slice(1), 10)) : null;
  return { hist: r.hist, stunden: r.stunden, kz: kz, html: f.ergebnisHtml(daten, a), vg: vg };
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


def mit_verhalten(daten):
    """Zwei Verhaltensgruppen wie aus verhalten.py: Profile in 2-km/h-Klassen und erwartete Fahrzeuge je Zelle (Gruppe 1 nachts mehr)."""
    d = copy.deepcopy(daten)
    langsam, schnell = [0.0] * 46, [0.0] * 46
    langsam[3], langsam[4] = 0.5, 0.5  # 6-10 km/h
    schnell[14], schnell[15], schnell[45] = 0.6, 0.3, 0.1  # 28-32 km/h, ein Rest ab 90
    raten = {}
    for key, zelle in d["z"].items():
        n = sum(zelle[1::2])
        h = int(key.split("|")[1])
        raten[key] = [round(0.3 * n if h < 6 else 0.05 * n, 2), round(0.9 * n, 2)]
    d["verhalten"] = {"profile": [langsam, schnell], "klassen": ["rauschen", "haupt"], "raten": raten,
                      "namen": ["A1·1 – Regenphantome (S-R1)", "A1·2 – Hauptgruppe"]}
    return d


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

    def test_verhaltensgruppe_ist_summe_der_raten_mal_profil(self):
        daten = mit_verhalten(self.daten)
        (nacht, tag) = laufe(daten, [{"zeit": "nacht", "tage": "werktag", "gruppe": "v1"}, {"zeit": "nachmittag", "tage": "alle", "gruppe": "v1"}])
        for r, tage, stunden in ((nacht, range(5), [22, 23, 0, 1, 2, 3, 4, 5]), (tag, range(8), range(12, 19))):
            n = sum(daten["verhalten"]["raten"].get(f"{t}|{h}", [0, 0])[0] for t in tage for h in stunden)
            self.assertAlmostEqual(r["vg"]["n"], n, places=6)
            hist = {int(k): v for k, v in r["vg"]["hist"].items()}
            self.assertEqual(sorted(hist), [6, 7, 8, 9])  # 2-km/h-Klassen je zur Haelfte auf ihre beiden Werte
            self.assertAlmostEqual(hist[6], n * 0.25, places=6)
            self.assertAlmostEqual(sum(hist.values()), n, places=6)
        (h,) = laufe(daten, [{"zeit": "alle", "tage": "alle", "gruppe": "v2"}])
        self.assertIn(91, {int(k) for k in h["vg"]["hist"]})  # die letzte Klasse (ab 90) liegt bei 91

    def test_ausgabe_html(self):
        daten = mit_verhalten(self.daten)
        (alle,) = laufe(daten, [{"zeit": "alle", "tage": "alle", "gruppe": "alle"}])
        self.assertIn("<table>", alle["html"])
        self.assertIn('<svg class="hist"', alle["html"])
        self.assertIn("hist-limit", alle["html"])
        self.assertIn("Klassenbreite", alle["html"])
        self.assertNotIn("hist-grau", alle["html"])  # ohne Gruppe keine ausgegrauten Saeulen
        self.assertNotIn("hist-modell", alle["html"])
        (v2,) = laufe(daten, [{"zeit": "alle", "tage": "alle", "gruppe": "v2"}])
        self.assertIn("hist-grau", v2["html"])  # alle Fahrten bleiben grau sichtbar
        self.assertIn("hist-ok", v2["html"])  # der Teil der Gruppe ist farbig
        self.assertIn("hist-modell", v2["html"])  # und die Gruppe liegt als Linie darueber
        self.assertIn("Anteil an allen", v2["html"])
        self.assertIn("A1·2 – Hauptgruppe", v2["html"])
        self.assertIn("Schätzung", v2["html"])
        self.assertIn("V85", v2["html"])
        (klein,) = laufe(daten, [{"zeit": "schulweg", "tage": "samstag", "gruppe": "v2"}])
        self.assertIn("<table>", klein["html"])
        self.assertIn("Wenige Fahrzeuge", klein["html"])  # Anteile bei kleinen Auswahlen sind unsicher
        (ohne,) = laufe(self.daten, [{"zeit": "alle", "tage": "alle", "gruppe": "v1"}])
        self.assertIn("keine Verhaltensgruppen", ohne["html"])

    def test_rauschboden(self):
        """Der Rauschboden zeigt alle aufgezeichneten Fahrten grau und nur den herausgerechneten Rauschboden farbig."""
        daten = copy.deepcopy(self.daten)
        daten["r"] = {"0|8": [3, 400, 4, 300, 5, 200, 6, 100], "1|9": [3, 150, 4, 100]}
        (r,) = laufe(daten, [{"zeit": "alle", "tage": "alle", "gruppe": "rausch"}])
        (ohne,) = laufe(daten, [{"zeit": "alle", "tage": "alle", "gruppe": "alle"}])
        self.assertEqual(sum(r["hist"].values()), 1250)  # waehle(..., rausch=true): nur der Rauschboden
        n = sum(ohne["hist"].values())
        anteil = ("%.1f" % (100 * 1250 / (n + 1250))).replace(".", "[.,]")  # Anteil an allen aufgezeichneten Fahrten (je nach Locale mit Komma oder Punkt)
        self.assertRegex(r["html"], anteil + " %")
        self.assertIn("hist-grau", r["html"])
        self.assertIn("hist-ok", r["html"])  # der Rauschboden ist farbig
        self.assertNotIn("hist-modell", r["html"])  # keine Kurve
        self.assertIn("aufgezeichneten Fahrten der Auswahl (Fahrzeuge und Rauschboden)", r["html"])
        self.assertIn("der Rauschboden, der herausgerechnet wurde", r["html"])
        self.assertIn("1.250", r["html"].replace("1,250", "1.250"))  # Zahl der Fahrten des Rauschbodens in der Tabelle
        (leer,) = laufe(self.daten, [{"zeit": "alle", "tage": "alle", "gruppe": "rausch"}])  # ohne abgezogenen Rauschboden
        self.assertIn("kein Rauschboden", leer["html"])

    def test_farbige_saeule_ist_nie_hoeher_als_die_graue(self):
        (g,) = laufe(mit_verhalten(self.daten), [{"zeit": "alle", "tage": "alle", "gruppe": "v2"}])
        grau = [float(m.group(1)) for m in re.finditer(r'class="hist-grau" x="[\d.]+" y="[\d.]+" width="[\d.]+" height="([\d.]+)"', g["html"])]
        farbig = [float(m.group(1)) for m in re.finditer(r'class="hist-(?:ok|ueber)" x="[\d.]+" y="[\d.]+" width="[\d.]+" height="([\d.]+)"', g["html"])]
        self.assertTrue(grau)
        self.assertTrue(farbig)
        self.assertLessEqual(max(farbig), max(grau) + 0.11)  # gerundet auf eine Nachkommastelle


if __name__ == "__main__":
    unittest.main()
