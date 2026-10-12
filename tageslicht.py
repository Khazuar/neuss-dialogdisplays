# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fabian Grewing
"""Tageslicht fuer einen Ort: Sonnenaufgang, Sonnenuntergang und buergerliche Daemmerung (NOAA-Naeherung).

Rein rechnerisch, ohne Daten von aussen. Genauigkeit einige Minuten in mittleren Breiten. Die Refraktion ist eingerechnet
(Sonnenhoehe -0,833 Grad fuer Auf- und Untergang, -6 Grad fuer die buergerliche Daemmerung). Zeiten sind UTC.
Bezugsort ist Neuss (Stadtmitte, Naeherung): BEZUG.

Aufruf: python3 tageslicht.py 2025-06-21   (Ausgabe in Ortszeit)
"""
import datetime as dt
import math
import sys

BEZUG = (51.2042, 6.6879)  # Breite, Laenge: Neuss, Stadtmitte (Naeherung)
H_AUFGANG = -0.833
H_DAEMMERUNG = -6.0


def _sonne(tag, breite, laenge, hoehe):
    """UTC-Zeiten (auf, unter) fuer die Sonnenhoehe `hoehe` (Grad) am Kalendertag `tag`, oder None (Polartag / Polarnacht)."""
    gamma = 2 * math.pi / 365 * (tag.timetuple().tm_yday - 1)
    zeitgleichung = 229.18 * (0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma)
                              - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma))  # Minuten
    dekl = (0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma) - 0.006758 * math.cos(2 * gamma)
            + 0.000907 * math.sin(2 * gamma) - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma))
    phi = math.radians(breite)
    zenit = math.radians(90 - hoehe)
    c = math.cos(zenit) / (math.cos(phi) * math.cos(dekl)) - math.tan(phi) * math.tan(dekl)
    if c < -1 or c > 1:
        return None
    ha = math.degrees(math.acos(c))  # Stundenwinkel in Grad
    beginn = dt.datetime(tag.year, tag.month, tag.day)
    return (beginn + dt.timedelta(minutes=720 - 4 * (laenge + ha) - zeitgleichung),
            beginn + dt.timedelta(minutes=720 - 4 * (laenge - ha) - zeitgleichung))


def sonnenzeiten(tag, ort=BEZUG):
    """dict mit 'aufgang', 'untergang', 'daemmerung_beginn', 'daemmerung_ende' (UTC, naive datetime; None, wo es sie nicht gibt)
    und 'tageslaenge_h'."""
    a = _sonne(tag, ort[0], ort[1], H_AUFGANG)
    z = _sonne(tag, ort[0], ort[1], H_DAEMMERUNG)
    return {"aufgang": a[0] if a else None, "untergang": a[1] if a else None,
            "daemmerung_beginn": z[0] if z else None, "daemmerung_ende": z[1] if z else None,
            "tageslaenge_h": (a[1] - a[0]).total_seconds() / 3600 if a else None}


def lichtart(utc, ort=BEZUG):
    """'tag' (Sonne ueber dem Horizont), 'daemmerung' (bis -6 Grad) oder 'nacht' fuer einen UTC-Zeitpunkt."""
    z = sonnenzeiten(utc.date(), ort)
    if z["aufgang"] and z["aufgang"] <= utc <= z["untergang"]:
        return "tag"
    if z["daemmerung_beginn"] and z["daemmerung_beginn"] <= utc <= z["daemmerung_ende"]:
        return "daemmerung"
    return "tag" if z["aufgang"] is None and z["daemmerung_beginn"] is None and ort[0] * (1 if tag_sommer(utc) else -1) > 0 else "nacht"


def tag_sommer(utc):
    """Naeherung fuer Polartage: Sommerhalbjahr der Nordhalbkugel (Maerz bis September)."""
    return 3 <= utc.month <= 9


def main():
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I nimmt das Skriptverzeichnis nicht auf
    import dsd2csv  # nur fuer die Ortszeit der Ausgabe
    tag = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else dt.date.today()
    z = sonnenzeiten(tag)
    versatz = dt.timedelta(hours=dsd2csv.utc_versatz_h(dt.datetime(tag.year, tag.month, tag.day, 12)))
    for k in ("daemmerung_beginn", "aufgang", "untergang", "daemmerung_ende"):
        print("%-18s %s" % (k, (z[k] + versatz).strftime("%H:%M") if z[k] else "-"))
    print("Tageslaenge        %.2f h" % z["tageslaenge_h"])


if __name__ == "__main__":
    main()
