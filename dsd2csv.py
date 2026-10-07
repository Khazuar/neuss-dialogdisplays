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
  2. Konfigurationswert "safety_speed" (damit schaltet das Display Smiley/Frowny; stimmt in
                                       allen Dateien mit "Vmax StVO" der DataCollect-PDFs ueberein)
  3. Zahl im Geraetenamen ("Tempo30", "Ville Norf 30", ...)

Auswertung je Datei (als <name>.yaml neben der CSV):
  V85/V95/V99   kleinste Geschwindigkeit, bei der mind. 85/95/99 % der Fahrzeuge <= v
  Einhaltungsquote               Anteil mit v <= Limit
  qualifizierte Einhaltungsquote Anteil mit v - Toleranz <= Limit
                                 (Toleranz: 3 km/h unter 100 km/h, ab 100 km/h 3 % aufgerundet)

Aufruf:
  python3 -I dsd2csv.py datei.dsd                  -> datei.csv + datei.yaml (Kurzstatistik auf stderr)
  python3 -I dsd2csv.py ordner/                    -> rekursiv je DSD eine CSV + YAML daneben,
                                                      dazu auswertung.yaml und summary.csv im Ordner
  python3 -I dsd2csv.py ordner/ -o ausgabe_ordner  -> Ergebnisse unter ausgabe_ordner (Unterordner bleiben erhalten)
  Optionen: --limit 30   Tempolimit fuer alle Dateien erzwingen
            --min-kmh N  Werte unter N km/h komplett aus der Auswertung nehmen (CSV bleibt vollstaendig)
            --meta       Konfigurationswerte der Datei ausgeben
            --status     Status-Records (0x33/0x20) als eigene CSV mitschreiben

Nur Standardbibliothek. Mit "python3 -I" starten, wenn Dateien aus unsicherer
Quelle stammen.
"""
import argparse
import csv
import datetime as dt
import json
import math
import os
import re
import sys

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
                status.append((ts, t, r[7:-1].hex()))
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


def tempolimit(meta, override=None):
    """Gibt (limit, quelle) zurueck: --limit, sonst safety_speed der DSD, sonst Zahl im Namen."""
    if override:
        return override, "parameter"
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
        else:
            zeilen.append(f"{pad}{k}: {yaml_skalar(x)}")
    return zeilen


def schreibe_yaml(pfad, zeilen):
    with open(pfad, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(zeilen) + "\n")


def flach(obj, prefix=""):
    """Verschachteltes Dict -> flaches Dict (fuer summary.csv)."""
    out = {}
    for k, x in obj.items():
        if isinstance(x, dict):
            out.update(flach(x, f"{prefix}{k}."))
        else:
            out[prefix + k] = x
    return out


def convert(path, outdir, standort, limit, show_meta, write_status, min_kmh=0):
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
            for ts, t, pl in status:
                w.writerow([ts.isoformat(sep=" ") if ts else "", hex(t), pl])
    if show_meta:
        for k, v in meta.items():
            print(f"  {k} = {v}", file=sys.stderr)
    for wmsg in warn[:10]:
        print(f"  WARNUNG {base}: {wmsg}", file=sys.stderr)
    lim, quelle = tempolimit(meta, limit)
    res = {
        "standort": standort,
        "datei": os.path.basename(path),
        "geraet": meta.get("configuration_number"),
        "geraetename": meta.get("name") or None,
        "tempolimit_kmh": lim,
        "tempolimit_quelle": quelle,
        "erfassung_ab_kmh": byte_wert(meta.get("capture_min_speed")),
        "auswertung_ab_kmh": min_kmh,
        "warnungen": len(warn),
    }
    res.update(stats(veh, lim, min_kmh) or {"anzahl_fahrzeuge": 0})
    schreibe_yaml(os.path.join(outdir, base + ".yaml"), yaml_zeilen(res))
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("eingabe", help=".dsd-Datei oder Ordner mit .dsd-Dateien")
    ap.add_argument("-o", "--out", help="Ausgabeordner (Standard: neben der Eingabe)")
    ap.add_argument("--limit", type=int,
                    help="Tempolimit (km/h) fuer alle Dateien erzwingen (Standard: aus der DSD ableiten)")
    ap.add_argument("--min-kmh", type=int, default=0,
                    help="Werte unter dieser Geschwindigkeit aus der Auswertung nehmen (CSV bleibt vollstaendig)")
    ap.add_argument("--meta", action="store_true")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()

    if os.path.isdir(a.eingabe):
        wurzel = a.eingabe
        files = sorted(os.path.join(d, f) for d, _, fs in os.walk(wurzel) for f in fs if f.lower().endswith(".dsd"))
    else:
        wurzel = os.path.dirname(os.path.abspath(a.eingabe))
        files = [a.eingabe]

    rows = []
    for f in files:
        # ohne -o neben der DSD, mit -o dieselbe Ordnerstruktur unter dem Ausgabeordner
        dsd_ordner = os.path.dirname(os.path.abspath(f))
        rel = os.path.relpath(dsd_ordner, os.path.abspath(wurzel)).replace(os.sep, "/")
        standort = os.path.basename(dsd_ordner) if rel == "." else rel  # relativer Ordnerpfad
        outdir = os.path.join(a.out, rel) if a.out else dsd_ordner
        os.makedirs(outdir, exist_ok=True)
        try:
            s = convert(f, outdir, standort, a.limit, a.meta, a.status, a.min_kmh)
        except Exception as e:
            print(f"FEHLER {f}: {e}", file=sys.stderr)
            continue
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
        schreibe_yaml(os.path.join(summe, "auswertung.yaml"), ["standorte:"] + z)
        flache = [flach(r) for r in rows]
        keys = list(dict.fromkeys(k for r in flache for k in r))
        with open(os.path.join(summe, "summary.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(flache)


if __name__ == "__main__":
    main()
