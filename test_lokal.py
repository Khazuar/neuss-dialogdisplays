# SPDX-License-Identifier: MIT
"""Tests fuer lokal_bauen.py (lokale Vorschau).  Aufruf: python3 -m unittest -v"""
import os
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lokal_bauen as lb  # noqa: E402

HIER = os.path.dirname(os.path.abspath(__file__))


class Befehle(unittest.TestCase):
    def test_befehle(self):
        b = lb.befehle("eingabe", "ziel", "cache", 3)
        self.assertEqual(len(b), 2)
        self.assertIn("-I", b[0])
        self.assertIn("--keine-csv", b[0])
        self.assertEqual(b[0][b[0].index("--jobs") + 1], "3")
        self.assertEqual(b[0][b[0].index("--cache") + 1], "cache")
        self.assertNotIn("--cache", lb.befehle("e", "z", None, 1)[0])
        self.assertTrue(b[1][-3].endswith("seiten_bauen.py") or any(x.endswith("seiten_bauen.py") for x in b[1]))
        self.assertIn(os.path.join("ziel", "auswertung.json"), b[1])


class Bauen(unittest.TestCase):
    def test_vorschau_mit_einer_datei(self):
        dsds = sorted((os.path.getsize(os.path.join(o, f)), os.path.join(o, f)) for o, _, fs in os.walk(HIER) for f in fs
                      if f.lower().endswith(".dsd") and os.path.getsize(os.path.join(o, f)) > 250000)
        with tempfile.TemporaryDirectory() as t:
            eingabe, ziel = os.path.join(t, "eingabe", "01_Teststrasse"), os.path.join(t, "vorschau")
            os.makedirs(eingabe)
            shutil.copy(dsds[0][1], os.path.join(eingabe, "messung.dsd"))
            with open(os.devnull, "w") as aus:
                start = lb.bauen(os.path.join(t, "eingabe"), ziel, None, 1, ausgabe=aus)
            self.assertEqual(start, os.path.join(ziel, "index.html"))
            for name in lb.SEITEN + ("impressum.html", "auswertung.json", "summary.csv"):
                self.assertTrue(os.path.exists(os.path.join(ziel, name)), name)
            seiten = os.listdir(os.path.join(ziel, "standorte"))
            self.assertEqual(len(seiten), 1)
            with open(os.path.join(ziel, "standorte", seiten[0]), encoding="utf-8") as fh:
                h = fh.read()
            self.assertIn("<h1>", h)
            self.assertIn('src="../filter.js"', h)
            # der Server liefert die Seiten nur auf dem eigenen Rechner aus
            import http.server
            import functools
            handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ziel)
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                port = server.server_address[1]
                self.assertEqual(server.server_address[0], "127.0.0.1")
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/index.html", timeout=10) as r:
                    self.assertEqual(r.status, 200)
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
