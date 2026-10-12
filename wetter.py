#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fabian Grewing
"""Wetterdaten des Deutschen Wetterdienstes (DWD) fuer die Auswertung: erzeugt belege/wetter.json.

Quelle: Deutscher Wetterdienst, Climate Data Center (https://opendata.dwd.de/climate_environment/CDC/), Lizenz CC BY 4.0,
Quellenvermerk "Quelle: Deutscher Wetterdienst". Siehe docs/wetter.md.

Je Kalendertag (Ortszeit):
  - Niederschlag in mm je Ortszeit-Stunde (nur an Tagen mit Niederschlag) und als Tagessumme, von der naechstgelegenen Station
    (Abstand zum Bezugsort Neuss), die fuer den Tag mindestens 22 gueltige Stunden hat; die Station steht im Feld "st".
    Wechselt sie von Tag zu Tag, steht das in der Tabelle und wird auf den Seiten ausgezeichnet.
  - Tageswerte der Klimastation (Temperatur, Wind, Schnee) aus den DWD-Tageswerten.

Zeitangabe der DWD-Stundenwerte: UTC, der Zeitstempel ist das Ende der Stunde. Der Niederschlag der Ortszeit-Stunde [h, h+1)
ist der Wert zum Zeitstempel UTC(h) + 1 Stunde. Das folgt aus dem Stoersignal, das Regen im Radar der Geraete erzeugt
(docs/wetter.md).

Aufruf:
  python3 -I wetter.py --von 2022-03-01 --bis 2026-09-01 --laden ROHDATEN -o belege/wetter.json
  python3 -I wetter.py --von 2022-03-01 --bis 2026-09-01 --roh ROHDATEN -o belege/wetter.json    (ohne Download)
Die heruntergeladenen Dateien gelten als fremde Daten: eigener Ordner, nur die Datei produkt_*.txt der ZIP-Archive wird gelesen.
"""
import argparse
import datetime as dt
import io
import json
import math
import os
import re
import sys
import urllib.request
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I nimmt das Skriptverzeichnis nicht auf
import dsd2csv  # noqa: E402  (ortszeit_zu_utc)

BASIS = "https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate"
BEZUG = (51.2042, 6.6879)  # Neuss, Stadtmitte (Naeherung); die Messstellen haben keine Koordinaten im Datenbestand
RADIUS_KM = 25
MIN_STUNDEN = 22  # so viele gueltige Stunden braucht ein Tag von einer Station
KLIMA_STATION = "01078"  # Duesseldorf: naechste Station mit Temperatur, Wind und Schnee
MAX_MITGLIED = 60_000_000  # groesstes Archivmitglied, das gelesen wird (Byte)
VERMERK = "Quelle: Deutscher Wetterdienst"
AENDERUNG = ("Datenbasis: Deutscher Wetterdienst, Stundenwerte des Niederschlags auf Ortszeit-Tage umgerechnet, Station je Tag nach "
             "Abstand zu Neuss gewaehlt, Einzelwerte ausgewaehlt und zusammengefasst")
HOUR = dt.timedelta(hours=1)


def km(a, b):
    """Abstand zweier Punkte (Breite, Laenge in Grad) in km (Haversine)."""
    p = math.pi / 180
    x = math.sin((b[0] - a[0]) * p / 2) ** 2 + math.cos(a[0] * p) * math.cos(b[0] * p) * math.sin((b[1] - a[1]) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))


# ------------------------------------------------------------------ Einlesen

def lies_stationen(text):
    """Stationsliste (RR_Stundenwerte_Beschreibung_Stationen.txt) -> [dict(id, von, bis, breite, laenge, name)].

    Zeilen: ID, von, bis, Hoehe, Breite, Laenge, Name (kann Leerzeichen enthalten), Bundesland, Abgabe; durch Leerraum getrennt.
    Nur Stationen mit "Abgabe: Frei" (frei abgegebene Daten); bei den uebrigen fehlt das Feld und es gibt keine Datei."""
    out = []
    for z in text.splitlines()[2:]:
        t = z.split()
        if len(t) < 9 or t[-1] != "Frei":
            continue
        try:
            out.append({"id": t[0], "von": t[1], "bis": t[2], "breite": float(t[4]), "laenge": float(t[5]), "name": " ".join(t[6:-2])})
        except ValueError:
            continue
    return out


def lies_zip(daten, anfang="produkt_"):
    """Zeilen der Produktdatei eines DWD-ZIP-Archivs (Text, latin-1)."""
    with zipfile.ZipFile(io.BytesIO(daten)) as zf:
        for info in zf.infolist():
            if os.path.basename(info.filename).startswith(anfang) and info.file_size <= MAX_MITGLIED:
                return io.TextIOWrapper(zf.open(info), encoding="latin-1").read().splitlines()
    return []


def stundenwerte(zeilen):
    """DWD-Stundenwerte des Niederschlags -> {'JJJJMMTTHH' (UTC, Ende der Stunde): mm oder None}."""
    out = {}
    for z in zeilen:
        t = [x.strip() for x in z.split(";")]
        if len(t) < 4 or not t[1].isdigit():
            continue
        try:
            r1 = float(t[3])
        except ValueError:
            continue
        out[t[1]] = None if r1 <= -999 else r1
    return out


def tageswerte(zeilen):
    """DWD-Tageswerte (KL) -> {date: dict(tmk, tnk, txk, tgk, fx, fm, shk)}; fehlende Werte None."""
    kopf = None
    out = {}
    for z in zeilen:
        t = [x.strip() for x in z.split(";")]
        if t[0] == "STATIONS_ID":
            kopf = t
            continue
        if kopf is None or len(t) < len(kopf) - 1 or not t[1].isdigit():
            continue
        s = dict(zip(kopf, t))

        def f(name):
            try:
                v = float(s[name])
            except (KeyError, ValueError):
                return None
            return None if v <= -999 else v
        tag = dt.datetime.strptime(t[1], "%Y%m%d").date()
        out[tag] = {"tmk": f("TMK"), "tnk": f("TNK"), "txk": f("TXK"), "tgk": f("TGK"), "fx": f("FX"), "fm": f("FM"), "shk": f("SHK_TAG")}
    return out


# ------------------------------------------------------------------ Umrechnung auf Ortszeit-Tage

def ortszeit_stunden(tag, werte):
    """24 Werte (mm) der Ortszeit-Stunden [h, h+1) des Kalendertags `tag`; None, wo die Station keinen Wert hat."""
    out = []
    for h in range(24):
        u = dsd2csv.ortszeit_zu_utc(dt.datetime(tag.year, tag.month, tag.day, h)) + HOUR  # Zeitstempel = Ende der Stunde
        out.append(werte.get(u.strftime("%Y%m%d%H")))
    return out


def waehle_station(tag, reihe):
    """Erste Station der Reihe (nach Abstand geordnet) mit mindestens MIN_STUNDEN gueltigen Stunden am Tag.

    reihe: [(Stations-ID, {Zeitstempel: mm})]. Gibt (ID, 24 Stundenwerte) oder (None, None) zurueck."""
    for sid, werte in reihe:
        std = ortszeit_stunden(tag, werte)
        if sum(1 for x in std if x is not None) >= MIN_STUNDEN:
            return sid, std
    return None, None


def bauen(von, bis, reihe, klima, stationen_info):
    """Tabelle belege/wetter.json als dict. reihe: nach Abstand geordnet, klima: {date: Tageswerte}, stationen_info: {ID: dict}."""
    tage = {}
    tag = von
    while tag <= bis:
        sid, std = waehle_station(tag, reihe)
        eintrag = {}
        if sid:
            gueltig = [x for x in std if x is not None]
            eintrag["st"] = sid
            eintrag["mm"] = round(sum(gueltig), 1)
            if eintrag["mm"] >= 0.1:
                eintrag["std"] = [None if x is None else round(x, 1) for x in std]
        k = klima.get(tag)
        if k:
            eintrag.update({n: v for n, v in k.items() if v is not None})
        if eintrag:
            tage[tag.isoformat()] = eintrag
        tag += dt.timedelta(days=1)
    reihen = {}  # je Station alle Tage mit mindestens MIN_STUNDEN gueltigen Stunden: daraus waehlt dsd2csv.py die Station je Messstelle
    for sid, werte in reihe:
        info = stationen_info.get(sid, {})
        t_station = {}
        tag = von
        while tag <= bis:
            std = ortszeit_stunden(tag, werte)
            gueltig = [x for x in std if x is not None]
            if len(gueltig) >= MIN_STUNDEN:
                e = {"mm": round(sum(gueltig), 1)}
                if e["mm"] >= 0.1:
                    e["std"] = [None if x is None else round(x, 1) for x in std]
                t_station[tag.isoformat()] = e
            tag += dt.timedelta(days=1)
        if t_station:
            reihen[sid] = {"name": info.get("name"), "breite": info.get("breite"), "laenge": info.get("laenge"), "tage": t_station}
    wechsel = sum(1 for a, b in zip(sorted(tage), sorted(tage)[1:]) if tage[a].get("st") and tage[b].get("st") and tage[a]["st"] != tage[b]["st"])
    return {"quelle": "Deutscher Wetterdienst (DWD), Climate Data Center, " + BASIS.rsplit("/", 2)[0] + "/",
            "lizenz": "CC BY 4.0 (Creative Commons Namensnennung, https://creativecommons.org/licenses/by/4.0/), nicht CC0",
            "quellenvermerk": VERMERK, "aenderungen": AENDERUNG,
            "bezugsort": {"name": "Neuss", "breite": BEZUG[0], "laenge": BEZUG[1]},
            "zeitangabe": "Tage und Stunden in Ortszeit (MEZ/MESZ); Niederschlag je Stunde [h, h+1) in mm; Tageswerte der Klimastation wie vom DWD (Tag nach UTC)",
            "felder": {"st": "Station des Niederschlags (siehe stationen)", "mm": "Niederschlag des Tages (Summe der Stunden), mm",
                       "std": "Niederschlag je Ortszeit-Stunde 0 bis 23, mm, null = fehlt (nur an Tagen mit mindestens 0,1 mm)",
                       "tmk": "Tagesmittel der Temperatur, Grad C", "tnk": "Tagesminimum, Grad C", "txk": "Tagesmaximum, Grad C",
                       "tgk": "Minimum in 5 cm Hoehe (Bodenfrost), Grad C", "fx": "Windspitze, m/s", "fm": "mittlere Windgeschwindigkeit, m/s",
                       "shk": "Schneehoehe, cm"},
            "stationen": {sid: stationen_info[sid] for sid in sorted({t["st"] for t in tage.values() if t.get("st")})},
            "klimastation": stationen_info.get(KLIMA_STATION, {"id": KLIMA_STATION}),
            "reihen": reihen,
            "reihen_hinweis": "Niederschlag je Station (mm, std wie bei tage); die Auswertung nimmt je Messstelle und Tag die naechste Station mit "
                              "mindestens 22 gueltigen Stunden. 'tage' gilt fuer den Bezugsort Neuss.",
            "stationswechsel": wechsel, "von": von.isoformat(), "bis": bis.isoformat(), "tage": tage}


# ------------------------------------------------------------------ Laden und Zusammenstellen

def hole(url, ziel=None):
    with urllib.request.urlopen(url, timeout=120) as r:
        daten = r.read()
    if ziel:
        with open(ziel, "wb") as fh:
            fh.write(daten)
    return daten


def dateiliste(url):
    return sorted(set(re.findall(r'href="([^"]+\.zip)"', hole(url).decode("utf-8", "replace"))))


def sammle(roh, laden, von, bis):
    """Liest (und laedt bei `laden`) Stationsliste, Stundenwerte der Stationen im Umkreis und Tageswerte der Klimastation."""
    os.makedirs(roh, exist_ok=True)
    pfad_st = os.path.join(roh, "RR_Stundenwerte_Beschreibung_Stationen.txt")
    if laden:
        hole(BASIS + "/hourly/precipitation/recent/RR_Stundenwerte_Beschreibung_Stationen.txt", pfad_st)
    liste = lies_stationen(open(pfad_st, encoding="latin-1").read())
    nah = []
    for s in liste:
        s["km"] = round(km(BEZUG, (s["breite"], s["laenge"])), 1)
        if s["km"] <= RADIUS_KM and s["bis"] >= von.strftime("%Y%m%d") and s["von"] <= bis.strftime("%Y%m%d"):
            nah.append(s)
    nah.sort(key=lambda s: s["km"])
    zips = {}
    if laden:
        for art in ("historical", "recent"):
            zips[art] = dateiliste("%s/hourly/precipitation/%s/" % (BASIS, art))
    reihe, info = [], {}
    for s in nah:
        werte = {}
        for art in ("historical", "recent"):
            namen = [n for n in zips.get(art, []) if n.startswith("stundenwerte_RR_%s_" % s["id"])] or \
                    [n for n in (os.listdir(roh) if os.path.isdir(roh) else []) if n.startswith("stundenwerte_RR_%s_" % s["id"]) and (("_hist" in n) == (art == "historical"))]
            for n in namen:
                p = os.path.join(roh, os.path.basename(n))
                if laden:
                    hole("%s/hourly/precipitation/%s/%s" % (BASIS, art, os.path.basename(n)), p)
                if os.path.exists(p):
                    werte.update(stundenwerte(lies_zip(open(p, "rb").read())))
        if werte:
            reihe.append((s["id"], werte))
            info[s["id"]] = {"id": s["id"], "name": s["name"], "km": s["km"], "breite": s["breite"], "laenge": s["laenge"]}
    # Klimastation
    klima = {}
    ks = next((s for s in liste if s["id"] == KLIMA_STATION), None)
    for art, muster in (("historical", r"tageswerte_KL_%s_.*_hist\.zip"), ("recent", r"tageswerte_KL_%s_akt\.zip")):
        if laden:
            for n in dateiliste("%s/daily/kl/%s/" % (BASIS, art)):
                if re.fullmatch(muster % KLIMA_STATION, os.path.basename(n)):
                    hole("%s/daily/kl/%s/%s" % (BASIS, art, os.path.basename(n)), os.path.join(roh, os.path.basename(n)))
        for n in os.listdir(roh):
            if re.fullmatch(muster % KLIMA_STATION, n):
                klima.update(tageswerte(lies_zip(open(os.path.join(roh, n), "rb").read())))
    if ks:
        info[KLIMA_STATION] = {"id": KLIMA_STATION, "name": ks["name"], "km": round(km(BEZUG, (ks["breite"], ks["laenge"])), 1),
                               "breite": ks["breite"], "laenge": ks["laenge"]}
    return reihe, klima, info


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--von", required=True, help="erster Tag (JJJJ-MM-TT)")
    ap.add_argument("--bis", required=True, help="letzter Tag (JJJJ-MM-TT)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--laden", metavar="ORDNER", help="DWD-Dateien in diesen Ordner laden und lesen")
    g.add_argument("--roh", metavar="ORDNER", help="bereits geladene DWD-Dateien in diesem Ordner lesen")
    ap.add_argument("-o", "--ausgabe", default="belege/wetter.json")
    a = ap.parse_args()
    von, bis = dt.date.fromisoformat(a.von), dt.date.fromisoformat(a.bis)
    reihe, klima, info = sammle(a.laden or a.roh, bool(a.laden), von, bis)
    erg = bauen(von, bis, reihe, klima, info)
    os.makedirs(os.path.dirname(os.path.abspath(a.ausgabe)), exist_ok=True)
    with open(a.ausgabe, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(erg, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")
    mit = sum(1 for t in erg["tage"].values() if "st" in t)
    print("%d Tage (%d mit Niederschlag von %d Stationen: %s), %d Stationswechsel -> %s" % (
        len(erg["tage"]), mit, len(erg["stationen"]), ", ".join("%s %s (%.1f km)" % (s["id"], s["name"], s["km"]) for s in erg["stationen"].values()),
        erg["stationswechsel"], a.ausgabe), file=sys.stderr)


if __name__ == "__main__":
    main()
