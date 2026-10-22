# SPDX-License-Identifier: MIT
"""V85 der Einsaetze gegen die Messungen und die Angaben der Verwaltung (docs/einsaetze.md): Aendert die Zuordnung die Einstufung?

Stufen der Verwaltung (V85 ueber dem Tempolimit): bis +4 unauffaellig, +5 bis +8 unkritisch, +9 bis +10 noch akzeptabel, ab +11 kritisch.
Fuer jeden Einsatz, der nicht mit seiner Messung zusammenfaellt: V85 des Einsatzes, der Messung (unsere Auswertung, Sicht der Verwaltung) und
die V85 aus den Mitteilungen der Verwaltung. Aufruf: python3 -I tools/einsatz_v85.py [_vorschau]"""
import json
import os
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)
import seiten_bauen  # noqa: E402


def stufe(d):
    return None if d is None else "kritisch" if d >= 11 else "akzeptabel" if d >= 9 else "unkritisch" if d >= 5 else "unauffällig"


def main():
    vorschau = sys.argv[1] if len(sys.argv) > 1 else os.path.join(WURZEL, "_vorschau")
    with open(os.path.join(vorschau, "einsaetze.json"), encoding="utf-8") as fh:
        ein = json.load(fh)
    with open(os.path.join(vorschau, "auswertung.json"), encoding="utf-8") as fh:
        au = json.load(fh)
    with open(os.path.join(WURZEL, "belege", "metadaten.json"), encoding="utf-8") as fh:
        meta = json.load(fh)
    zeile = {seiten_bauen.messung_id(r["standort"], r["datei"]): r for r in au["standorte"]}
    print("%-46s %5s %8s %8s %10s  %s" % ("Einsatz", "Limit", "Einsatz", "Messung", "Verwaltung", "Stufe Einsatz / Messung / Verwaltung"))
    wechsel = 0
    for e in ein["einsaetze"]:
        if e["status"] == "identisch" or not e.get("kennzahlen"):
            continue
        r = zeile[e["messung"]]
        lim = e["limit"]
        v_e = (e["kennzahlen"]["bereinigt"].get("geschwindigkeit_kmh") or {}).get("v85")
        v_m = ((r.get("bereinigt") or {}).get("geschwindigkeit_kmh") or {}).get("v85")
        mm = next((m for m in ((meta.get("standorte") or {}).get(r["standort"]) or {}).get("messungen", []) if m["datei"] == r["datei"]), {})
        v_v = [v.get("v85_kmh") for v in mm.get("verwaltung", []) if v.get("v85_kmh") is not None]
        s = (stufe(v_e - lim if v_e and lim else None), stufe(v_m - lim if v_m and lim else None), stufe(v_v[0] - lim if v_v and lim else None))
        wechsel += s[0] != s[1] or (s[2] is not None and s[0] != s[2])
        print("%-46s %5s %8s %8s %10s  %s / %s / %s%s" % (e["id"][:46], lim, v_e, v_m, ",".join(map(str, v_v)) or "–", *s,
                                                         "  <- andere Stufe" if s[0] != s[1] or (s[2] and s[0] != s[2]) else ""))
    print("Einsaetze mit anderer Stufe als Messung oder Verwaltung:", wechsel)


if __name__ == "__main__":
    main()
