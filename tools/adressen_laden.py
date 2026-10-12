# SPDX-License-Identifier: MIT
"""Zieht die Hauskoordinaten der Stadt Neuss aus den Gebaeudereferenzen von Geobasis NRW.

Aufruf:
  python3 -I tools/adressen_laden.py belege/neuss-adressen.csv [gebref.zip]

Ohne zweites Argument wird die Landesdatei geladen (rund 100 MB, Open Data, keine Anmeldung):
  https://www.opengeodata.nrw.de/produkte/geobasis/lk/akt/gebref_txt/gebref_EPSG25832_ASCII.zip
Wer die Datei schon hat, gibt ihren Pfad an. Aus den Zeilen der Gemeinde Neuss (Rhein-Kreis Neuss) wird eine
kleine CSV mit den Spalten, die standorte.py braucht, gebaut:
  schluessel;strasse;hausnr;zusatz;ost;nord;qualitaet
(schluessel = Strassenschluessel des Landes; derselbe Strassenname kann mehrere Schluessel haben, wenn die Strasse
in Abschnitte geteilt ist. ost/nord in Metern, ETRS89 / UTM 32 (EPSG:25832). qualitaet: A = Lage aus Liegenschaftskataster,
B/C = abgeleitet.)

Lizenz der Daten: Datenlizenz Deutschland - Zero - Version 2.0 (https://www.govdata.de/dl-de/zero-2-0),
Quelle: Geobasis NRW, Gebaeudereferenzen (Hauskoordinaten). Die Datei darf ohne Einschraenkung verwendet werden;
die Quelle wird trotzdem genannt.

Python 3.7 unter Windows kennt die Zwischenzertifikate nicht immer; dann SSL_CERT_FILE auf ein CA-Buendel setzen
(die Pruefung bleibt an).
"""
import csv
import io
import os
import sys
import urllib.request
import zipfile

URL = "https://www.opengeodata.nrw.de/produkte/geobasis/lk/akt/gebref_txt/gebref_EPSG25832_ASCII.zip"
KENNUNG = "neuss-dialogdisplays/1.0 (Recherche; fabian.grewing@proton.me)"
GEMEINDE = "Neuss"
KREIS = "Rhein-Kreis Neuss"


def lade(url, ziel):
    req = urllib.request.Request(url, headers={"User-Agent": KENNUNG})
    with urllib.request.urlopen(req, timeout=300) as r, open(ziel, "wb") as fh:
        while True:
            block = r.read(1 << 20)
            if not block:
                break
            fh.write(block)


def zeilen(pfad_zip):
    """(schluessel, strasse, hausnr, zusatz, ost, nord, qualitaet) der Gemeinde Neuss."""
    with zipfile.ZipFile(pfad_zip) as z:
        with z.open("gebref.txt") as fh:
            for zeile in io.TextIOWrapper(fh, encoding="utf-8"):
                t = zeile.rstrip("\n").split(";")
                if len(t) < 20 or t[0] != "N" or t[8] != KREIS or t[10] != GEMEINDE:
                    continue
                yield t[13], t[14], t[15], t[16], t[18], t[19], t[2]


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    ziel = sys.argv[1]
    pfad = sys.argv[2] if len(sys.argv) > 2 else ziel + ".zip.tmp"
    if len(sys.argv) <= 2:
        print("lade", URL, file=sys.stderr)
        lade(URL, pfad)
    daten = sorted(set(zeilen(pfad)), key=lambda z: (z[1], z[0], int(z[2] or 0), z[3]))
    with open(ziel, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter=";", lineterminator="\n")
        w.writerow(["schluessel", "strasse", "hausnr", "zusatz", "ost", "nord", "qualitaet"])
        for s, strasse, nr, zus, ost, nord, q in daten:
            w.writerow([s, strasse, nr, zus, "%.1f" % float(ost), "%.1f" % float(nord), q])
    if len(sys.argv) <= 2:
        os.remove(pfad)
    print(len(daten), "Adressen in", ziel, file=sys.stderr)


if __name__ == "__main__":
    main()
