# SPDX-License-Identifier: MIT
"""Liest die mit ris_sammeln.py geladenen Dokumente und schreibt die genannten Messorte und
Erfassungszeitraeume nach belege/ris.json.

Aufruf:
  PYPDF_PFAD=<Ordner mit pypdf> python3 -I tools/ris_auswerten.py ris_roh . belege/ris.json

  ris_roh   Ordner von ris_sammeln.py
  .         Ordner mit den DSD-Dateien (die Ordnernamen sind die Liste der Messorte)
  Ausgabe   JSON mit je Dokument: Vorlage, Gremium, Sitzung, Zeitraeume, genannte Orte

Es werden nur Tatsachen uebernommen (Datum, Gremium, Ortsnamen, Quelle), kein Fliesstext.
Die Zuordnung "Ort wird im Dokument genannt" ist ein Namensvergleich ohne Wortgrenzen und deshalb
nur ein Indiz: der Ortsname einer Messstelle muss im Dokument vorkommen, die Zeitraeume gelten fuer
das ganze Dokument, nicht fuer einen einzelnen Ort.

pypdf ist keine Standardbibliothek. Wer es nicht installiert hat, setzt PYPDF_PFAD auf einen
Ordner, in den es mit "pip install --target <Ordner> pypdf" installiert wurde.
"""
import datetime as dt
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from uhr_belege import messort_namen, schluessel  # noqa: E402

if os.environ.get("PYPDF_PFAD"):
    sys.path.insert(0, os.environ["PYPDF_PFAD"])
try:
    from pypdf import PdfReader
except ImportError:
    sys.exit("pypdf fehlt: pip install --target <Ordner> pypdf und PYPDF_PFAD=<Ordner> setzen")

ZEITRAUM = re.compile(r"(?:vom|von)\s+(\d{2})\.(\d{2})\.(\d{4})\s+bis\s+(?:zum\s+)?(\d{2})\.(\d{2})\.(\d{4})")
SITZUNG = re.compile(r"(Bezirksausschuss[^0-9\n]{3,70}?|Ausschuss[^0-9\n]{3,70}?|Rat der Stadt Neuss)\s+(\d{2})\.(\d{2})\.(\d{4})")
VORLAGE = re.compile(r"\b(\d{2}/\d{1,4}/\d{4})\b")


def ortsnamen(wurzel):
    """Messorte aus den Ordnernamen (Schluessel -> Name)."""
    namen = {}
    for ordner in sorted(os.listdir(wurzel)):
        if not os.path.isdir(os.path.join(wurzel, ordner)) or ordner.startswith((".", "_", "site", "docs", "tools", "belege", "analyse")):
            continue
        for name in messort_namen(ordner):
            namen.setdefault(schluessel(name), name)
    return namen


def datum(t, m, j):
    return dt.date(int(j), int(m), int(t)).isoformat()


def main():
    roh, wurzel, ziel = sys.argv[1:4]
    index = json.load(open(os.path.join(roh, "index.json"), encoding="utf-8"))
    orte = ortsnamen(wurzel)
    ausgabe = []
    for kvonr, v in sorted(index.items(), key=lambda x: int(x[0])):
        for dok in v["dokumente"]:
            pfad = os.path.join(roh, f"do_{dok}.pdf")
            try:
                text = "\n".join((p.extract_text() or "") for p in PdfReader(pfad).pages)
            except Exception as e:  # beschaedigte Datei
                print(f"  {pfad}: {e}", file=sys.stderr)
                continue
            t = re.sub(r"-\s*\n\s*", "", text)  # Silbentrennung am Zeilenende
            t = re.sub(r"\s+", " ", t)
            zeitraeume = []
            for m in ZEITRAUM.finditer(t):
                z = [datum(*m.group(1, 2, 3)), datum(*m.group(4, 5, 6))]
                if z not in zeitraeume:
                    zeitraeume.append(z)
            if not zeitraeume:
                continue
            s = SITZUNG.search(t)
            vorl = VORLAGE.search(t)
            schl = schluessel(t)
            genannt = sorted({name for key, name in orte.items() if key in schl})
            ausgabe.append({
                "vorlage": vorl.group(1) if vorl else None,
                "betreff": v["titel"],
                "gremium": s.group(1).strip() if s else None,
                "sitzung": datum(*s.group(2, 3, 4)) if s else None,
                "dokument": f"{v['url'].split('vo0050')[0]}getfile.asp?id={dok}&type=do",
                "zeitraeume": zeitraeume,
                "orte": genannt,
            })
    os.makedirs(os.path.dirname(ziel) or ".", exist_ok=True)
    with open(ziel, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"quelle": "Ratsinformationssystem der Stadt Neuss (ris-neuss.itk-rheinland.de), Mitteilungen der Verwaltung "
                             "zu den Dialog Displays; erzeugt von tools/ris_auswerten.py",
                   "hinweis": "Zeitraeume gelten fuer das ganze Dokument, Orte sind Namensvergleiche (siehe Skript)",
                   "dokumente": ausgabe}, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"{len(ausgabe)} Dokumente mit Zeitraeumen, {len(orte)} Ortsschluessel", file=sys.stderr)


if __name__ == "__main__":
    main()
