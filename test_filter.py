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
import datetime as dt  # noqa: E402
import dsd2csv  # noqa: E402
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
        cls.daten = gruppen.datentabelle(gruppen.zellen_bauen(fahrten, fahrten, spannen), 30)
        cls.fahrzeuge = sum(1 for t, _ in fahrten if (t.date(), t.hour) in __import__("rauschen").abgedeckte_stunden(spannen))

    def test_alles_stimmt_mit_der_python_rechnung(self):
        (r,) = laufe(self.daten, [{"zeit": "alle", "tage": "alle", "gruppe": "alle"}])
        h, std = zelle_hist(self.daten, "z", range(8), range(24))
        self.assertEqual({int(k): v for k, v in r["hist"].items()}, h)
        self.assertEqual(r["stunden"], std)
        t0 = dt.datetime(2024, 1, 1)
        erwartet = dsd2csv.stats([(t0, v) for v, c in h.items() for _ in range(c)], 30)  # dieselben Kennzahlen wie in der YAML
        g, e = erwartet["geschwindigkeit_kmh"], erwartet["einhaltung"]
        kz = r["kz"]
        self.assertEqual(round(kz["n"]), erwartet["anzahl_fahrzeuge"])
        self.assertAlmostEqual(kz["mittel"], g["mittel"], places=2)
        self.assertEqual((kz["v85"], kz["v95"], kz["v99"]), (g["v85"], g["v95"], g["v99"]))
        self.assertAlmostEqual(kz["einhaltung"], e["einhaltungsquote_prozent"], places=1)
        self.assertAlmostEqual(kz["qualifiziert"], e["qualifizierte_einhaltungsquote_prozent"], places=1)
        self.assertEqual(round(kz["n"]), self.fahrzeuge)

    def test_v85_wird_nach_den_stufen_der_verwaltung_gefaerbt(self):
        skript = ("const f=require(process.argv[1]); const o={}; for (const v of [34,35,38,39,40,41]) { o[v]=f.klasseV85(v, 30); }"
                  " o.ohne=f.klasseV85(50, 0); console.log(JSON.stringify(o));")
        out = subprocess.run([NODE, "-e", skript, os.path.join(HIER, "site", "filter.js")], stdout=subprocess.PIPE, check=True, timeout=60)
        self.assertEqual(json.loads(out.stdout.decode("utf-8")), {"34": "", "35": " v85-gelb", "38": " v85-gelb", "39": " v85-orange", "40": " v85-orange",
                                                                  "41": " v85-rot", "ohne": ""})
        (alle,) = laufe(self.daten, [{"zeit": "alle", "tage": "alle", "gruppe": "alle"}])
        kz = alle["kz"]
        erwartet = {"": kz["v85"] - 30 < 5, " v85-gelb": 5 <= kz["v85"] - 30 < 9, " v85-orange": 9 <= kz["v85"] - 30 < 11, " v85-rot": kz["v85"] - 30 >= 11}
        klasse = [k for k, ok in erwartet.items() if ok][0]
        self.assertIn('<td class="num%s">%d</td>' % (klasse, kz["v85"]), alle["html"])

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

    def test_nur_trockene_stunden(self):
        """Die Auswahl 'nur trockene Stunden' nimmt die Zellen 'trocken' (ganze Messung und Abschnitt) und laesst die Verhaltensgruppen weg."""
        daten = mit_verhalten(self.daten)
        trocken = {"tage": {"0|7": 2}, "z": {"0|7": [30, 4, 31, 1]}, "r": {}}
        daten["trocken"] = trocken
        daten["abschnitte"] = [{"nr": 2, "von": "2024-01-01", "bis": "2024-01-31", "tage": {"1|8": 3}, "z": {"1|8": [40, 2]}, "r": {},
                                "trocken": {"tage": {"1|8": 1}, "z": {"1|8": [40, 1]}, "r": {}}}]
        skript = ("const f=require(process.argv[1]); const d=JSON.parse(require('fs').readFileSync(process.argv[2],'utf8'));"
                  "const a=f.datenFuer(d,'alle','trocken'), b=f.datenFuer(d,'2','trocken'), c=f.datenFuer(d,'alle','alle');"
                  "console.log(JSON.stringify({a:[a.z,a.tage,a.verhalten,!!a.tageAlle,a.limit], b:[b.z,b.limit,b.von], c:[c.z===undefined, !!c.verhalten, !!c.tageAlle],"
                  " html: f.ergebnisHtml(a,{zeit:'alle',tage:'alle',gruppe:'alle'})}));")
        with tempfile.TemporaryDirectory() as t:
            p = os.path.join(t, "d.json")
            with open(p, "w", encoding="utf-8") as fh:
                json.dump(daten, fh)
            out = json.loads(subprocess.run([NODE, "-e", skript, os.path.join(HIER, "site", "filter.js"), p], stdout=subprocess.PIPE, check=True,
                                            timeout=60).stdout.decode("utf-8"))
        self.assertEqual(out["a"], [trocken["z"], trocken["tage"], None, True, daten["limit"]])
        self.assertEqual(out["b"], [{"1|8": [40, 1]}, daten["limit"], "2024-01-01"])
        self.assertEqual(out["c"], [False, True, False])  # ohne Wetterauswahl alles wie bisher
        self.assertIn("Nur trockene Stunden: 2 von", out["html"])

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


LABOR = r"""
const pfad = process.argv[2], such = process.argv[3], gespeichert = process.argv[4] === "1", kaputt = process.argv[5] === "1";
const klassen = new Set();
const speicher = {};
if (gespeichert) speicher.labor = "1";
global.window = { location: { search: such }, localStorage: kaputt ? { getItem() { throw new Error("x"); }, setItem() { throw new Error("x"); },
  removeItem() { throw new Error("x"); } } : { getItem: k => (k in speicher ? speicher[k] : null), setItem: (k, v) => { speicher[k] = v; }, removeItem: k => { delete speicher[k]; } } };
global.document = { documentElement: { classList: { add: k => klassen.add(k) } } };
require(pfad);
console.log(JSON.stringify({ an: klassen.has("labor"), speicher }));
"""


@unittest.skipUnless(NODE, "Node ist nicht installiert")
class LaborJs(unittest.TestCase):
    def lauf(self, suche, gespeichert=False, kaputt=False):
        with tempfile.TemporaryDirectory() as d:
            skript = os.path.join(d, "t.js")
            with open(skript, "w", encoding="utf-8") as fh:
                fh.write(LABOR)
            out = subprocess.run([NODE, skript, os.path.join(HIER, "site", "labor.js"), suche, "1" if gespeichert else "0", "1" if kaputt else "0"],
                                 stdout=subprocess.PIPE, check=True, timeout=60)
        return json.loads(out.stdout.decode("utf-8"))

    def test_ohne_schalter_aus(self):
        self.assertFalse(self.lauf("")["an"])
        self.assertFalse(self.lauf("?x=1")["an"])
        self.assertFalse(self.lauf("?laboratorium")["an"])  # nur der Schalter "labor" zaehlt, nicht ein Wort, das so anfaengt

    def test_schalter_wird_gemerkt(self):
        r = self.lauf("?labor")
        self.assertTrue(r["an"])
        self.assertEqual(r["speicher"]["labor"], "1")
        self.assertTrue(self.lauf("?a=1&labor=1")["an"])
        self.assertTrue(self.lauf("", gespeichert=True)["an"])  # spaeter ohne Schalter weiter an

    def test_ausschalten(self):
        for such in ("?labor=0", "?labor=aus"):
            r = self.lauf(such, gespeichert=True)
            self.assertFalse(r["an"], such)
            self.assertNotIn("labor", r["speicher"])

    def test_ohne_speicher_gilt_der_schalter_nur_fuer_die_adresse(self):
        self.assertTrue(self.lauf("?labor", kaputt=True)["an"])
        self.assertFalse(self.lauf("", kaputt=True)["an"])
        self.assertFalse(self.lauf("?labor=0", kaputt=True)["an"])


if __name__ == "__main__":
    unittest.main()
