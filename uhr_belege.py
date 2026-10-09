# SPDX-License-Identifier: MIT
"""Belege und Urteil zur Geraeteuhr je DSD-Datei und Uhr-Segment.

Die Uhren der Geraete sind nicht verlaesslich: sie werden nie auf Sommerzeit umgestellt, manchmal
zurueckgesetzt (Standarddatum 2020-01-01) oder um Stunden und Tage verstellt. Dieses Skript
entscheidet fuer jeden zusammenhaengenden Abschnitt (Segment) einer Aufzeichnung, ob die
Zeitstempel

  plausibel        uneingeschraenkt glaubwuerdig sind (mindestens zwei unabhaengige Belege, kein Widerspruch),
  eingeschraenkt   womoeglich verschoben sind (Minuten bis Jahre) oder nicht genug Belege vorliegen,
  unbrauchbar      Unsinn sind (unmoegliches Datum, kein erkennbarer Tagesgang).

Jedes Urteil nennt die Belege, auf die es sich stuetzt. Belege (je "bestaetigt", "widerspricht", "offen"):

  datum             Datum liegt in 2020 bis 2030 und ist nicht das Standarddatum 2020-01-01 12:00
  wochenrhythmus    Das Wochenmuster (Sonntag schwach, Samstag danach) liegt auf den richtigen Wochentagen
  tagesgang         Der Werktags-Tagesgang entspricht dem typischen Verlauf aller Messungen
  zeitumstellung    Der Tagesgang vor und nach einer Zeitumstellung passt nach der Sommerzeit-Korrektur
  ris               Die Mitteilungen der Verwaltung nennen Ort und einen dazu passenden Zeitraum

Der Wochentag-Versatz und die Tageszeit-Abweichung eines Segments werden nur geschaetzt und nicht
angewendet. Alle Schwellen stehen in SCHWELLEN. Die Referenzkurven (typische Woche, typischer Tagesgang)
werden aus den Segmenten berechnet, deren Wochenrhythmus eindeutig stimmt; ein Segment wird dabei nie
mit sich selbst verglichen.

Aufruf:
  python3 -I uhr_belege.py .
    -> belege/uhr-bewertung.json (maschinenlesbar) und <Standortordner>/uhr-analyse.md (zum Lesen)
  --ris belege/ris.json   Mitteilungen der Verwaltung (tools/ris_auswerten.py), falls vorhanden
"""
import argparse
import collections
import datetime as dt
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I nimmt das Skriptverzeichnis nicht auf
import dsd2csv as d  # noqa: E402

SCHWELLEN = {
    "woche_min_volle_tage": 21,  # darunter ist das Wochenmuster nicht beurteilbar
    "woche_min_korrelation": 0.75,
    "woche_min_abstand": 0.25,  # beste Drehung muss die zweitbeste um so viel uebertreffen
    "woche_referenz_korrelation": 0.9,  # nur solche Segmente bilden die Referenzwoche
    "tagesgang_min_fahrzeuge": 3000,
    "tagesgang_min_werktage": 5,
    "tagesgang_bestaetigt_max_min": 60,
    "tagesgang_widerspruch_min": 90,
    "tagesgang_min_korrelation": 0.9,
    "tagesgang_struktur_min_korrelation": 0.5,  # darunter ist kein Verkehrsgang erkennbar
    "umstellung_bestaetigt_max_min": 30,
    "umstellung_widerspruch_min": 45,
    "anker_min_trefferquote": 0.8,  # Anteil der Tage um die Umstellung, die zur Stufe passen
    "anker_max_tage": 2,  # Stufe hoechstens so viele Tage neben dem amtlichen Umstellungstag
    "ris_toleranz_tage": 1,
    "werksdatum_min_fahrzeuge": 500,  # kuerzere Segmente nach Reset sind nicht zu rekonstruieren
    "hb_abdeckung_ok": 0.8,
    "gesamt_plausibel_min": 0.99,  # Gesamturteil einer Datei: Anteil der Fahrzeuge in plausiblen Abschnitten
    "gesamt_unbrauchbar_min": 0.5,  # ... bzw. in unbrauchbaren Abschnitten
}
URTEILE = ("plausibel", "eingeschraenkt", "unbrauchbar")
WT = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def schluessel(text):
    """Vergleichsform fuer Ortsnamen: nur Buchstaben, klein, ss statt Eszett, Umlaute ohne Punkte."""
    t = text.lower().replace("ß", "ss").replace("straße", "strasse")
    for a, b in (("ä", "a"), ("ö", "o"), ("ü", "u")):
        t = t.replace(a, b)
    t = t.replace("str.", "strasse")  # auch am Wortende: "Kirchstr." -> "Kirchstrasse"
    return re.sub(r"[^a-z]", "", t)


def messort_namen(ordner):
    """Namen der Messstelle(n) aus dem Ordnernamen: ohne Nummer, Jahr, Klammerzusatz und Hausnummer."""
    erster = ordner.split("/")[0]
    name = re.sub(r"^\d+(?:[-_]\d{4})?_\s*", "", erster)
    name = re.sub(r"\(.*?\)", "", name)
    name = re.sub(r",.*$", "", name)
    name = re.sub(r"\s+\d+[a-z]?(?:-\d+)?\s*$", "", name).strip()
    teile = [t.strip() for t in name.split("_")]
    if teile and teile[0].lower().startswith("station"):
        teile = teile[1:]
    namen = [t for t in teile if len(schluessel(t)) >= 5]
    ganz = " ".join(teile)  # "Im_Tal" -> "Im Tal": die Teile allein sind zu kurz
    if len(teile) > 1 and len(schluessel(ganz)) >= 5:
        namen.insert(0, ganz)
    return namen


# ------------------------------------------------------------------ Merkmale

def wochenvektor(zeiten, start, ende):
    """Mittlere Fahrzeuge je Wochentag (Mo..So), normiert auf Mittel 1, ueber volle Tage; None wenn zu wenig."""
    zaehler = collections.Counter(t.date() for t in zeiten)
    summe, tage = [0] * 7, [0] * 7
    tag = start.date() + dt.timedelta(days=1)
    while tag < ende.date():
        summe[tag.weekday()] += zaehler.get(tag, 0)
        tage[tag.weekday()] += 1
        tag += dt.timedelta(days=1)
    if sum(tage) < SCHWELLEN["woche_min_volle_tage"] or min(tage) < 3:
        return None, sum(tage)
    m = [summe[i] / tage[i] for i in range(7)]
    mittel = sum(m) / 7
    return ([x / mittel for x in m] if mittel else None), sum(tage)


def drehungen(v, vorlage):
    """Korrelation der Woche v mit der Vorlage fuer jede Drehung r: Wochentag-Etikett der Uhr = wahrer Tag + r."""
    return {r: d._pearson([v[(i + r) % 7] for i in range(7)], vorlage) for r in range(7)}


def beste_drehung(v, vorlage):
    sc = drehungen(v, vorlage)
    r = max(sc, key=sc.get)
    return r, sc[r], sc[r] - max(x for k, x in sc.items() if k != r), sc[0]


def tagesgang_verschiebung(profil, referenz):
    """(Minuten, Korrelation): positiv = Verkehr zeigt sich in Geraetezeit spaeter als im Referenzverlauf (Uhr geht vor).

    Gesucht wird ueber den ganzen Tag (-12 bis +12 Stunden), damit eine um Stunden verstellte Uhr als
    verschobener, aber erkennbarer Tagesgang auftaucht und nicht als fehlender.
    """
    k = max(range(-47, 49), key=lambda k: d._pearson(referenz, [profil[(i + k) % 96] for i in range(96)]))
    return k * 15, d._pearson(referenz, [profil[(i + k) % 96] for i in range(96)])


def _tagesprofile(zeiten):
    """Datum -> Zaehler je Viertelstunde (Geraetezeit)."""
    p = collections.defaultdict(lambda: [0] * 96)
    for t in zeiten:
        p[t.date()][(t.hour * 60 + t.minute) // 15] += 1
    return p


def _normiert(c):
    s = sum(c)
    return [x / s for x in c] if s else None


def _mittelprofil(profile, tage):
    """Mittleres normiertes Tagesprofil, Werktage ("wt") und Wochenende ("we") getrennt; None bei < 3 Tagen."""
    acc = {"wt": [0.0] * 96, "we": [0.0] * 96}
    n = {"wt": 0, "we": 0}
    for t in tage:
        if t in profile and sum(profile[t]) >= 100:
            k = "wt" if t.weekday() < 5 else "we"
            acc[k] = [x + y for x, y in zip(acc[k], _normiert(profile[t]))]
            n[k] += 1
    return {k: ([x / n[k] for x in acc[k]] if n[k] >= 3 else None) for k in acc}


def zeitumstellung_anker(zeiten, start, ende):
    """Wann (an welchem Geraete-Tag) springt der Verkehrsgang um etwa eine Stunde?

    Die Geraeteuhr wird nie umgestellt, der Verkehr folgt aber der Ortszeit: in Geraetezeit verschiebt sich der
    Tagesgang am Tag der amtlichen Zeitumstellung. Der Tag, an dem das geschieht, verankert die Uhr auf den Tag
    genau. Rueckgabe je pruefbarer Umstellung: datum (amtlich), tage_abweichung (Geraete-Tag der Stufe minus
    amtlicher Tag, 0 = stimmt), trefferquote (Anteil der Tage, die zur Stufe passen), tage.
    """
    erg = []
    profile = None
    for jahr in range(start.year, ende.year + 1):
        for monat in (3, 10):
            sonntag = d.letzter_sonntag(jahr, monat)
            if not (start.date() + dt.timedelta(days=21) < sonntag < ende.date() - dt.timedelta(days=21)):
                continue
            profile = profile or _tagesprofile(zeiten)
            tag = lambda k: sonntag + dt.timedelta(days=k)
            vorher = _mittelprofil(profile, [tag(k) for k in range(-28, -4)])
            nachher = _mittelprofil(profile, [tag(k) for k in range(5, 29)])
            if not all(vorher[k] and nachher[k] for k in ("wt", "we")):
                continue
            punkte = {}
            for k in range(-7, 8):
                t = tag(k)
                if t not in profile or sum(profile[t]) < 100:
                    continue
                c, typ = _normiert(profile[t]), ("wt" if t.weekday() < 5 else "we")
                punkte[k] = d._pearson(c, nachher[typ]) - d._pearson(c, vorher[typ])
            if len(punkte) < 10:
                continue
            beste = max(range(-6, 8), key=lambda c: sum((-v if k < c else v) for k, v in punkte.items()))
            treffer = sum(1 for k, v in punkte.items() if (v < 0) == (k < beste)) / len(punkte)
            erg.append({"datum": sonntag.isoformat(), "tage_abweichung": beste, "trefferquote": round(treffer, 2), "tage": len(punkte)})
    return erg


def segment_zeiten(s, veh):
    """Zeiten fuer die Merkmale: Ortszeit, wo die Sommerzeit-Korrektur gilt, sonst Geraetezeit."""
    if s.get("ortszeit"):
        return s["ortszeit"], "ortszeit"
    return [veh[i][0] for i in s["idx"]], "geraetezeit"


# ------------------------------------------------------------------ Belege

def beleg(status, text, **werte):
    return {"status": status, "text": text, **werte}


def beleg_datum(s):
    if s["bewertung"] == "werksdatum":
        return beleg("widerspricht", "Uhr nach einem Reset auf das Standarddatum 2020-01-01 12:00 nicht neu gestellt")
    if s["bewertung"] == "ungueltiges_datum":
        return beleg("widerspricht", s.get("grund", "unmögliches Datum"))
    return beleg("bestaetigt", "Datum liegt zwischen 2020 und 2030 und ist nicht das Standarddatum")


def beleg_wochenrhythmus(e, vorlage):
    v, tage = e["wochenvektor"], e["volle_tage"]
    if v is None:
        return beleg("offen", f"zu kurz für das Wochenmuster ({tage} volle Tage, nötig {SCHWELLEN['woche_min_volle_tage']})")
    r, korr, abstand, korr0 = beste_drehung(v, vorlage)
    ok = korr >= SCHWELLEN["woche_min_korrelation"] and abstand >= SCHWELLEN["woche_min_abstand"]
    werte = {"volle_tage": tage, "korrelation_unverschoben": round(korr0, 2), "beste_drehung_tage": r,
             "korrelation_beste": round(korr, 2), "abstand_zur_zweitbesten": round(abstand, 2)}
    if ok and r == 0:
        return beleg("bestaetigt", f"Wochenmuster passt zu den Kalendertagen (Korrelation {korr:.2f})", **werte)
    if ok:
        return beleg("widerspricht", f"Wochenmuster passt erst, wenn das Datum der Uhr um {r} Tag(e) später liegt als der "
                     f"wahre Tag (Korrelation {korr:.2f})", **werte)
    return beleg("offen", f"Wochenmuster nicht eindeutig (beste Korrelation {korr:.2f}, Abstand {abstand:.2f})", **werte)


def beleg_tagesgang(e, referenz, abdeckung=None):
    if e["profil"] is None:
        return beleg("offen", "zu wenige Fahrzeuge oder Werktage für den Tagesgang")
    if abdeckung is not None and abdeckung < SCHWELLEN["hb_abdeckung_ok"]:
        return beleg("offen", f"Gerät lief nur zu {abdeckung:.0%} der Zeit (Heartbeat), der Tagesgang ist abgeschnitten "
                     "und nicht beurteilbar")
    min_, korr = tagesgang_verschiebung(e["profil"], referenz)
    werte = {"verschiebung_min": min_, "korrelation": round(korr, 2), "werktage": e["werktage"], "zeitbasis": e["zeitbasis"]}
    if korr < SCHWELLEN["tagesgang_struktur_min_korrelation"]:
        return beleg("widerspricht", f"kein erkennbarer Tagesgang (Korrelation {korr:.2f})", **werte)
    if abs(min_) >= SCHWELLEN["tagesgang_widerspruch_min"]:
        return beleg("widerspricht", f"Tagesgang um {min_:+d} Minuten gegenüber dem typischen Verlauf verschoben", **werte)
    if abs(min_) <= SCHWELLEN["tagesgang_bestaetigt_max_min"] and korr >= SCHWELLEN["tagesgang_min_korrelation"]:
        return beleg("bestaetigt", f"Tagesgang entspricht dem typischen Verlauf ({min_:+d} min, Korrelation {korr:.2f})", **werte)
    return beleg("offen", f"Tagesgang weicht etwas ab ({min_:+d} min, Korrelation {korr:.2f})", **werte)


def beleg_zeitumstellung(s, anker):
    """Zwei Pruefungen an jeder Zeitumstellung im Segment: der Tag der Stufe im Verkehrsgang (verankert das Datum)
    und der Restversatz des Tagesgangs nach der Sommerzeit-Korrektur (prueft die Kontinuitaet der Uhr)."""
    pruefungen = s.get("zeitumstellung") or []
    zuverlaessig = [a for a in anker if a["trefferquote"] >= SCHWELLEN["anker_min_trefferquote"]]
    if not pruefungen and not zuverlaessig:
        return beleg("offen", "keine Zeitumstellung im Segment mit genug Daten davor und danach")
    werte = {}
    if pruefungen:
        werte["abweichungen_min"] = {p["datum"]: p["abweichung_min"] for p in pruefungen}
    if anker:
        werte["stufe_im_verkehr"] = {a["datum"]: {"tage_abweichung": a["tage_abweichung"], "trefferquote": a["trefferquote"]}
                                      for a in anker}
    falsch = [a for a in zuverlaessig if abs(a["tage_abweichung"]) > SCHWELLEN["anker_max_tage"]]
    if falsch:
        a = falsch[0]
        return beleg("widerspricht", f"Der Sprung im Verkehrsgang liegt am {a['datum']} um {a['tage_abweichung']:+d} Tage "
                     "neben dem amtlichen Umstellungstag: Datum der Uhr verschoben", **werte)
    schlecht = [p for p in pruefungen if abs(p["abweichung_min"]) >= SCHWELLEN["umstellung_widerspruch_min"]]
    if schlecht:
        p = schlecht[0]
        return beleg("widerspricht", f"Tagesgang springt bei der Zeitumstellung am {p['datum']} um {p['abweichung_min']} Minuten "
                     "(Ferien oder verstellte Uhr)", **werte)
    teile = []
    if zuverlaessig:
        a = zuverlaessig[0]
        teile.append(f"Sprung im Verkehrsgang liegt am amtlichen Umstellungstag {a['datum']} (Abweichung {a['tage_abweichung']:+d} "
                     f"Tage, {a['trefferquote']:.0%} der Tage passen): Datum auf den Tag genau verankert")
    if pruefungen and all(abs(p["abweichung_min"]) <= SCHWELLEN["umstellung_bestaetigt_max_min"] for p in pruefungen):
        teile.append(f"Tagesgang passt über {len(pruefungen)} Zeitumstellung(en) nach der Korrektur")
    if teile:
        return beleg("bestaetigt", "; ".join(teile), **werte)
    return beleg("offen", "Abweichung bei der Zeitumstellung zwischen 30 und 45 Minuten", **werte)


def beleg_ris(namen, s, ris):
    keys = [schluessel(n) for n in namen]
    if not ris or not keys:
        return beleg("offen", "keine Mitteilungen der Verwaltung geladen" if not ris else "Ortsname nicht ableitbar")
    tol = dt.timedelta(days=SCHWELLEN["ris_toleranz_tage"])
    start, ende = s["start"].date(), s["ende"].date()
    genannt = 0
    for dok in ris["dokumente"]:
        if not any(k in dok["_orte"] for k in keys):
            continue
        genannt += 1
        for von, bis in dok["_zeitraeume"]:
            if von - tol <= start and ende <= bis + tol and (abs(start - von) <= tol or abs(ende - bis) <= tol):
                passt = " und ".join(n for n, ok in (("Beginn", abs(start - von) <= tol), ("Ende", abs(ende - bis) <= tol)) if ok)
                name = f"Mitteilung {dok['vorlage']}" if dok["vorlage"] else f"Mitteilung ({dok['betreff']})"
                return beleg("bestaetigt", f"{name} ({dok['gremium']}, {dok['sitzung']}) nennt den Ort und den Zeitraum "
                             f"{von.isoformat()} bis {bis.isoformat()}; {passt} des Abschnitts stimmt(en) auf den Tag überein",
                             quelle=dok["dokument"], zeitraum=[von.isoformat(), bis.isoformat()])
    if genannt:
        return beleg("offen", f"Ort in {genannt} Mitteilung(en) genannt, aber kein Zeitraum passt zum Segment")
    return beleg("offen", "Ort in keiner Mitteilung mit Erfassungszeitraum genannt")


def beleg_kontinuitaet(s, hb_vorhanden):
    n_tage = max((s["ende"] - s["start"]).total_seconds() / 86400, 1e-9)
    werte = {"dauer_tage": round(n_tage, 1), "fahrzeuge": len(s["idx"])}
    hinweise = []
    if hb_vorhanden:
        abdeckung = min(1.0, s["heartbeats"] * 600 / max((s["ende"] - s["start"]).total_seconds(), 1))
        werte["heartbeat_abdeckung"] = round(abdeckung, 2)
        if abdeckung < SCHWELLEN["hb_abdeckung_ok"]:
            hinweise.append(f"Gerät lief nur zu {abdeckung:.0%} der Zeit (Heartbeat), Aufzeichnungslücken")
    if s.get("sprung_min") is not None and s["sprung_min"] <= -5:
        hinweise.append(f"Uhr wurde vor diesem Segment um {-s['sprung_min']} Minuten zurückgestellt")
    return beleg("offen" if hinweise else "bestaetigt", "; ".join(hinweise) or "Heartbeat lückenlos, keine Uhrsprünge", **werte)


# ------------------------------------------------------------------ Urteil

def urteil(s, b, schaetzung):
    """(Urteil, Begruendungen, Art). Regeln siehe Modul-Docstring und docs/uhr-bewertung.md.

    Art (nur bei "eingeschraenkt"): "zurueckgesetzt" (Uhr nach Reset, relative Zeiten nutzbar),
    "widerspruch" (mindestens ein Beleg widerspricht), "unzureichend_belegt" (nichts widerspricht, aber weniger
    als zwei Belege bestaetigen die Zeitstempel).
    """
    n = len(s["idx"])
    gruende = []
    if s["bewertung"] == "ungueltiges_datum":
        return "unbrauchbar", [b["datum"]["text"]], None
    if s["bewertung"] == "werksdatum":
        if n < SCHWELLEN["werksdatum_min_fahrzeuge"]:
            return "unbrauchbar", [b["datum"]["text"], f"nur {n} Fahrzeuge: Datum und Tageszeit nicht rekonstruierbar"], None
        gruende.append(b["datum"]["text"])
        gruende.append("Die Uhr lief nach dem Reset gleichmäßig weiter: relative Zeiten sind nutzbar, Datum, Wochentag und "
                       "Uhrzeit müssen rekonstruiert werden")
        return "eingeschraenkt", gruende, "zurueckgesetzt"
    if b["tagesgang"]["status"] == "widerspricht" and "kein erkennbarer" in b["tagesgang"]["text"]:
        return "unbrauchbar", [b["tagesgang"]["text"]], None
    unabhaengig = ("wochenrhythmus", "tagesgang", "zeitumstellung", "ris")
    ok = [k for k in unabhaengig if b[k]["status"] == "bestaetigt"]
    wider = [k for k in unabhaengig if b[k]["status"] == "widerspricht"]
    if wider:
        gruende += [f"{k}: {b[k]['text']}" for k in wider]
        return "eingeschraenkt", gruende, "widerspruch"
    if len(ok) >= 2:
        gruende += [f"{k}: {b[k]['text']}" for k in ok]
        return "plausibel", gruende, None
    gruende.append(f"nur {len(ok)} von 4 unabhängigen Belegen bestätigt, mindestens 2 nötig; nichts widerspricht")
    gruende += [f"{k}: {b[k]['text']}" for k in ok]
    return "eingeschraenkt", gruende, "unzureichend_belegt"


def gesamturteil(abschnitte):
    """(Urteil, Anteil der Fahrzeuge in plausiblen Abschnitten) fuer eine ganze Datei, None ohne Fahrzeuge.

    plausibel: mindestens 99 % der Fahrzeuge liegen in plausiblen Abschnitten; unbrauchbar: mindestens die Haelfte in
    unbrauchbaren; sonst eingeschraenkt. Regeln in docs/uhr-bewertung.md.
    """
    n = sum(a["fahrzeuge"] for a in abschnitte)
    if not n:
        return None
    anteil = {u: sum(a["fahrzeuge"] for a in abschnitte if a["urteil"] == u) / n for u in URTEILE}
    if anteil["plausibel"] >= SCHWELLEN["gesamt_plausibel_min"]:
        return "plausibel", anteil["plausibel"]
    if anteil["unbrauchbar"] >= SCHWELLEN["gesamt_unbrauchbar_min"]:
        return "unbrauchbar", anteil["plausibel"]
    return "eingeschraenkt", anteil["plausibel"]


# ------------------------------------------------------------------ Ablauf

def lade_ris(pfad):
    if not pfad or not os.path.exists(pfad):
        return None
    ris = json.load(open(pfad, encoding="utf-8"))
    for dok in ris["dokumente"]:
        dok["_orte"] = {schluessel(o) for o in dok["orte"]}
        dok["_zeitraeume"] = [(dt.date.fromisoformat(v), dt.date.fromisoformat(b)) for v, b in dok["zeitraeume"]]
    return ris


def sammle(wurzel):
    """Parst alle DSDs; gibt [(ordner, datei, segmente, veh, hb_vorhanden)] zurueck."""
    ergebnis = []
    for ordner, _, dateien in sorted(os.walk(wurzel)):
        for f in sorted(dateien):
            if not f.lower().endswith(".dsd"):
                continue
            rel = os.path.relpath(ordner, wurzel).replace(os.sep, "/")
            meta, veh, status, warn = d.parse(open(os.path.join(ordner, f), "rb").read())
            segs = d.uhr_segmente(veh, status)
            d.bewerte_segmente(segs, veh)
            # Heartbeat-Abdeckung nur auswerten, wenn die Datei ueberhaupt regelmaessige Heartbeats hat
            # (Geraete mit aelterer Firmware schreiben fast keine 0x33-Records)
            dauer = sum((s["ende"] - s["start"]).total_seconds() for s in segs if s["idx"])
            hb = dauer > 0 and sum(s["heartbeats"] for s in segs if s["idx"]) * 600 / dauer >= 0.3
            ergebnis.append((rel, f, segs, veh, hb))
    return ergebnis


def merkmale(s, veh):
    """Rohmerkmale eines Segments fuer Wochen- und Tagesgang-Belege."""
    e = {"wochenvektor": None, "volle_tage": 0, "profil": None, "werktage": 0, "zeitbasis": None}
    if not s["idx"] or s["bewertung"] == "ungueltiges_datum":
        return e
    zeiten, e["zeitbasis"] = segment_zeiten(s, veh)
    e["wochenvektor"], e["volle_tage"] = wochenvektor(zeiten, s["start"], s["ende"])
    if len(zeiten) >= SCHWELLEN["tagesgang_min_fahrzeuge"]:
        profil, werktage = d.tagesgang(zeiten)
        if profil is not None and werktage >= SCHWELLEN["tagesgang_min_werktage"]:
            e["profil"], e["werktage"] = profil, werktage
    return e


def referenzen(alle):
    """Typische Woche und typischer Tagesgang aus den Segmenten, deren Wochenrhythmus eindeutig stimmt."""
    kandidaten = [e for e in alle if e["wochenvektor"] is not None]
    vorlage = [sorted(e["wochenvektor"][i] for e in kandidaten)[len(kandidaten) // 2] for i in range(7)]
    gut = kandidaten
    for _ in range(3):
        gut = [e for e in kandidaten if beste_drehung(e["wochenvektor"], vorlage)[0] == 0
               and beste_drehung(e["wochenvektor"], vorlage)[3] >= SCHWELLEN["woche_referenz_korrelation"]]
        vorlage = [sorted(e["wochenvektor"][i] for e in gut)[len(gut) // 2] for i in range(7)]
    ref = [e for e in gut if e["profil"] is not None and e["zeitbasis"] == "ortszeit"]
    summe = [sum(e["profil"][i] for e in ref) for i in range(96)]
    return vorlage, summe, ref


BELEG_NAMEN = [("datum", "Datum"), ("wochenrhythmus", "Wochenrhythmus"), ("tagesgang", "Tagesgang"),
               ("zeitumstellung", "Zeitumstellung"), ("ris", "Mitteilungen der Verwaltung"), ("kontinuitaet", "Kontinuität")]
STATUS_TEXT = {"bestaetigt": "bestätigt", "widerspricht": "widerspricht", "offen": "offen"}
MIN_FAHRZEUGE_DETAIL = 50  # kleinere Abschnitte werden nur gezaehlt


def zahl(n):
    return f"{n:,}".replace(",", ".")


def schreibe_analyse(dateien, wurzel):
    """Je Standortordner eine Datei uhr-analyse.md mit allen Abschnitten, Urteilen und Belegen (neben den DSD-Dateien)."""
    je_standort = collections.defaultdict(list)
    for dd in dateien.values():
        je_standort[dd["standort"]].append(dd)
    for standort, liste in je_standort.items():
        z = [f"# Geräteuhr: {standort}", "",
             "Eigene Berechnung, nicht amtlich; Fehler in der Auswertung können nicht ausgeschlossen werden, alle Angaben ohne Gewähr. "
             "Erzeugt von `uhr_belege.py` aus den DSD-Dateien und den Mitteilungen der Verwaltung. Alle Zeiten sind "
             "Gerätezeit, wie in der CSV. Urteil und Belege sind Ergebnis des Skripts, Schwellen und Regeln stehen "
             "in `uhr_belege.py` und `docs/uhr-bewertung.md`.", ""]
        for dd in sorted(liste, key=lambda x: x["datei"]):
            z += [f"## {dd['datei']}", ""]
            gross = [a for a in dd["abschnitte"] if a["fahrzeuge"] >= MIN_FAHRZEUGE_DETAIL]
            klein = [a for a in dd["abschnitte"] if a["fahrzeuge"] < MIN_FAHRZEUGE_DETAIL]
            if not dd["abschnitte"]:
                z += ["Die Datei enthält keine Fahrzeugdaten.", ""]
                continue
            summe = collections.Counter()
            for a in dd["abschnitte"]:
                summe[a["urteil"]] += a["fahrzeuge"]
            gesamt = sum(summe.values())
            z += [f"{zahl(gesamt)} Fahrzeuge in {len(dd['abschnitte'])} Abschnitt(en): " +
                  ", ".join(f"{zahl(summe[u])} {u}" for u in URTEILE if summe[u]) + ".", ""]
            z += ["| Abschnitt (Gerätezeit) | Fahrzeuge | Urteil |", "|---|---:|---|"]
            for a in gross:
                z.append(f"| {a['start'][:16]} bis {a['ende'][:16]} | {zahl(a['fahrzeuge'])} | {a['urteil']} |")
            if klein:
                z.append(f"| {len(klein)} weitere Abschnitte | {zahl(sum(a['fahrzeuge'] for a in klein))} | "
                         f"{', '.join(sorted({a['urteil'] for a in klein}))} |")
            z.append("")
            for a in gross:
                art = f", {a['art'].replace('_', ' ')}" if a.get("art") else ""
                z += [f"### {a['start'][:16]} bis {a['ende'][:16]}: {a['urteil']}{art} ({zahl(a['fahrzeuge'])} Fahrzeuge)", ""]
                z += [f"- Begründung: {g}" for g in a["begruendung"]]
                z += ["- Belege:"]
                for key, name in BELEG_NAMEN:
                    b = a["belege"][key]
                    z.append(f"  - {name}: {STATUS_TEXT[b['status']]}. {b['text']}" +
                             (f" Quelle: <{b['quelle']}>" if b.get("quelle") else ""))
                if a.get("schaetzung"):
                    sch = a["schaetzung"]
                    teile = []
                    if "wochentag_versatz_tage" in sch:
                        teile.append(f"Datum der Uhr {sch['wochentag_versatz_tage']} Tag(e) hinter dem wahren Tag (mod 7)")
                    if "tageszeit_abweichung_min" in sch:
                        teile.append(f"Tageszeit {sch['tageszeit_abweichung_min']:+d} Minuten (positiv: Uhr geht vor)")
                    z.append(f"- Schätzung, nicht angewendet: {'; '.join(teile)}")
                z.append("")
        ziel = os.path.join(wurzel, *standort.split("/"), "uhr-analyse.md")
        os.makedirs(os.path.dirname(ziel), exist_ok=True)
        with open(ziel, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(z).rstrip() + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("eingabe", help="Ordner mit den DSD-Dateien")
    ap.add_argument("--ris", default="belege/ris.json")
    ap.add_argument("--out", default="belege/uhr-bewertung.json")
    ap.add_argument("--analyse", help="Wurzel fuer die Analyse-Texte (Standard: neben den DSD-Dateien)")
    a = ap.parse_args()

    daten = sammle(a.eingabe)
    ris = lade_ris(a.ris)
    alle = []
    for rel, f, segs, veh, hb in daten:
        for s in segs:
            s["_e"] = merkmale(s, veh)
            alle.append(s["_e"])
    vorlage, ref_summe, ref_segmente = referenzen(alle)
    print(f"Referenz: {len(ref_segmente)} Segmente; typische Woche Mo..So: " + " ".join(f"{x:.2f}" for x in vorlage), file=sys.stderr)

    dateien = {}
    for rel, f, segs, veh, hb in daten:
        abschnitte = []
        for s in segs:
            if not s["idx"]:
                continue
            e = s["_e"]
            if e["profil"] is not None:  # Referenz ohne das Segment selbst
                eigen = any(e is r for r in ref_segmente)
                n_ref = len(ref_segmente) - (1 if eigen else 0)
                referenz = [(ref_summe[i] - (e["profil"][i] if eigen else 0)) / n_ref for i in range(96)]
            b = {"datum": beleg_datum(s)}
            b["wochenrhythmus"] = beleg_wochenrhythmus(e, vorlage)
            b["kontinuitaet"] = beleg_kontinuitaet(s, hb)
            b["tagesgang"] = beleg_tagesgang(e, referenz if e["profil"] is not None else None,
                                             b["kontinuitaet"].get("heartbeat_abdeckung"))
            anker = []
            if s["bewertung"] in ("gueltig", "auffaellig") and len(s["idx"]) >= SCHWELLEN["tagesgang_min_fahrzeuge"]:
                anker = zeitumstellung_anker([veh[i][0] for i in s["idx"]], s["start"], s["ende"])
            b["zeitumstellung"] = beleg_zeitumstellung(s, anker)
            b["ris"] = beleg_ris(messort_namen(rel), s, ris) if s["bewertung"] in ("gueltig", "auffaellig") else \
                beleg("offen", "Datum der Uhr nicht verwertbar")
            schaetzung = {}
            if b["wochenrhythmus"].get("beste_drehung_tage") and b["wochenrhythmus"]["status"] == "widerspricht":
                schaetzung["wochentag_versatz_tage"] = b["wochenrhythmus"]["beste_drehung_tage"]
            if b["tagesgang"].get("verschiebung_min") is not None and b["tagesgang"]["status"] != "bestaetigt":
                schaetzung["tageszeit_abweichung_min"] = b["tagesgang"]["verschiebung_min"]
            u, gruende, art = urteil(s, b, schaetzung)
            abschnitt = {"start": s["start"].isoformat(sep=" "), "ende": s["ende"].isoformat(sep=" "),
                         "fahrzeuge": len(s["idx"]), "urteil": u, "art": art, "begruendung": gruende, "belege": b}
            if schaetzung:
                abschnitt["schaetzung"] = schaetzung
            abschnitte.append(abschnitt)
        dateien[f"{rel}/{f}"] = {"standort": rel, "datei": f, "abschnitte": abschnitte}

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"erzeugt_von": "uhr_belege.py", "schwellen": SCHWELLEN,
                   "referenz": {"segmente": len(ref_segmente), "typische_woche_mo_bis_so": [round(x, 3) for x in vorlage]},
                   "ris_dokumente": len(ris["dokumente"]) if ris else 0, "dateien": dateien},
                  fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    schreibe_analyse(dateien, a.analyse or a.eingabe)
    zaehler = collections.Counter()
    fahrzeuge = collections.Counter()
    for dd in dateien.values():
        for ab in dd["abschnitte"]:
            zaehler[ab["urteil"]] += 1
            fahrzeuge[ab["urteil"]] += ab["fahrzeuge"]
    for u in URTEILE:
        print(f"{u:15s} {zaehler[u]:4d} Abschnitte, {fahrzeuge[u]:9d} Fahrzeuge", file=sys.stderr)
    arten = collections.Counter()
    for dd in dateien.values():
        for ab in dd["abschnitte"]:
            if ab["urteil"] == "eingeschraenkt":
                arten[ab["art"]] += ab["fahrzeuge"]
    for art, n in arten.most_common():
        print(f"  eingeschraenkt, {art}: {n} Fahrzeuge", file=sys.stderr)


if __name__ == "__main__":
    main()
