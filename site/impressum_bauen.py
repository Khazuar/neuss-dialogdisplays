#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fabian Grewing
"""
Erzeugt das Impressum aus der Vorlage site/impressum.html.

Anschrift und Telefonnummer stehen nicht im Repository, sondern in GitHub-Repository-Variablen
(Settings -> Secrets and variables -> Actions -> Variables):

  IMPRESSUM_STRASSE   Strasse und Hausnummer (Pflicht)
  IMPRESSUM_ORT       PLZ und Ort (Pflicht)
  IMPRESSUM_TELEFON   Telefonnummer (optional)

Fehlt eine Pflichtangabe, bricht das Skript ab, damit die Seite nie ohne Impressum veroeffentlicht wird.

Aufruf: python3 site/impressum_bauen.py site/impressum.html _site/impressum.html
"""
import html
import os
import sys


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    vorlage, ziel = sys.argv[1:]

    werte = {k: os.environ.get(k, "").strip() for k in ("IMPRESSUM_STRASSE", "IMPRESSUM_ORT", "IMPRESSUM_TELEFON")}
    # fehlt = [k for k in ("IMPRESSUM_STRASSE", "IMPRESSUM_ORT") if not werte[k]]
    # if fehlt:
    #     sys.exit("FEHLER: Repository-Variable(n) nicht gesetzt: " + ", ".join(fehlt))

    with open(vorlage, encoding="utf-8") as f:
        text = f.read()
    telefon = f"<br>\n    Telefon: {html.escape(werte['IMPRESSUM_TELEFON'])}" if werte["IMPRESSUM_TELEFON"] else ""
    ersetzungen = {
        "{{STRASSE}}": html.escape(werte["IMPRESSUM_STRASSE"]),
        "{{ORT}}": html.escape(werte["IMPRESSUM_ORT"]),
        "{{TELEFON_ZEILE}}": telefon,
    }
    for platzhalter, wert in ersetzungen.items():
        if platzhalter not in text:
            sys.exit(f"FEHLER: Platzhalter {platzhalter} fehlt in {vorlage}")
        text = text.replace(platzhalter, wert)
    with open(ziel, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


if __name__ == "__main__":
    main()
