# SPDX-License-Identifier: MIT
"""Metadaten je Standort aus den Mitteilungen der Verwaltung und der DSD-Konfiguration.

Aufruf:
  python3 -I metadaten.py .
    -> <Standortordner>/metadaten.yaml (neben den DSD-Dateien)
       belege/ris-zuordnung.json (welche Angabe der Verwaltung zu welcher DSD-Datei, und was offen blieb)

Eingabe: belege/ris-messstellen.json (tools/ris_messstellen.py) und die DSD-Dateien.

Je DSD-Datei steht in der YAML:
  geraet        Konfiguration aus der DSD (Geraet, Name, Tempolimit der Anzeige, Erfassung ab, verdeckte Messung)
  verwaltung    Angaben der Verwaltung zu dieser Messung (Bezeichnung, Fahrtrichtung, Erfassungszeitraum,
                Tempolimit, Fahrzeuge, V85, mittleres Tempo, Anteile, Einstufung, Hinweise) mit Quelle
  zuordnung     warum die Angabe zu dieser Datei gehoert
  abgleich_dsd  dieselben Kennzahlen, aus der DSD berechnet (keine Angabe der Verwaltung)

Zuordnung einer Angabe zu einer DSD-Datei:
  1. Der Strassenname der Mitteilung passt zum Ordnernamen (Nummer, Jahr und Hausnummer abgezogen).
  2. Nennt die Mitteilung eine Fahrtrichtung und die Datei/der Ordner ebenfalls ("FR Norf"), muessen sie
     uebereinstimmen.
  3. Nennt die Mitteilung einen Erfassungszeitraum, muss er mit den Tagen uebereinstimmen, an denen die Datei
     Fahrzeuge mit glaubwuerdiger Uhr enthaelt (Ueberlappung ab 80 % des kuerzeren Zeitraums).
  4. Nennt sie keinen, entscheiden V85 (hoechstens 2 km/h Abweichung) und mittleres Tempo (hoechstens 3 km/h);
     die Angabe wird nur zugeordnet, wenn genau eine Datei am besten passt. Diese Zuordnung stuetzt sich auf
     die DSD-Werte, der Abgleich ist dann nicht unabhaengig.
  5. Passt der Zeitraum nicht, stimmen aber V85 und mittleres Tempo auf die Datei (1 bzw. 2 km/h), wird sie
     mit dem Vermerk "zeitraum_abweichend" zugeordnet.
Alles andere bleibt unzugeordnet und steht in belege/ris-zuordnung.json.
"""
import argparse
import collections
import datetime as dt
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I nimmt das Skriptverzeichnis nicht auf
import dsd2csv as d  # noqa: E402
from uhr_belege import messort_namen, schluessel  # noqa: E402

SCHWELLEN = {
    "zeitraum_ueberlappung_min": 0.8,  # Anteil des kuerzeren Zeitraums, der im anderen liegt
    "zeitraum_anteil_groesserer_min": 0.25,
    "undatiert_v85_max_abw": 2,
    "undatiert_mittel_max_abw": 3,
    "undatiert_abstand_zum_zweiten": 1.0,  # Punktabstand (|dV85| + 0,5 |dMittel|) zur zweitbesten Datei
    "abweichend_v85_max_abw": 1,
    "abweichend_mittel_max_abw": 2,
    "sitzung_max_monate": 15,  # Messende hoechstens so lange vor der Sitzung der Mitteilung
}
GUELTIG = ("gueltig", "auffaellig")
ALIAS_RICHTUNG = {"gv": "grevenbroich"}


# ------------------------------------------------------------------ DSD-Seite

def lade_dsd(wurzel):
    """Alle DSD-Dateien: Konfiguration und Fahrzeuge mit glaubwuerdiger Uhr (Geraetezeit)."""
    ergebnis = []
    for ordner, _, dateien in sorted(os.walk(wurzel)):
        for f in sorted(dateien):
            if not f.lower().endswith(".dsd"):
                continue
            rel = os.path.relpath(ordner, wurzel).replace(os.sep, "/")
            meta, veh, status, _ = d.parse(open(os.path.join(ordner, f), "rb").read())
            segs = d.uhr_segmente(veh, status)
            d.bewerte_segmente(segs, veh)
            gueltig = [veh[i] for s in segs if s["bewertung"] in GUELTIG for i in s["idx"]]
            ergebnis.append({
                "rel": rel, "datei": f, "meta": meta, "alle": veh, "gueltig": gueltig,
                "tage": {t.date() for t, _ in gueltig},
                "namen": [schluessel(n) for n in messort_namen(rel)],
                "richtungen": richtungen(f"{rel} {f}"),
            })
    return ergebnis


def richtungen(text):
    """Fahrtrichtungen, die im Ordner- oder Dateinamen stehen ("FR Norf", "FR GV", "FR Speck20")."""
    r = set()
    for m in re.findall(r"\bFR\.?\s+([A-Za-zÄÖÜäöüß]+)", text):
        k = schluessel(m)
        r.add(ALIAS_RICHTUNG.get(k, k))
    return r


def kennzahlen(vehs, tage):
    v = sorted(x[1] for x in vehs)
    if not v:
        return None
    n = len(v)
    return {"fahrzeuge": n, "v85_kmh": d.pct(v, 85), "mittel_kmh": round(sum(v) / n, 1),
            "fahrzeuge_je_tag": round(n / max(tage, 1))}


def im_zeitraum(vehs, von, bis):
    a = dt.datetime.combine(von, dt.time())
    b = dt.datetime.combine(bis + dt.timedelta(days=1), dt.time())
    return [x for x in vehs if a <= x[0] < b]


# ------------------------------------------------------------------ Zuordnung

def passt_name(strasse, namen):
    bk = schluessel(strasse)
    for nk in namen:
        if nk == bk:
            return True
        kurz, lang = sorted((nk, bk), key=len)
        if len(kurz) >= 6 and kurz in lang:
            return True
    return False


def passt_richtung(block, datei):
    fr = block.get("fahrtrichtung")
    if not fr or not datei["richtungen"]:
        return True
    bk = schluessel(fr)
    return any(bk == t or (len(t) >= 4 and (t in bk or bk in t)) for t in datei["richtungen"])


def zeitraum_pruefung(block_zeitraum, datei):
    """(Tage der Ueberlappung, Anteil am kuerzeren, Anteil am laengeren) zwischen Erfassungszeitraum und Datei."""
    von, bis = (dt.date.fromisoformat(x) for x in block_zeitraum)
    tage_block = (bis - von).days + 1
    ueber = sum(1 for t in datei["tage"] if von <= t <= bis)
    if not datei["tage"] or tage_block <= 0:
        return 0, 0.0, 0.0
    return ueber, ueber / min(len(datei["tage"]), tage_block), ueber / max(len(datei["tage"]), tage_block)


def vergleich(block, k):
    """Abweichungen (DSD minus Verwaltung) der Kennzahlen eines Blocks gegen die DSD-Kennzahlen k."""
    a = {}
    if block.get("v85_kmh") is not None:
        a["v85_kmh"] = k["v85_kmh"] - block["v85_kmh"]
    if block.get("mittel_kmh") is not None:
        a["mittel_kmh"] = round(k["mittel_kmh"] - block["mittel_kmh"], 1)
    je_tag = block.get("fahrzeuge_je_tag")
    if je_tag:
        soll = sum(je_tag.values()) if "gesamt" not in je_tag else je_tag["gesamt"]
        if soll:
            a["fahrzeuge_je_tag_prozent"] = round(100 * (k["fahrzeuge_je_tag"] - soll) / soll)
    return a


def punkte(a):
    return abs(a.get("v85_kmh", 0)) + 0.5 * abs(a.get("mittel_kmh", 0))


def block_tage(block):
    """Tage des Erfassungszeitraums wie die Verwaltung rechnet (Ende minus Beginn: 25.04. bis 24.07. = 90 Tage)."""
    z = block.get("zeitraum")
    if z:
        return (dt.date.fromisoformat(z[1]) - dt.date.fromisoformat(z[0])).days
    return None


def tage_der_datei(vehs, block):
    """Tage, durch die die Fahrzeuge der Datei (im Zeitraum des Blocks) geteilt werden: nicht mehr als der Zeitraum."""
    ds = [t.date() for t, _ in vehs]
    if not ds:
        return 1
    span = (max(ds) - min(ds)).days + 1
    return max(min(span, block_tage(block) or span), 1)


def zeit_passt(block, datei):
    """Die Messung muss vor der Sitzung liegen und darf hoechstens 15 Monate zurueckliegen. Ohne Uhr: keine Aussage."""
    sitzungen = [q["sitzung"] for q in block["quellen"] if q.get("sitzung")]
    if not sitzungen or not datei["gueltig"]:
        return True
    sitzung = dt.date.fromisoformat(min(sitzungen))
    ende = max(t for t, _ in datei["gueltig"]).date()
    return sitzung - dt.timedelta(days=SCHWELLEN["sitzung_max_monate"] * 30.5) <= ende <= sitzung + dt.timedelta(days=3)


def bewerte_kandidat(block, datei, einzige=False):
    """Eine Datei als Kandidat fuer einen Block bewerten. Gibt dict mit 'methode' oder None zurueck."""
    z = block.get("zeitraum")
    if z:
        ueber, r_klein, r_gross = zeitraum_pruefung(z, datei)
        if ueber and r_klein >= SCHWELLEN["zeitraum_ueberlappung_min"] and r_gross >= SCHWELLEN["zeitraum_anteil_groesserer_min"]:
            von, bis = (dt.date.fromisoformat(x) for x in z)
            vehs = im_zeitraum(datei["gueltig"], von, bis)
            k = kennzahlen(vehs, tage_der_datei(vehs, block))
            return {"methode": "name_zeitraum", "k": k, "a": vergleich(block, k) if k else {},
                    "zeitraum_ueberlappung_tage": ueber}
    if not zeit_passt(block, datei):
        return None
    # keine oder nicht passende Zeitangabe: Werte der Datei (glaubwuerdige Uhr, sonst alle Fahrzeuge)
    quelle = datei["gueltig"] or datei["alle"]
    if not quelle:
        return None
    k = kennzahlen(quelle, tage_der_datei(quelle, block))
    a = vergleich(block, k)
    hat_v85 = "v85_kmh" in a
    if z:  # Zeitraum der Mitteilung passt nicht zur Datei: nur ueber die Werte
        ok = (hat_v85 and abs(a["v85_kmh"]) <= SCHWELLEN["abweichend_v85_max_abw"]
              and abs(a.get("mittel_kmh", 0)) <= SCHWELLEN["abweichend_mittel_max_abw"])
        return {"methode": "name_werte_zeitraum_abweichend", "k": k, "a": a} if ok else None
    ok = (hat_v85 and abs(a["v85_kmh"]) <= SCHWELLEN["undatiert_v85_max_abw"]
          and abs(a.get("mittel_kmh", 0)) <= SCHWELLEN["undatiert_mittel_max_abw"])
    if ok:
        return {"methode": "name_werte", "k": k, "a": a, "punkte": punkte(a), "rohdaten": not datei["gueltig"]}
    if einzige:
        return {"methode": "name_einzige_datei", "k": k, "a": a, "punkte": punkte(a), "rohdaten": not datei["gueltig"]}
    return None


def zuordnen(bloecke, dateien):
    """Gibt (zuordnungen {(rel, datei): [(block, bewertung)]}, offen [dict]) zurueck."""
    zugeordnet = collections.defaultdict(list)
    offen = []
    for b in bloecke:
        namens_treffer = [f for f in dateien if passt_name(b["strasse"], f["namen"]) and passt_richtung(b, f)]
        # ohne Zeitraum und ohne Gegenbeweis: gibt es nur eine Datei, die zur Sitzung passt, gehoert die Angabe dazu
        passende = [f for f in namens_treffer if zeit_passt(b, f)]
        einzige = not b.get("zeitraum") and len(passende) == 1
        treffer = [(f, e) for f, e in ((f, bewerte_kandidat(b, f, einzige=einzige)) for f in namens_treffer) if e]
        datiert = [(f, e) for f, e in treffer if e["methode"] == "name_zeitraum"]
        if datiert:
            for f, e in datiert:
                zugeordnet[(f["rel"], f["datei"])].append((b, e))
            continue
        if not treffer:
            offen.append({"messstelle": b["bezeichnung"], "zeitraum": b.get("zeitraum"), "quellen": b["quellen"],
                          "grund": ("kein Ordner mit passendem Namen und passender Fahrtrichtung" if not namens_treffer else
                                    "Name passt, aber weder Zeitraum noch Werte (V85, Tempo) noch Sitzungsdatum einer Datei"),
                          "kandidaten": sorted(f"{f['rel']}/{f['datei']}" for f in namens_treffer)})
            continue
        treffer.sort(key=lambda x: x[1].get("punkte", punkte(x[1]["a"])))
        beste = treffer[0]
        zweite = treffer[1] if len(treffer) > 1 else None
        if zweite and zweite[1].get("punkte", punkte(zweite[1]["a"])) - beste[1].get("punkte", punkte(beste[1]["a"])) < SCHWELLEN["undatiert_abstand_zum_zweiten"]:
            offen.append({"messstelle": b["bezeichnung"], "zeitraum": b.get("zeitraum"), "quellen": b["quellen"],
                          "grund": "mehrdeutig: mehrere Dateien passen gleich gut",
                          "kandidaten": [f"{f['rel']}/{f['datei']}" for f, _ in treffer]})
            continue
        zugeordnet[(beste[0]["rel"], beste[0]["datei"])].append((b, beste[1]))
    return zugeordnet, offen


# ------------------------------------------------------------------ Bloecke laden

def lade_bloecke(pfad):
    """Messstellen aus belege/ris-messstellen.json; identische Angaben mehrerer Dokumente werden vereint."""
    with open(pfad, encoding="utf-8") as fh:
        j = json.load(fh)
    vereint = {}
    for doc in j["dokumente"]:
        quelle = {"vorlage": doc["vorlage"], "ris_vorlage_id": doc.get("ris_vorlage_id"),
                  "gremium": doc["gremium"], "sitzung": doc["sitzung"], "dokument": doc["dokument"]}
        for b in doc["messstellen"]:
            schl = json.dumps({k: b.get(k) for k in ("strasse", "fahrtrichtung", "v85_kmh", "fahrzeuge_je_tag",
                                                       "fahrzeuge_im_zeitraum", "anteil_unter")}, sort_keys=True)
            alt = vereint.get(schl)
            if alt and not (alt.get("zeitraum") and b.get("zeitraum") and alt["zeitraum"] != b["zeitraum"]):
                # dieselbe Messung in mehreren Mitteilungen: Quellen sammeln, fehlende Angaben ergaenzen
                alt["quellen"].append(quelle)
                for k, v in b.items():
                    if alt.get(k) is None:
                        alt[k] = v
                continue
            kopie = dict(b)
            kopie["quellen"] = [quelle]
            vereint[schl if not alt else schl + str(len(vereint))] = kopie
    for b in vereint.values():
        sitzungen = [q["sitzung"] for q in b["quellen"] if q.get("sitzung")]
        if b.get("zeitraum") and sitzungen and b["zeitraum"][1] > min(sitzungen):
            b["zeitraum_in_mitteilung"] = b["zeitraum"]
            b["zeitraum"] = None
            b["zeitraum_hinweis"] = ("Der genannte Zeitraum endet nach der Sitzung, in der er berichtet wurde "
                                     "(vermutlich ein Tippfehler); er wird für die Zuordnung nicht verwendet")
    return list(vereint.values()), j


# ------------------------------------------------------------------ Ausgabe

SCHLUESSEL_VERWALTUNG = ("bezeichnung", "strasse", "fahrtrichtung", "beidseitig", "wiederholungsmessung", "zeitraum",
                         "zeitraum_in_mitteilung", "zeitraum_hinweis",
                         "tempolimit_kmh", "tempolimit_deutlich_unter", "fahrzeuge_je_tag", "fahrzeuge_im_zeitraum",
                         "v85_kmh", "mittel_kmh", "anteil_unter", "anteil_ueber", "einstufung_verwaltung",
                         "massnahmen_verwaltung", "hinweise_verwaltung")


def wert_byte(meta, key):
    return d.byte_wert(meta.get(key))


def geraet(datei):
    m = datei["meta"]
    g = {"konfiguration": (m.get("configuration_number") or "").strip() or None,
         "name": (m.get("name") or "").strip() or None,
         "tempolimit_anzeige_kmh": wert_byte(m, "safety_speed"),
         "erfassung_ab_kmh": wert_byte(m, "capture_min_speed"),
         "verdeckte_messung": m.get("hidden_measurement_on") == "01"}
    return g


def eintrag(block, bew):
    e = {k: block[k] for k in SCHLUESSEL_VERWALTUNG if block.get(k) is not None}
    e["quellen"] = block["quellen"]
    z = {"methode": bew["methode"]}
    for k in ("zeitraum_ueberlappung_tage", "rohdaten"):
        if bew.get(k):
            z[k] = bew[k]
    hinweise = {
        "name_werte": "Zuordnung über Straßenname, Sitzungsdatum und die Werte (V85, mittleres Tempo) der DSD-Datei; "
                      "der Abgleich ist nicht unabhängig",
        "name_werte_zeitraum_abweichend": "Zuordnung über Straßenname und die Werte (V85, mittleres Tempo) der DSD-Datei; "
                                          "der genannte Zeitraum passt nicht zur DSD-Datei; der Abgleich ist nicht unabhängig",
        "name_einzige_datei": "Zuordnung nur über den Straßennamen und das Sitzungsdatum: die Mitteilung nennt keinen "
                              "verwendbaren Zeitraum und es gibt keine andere passende DSD-Datei; die Werte können "
                              "abweichen (siehe abgleich_dsd)",
    }
    if bew["methode"] in hinweise:
        z["hinweis"] = hinweise[bew["methode"]]
    e["zuordnung"] = z
    if bew["k"]:
        e["abgleich_dsd"] = {"hinweis": "aus der DSD berechnet (Gerätezeit, nur Fahrzeuge mit glaubwürdiger Uhr), keine Angabe der Verwaltung",
                             **bew["k"], "abweichung_dsd_minus_verwaltung": bew["a"]}
    return e


def schreibe(wurzel, dateien, zugeordnet):
    je_ordner = collections.defaultdict(list)
    for f in dateien:
        je_ordner[f["rel"]].append(f)
    for rel, liste in je_ordner.items():
        zeilen = ["# Zusätzlich erhobene Metadaten zu den Messungen in diesem Ordner.",
                  "# Erzeugt von metadaten.py aus den DSD-Dateien und den Mitteilungen der Verwaltung (Ratsinformationssystem",
                  "# der Stadt Neuss), siehe docs/metadaten.md. Angaben der Verwaltung stehen unter 'verwaltung', was aus der",
                  "# DSD stammt unter 'geraet' und 'abgleich_dsd'.",
                  f"ordner: {d.yaml_skalar(rel)}", "messungen:"]
        for f in sorted(liste, key=lambda x: x["datei"]):
            eintraege = [eintrag(b, e) for b, e in sorted(zugeordnet.get((rel, f["datei"]), []),
                                                          key=lambda x: (x[0].get("zeitraum") or ["9"])[0])]
            m = {"datei": f["datei"], "geraet": geraet(f), "verwaltung": eintraege}
            teil = d.yaml_zeilen(m, 2)
            teil[0] = "  - " + teil[0].lstrip()
            zeilen += teil
        d.schreibe_yaml(os.path.join(wurzel, *rel.split("/"), "metadaten.yaml"), zeilen)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("eingabe", help="Ordner mit den DSD-Dateien")
    ap.add_argument("--messstellen", default="belege/ris-messstellen.json")
    ap.add_argument("--zuordnung", default="belege/ris-zuordnung.json")
    a = ap.parse_args()

    bloecke, quelle = lade_bloecke(a.messstellen)
    dateien = lade_dsd(a.eingabe)
    zugeordnet, offen = zuordnen(bloecke, dateien)
    schreibe(a.eingabe, dateien, zugeordnet)

    nicht_ausgewertet = [{"dokument": doc["dokument"], **x} for doc in quelle["dokumente"] for x in doc["nicht_ausgewertet"]]
    os.makedirs(os.path.dirname(a.zuordnung) or ".", exist_ok=True)
    with open(a.zuordnung, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"erzeugt_von": "metadaten.py", "schwellen": SCHWELLEN,
                   "zugeordnet": {f"{rel}/{datei}": [{"messstelle": b["bezeichnung"], "zeitraum": b.get("zeitraum"),
                                                    "methode": e["methode"], "abweichung": e["a"]} for b, e in v]
                                  for (rel, datei), v in sorted(zugeordnet.items())},
                   "nicht_zugeordnet": offen, "nicht_ausgewertet": nicht_ausgewertet}, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    n_zu = sum(len(v) for v in zugeordnet.values())
    print(f"{len(bloecke)} Messstellen der Verwaltung: {len(bloecke) - len(offen)} zugeordnet "
          f"({n_zu} Zuordnungen zu {len(zugeordnet)} Dateien), {len(offen)} offen; "
          f"{len({f['rel'] for f in dateien})} Standortordner geschrieben", file=sys.stderr)


if __name__ == "__main__":
    main()
