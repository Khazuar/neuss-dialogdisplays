#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fabian Grewing
"""
dsd2csv.py - wandelt .dsd-Dateien (Dialogdisplay/DataCollect "DSD") in CSV um und wertet sie
je Standort aus (V85/V95/V99, Einhaltungsquote, qualifizierte Einhaltungsquote) als YAML.

Dateiformat (durch Analyse ermittelt, nicht offiziell dokumentiert):

  Kopf      6 Byte  "004DSD"
  Konfig    Folge von Key/Value-Records:
              [Typ 1B][0x00][Wertlaenge 1B][Namenslaenge 1B][Name][Wert][2 Byte Pruefsumme]
            Ein 0xFF-Byte trennt Bloecke (Konfig, Aktiv-Flags, Signatur).
  Daten     Folge von Records, jeweils mit CRC-8/MAXIM ueber alle Bytes davor
            (Poly 0x31 reflektiert, Init 0) als letztem Byte:
              Typ 0x0F  Fahrzeug (9 Byte): 0F  v  YY MM DD hh mm ss  crc
                                   v = Geschwindigkeit in km/h (1 Byte)
              Typ 0x33  Status  (9 Byte): 33  YY MM DD hh mm ss  x  crc
              Typ 0x20  Status (10 Byte): 20  YY MM DD hh mm ss  x1 x2 crc  (aeltere Firmware)
            Jahr = 2000 + YY. Abschluss mit 0xFF. Records mit falscher CRC werden
            uebersprungen und in den Warnungen gezaehlt.

Tempolimit (fuer die Quoten), in dieser Reihenfolge:
  1. --limit N                        (erzwingt N fuer alle Dateien)
  2. Korrektur aus belege/korrekturen.json: nennt die Mitteilung der Verwaltung ein anderes Limit als die DSD
                                       (metadaten.py, siehe docs/metadaten.md), gilt das Limit der Mitteilung
  3. Konfigurationswert "safety_speed" (damit schaltet das Display Smiley/Frowny; das ist eine Anzeige-Schwelle und
                                       nicht immer das vorgeschriebene Limit; stimmt mit "Vmax StVO" der DataCollect-PDFs ueberein)
  4. Zahl im Geraetenamen ("Tempo30", "Ville Norf 30", ...)

Auswertung je Datei (als <name>.yaml neben der CSV):
  V85/V95/V99   kleinste Geschwindigkeit, bei der mind. 85/95/99 % der Fahrzeuge <= v
  Einhaltungsquote               Anteil mit v <= Limit
  qualifizierte Einhaltungsquote Anteil mit v - Toleranz <= Limit
                                 (Toleranz: 3 km/h unter 100 km/h, ab 100 km/h 3 % aufgerundet)

Aufruf:
  python3 -I dsd2csv.py datei.dsd                  -> datei.csv + datei.yaml (Kurzstatistik auf stderr)
  python3 -I dsd2csv.py ordner/                    -> rekursiv je DSD eine CSV + YAML daneben,
                                                      dazu auswertung.yaml, auswertung.json und summary.csv
  python3 -I dsd2csv.py ordner/ -o ausgabe_ordner  -> Ergebnisse unter ausgabe_ordner (Unterordner bleiben erhalten)
  Optionen: --limit 30   Tempolimit fuer alle Dateien erzwingen
            --min-kmh N  zusaetzlich Werte unter N km/h aus der Auswertung nehmen (CSV bleibt vollstaendig); Standard 0.
                         Den verkehrsunabhaengigen Rauschboden (sehr langsame Werte) rechnet rauschen.py heraus.
            --meta       Konfigurationswerte der Datei ausgeben
            --status     Status-Records (0x33/0x20) als eigene CSV mitschreiben

Nur Standardbibliothek. Mit "python3 -I" starten, wenn Dateien aus unsicherer
Quelle stammen.
"""
import argparse
import bisect
import collections
import csv
import datetime as dt
import functools
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I nimmt das Skriptverzeichnis nicht auf
import rauschen  # noqa: E402

MAGIC = b"004DSD"
T_VEH = 0x0F
# Recordlaenge je Typ (inkl. Typ-Byte und CRC): 0x0F Fahrzeug, 0x33/0x20 Status
REC_LEN = {0x0F: 9, 0x33: 9, 0x20: 10}


def _crc_table():
    t = []
    for i in range(256):
        c = i
        for _ in range(8):
            c = (c >> 1) ^ 0x8C if c & 1 else c >> 1
        t.append(c)
    return t


_T = _crc_table()


def crc8(data):
    """CRC-8/MAXIM (Poly 0x31 reflektiert, Init 0) - Pruefbyte am Recordende."""
    c = 0
    for x in data:
        c = _T[c ^ x]
    return c


def parse(buf):
    """Gibt (meta, fahrzeuge, status, warnungen) zurueck."""
    if not buf.startswith(MAGIC):
        raise ValueError("Kein DSD-Header (004DSD) gefunden")
    meta, veh, status, warn = {}, [], [], []
    p, n = len(MAGIC), len(buf)

    # --- Konfigurationsbloecke ---
    while p < n:
        if buf[p] == 0xFF:
            p += 1
            continue
        if p + 4 > n:
            break
        t, z, vl, nl = buf[p], buf[p + 1], buf[p + 2], buf[p + 3]
        name = buf[p + 4:p + 4 + nl]
        if z != 0 or nl == 0 or not all(32 <= c < 127 for c in name):
            break  # Beginn des Datenteils
        val = buf[p + 4 + nl:p + 4 + nl + vl]
        txt = val.decode("ascii") if val and all(32 <= c < 127 for c in val) else val.hex()
        meta[name.decode()] = txt
        p += 6 + nl + vl
    data_start = p

    # --- Datenrecords (Laenge je Typ, jeder Record per CRC-8 geprueft) ---
    bad_crc = skipped = 0
    while p < n:
        t = buf[p]
        L = REC_LEN.get(t)
        if t == 0xFF and L is None:
            p += 1
            continue
        if L is None or p + L > n:
            skipped += 1
            p += 1
            continue
        r = buf[p:p + L]
        if crc8(r[:-1]) != r[-1]:
            bad_crc += 1
            skipped += 1
            p += 1  # Resynchronisation: Byte fuer Byte weitersuchen
            continue
        try:
            if t == T_VEH:
                v, yy, mo, d, h, mi, s = r[1:8]
                veh.append((dt.datetime(2000 + yy, mo, d, h, mi, s), v))
            else:  # Statusrecords: Zeitstempel + Nutzlast
                yy, mo, d, h, mi, s = r[1:7]
                try:
                    ts = dt.datetime(2000 + yy, mo, d, h, mi, s)
                except ValueError:
                    ts = None  # z.B. Geraeteuhr noch nicht gestellt
                # vierter Wert: Anzahl der bis hier gelesenen Fahrzeuge (Reihenfolge in der Datei)
                status.append((ts, t, r[7:-1].hex(), len(veh)))
        except ValueError:
            warn.append(f"Ungueltiger Zeitstempel bei Offset {p}: {r.hex()}")
        p += L
    if skipped:
        warn.append(f"{skipped} Bytes uebersprungen (davon {bad_crc} mit falscher CRC)")
    meta["_data_offset"] = str(data_start)
    return meta, veh, status, warn


def pct(sorted_v, q):
    """Perzentil: kleinste Geschwindigkeit, bei der mind. q% der Fahrzeuge <= v."""
    k = max(0, math.ceil(q / 100 * len(sorted_v)) - 1)
    return sorted_v[k]


def byte_wert(txt):
    """Einbyte-Konfigwert: parse() liefert druckbare Bytes als Zeichen (0x32 -> "2"), sonst als Hex."""
    if not txt:
        return None
    try:
        return ord(txt) if len(txt) == 1 else int(txt, 16)
    except ValueError:
        return None


def tempolimit(meta, override=None, korrektur=None):
    """Gibt (limit, quelle) zurueck: --limit, sonst Korrektur aus den Mitteilungen, sonst safety_speed der DSD, sonst Zahl im Namen.

    Die Korrektur (belege/korrekturen.json, von metadaten.py) gilt nur, wo die Mitteilung der Verwaltung ein anderes Limit
    nennt als die Anzeige-Schwelle in der DSD-Konfiguration.
    """
    if override:
        return override, "parameter"
    if korrektur:
        return korrektur["tempolimit_kmh"], "mitteilung_verwaltung"
    v = byte_wert(meta.get("safety_speed"))
    if v and 10 <= v <= 120:
        return v, "dsd_konfiguration"
    m = re.search(r"(?:tempo|\b)\s*(\d{2,3})\s*(?:km|$)?", meta.get("name", ""), re.I)
    if m and 10 <= int(m.group(1)) <= 120:
        return int(m.group(1)), "geraetename"
    return None, None


def toleranz(v):
    """Messtoleranz: 3 km/h unter 100 km/h, ab 100 km/h 3 % (aufgerundet)."""
    return 3 if v < 100 else math.ceil(0.03 * v)


def stats(veh, limit=None, min_kmh=0):
    veh = [x for x in veh if x[1] >= min_kmh]
    v = sorted(x[1] for x in veh)
    if not v:
        return {}
    n = len(v)
    s = {
        "anzahl_fahrzeuge": n,
        "messzeitraum": {"start": min(x[0] for x in veh).isoformat(sep=" "),
                         "ende": max(x[0] for x in veh).isoformat(sep=" ")},
        "geschwindigkeit_kmh": {
            "mittel": round(sum(v) / n, 2), "maximal": v[-1],
            "v85": pct(v, 85), "v95": pct(v, 95), "v99": pct(v, 99),
        },
    }
    if limit:
        ueber = sum(1 for x in v if x > limit)
        ueber_tol = sum(1 for x in v if x - toleranz(x) > limit)
        s["einhaltung"] = {
            "einhaltungsquote_prozent": round(100 * (n - ueber) / n, 2),
            "qualifizierte_einhaltungsquote_prozent": round(100 * (n - ueber_tol) / n, 2),
            "anzahl_ueber_limit": ueber,
            "anzahl_ueber_limit_plus_toleranz": ueber_tol,
        }
    return s


def yaml_skalar(x):
    if x is None:
        return "null"
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, (int, float)):
        return repr(x)
    return json.dumps(x, ensure_ascii=False)  # JSON-String ist gueltiges YAML


def yaml_zeilen(obj, einzug=0):
    pad = "  " * einzug
    zeilen = []
    for k, x in obj.items():
        if isinstance(x, dict):
            zeilen.append(f"{pad}{k}:")
            zeilen += yaml_zeilen(x, einzug + 1)
        elif isinstance(x, list) and not x:
            zeilen.append(f"{pad}{k}: []")
        elif isinstance(x, list) and all(isinstance(i, int) and not isinstance(i, bool) for i in x):
            zeilen.append(f"{pad}{k}: [{', '.join(str(i) for i in x)}]")  # Zahlenlisten (Histogramm) in einer Zeile
        elif isinstance(x, list):
            zeilen.append(f"{pad}{k}:")
            for item in x:
                if isinstance(item, dict):
                    sub = yaml_zeilen(item)
                    zeilen.append(f"{pad}  - {sub[0]}")
                    zeilen += [f"{pad}    {z}" for z in sub[1:]]
                else:
                    zeilen.append(f"{pad}  - {yaml_skalar(item)}")
        else:
            zeilen.append(f"{pad}{k}: {yaml_skalar(x)}")
    return zeilen


def schreibe_yaml(pfad, zeilen):
    with open(pfad, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(zeilen) + "\n")


def standort_slug(standort):
    """Dateiname der Detailseite eines Standortordners: "Stationär_Villestraße/FR GV" -> "stationaer-villestrasse-fr-gv"."""
    t = standort.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        t = t.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def flach(obj, prefix=""):
    """Verschachteltes Dict -> flaches Dict (fuer summary.csv)."""
    out = {}
    for k, x in obj.items():
        if k in ("histogramm", "spektrum"):
            continue  # Zaehllisten stehen nur in der YAML
        if isinstance(x, dict):
            out.update(flach(x, f"{prefix}{k}."))
        elif isinstance(x, list):
            # Listen aus Text als eine Zelle; Listen aus Dicts (z.B. Uhr-Segmente) nur in der YAML
            if all(not isinstance(i, dict) for i in x):
                out[prefix + k] = "; ".join(str(i) for i in x)
        else:
            out[prefix + k] = x
    return out


# --- Geraeteuhr: Zeitumstellung, Uhr-Segmente, Plausibilitaet ------------------------------
# Befund (siehe docs/dsd-format.md): Die Geraete stellen nie auf Sommerzeit um, auch nicht bei
# dst_on=01. Die Uhr wird bei der Inbetriebnahme auf Ortszeit gestellt und laeuft danach durch.
# Ortszeit = Geraetezeit + (Versatz der Ortszeit zu UTC am Fahrzeugzeitpunkt - Versatz bei Segmentbeginn).

EPOCHE = dt.datetime(2000, 1, 1)
WERKSDATUM = dt.datetime(2020, 1, 1, 12, 0, 0)  # Standarduhr nach Reset (Toleranz 10 Minuten)
UHR_JAHRE = (2020, 2030)  # Zeitstempel ausserhalb gelten als unplausibel
SPRUNG_TOLERANZ = dt.timedelta(seconds=120)  # kleinere Rueckspruenge zaehlen nicht als Uhrsprung
LUECKE_MAX = dt.timedelta(days=3)  # laengere Luecke in der Aufzeichnung beginnt ein neues Segment
NACHT_MAX = 0.15  # mehr Fahrzeuge zwischen 0 und 5 Uhr Ortszeit: Uhr vermutlich um Stunden verstellt
UMSTELLUNG_MAX_MIN = 45  # Tagesgang nach der Korrektur um mehr verschoben: Korrektur passt nicht
MIN_FAHRZEUGE_PRUEFUNG = 3000  # darunter keine Tagesgang-Pruefung
TEILZEITRAEUME = {
    "tags": ("06:00 bis 18:00 Uhr Ortszeit, alle Tage", lambda c: 6 <= c.hour < 18),
    "nachts": ("18:00 bis 06:00 Uhr Ortszeit, alle Tage", lambda c: c.hour < 6 or c.hour >= 18),
    "schulweg": ("07:00 bis 08:00 Uhr Ortszeit, Montag bis Freitag", lambda c: c.hour == 7 and c.weekday() < 5),
}


@functools.lru_cache(maxsize=None)
def _sommerzeit_utc(jahr):
    """Beginn und Ende der Sommerzeit (EU-Regel): letzter Sonntag im Maerz/Oktober, 01:00 UTC."""
    def sonntag(monat):
        d = dt.date(jahr, monat, 31)
        while d.weekday() != 6:
            d -= dt.timedelta(days=1)
        return dt.datetime(d.year, d.month, d.day, 1)
    return sonntag(3), sonntag(10)


def utc_versatz_h(utc):
    """Versatz der deutschen Ortszeit zu UTC in Stunden: 2 (MESZ) oder 1 (MEZ)."""
    beginn, ende = _sommerzeit_utc(utc.year)
    return 2 if beginn <= utc < ende else 1


def ortszeit_zu_utc(lokal):
    for off in (2, 1):
        u = lokal - dt.timedelta(hours=off)
        if utc_versatz_h(u) == off:
            return u
    return lokal - dt.timedelta(hours=1)  # nicht existierende Stunde beim Vorstellen


def geraet_zu_ortszeit(versatz_h):
    """Funktion Geraetezeit -> Ortszeit fuer eine Uhr, die mit dem UTC-Versatz versatz_h gestellt wurde."""
    start_off = dt.timedelta(hours=versatz_h)
    h1, h2 = dt.timedelta(hours=1), dt.timedelta(hours=2)

    def f(geraet):
        u = geraet - start_off
        return u + (h2 if utc_versatz_h(u) == 2 else h1)
    return f


def _fremd_im_nachbarn(secs, fenster=50, schwelle=86400):
    """True = Zeitstempel liegt hoechstens einen Tag neben dem gleitenden Median seiner Nachbarn."""
    n = len(secs)
    ok = [True] * n
    if not n:
        return ok
    win = sorted(secs[:fenster + 1])
    for i in range(n):
        ok[i] = abs(secs[i] - win[len(win) // 2]) <= schwelle
        j = i + fenster + 1
        if j < n:
            bisect.insort(win, secs[j])
        k = i - fenster
        if k >= 0:
            del win[bisect.bisect_left(win, secs[k])]
    return ok


def uhr_segmente(veh, status):
    """Zerlegt die Aufzeichnung (Dateireihenfolge, Fahrzeuge + 10-Minuten-Heartbeats) in Uhr-Segmente."""
    beats = [(pos, ts) for ts, t, _, pos in status if t == 0x33 and ts]
    seq = []  # (Zeitstempel, Fahrzeugindex oder -1 fuer Heartbeat)
    b = 0
    for i, (ts, _) in enumerate(veh):
        while b < len(beats) and beats[b][0] <= i:
            seq.append((beats[b][1], -1))
            b += 1
        seq.append((ts, i))
    seq += [(ts, -1) for _, ts in beats[b:]]
    ok = _fremd_im_nachbarn([(ts - EPOCHE).total_seconds() for ts, _ in seq])
    segs, cur, prev = [], None, None
    for (ts, idx), gut in zip(seq, ok):
        if not gut:
            continue  # einzelne Ausreisser-Zeitstempel (z.B. Jahr 2255) bilden kein Segment
        if prev is not None and (ts < prev - SPRUNG_TOLERANZ or ts > prev + LUECKE_MAX):
            segs.append(cur)
            cur = None
        if cur is None:
            cur = {"start": ts, "ende": ts, "idx": [], "heartbeats": 0}
        cur["start"], cur["ende"] = min(cur["start"], ts), max(cur["ende"], ts)
        if idx >= 0:
            cur["idx"].append(idx)
        else:
            cur["heartbeats"] += 1
        prev = ts
    if cur:
        segs.append(cur)
    return segs


def tagesgang(zeiten):
    """Werktags-Tagesgang in 96 Viertelstunden (Anteile, leicht geglaettet) und Anzahl Werktage."""
    c, tage = [0] * 96, set()
    for t in zeiten:
        if t.weekday() < 5:
            c[(t.hour * 60 + t.minute) // 15] += 1
            tage.add(t.date())
    s = sum(c)
    if not s:
        return None, 0
    c = [x / s for x in c]
    return [(c[i - 1] + 2 * c[i] + c[(i + 1) % 96]) / 4 for i in range(96)], len(tage)


def _pearson(x, y):
    mx, my = sum(x) / len(x), sum(y) / len(y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sxy / (sx * sy) if sx and sy else 0


def tagesgang_verschiebung_min(vorher, nachher):
    """Um wie viele Minuten liegt der Werktags-Tagesgang 'nachher' spaeter als 'vorher' (None: zu wenig Daten)."""
    if len(vorher) < MIN_FAHRZEUGE_PRUEFUNG or len(nachher) < MIN_FAHRZEUGE_PRUEFUNG:
        return None
    pv, dv = tagesgang(vorher)
    pn, dn = tagesgang(nachher)
    if pv is None or pn is None or dv < 10 or dn < 10:
        return None
    beste = max(range(-8, 9), key=lambda k: _pearson([pv[(i - k) % 96] for i in range(96)], pn))
    return beste * 15


def letzter_sonntag(jahr, monat):
    d = dt.date(jahr, monat, 31)
    while d.weekday() != 6:
        d -= dt.timedelta(days=1)
    return d


def umstellungs_pruefung(ortszeiten, start, ende):
    """Tagesgang 35 Tage vor/nach jeder Zeitumstellung im Segment (in Ortszeit, sollte ~0 min Versatz haben)."""
    erg = []
    for jahr in range(start.year, ende.year + 1):
        for monat in (3, 10):
            tag = letzter_sonntag(jahr, monat)
            if not (start.date() + dt.timedelta(days=7) < tag < ende.date() - dt.timedelta(days=7)):
                continue
            t0 = dt.datetime(tag.year, tag.month, tag.day)
            w = dt.timedelta(days=35)
            vor = [c for c in ortszeiten if t0 - w <= c < t0]
            nach = [c for c in ortszeiten if t0 + dt.timedelta(days=1) <= c < t0 + dt.timedelta(days=1) + w]
            abw = tagesgang_verschiebung_min(vor, nach)
            if abw is not None:
                erg.append({"datum": tag.isoformat(), "abweichung_min": abw})
    return erg


def bewerte_segmente(segs, veh):
    """Erste Einstufung der Uhr-Segmente (veraendert segs).

    Setzt je Segment: bewertung (None = nur Heartbeats, "werksdatum", "ungueltiges_datum", "gueltig",
    "auffaellig"), grund, sprung_min (Abstand zum vorigen glaubwuerdigen Segment) und fuer Segmente
    mit gueltigem Datum utc_versatz_h, ortszeit (umgerechnete Zeiten), nachtanteil_prozent und
    zeitumstellung (Pruefung des Tagesgangs vor und nach jeder Umstellung).
    """
    vorher = None  # letztes glaubwuerdiges Segment: Datum plausibel, keine zurueckgesetzte Standarduhr
    anker_h = None  # UTC-Versatz, mit dem die Uhr zuletzt auf Ortszeit gestellt wurde
    for s in segs:
        n = len(s["idx"])
        s["bewertung"], s["sprung_min"] = None, None  # Bewertung None: nur Heartbeats, keine Fahrzeuge
        if WERKSDATUM <= s["start"] < WERKSDATUM + dt.timedelta(minutes=10):
            if n:
                s["bewertung"], s["grund"] = "werksdatum", "Uhr nach Reset nicht gestellt (Standarddatum 2020-01-01 12:00)"
            anker_h = None  # Reset: eine spaeter wieder plausible Uhr wurde neu gestellt
            continue
        if not UHR_JAHRE[0] <= s["start"].year <= UHR_JAHRE[1]:
            if n:
                s["bewertung"], s["grund"] = "ungueltiges_datum", f"Zeitstempel im Jahr {s['start'].year}"
            continue
        if vorher is not None:
            s["sprung_min"] = round((s["start"] - vorher["ende"]).total_seconds() / 60)
            if s["sprung_min"] < -24 * 60:
                # kein Nachstellen der Uhr, sondern ein Block mit versprungenem Datum mitten in der Aufzeichnung
                if n:
                    s["bewertung"] = "ungueltiges_datum"
                    s["grund"] = f"Zeitstempel springen um {round(-s['sprung_min'] / 1440)} Tage zurück"
                continue
        # Uhr gilt als neu gestellt (Beginn, Reset, Rueckwaertssprung); nach einer reinen Luecke
        # ohne Aufzeichnung (Sprung vorwaerts) laeuft sie mit dem alten Versatz weiter.
        weiter = (vorher is not None and anker_h is not None and s["sprung_min"] >= 0
                  and vorher.get("bewertung") in ("gueltig", "auffaellig"))
        vorher = s
        if not n:
            continue
        if not weiter:
            anker_h = utc_versatz_h(ortszeit_zu_utc(s["start"]))
        umrechnen = geraet_zu_ortszeit(anker_h)
        s["utc_versatz_h"] = anker_h
        s["ortszeit"] = [umrechnen(veh[i][0]) for i in s["idx"]]
        s["bewertung"] = "gueltig"
        if n >= MIN_FAHRZEUGE_PRUEFUNG:
            s["nachtanteil_prozent"] = round(100 * sum(1 for c in s["ortszeit"] if c.hour < 5) / n, 1)
            s["zeitumstellung"] = umstellungs_pruefung(s["ortszeit"], s["start"], s["ende"])
            if s["nachtanteil_prozent"] > 100 * NACHT_MAX:
                s["bewertung"] = "auffaellig"
                s["grund"] = f"{s['nachtanteil_prozent']} % der Fahrzeuge zwischen 0 und 5 Uhr, Uhr vermutlich um Stunden verstellt"
            else:
                # nur Hinweis: auch Ferien oder Baustellen verschieben den Tagesgang vor/nach dem Stichtag
                s["umstellung_auffaellig"] = [u for u in s["zeitumstellung"] if abs(u["abweichung_min"]) >= UMSTELLUNG_MAX_MIN]


def analysiere_uhr(veh, status, mit_spannen=False):
    """Gibt (uhr, bereinigt, teilzeitraeume) zurueck, mit mit_spannen=True zusaetzlich die Spannen.

    uhr: Nutzbarkeit der Zeitstempel (Dict fuer die YAML; keine Aussage, ob die Uhrzeit stimmt), bereinigt: [(Ortszeit, v)]
    aller Fahrzeuge in Segmenten mit nutzbarer Zeit, teilzeitraeume: dasselbe getrennt nach TEILZEITRAEUME,
    spannen: [(erste, letzte Ortszeit)] je Abschnitt mit nutzbarer Zeit (fuer die Auswertung je Nacht).
    """
    segs = uhr_segmente(veh, status)
    bewerte_segmente(segs, veh)
    teil = {k: [] for k in TEILZEITRAEUME}
    bereinigt = []
    spannen = []
    for s in segs:
        if s["bewertung"] != "gueltig":
            continue
        spannen.append((min(s["ortszeit"]), max(s["ortszeit"])))
        for c, i in zip(s["ortszeit"], s["idx"]):
            v = veh[i][1]
            bereinigt.append((c, v))
            for name, (_, in_zeitraum) in TEILZEITRAEUME.items():
                if in_zeitraum(c):
                    teil[name].append((c, v))

    mit = [s for s in segs if s["idx"]]
    gesamt = len(veh)
    nutzbar = sum(len(s["idx"]) for s in mit if s["bewertung"] == "gueltig")
    anteil = nutzbar / gesamt if gesamt else 0
    hinweise = []
    for bew, text in (("werksdatum", "Fahrzeuge mit zurückgesetzter Geräteuhr (Standarddatum 2020-01-01), ohne gültige Uhrzeit"),
                      ("ungueltiges_datum", "Fahrzeuge mit unplausiblem Datum")):
        k = sum(len(s["idx"]) for s in mit if s["bewertung"] == bew)
        if k:
            hinweise.append(f"{k} {text}")
    einzeln = gesamt - sum(len(s["idx"]) for s in segs)
    if einzeln:
        hinweise.append(f"{einzeln} Fahrzeuge mit einzelnem Ausreißer-Zeitstempel")
    pruefen = False
    for s in mit:
        if s["bewertung"] == "auffaellig":
            hinweise.append(f"Segment ab {s['start'].isoformat(sep=' ')} ({len(s['idx'])} Fahrzeuge): {s['grund']}")
        for u in s.get("umstellung_auffaellig", []):
            pruefen = True
            hinweise.append(f"Tagesgang weicht nach der Zeitumstellung am {u['datum']} um {u['abweichung_min']} Minuten ab "
                            f"(Ferien, Baustelle oder verstellte Uhr möglich)")
    spruenge = [s for s in mit if s["bewertung"] == "gueltig" and s["sprung_min"] is not None and s["sprung_min"] <= -5]
    for s in spruenge[:3]:
        hinweise.append(f"Uhr um {-s['sprung_min']} Minuten zurückgestellt (Segment ab {s['start'].isoformat(sep=' ')})")
    if len(spruenge) > 3:
        hinweise.append(f"{len(spruenge) - 3} weitere Uhrsprünge")

    def segment_yaml(s):
        d = {"start": s["start"].isoformat(sep=" "), "ende": s["ende"].isoformat(sep=" "),
             "fahrzeuge": len(s["idx"]), "bewertung": s["bewertung"]}
        if s.get("grund"):
            d["grund"] = s["grund"]
        if "utc_versatz_h" in s:
            d["geraeteuhr_utc_versatz_h"] = s["utc_versatz_h"]
        if s.get("nachtanteil_prozent") is not None:
            d["nachtanteil_0_bis_5_uhr_prozent"] = s["nachtanteil_prozent"]
        if s.get("zeitumstellung"):
            d["zeitumstellung_abweichung_min"] = {u["datum"]: u["abweichung_min"] for u in s["zeitumstellung"]}
        if s["sprung_min"] is not None and abs(s["sprung_min"]) >= 5:
            d["abstand_zum_vorigen_segment_min"] = s["sprung_min"]  # negativ: Uhr zurueckgesprungen
        return d

    groesste = {id(s) for s in sorted(mit, key=lambda s: -len(s["idx"]))[:8]}
    uhr = {
        "zeitmodell": "Geräteuhr ohne Sommerzeitumstellung, Teilzeiträume in Ortszeit (Europe/Berlin) umgerechnet",
        # Formale Pruefung der Zeitstempel (kein Reset, keine Spruenge, kein Versatz um Stunden). Sie sagt nichts darueber,
        # ob die Uhrzeit stimmt; das belegt uhr_belege.py (belege/uhr-bewertung.json).
        "nutzbarkeit": ("nicht_nutzbar" if anteil < 0.5 else
                        "nutzbar" if anteil >= 0.99 and not pruefen else "teilweise_nutzbar"),
        "fahrzeuge_mit_nutzbarer_zeit_prozent": round(100 * anteil, 2) if gesamt else None,
        "fahrzeuge_ohne_nutzbare_zeit": gesamt - nutzbar,
        "hinweise": list(dict.fromkeys(hinweise)),
        "segmente_mit_fahrzeugen": len(mit),
        "segmente": [segment_yaml(s) for s in segs if id(s) in groesste],
    }
    return (uhr, bereinigt, teil, spannen) if mit_spannen else (uhr, bereinigt, teil)


# --- Gefaehrdung, Laerm und Ereignisse je Nacht --------------------------------------------------
# Alles Schaetzungen aus der Geschwindigkeitsverteilung einer Messstelle (siehe docs/gefaehrdung.md). Sie ersetzen
# weder eine Unfallanalyse noch eine Laermmessung. Die Annahmen stehen hier und in der Dokumentation.
GEFAEHRDUNG = {
    "exponent": 4,  # Potenzmodell nach Nilsson: Unfallschwere (Tote) waechst mit der 4. Potenz der Geschwindigkeit
    "reaktionszeit_s": 1.0,  # Zeit, bis die Bremsung beginnt
    "verzoegerung_m_s2": 7.0,  # Bremsverzoegerung auf trockener Fahrbahn
    "aufprall_schwellen_kmh": (30, 50),  # Anteil der Fahrzeuge, die mit mehr als so viel auftreffen wuerden
}
NACHT = (22, 6)  # Nacht: 22:00 bis 06:00 Uhr Ortszeit
NACHT_SCHWELLEN_KMH = (100, 120)  # zusaetzlich zum doppelten Tempolimit


def anhaltestrecke_m(v_kmh, a=None, t=None):
    a = a or GEFAEHRDUNG["verzoegerung_m_s2"]
    t = GEFAEHRDUNG["reaktionszeit_s"] if t is None else t
    v = v_kmh / 3.6
    return v * t + v * v / (2 * a)


def aufprall_kmh(v_kmh, limit):
    """Tempo, mit dem ein Fahrzeug mit v_kmh auftrifft, wo ein Fahrzeug mit dem Tempolimit gerade noch zum Stehen kommt.

    Beide haben dieselbe Reaktionszeit und Verzoegerung. Vom Fahrzeug mit v_kmh bleibt nach der Reaktionsstrecke
    nur noch die Reststrecke zum Bremsen; ist sie aufgebraucht, trifft es mit voller Geschwindigkeit.
    """
    a, t = GEFAEHRDUNG["verzoegerung_m_s2"], GEFAEHRDUNG["reaktionszeit_s"]
    v = v_kmh / 3.6
    rest = anhaltestrecke_m(limit) - v * t
    if rest <= 0:
        return float(v_kmh)
    return 3.6 * math.sqrt(max(0.0, v * v - 2 * a * rest))


def histogramm(vehs):
    """Anzahl Fahrzeuge je ganzem km/h (Aufloesung der Geraete): {"ab_kmh": kleinste Geschwindigkeit, "anzahl": [...]}.

    Die Klassenbreite fuer die Darstellung waehlt seiten_bauen.py je nach Fahrzeugzahl.
    """
    zaehler = collections.Counter(v for _, v in vehs)
    if not zaehler:
        return None
    lo, hi = min(zaehler), max(zaehler)
    return {"ab_kmh": lo, "anzahl": [zaehler.get(v, 0) for v in range(lo, hi + 1)]}


def gefaehrdung(vehs, limit):
    """Relativer Risikoindex (Nilsson) und Aufprallgeschwindigkeiten. None ohne Fahrzeuge oder Tempolimit.

    aufprall_*: Tempo, mit dem die gemessenen Fahrzeuge auf das Hindernis treffen (0 = steht vorher). Die Perzentile
    gelten fuer alle Fahrzeuge; weil die Aufprallgeschwindigkeit mit dem Tempo steigt, ist das P95 der Aufprallgeschwindigkeit
    die Aufprallgeschwindigkeit des Fahrzeugs bei der V95.
    """
    if not limit:
        return None
    zaehler = collections.Counter(v for _, v in vehs if v > 0)
    n = sum(zaehler.values())
    if not n:
        return None
    index = sum(c * (v / limit) ** GEFAEHRDUNG["exponent"] for v, c in zaehler.items()) / n
    auf = {v: aufprall_kmh(v, limit) for v in zaehler}
    treffer = sum(c for v, c in zaehler.items() if auf[v] > 0.05)
    erg = {"risikoindex_nilsson": round(index, 2),
           "aufprall_anteil_prozent": round(100 * treffer / n, 2),
           "aufprall_mittel_kmh": round(sum(c * auf[v] for v, c in zaehler.items()) / n, 1)}
    if treffer:
        erg["aufprall_mittel_der_aufprallenden_kmh"] = round(sum(c * auf[v] for v, c in zaehler.items() if auf[v] > 0.05) / treffer, 1)
    kumul, perz = 0, {}
    for v, c in sorted(zaehler.items()):
        kumul += c
        for q in (95, 99):
            if q not in perz and kumul >= q / 100 * n:
                perz[q] = v
    for q in (95, 99):
        erg[f"aufprall_p{q}_kmh"] = round(auf[perz[q]], 1)
    for schwelle in GEFAEHRDUNG["aufprall_schwellen_kmh"]:
        erg[f"aufprall_ueber_{schwelle}_kmh_prozent"] = round(100 * sum(c for v, c in zaehler.items() if auf[v] > schwelle) / n, 2)
    erg["anhaltestrecke_bei_limit_m"] = round(anhaltestrecke_m(limit), 1)
    return erg

def pegel_pkw_db(v_kmh):
    """Geschwindigkeitsterm des Pkw-Emissionspegels nach RLS-90: 27,7 + 10 lg(1 + (0,02 v)^3) in dB(A)."""
    return 27.7 + 10 * math.log10(1 + (0.02 * v_kmh) ** 3)


def laerm(vehs, limit):
    """Grobe Laermschaetzung relativ zu einem Fahrzeug mit Tempolimit. None ohne Fahrzeuge oder Tempolimit."""
    if not limit:
        return None
    zaehler = collections.Counter(v for _, v in vehs if v > 0)
    n = sum(zaehler.values())
    if not n:
        return None
    ref = pegel_pkw_db(limit)
    delta = {v: pegel_pkw_db(v) - ref for v in zaehler}
    energie = sum(c * 10 ** (delta[v] / 10) for v, c in zaehler.items()) / n
    sortiert = sorted(zaehler.items())
    kumul, v99 = 0, sortiert[-1][0]
    for v, c in sortiert:
        kumul += c
        if kumul >= 0.99 * n:
            v99 = v
            break
    return {
        "mittelungspegel_gegenueber_limit_db": round(10 * math.log10(energie), 1),
        "spitzenpegel_p99_gegenueber_limit_db": round(delta[v99], 1),
        "anteil_mind_3_db_lauter_prozent": round(100 * sum(c for v, c in zaehler.items() if delta[v] >= 3) / n, 2),
        "anteil_mind_6_db_lauter_prozent": round(100 * sum(c for v, c in zaehler.items() if delta[v] >= 6) / n, 2),
    }


def nacht_ereignisse(fahrten, spannen, limit):
    """Wie oft faehrt in einer Nacht (22-6 Uhr Ortszeit) ein Fahrzeug mit doppeltem Tempo, ab 100 oder ab 120 km/h?

    Gezaehlt werden nur vollstaendig aufgezeichnete Naechte (Beginn und Ende innerhalb eines Abschnitts mit nutzbarer
    Zeit); Naechte, in denen das Geraet ausfiel, zaehlen als Naechte ohne Ereignis.
    """
    von, bis = NACHT
    dauer = dt.timedelta(hours=(bis - von) % 24)
    naechte = set()
    for a, b in spannen:
        tag = a.date() - dt.timedelta(days=1)
        while True:
            anfang = dt.datetime.combine(tag, dt.time(von))
            if anfang > b:
                break
            if anfang >= a and anfang + dauer <= b + dt.timedelta(hours=2):  # letzte Nacht darf knapp ueber das Ende ragen
                naechte.add(tag)
            tag += dt.timedelta(days=1)
    erg = {"definition": f"{von}:00 bis {bis:02d}:00 Uhr Ortszeit, nur vollständig aufgezeichnete Nächte", "naechte": len(naechte)}
    if not naechte:
        return erg
    schwellen = sorted({*NACHT_SCHWELLEN_KMH, *([2 * limit] if limit else [])})
    je_nacht = {s: collections.Counter() for s in schwellen}
    for c, v in fahrten:
        if not (c.hour >= von or c.hour < bis):
            continue
        tag = c.date() if c.hour >= von else c.date() - dt.timedelta(days=1)
        if tag not in naechte:
            continue
        for s in schwellen:
            if v >= s:
                je_nacht[s][tag] += 1
    erg["schwellen"] = [{
        "ab_kmh": s, "doppeltes_tempolimit": bool(limit) and s == 2 * limit,
        "naechte_mit_fahrt": len(je_nacht[s]), "anteil_naechte_prozent": round(100 * len(je_nacht[s]) / len(naechte), 1),
        "fahrten_gesamt": sum(je_nacht[s].values()), "fahrten_je_nacht": round(sum(je_nacht[s].values()) / len(naechte), 2),
    } for s in schwellen]
    return erg


HINWEIS_AUSWERTUNG = ("Eigene Berechnung aus den Rohdaten, nicht amtlich. Fehler in der Auswertung (Skripte, Annahmen, "
                      "Zuordnung) können nicht ausgeschlossen werden; ohne Gewähr.")


def rauschen_block(rb, abgezogen, roh=0):
    """YAML-Block zum Rauschboden (rauschen.pruefen). abgezogen: Zahl der herausgerechneten Fahrzeuge, roh: Fahrzeuge in der Datei."""
    if rb is None:
        return {"geprueft": False, "grund": f"weniger als {rauschen.MIN_FAHRZEUGE} Fahrzeuge mit nutzbarer Zeit oder kein Tempolimit"}
    b = {"geprueft": True, "belegt": rb["belegt"], "abgezogen_fahrzeuge": abgezogen}
    if rb["grund"]:
        b["grund"] = rb["grund"]
    b["anteil_prozent"] = round(100 * rb["anteil"], 2)  # Schaetzung des Modells; abgezogen wird weniger, wo nachts weniger gemessen wurde
    if abgezogen and roh:
        b["abgezogen_anteil_prozent"] = round(100 * abgezogen / roh, 2)
    if rb["mittel_kmh"] is not None:
        b["mittel_kmh"] = round(rb["mittel_kmh"], 1)
        b["obergrenze_kmh"] = rb["obergrenze_kmh"]
    b["stabil"] = rb["stabil"]
    b["anteil_gerade_tage_prozent"] = round(100 * rb["anteil_haelften"][0], 2)
    b["anteil_ungerade_tage_prozent"] = round(100 * rb["anteil_haelften"][1], 2)
    b["verkehrsschwelle_kmh"] = round(rb["verkehrsschwelle_kmh"], 1)
    if "spektrum" in rb:
        b["spektrum"] = rb["spektrum"]  # Fahrten je 1000 Stunden: rausch = verkehrsunabhaengig, alle = insgesamt
    return b


def convert(path, outdir, standort, limit, show_meta, write_status, min_kmh=0, korrekturen=None):
    buf = open(path, "rb").read()
    meta, veh, status, warn = parse(buf)
    base = os.path.splitext(os.path.basename(path))[0]
    out = os.path.join(outdir, base + ".csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["zeitstempel", "geschwindigkeit_kmh"])
        for ts, v in veh:
            w.writerow([ts.isoformat(sep=" "), v])
    if write_status:
        with open(os.path.join(outdir, base + "_status.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["zeitstempel", "typ", "nutzlast_hex"])
            for ts, t, pl, _ in status:
                w.writerow([ts.isoformat(sep=" ") if ts else "", hex(t), pl])
    if show_meta:
        for k, v in meta.items():
            print(f"  {k} = {v}", file=sys.stderr)
    for wmsg in warn[:10]:
        print(f"  WARNUNG {base}: {wmsg}", file=sys.stderr)
    kor = (korrekturen or {}).get(f"{standort}/{os.path.basename(path)}")
    lim, quelle = tempolimit(meta, limit, kor)
    uhr, bereinigt, teil, spannen = analysiere_uhr(veh, status, mit_spannen=True)
    rb = rauschen.pruefen(bereinigt, spannen, lim)
    anzahl_roh = len(veh)
    if rb and rb["belegt"]:  # verkehrsunabhaengigen Rauschboden herausrechnen (docs/rauschen.md)
        modell = rb["_modell"]
        veh = rauschen.ohne_rauschen_je_v(veh, modell)
        bereinigt = rauschen.ohne_rauschen(bereinigt, modell)
        teil = {k: rauschen.ohne_rauschen(v, modell) for k, v in teil.items()}
    res = {
        "standort": standort,
        "datei": os.path.basename(path),
        "geraet": meta.get("configuration_number"),
        "geraetename": meta.get("name") or None,
        "tempolimit_kmh": lim,
        "tempolimit_quelle": quelle,
        **({"tempolimit_dsd_kmh": kor["tempolimit_dsd_kmh"]} if kor and quelle == "mitteilung_verwaltung" else {}),
        "erfassung_ab_kmh": byte_wert(meta.get("capture_min_speed")),
        "auswertung_ab_kmh": min_kmh,
        "fahrzeuge_unter_auswertung_ab": sum(1 for x in veh if x[1] < min_kmh),
        "fahrzeuge_in_datei": anzahl_roh,
        "warnungen": len(warn),
    }
    res.update(stats(veh, lim, min_kmh) or {"anzahl_fahrzeuge": 0})

    def zusatz(vehs):
        """Histogramm, Gefaehrdung und Laerm fuer eine Auswahl von Fahrzeugen (die beiden letzten nur mit Tempolimit)."""
        vehs = [x for x in vehs if x[1] >= min_kmh]
        return {k: x for k, x in (("histogramm", histogramm(vehs)), ("gefaehrdung", gefaehrdung(vehs, lim)),
                                  ("laerm", laerm(vehs, lim))) if x}

    res.update(zusatz(veh))
    res["uhr"] = uhr
    res["rauschen"] = rauschen_block(rb, anzahl_roh - len(veh) if rb and rb["belegt"] else 0, anzahl_roh)
    b = stats(bereinigt, lim, min_kmh) or {"anzahl_fahrzeuge": 0}
    res["bereinigt"] = {"beschreibung": "alle Tageszeiten, nur Fahrzeuge mit nutzbarer Zeit (siehe uhr), Zeiten in Ortszeit",
                        **b, **zusatz(bereinigt)}
    res["teilzeitraeume"] = {}
    for name, (definition, _) in TEILZEITRAEUME.items():
        t = stats(teil[name], lim, min_kmh) or {"anzahl_fahrzeuge": 0}
        t.pop("messzeitraum", None)
        res["teilzeitraeume"][name] = {"definition": definition, **t, **zusatz(teil[name])}
    res["nacht_ereignisse"] = nacht_ereignisse([x for x in bereinigt if x[1] >= min_kmh], spannen, lim)
    schreibe_yaml(os.path.join(outdir, base + ".yaml"), ["# " + HINWEIS_AUSWERTUNG] + yaml_zeilen(res))
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("eingabe", help=".dsd-Datei oder Ordner mit .dsd-Dateien")
    ap.add_argument("-o", "--out", help="Ausgabeordner (Standard: neben der Eingabe)")
    ap.add_argument("--limit", type=int,
                    help="Tempolimit (km/h) fuer alle Dateien erzwingen (Standard: aus der DSD ableiten)")
    ap.add_argument("--min-kmh", type=int, default=0,
                    help="zusaetzlich Werte unter dieser Geschwindigkeit aus der Auswertung nehmen, CSV bleibt vollstaendig "
                         "(Standard: 0; den Rauschboden rechnet das Skript ohnehin heraus, siehe docs/rauschen.md)")
    ap.add_argument("--korrekturen", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "belege", "korrekturen.json"),
                    help="Korrekturen des Tempolimits aus den Mitteilungen (Standard: belege/korrekturen.json, falls vorhanden)")
    ap.add_argument("--meta", action="store_true")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()

    if os.path.isdir(a.eingabe):
        wurzel = a.eingabe
        files = sorted(os.path.join(d, f) for d, _, fs in os.walk(wurzel) for f in fs if f.lower().endswith(".dsd"))
    else:
        wurzel = os.path.dirname(os.path.abspath(a.eingabe))
        files = [a.eingabe]

    korrekturen = {}
    if os.path.exists(a.korrekturen):
        with open(a.korrekturen, encoding="utf-8") as fh:
            korrekturen = json.load(fh).get("tempolimit", {})
    rows = []
    for f in files:
        # ohne -o neben der DSD, mit -o dieselbe Ordnerstruktur unter dem Ausgabeordner
        dsd_ordner = os.path.dirname(os.path.abspath(f))
        rel = os.path.relpath(dsd_ordner, os.path.abspath(wurzel)).replace(os.sep, "/")
        standort = os.path.basename(dsd_ordner) if rel == "." else rel  # relativer Ordnerpfad
        outdir = os.path.join(a.out, rel) if a.out else dsd_ordner
        os.makedirs(outdir, exist_ok=True)
        try:
            s = convert(f, outdir, standort, a.limit, a.meta, a.status, a.min_kmh, korrekturen)
        except Exception as e:
            print(f"FEHLER {f}: {e}", file=sys.stderr)
            continue
        s["seite"] = f"standorte/{standort_slug(standort)}.html"  # Detailseite (seiten_bauen.py), nicht in der Einzel-YAML
        rows.append(s)
        g, e = s.get("geschwindigkeit_kmh", {}), s.get("einhaltung", {})
        print(f"{s['standort']} / {s['datei']}: limit={s['tempolimit_kmh']} n={s['anzahl_fahrzeuge']} "
              f"v85={g.get('v85')} v95={g.get('v95')} v99={g.get('v99')} "
              f"quote={e.get('einhaltungsquote_prozent')} qual={e.get('qualifizierte_einhaltungsquote_prozent')} "
              f"warnungen={s['warnungen']}", file=sys.stderr)

    if os.path.isdir(a.eingabe) and rows:
        summe = a.out or a.eingabe
        z = []
        for res in rows:
            teil = yaml_zeilen(res, 2)
            teil[0] = "  - " + teil[0].lstrip()
            z += teil
        schreibe_yaml(os.path.join(summe, "auswertung.yaml"), ["# " + HINWEIS_AUSWERTUNG, "standorte:"] + z)
        with open(os.path.join(summe, "auswertung.json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump({"standorte": rows}, f, ensure_ascii=False, indent=1)
            f.write("\n")
        flache = [flach(r) for r in rows]
        keys = list(dict.fromkeys(k for r in flache for k in r))
        with open(os.path.join(summe, "summary.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(flache)


if __name__ == "__main__":
    main()
