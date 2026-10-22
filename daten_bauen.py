# SPDX-License-Identifier: MIT
"""Schreibt die bereinigten Daten als CSV-Dateien (DATEN.md): Kennzahlen je Messung, Abschnitt, Zeitraum und Tag sowie die
Fahrzeuge je Tag, Stunde und km/h.

Aufruf (nach dsd2csv.py mit --aggregat):
  python3 -I daten_bauen.py --auswertung _site/auswertung.json --aggregat _aggregat --ziel _site/daten

Eingaben: auswertung.json (dsd2csv.py), die Zwischenstaende <Ordner>/<Standort>/<Datei>.aggregat.json (dsd2csv.py --aggregat),
belege/metadaten.json und belege/uhr-bewertung.json. Ausgabe in <ziel>:
  messungen.csv, abschnitte.csv, kennzahlen.csv, tage.csv, luecken.csv (Klartext) sowie stunden/<standort>.csv.gz je Standortseite und
  stunden.csv.gz (alle Standorte); die Stundendateien sind gzip-komprimiert (Klartext waere rund 280 MB)
Die Dateien enthalten nur, was dsd2csv.py ohnehin berechnet: Ortszeit, nur nutzbare Zeit, Rauschboden und Regenanteil abgezogen,
Abschnitte nach den Bruechen. Reihenfolge und Format sind deterministisch (gleiche Eingabe, gleiche Bytes).
"""
import argparse
import collections
import csv
import datetime as dt
import gzip
import io
import json
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)  # python -I nimmt das Skriptverzeichnis nicht auf
import aggregat  # noqa: E402
import gruppen  # noqa: E402
import kalender  # noqa: E402
import seiten_bauen  # noqa: E402
from uhr_belege import gesamturteil  # noqa: E402

ZEITRAEUME = ["alle", "nacht", "vormittag", "nachmittag", "abend", "schulweg"]
KENNZAHLEN = ["fahrzeuge", "mittel_kmh", "v85_kmh", "v95_kmh", "v99_kmh", "einhaltung_prozent", "qualifiziert_prozent",
              "fahrzeuge_je_stunde", "ueber_limit_plus_toleranz_je_stunde", "zusatzrisiko_je_stunde"]


def kennzahlen(d):
    """KENNZAHLEN aus einem Auswertungsblock der YAML (leer ohne Fahrzeuge); die Raten stehen nur mit vollstaendig aufgezeichneten Stunden da."""
    n = (d or {}).get("anzahl_fahrzeuge") or 0
    if not n:
        return [0] + [""] * (len(KENNZAHLEN) - 1)
    g, h, r = d.get("geschwindigkeit_kmh") or {}, d.get("einhaltung") or {}, d.get("raten") or {}
    return [n, g.get("mittel"), g.get("v85"), g.get("v95"), g.get("v99"), h.get("einhaltungsquote_prozent"),
            h.get("qualifizierte_einhaltungsquote_prozent"), r.get("fahrzeuge_je_stunde"), r.get("ueber_limit_plus_toleranz_je_stunde"),
            r.get("zusatzrisiko_je_stunde")]


def _schreiber(ziel, kopf):
    """CSV-Schreiber mit festem Zeilenende (LF) und UTF-8; None wird zur leeren Zelle."""
    fh = open(ziel, "w", encoding="utf-8", newline="")
    w = csv.writer(fh, lineterminator="\n")
    w.writerow(kopf)
    return fh, w


def _schreiber_gz(ziel, kopf):
    """Wie _schreiber, aber gzip-komprimiert und ohne Zeitstempel im Kopf (gleiche Eingabe, gleiche Bytes)."""
    fh = io.TextIOWrapper(gzip.GzipFile(ziel, "wb", mtime=0), encoding="utf-8", newline="")
    w = csv.writer(fh, lineterminator="\n")
    w.writerow(kopf)
    return fh, w


def _zelle(x):
    return "" if x is None else x


def tage_flags(datum, cache={}):
    """(Wochentag 1-7, Schulferien 0/1, Feiertag 0/1) eines Datums (ISO)."""
    if datum not in cache:
        d = dt.date.fromisoformat(datum)
        cache[datum] = (d.isoweekday(), 1 if kalender.schulferien(d) else 0, 1 if kalender.feiertag(d) else 0)
    return cache[datum]


def stunden_zeilen(mid, agg, stunde_zeitraum, einsatz=None):
    """Zeilen der Stundendatei einer Messung (aggregat.SPALTEN_STUNDEN). einsatz: Funktion Datum (ISO) -> Einsatz-ID oder "" (Umhaengtag)."""
    for datum, stunde, versatz, abschnitt, voll, klasse, flach in agg["stunden"]:
        wt, fe, ft = tage_flags(datum)
        zr = stunde_zeitraum[stunde]
        klasse = "" if klasse is None else klasse
        eid = einsatz(datum) if einsatz else ""
        for i in range(0, len(flach), 2):
            yield [mid, abschnitt, datum, wt, stunde, versatz, zr, fe, ft, voll, klasse, flach[i], flach[i + 1], eid]


def einsatz_je_datum(einsaetze):
    """{Messung: Funktion Datum (ISO) -> Einsatz-ID} aus einsaetze.json; Tage ausserhalb aller Teile (Umhaengtage) ergeben ""."""
    teile = collections.defaultdict(list)
    for e in (einsaetze or {}).get("einsaetze", []):
        for t in e["teile"]:
            if t["von"]:
                teile[t["messung"]].append((t["von"], t["bis"], e["id"]))
    return {mid: (lambda d, liste=liste: next((eid for von, bis, eid in liste if von <= d <= bis), "")) for mid, liste in teile.items()}


def einsaetze_schreiben(ziel, einsaetze, auswertung, w_k):
    """einsaetze.csv und brueche.csv (einsaetze.py, docs/einsaetze.md); Kennzahlen der Einsaetze in kennzahlen.csv (bereich = einsatz)."""
    zeilen = {seiten_bauen.messung_id(r["standort"], r["datei"]): r for r in auswertung["standorte"]}
    n_e = n_b = n_k = 0
    fh_e, w_e = _schreiber(os.path.join(ziel, "einsaetze.csv"), [
        "einsatz_id", "messung_id", "standort_seite", "standort_name", "geraet", "fahrtrichtung", "tempolimit_kmh", "von", "bis", "status", "teile",
        "abgegeben", "ausgenommene_tage"])
    for e in einsaetze.get("einsaetze", []):
        teile = " | ".join(f'{t["messung"]}#{t["abschnitt"]} {t["von"]}..{t["bis"]} ({t["herkunft"]})' for t in e["teile"] if t["von"])
        w_e.writerow([e["id"], e["messung"], _zelle(e["seite"]), e["name"], e["geraet"], e["fahrtrichtung"], _zelle(e["limit"]), _zelle(e["von"]),
                      _zelle(e["bis"]), e["status"], teile, " | ".join(f'#{a["abschnitt"]} -> {a["an"]}' for a in e["abgegeben"]),
                      " ".join(e["ausgenommene_tage"])])
        n_e += 1
        k = e.get("kennzahlen")
        if not k:  # identisch mit der Messung: deren Kennzahlen
            r = zeilen.get(e["messung"]) or {}
            k = {"bereinigt": r.get("bereinigt") or {}, "teilzeitraeume": r.get("teilzeitraeume") or {}}
        for zr in ZEITRAEUME:
            w_k.writerow([e["id"], "einsatz", "", zr] + kennzahlen(k["bereinigt"] if zr == "alle" else (k["teilzeitraeume"] or {}).get(zr)))
            n_k += 1
    fh_e.close()
    fh_b, w_b = _schreiber(os.path.join(ziel, "brueche.csv"), [
        "messung_id", "abschnitt_nr", "datum", "wahrscheinlichkeit", "zuordnung", "stufe", "erklaerung", "umhaengen_richtung", "umhaengen_von_messung",
        "score", "p_nulltest", "verhaeltnis_fahrzeuge", "gegenprobe_score", "naht_stetig", "ereignisse", "gleicher_tag"])
    for b in einsaetze.get("brueche", []):
        z, u = b["zuordnung"], (b["umhaengen"] or [{}])[0]
        w_b.writerow([b["messung"], b["nr"], b["datum"], _zelle(b["wahrscheinlichkeit"]), z["art"], z["stufe"], z["text"], u.get("richtung", ""),
                      u.get("von_messung", ""), _zelle(u.get("score")), _zelle(u.get("p_nulltest")), _zelle(u.get("verhaeltnis_fahrzeuge")),
                      _zelle(u.get("gegenprobe_score")), "" if not u.get("naht") else int(u["naht"]["stetig"]),
                      " | ".join(x["name"] for x in b["ereignisse"]), " ".join(b["gleicher_tag"])])
        n_b += 1
    fh_b.close()
    return n_e, n_b, n_k


def bauen(auswertung, metadaten, uhr, aggregat_ordner, ziel, einsaetze=None):
    """Schreibt alle Dateien nach <ziel>. Gibt eine Kurzfassung {Datei: Zeilen} zurueck. einsaetze: einsaetze.json (einsaetze.py) oder None."""
    einsatz_von = einsatz_je_datum(einsaetze)
    os.makedirs(os.path.join(ziel, "stunden"), exist_ok=True)
    stunde_zeitraum = aggregat.zeitraum_je_stunde(gruppen.ZEITSCHEIBEN)
    zaehler = {}

    fh_m, w_m = _schreiber(os.path.join(ziel, "messungen.csv"), [
        "messung_id", "standort_seite", "standort_name", "ordner", "datei", "geraet", "tempolimit_kmh", "tempolimit_quelle", "strasse", "lage_breite",
        "lage_laenge", "lage_unsicherheit_m", "lage_sicherheit", "fahrtrichtung", "beidseitige_messung", "verdeckte_messung", "messzeitraum_von", "messzeitraum_bis",
        "fahrzeuge_in_datei", "fahrzeuge_ohne_nutzbare_zeit", "rauschen_abgezogen", "regenanteil_abgezogen", "wetterstation", "wetterstation_abstand_km", "fahrzeuge_im_aggregat",
        "uhr_nutzbarkeit", "uhr_bewertung", "abschnitte", "bezeichnung_verwaltung"])
    fh_a, w_a = _schreiber(os.path.join(ziel, "abschnitte.csv"), [
        "messung_id", "abschnitt_nr", "von", "bis", "tage", "fahrzeuge", "bruch_wahrscheinlichkeit", "anmerkung"])
    fh_k, w_k = _schreiber(os.path.join(ziel, "kennzahlen.csv"), ["messung_id", "bereich", "abschnitt_nr", "zeitraum"] + KENNZAHLEN)
    fh_t, w_t = _schreiber(os.path.join(ziel, "tage.csv"), ["messung_id", "abschnitt_nr", "datum", "wochentag", "ferien", "feiertag"] + KENNZAHLEN)
    fh_l, w_l = _schreiber(os.path.join(ziel, "luecken.csv"), ["messung_id", "von_utc", "bis_utc", "stunden"])
    gesamt, w_g = _schreiber_gz(os.path.join(ziel, "stunden.csv.gz"), aggregat.SPALTEN_STUNDEN)
    n = {k: 0 for k in ("messungen", "abschnitte", "kennzahlen", "tage", "luecken", "stunden")}
    for slug, name, rels in seiten_bauen.standortgruppen(auswertung, metadaten):
        fh_s, w_s = _schreiber_gz(os.path.join(ziel, "stunden", slug + ".csv.gz"), aggregat.SPALTEN_STUNDEN)
        for rel in rels:
            for r in [z for z in auswertung["standorte"] if z["standort"] == rel]:
                mid = seiten_bauen.messung_id(rel, r["datei"])
                pfad = os.path.join(aggregat_ordner, rel.replace("/", os.sep), os.path.splitext(r["datei"])[0] + ".aggregat.json")
                agg = None
                if os.path.exists(pfad):
                    with open(pfad, encoding="utf-8") as fh:
                        agg = json.load(fh)
                bz = (r.get("bereinigt") or {}).get("messzeitraum") or r.get("messzeitraum") or {}
                liste = (r.get("abschnitte") or {}).get("liste") or []
                meta_messung = next((m for m in ((metadaten.get("standorte") or {}).get(rel) or {}).get("messungen", []) if m["datei"] == r["datei"]), {})
                verw = " | ".join(v["bezeichnung"] for v in meta_messung.get("verwaltung", []) if v.get("bezeichnung"))
                urteil = gesamturteil(((uhr.get("dateien") or {}).get(f'{rel}/{r["datei"]}') or {}).get("abschnitte", []))
                rb = r.get("rauschen") or {}
                lage = ((metadaten.get("standorte") or {}).get(rel) or {}).get("standort") or {}  # geschaetzt, docs/standorte.md
                beidseitig = lage.get("beidseitige_messung")
                w_m.writerow([mid, slug, name, rel, r["datei"], (r.get("geraet") or "").strip(), _zelle(r.get("tempolimit_kmh")), _zelle(r.get("tempolimit_quelle")),
                              _zelle(lage.get("strasse")), _zelle(lage.get("breite")), _zelle(lage.get("laenge")), _zelle(lage.get("unsicherheit_m")),
                              _zelle(lage.get("sicherheit")), ", ".join(seiten_bauen.fahrtrichtungen(meta_messung, rel)),
                              "" if beidseitig is None else int(bool(beidseitig)),
                              int(bool((meta_messung.get("geraet") or {}).get("verdeckte_messung"))), (bz.get("start") or "")[:10], (bz.get("ende") or "")[:10], r.get("fahrzeuge_in_datei"),
                              (r.get("uhr") or {}).get("fahrzeuge_ohne_nutzbare_zeit"), rb.get("abgezogen_fahrzeuge") or 0,
                              (rb.get("regen") or {}).get("abgezogen_fahrzeuge") or 0,
                              ((rb.get("regen") or {}).get("wetterstation") or {}).get("name", ""),
                              _zelle(((rb.get("regen") or {}).get("wetterstation") or {}).get("abstand_km")),
                              (r.get("bereinigt") or {}).get("anzahl_fahrzeuge") or 0, (r.get("uhr") or {}).get("nutzbarkeit"),
                              urteil[0] if urteil else "", len(liste) or 1, verw])
                n["messungen"] += 1
                # Kennzahlen: ganze Messung (nutzbare Zeit, nach Abzug) und je Abschnitt, je Zeitraum
                quellen = [("messung", "", r.get("bereinigt") or {}, r.get("teilzeitraeume") or {})]
                if liste:
                    quellen += [("abschnitt", a["nr"], a, a.get("teilzeitraeume") or {}) for a in liste]
                else:
                    quellen.append(("abschnitt", 1, r.get("bereinigt") or {}, r.get("teilzeitraeume") or {}))
                    von, bis = (bz.get("start") or "")[:10], (bz.get("ende") or "")[:10]
                    tage = (dt.date.fromisoformat(bis) - dt.date.fromisoformat(von)).days + 1 if von and bis else ""
                    w_a.writerow([mid, 1, von, bis, tage, (r.get("bereinigt") or {}).get("anzahl_fahrzeuge") or 0, "",
                                  "nicht prüfbar" if (r.get("abschnitte") or {}).get("geprueft") is False else "kein Bruch erkannt"])
                    n["abschnitte"] += 1
                for a in liste:
                    b = a.get("beginn") or {}
                    w_a.writerow([mid, a["nr"], a["von"], a["bis"], a["tage"], a.get("anzahl_fahrzeuge") or 0, _zelle(b.get("wahrscheinlichkeit")),
                                  "Beginn der Messung" if b.get("art") != "Bruch" else "Bruch davor"])
                    n["abschnitte"] += 1
                for bereich, nr, block, teil in quellen:
                    for zr in ZEITRAEUME:
                        w_k.writerow([mid, bereich, nr, zr] + kennzahlen(block if zr == "alle" else teil.get(zr)))
                        n["kennzahlen"] += 1
                if agg:
                    for t in agg["tage"]:
                        wt, fe, ft = tage_flags(t[1])
                        w_t.writerow([mid, t[0], t[1], wt, fe, ft] + t[2:])
                        n["tage"] += 1
                    for lk in agg["luecken"]:
                        w_l.writerow([mid] + lk)
                        n["luecken"] += 1
                    for z in stunden_zeilen(mid, agg, stunde_zeitraum, einsatz_von.get(mid)):
                        w_s.writerow(z)
                        w_g.writerow(z)
                        n["stunden"] += 1
        fh_s.close()
    if einsaetze:
        n["einsaetze"], n["brueche"], k = einsaetze_schreiben(ziel, einsaetze, auswertung, w_k)
        n["kennzahlen"] += k
    for fh in (fh_m, fh_a, fh_k, fh_t, fh_l):
        fh.close()
    gesamt.close()
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--auswertung", required=True, help="auswertung.json von dsd2csv.py")
    ap.add_argument("--aggregat", required=True, help="Ordner mit den Zwischenstaenden (dsd2csv.py --aggregat)")
    ap.add_argument("--metadaten", default=os.path.join(HIER, "belege", "metadaten.json"))
    ap.add_argument("--uhr", default=os.path.join(HIER, "belege", "uhr-bewertung.json"))
    ap.add_argument("--ziel", required=True, help="Ausgabeordner (zum Beispiel _site/daten)")
    ap.add_argument("--einsaetze", help="einsaetze.json (einsaetze.py); Standard: neben der auswertung.json, falls vorhanden")
    a = ap.parse_args()
    daten = []
    for pfad in (a.auswertung, a.metadaten, a.uhr):
        with open(pfad, encoding="utf-8") as fh:
            daten.append(json.load(fh))
    pfad_e = a.einsaetze or os.path.join(os.path.dirname(os.path.abspath(a.auswertung)), "einsaetze.json")
    einsaetze = None
    if os.path.exists(pfad_e):
        with open(pfad_e, encoding="utf-8") as fh:
            einsaetze = json.load(fh)
    n = bauen(daten[0], daten[1], daten[2], a.aggregat, a.ziel, einsaetze)
    print("Daten in %s: %s" % (a.ziel, ", ".join("%s %d" % (k, v) for k, v in n.items())), file=sys.stderr)


if __name__ == "__main__":
    main()
