# SPDX-License-Identifier: MIT
"""Rekonstruktion zurueckgesetzter Geraeteuhren (docs/einsaetze.md, Abschnitt "Uhr-Rekonstruktion").

Hypothese je Uhr-Segment mit zurueckgesetzter Uhr (dsd2csv.bewerte_segmente: Standarddatum 2020-01-01 12:00, "werksdatum"): Die Uhr begann
beim Einschalten bei 2020-01-01 12:00 und lief gleichmaessig weiter, ohne Sommerzeit. Echte Zeit (UTC) = Geraetezeit + Delta.

Gesucht wird Delta. Kandidaten: Phase (Wochentag und Uhrzeit des Beginns) aus Wochenmuster und Tagesgang in der ersten Woche nach dem Abbau
(letzter gueltiger Eintrag davor in derselben Datei), dann je 7 Tage weiter (je 1 Tag, wenn das Wochenmuster den Wochentag nicht festlegt) bis
zur naechsten gueltigen Aufzeichnung; dazu immer der Endanker. Je Kandidat:
  Anker (legen die Lage fest, unabhaengig voneinander):
    Beginn an Montagetag           das Einschalten faellt auf einen Tag, an dem ein Geraet sicher montiert wurde (bewegungen.py, erster Lauf)
    Ende an Auslese-Runde          das Ende faellt auf einen Tag, an dem mindestens AUSLESE_MIN_GERAETE Geraete eine Dateigrenze haben
    Ende am Exportdatum            das Ende faellt auf das Datum im Dateinamen (+-1 Tag)
    Ende an naechster Aufzeichnung die naechste gueltige Aufzeichnung desselben Geraets beginnt direkt nach dem letzten Fahrzeug (+-3 h)
    Zeitumstellung                 der Tagesgang springt in Geraetezeit am amtlichen Umstellungstag (+-1 Tag) um eine Stunde
  Proben (duerfen nicht widersprechen): Wochenmuster (ohne Ferien und Feiertage) auf den richtigen Wochentagen, Werktags-Tagesgang hoechstens
  TAGESGANG_OK Minuten neben dem typischen Verlauf.
Entscheidung: belegt (mindestens zwei Anker, kein anderer Kandidat ebenso viele), wahrscheinlich (ein Anker, Wochenmuster und Tagesgang
bestaetigt, kein anderer Kandidat mit Anker und bestaetigtem Wochenmuster), sonst offen. Segmente kuerzer als MIN_TAGE oder mit weniger als
MIN_FAHRZEUGE (taeglich neu gestartete Uhr, z.B. leerer Akku) werden nicht rekonstruiert.

Reines Python; die Segmente liefert bewegungen.py."""
import collections
import datetime as dt
import re

import dsd2csv as d
import kalender
import uhr_belege as ub

MIN_TAGE = 2.0
MIN_FAHRZEUGE = 500
MAX_ENDE_TAGE = 120
TAGESGANG_OK = 60
UMSTELLUNG_SUCHE = 10   # Tage um die amtliche Umstellung, in denen der Sprung gesucht wird
AUSLESE_MIN_GERAETE = 3
ENDE_TOLERANZ = dt.timedelta(hours=3)
TAG = dt.timedelta(days=1)


def lokal(utc):
    return utc + dt.timedelta(hours=d.utc_versatz_h(utc))


def dateidatum(name):
    """Datum aus dem Dateinamen: 23_05_04_... (JJ_MM_TT) oder 2023_07_19_... (JJJJ_MM_TT); sonst None."""
    m = re.match(r"(20\d\d)_(\d\d)_(\d\d)", name) or re.match(r"(\d\d)_(\d\d)_(\d\d)_", name)
    if not m:
        return None
    j, mo, t = (int(x) for x in m.groups())
    try:
        return dt.date(j if j > 2000 else 2000 + j, mo, t)
    except ValueError:
        return None


def segment(rel, datei, nr, s, veh):
    """Beschreibung eines Uhr-Segments fuer die Rekonstruktion (gueltige Segmente mit UTC-Spanne)."""
    zeiten = [veh[i][0] for i in s["idx"]]
    x = {"rel": rel, "datei": datei, "nr": nr, "erster_index": s["idx"][0], "n": len(s["idx"]), "bewertung": s.get("bewertung"),
         "geraet_von": min(zeiten), "geraet_bis": max(zeiten), "zeiten": zeiten}
    if s.get("bewertung") == "gueltig":
        versatz = dt.timedelta(hours=s["utc_versatz_h"])
        x["utc_von"], x["utc_bis"] = x["geraet_von"] - versatz, x["geraet_bis"] - versatz
    return x


def umstellungs_tag(zeiten, kandidaten_index):
    """(Index des Geraete-Tags ab dem ersten Tag, Sprung in Minuten, Guete), an dem der Tagesgang um etwa eine Stunde springt; nur die Tage
    kandidaten_index werden geprueft (Ferienbeginne verschieben den Tagesgang auch). None ohne klaren Sprung."""
    t0 = min(zeiten).date()
    profile = ub._tagesprofile(zeiten)
    tage = sorted(t for t in profile if sum(profile[t]) >= 100)
    if len(tage) < 20:
        return None
    best = None
    for i in range(7, len(tage) - 7):
        if (tage[i] - t0).days not in kandidaten_index:
            continue
        pv = [sum(profile[t][k] for t in tage[max(0, i - 21):i]) for k in range(96)]
        pn = [sum(profile[t][k] for t in tage[i:i + 21]) for k in range(96)]
        lag = max(range(-8, 9), key=lambda k: d._pearson([pv[(j - k) % 96] for j in range(96)], pn))
        guete = d._pearson([pv[(j - lag) % 96] for j in range(96)], pn) - d._pearson(pv, pn)
        if abs(abs(lag) * 15 - 60) <= 15 and (best is None or guete > best[2]):
            best = ((tage[i] - t0).days, lag * 15, guete)
    return best if best and best[2] > 0.005 else None


def wochenvektor_normal(zeiten):
    """Wie uhr_belege.wochenvektor, aber ohne Ferien- und Feiertage (sie verwischen das Wochenmuster) und ohne den ersten und letzten Tag."""
    zaehler = collections.Counter(t.date() for t in zeiten)
    erster, letzter = min(zaehler), max(zaehler)
    summe, tage = [0] * 7, [0] * 7
    tag = erster + TAG
    while tag < letzter:
        if not kalender.besonderer_tag(tag):
            summe[tag.weekday()] += zaehler.get(tag, 0)
            tage[tag.weekday()] += 1
        tag += TAG
    if sum(tage) < ub.SCHWELLEN["woche_min_volle_tage"] or min(tage) < 3:
        return None
    m = [summe[i] / tage[i] for i in range(7)]
    mittel = sum(m) / 7
    return [x / mittel for x in m] if mittel else None


def proben(seg, delta, vorlage, referenz, abbau):
    """Beginn und Ende (Ortszeit) und Proben fuer ein Delta."""
    utc = [t + delta for t in seg["zeiten"]]
    lok = [lokal(u) for u in utc]
    out = {"beginn": lokal(min(utc)), "ende": lokal(max(utc)), "pause_seit_abbau_h": round((min(utc) - abbau).total_seconds() / 3600, 1)}
    v = wochenvektor_normal(lok)
    if v:
        r, korr, abstand, korr0 = ub.beste_drehung(v, vorlage)
        out["woche"] = {"drehung": r, "korrelation": round(korr0, 2), "abstand": round(abstand, 2),
                        "status": "bestaetigt" if r == 0 and korr >= 0.75 and abstand >= 0.25 else "widerspricht" if r and abstand >= 0.25 else "offen"}
    prof, werktage = d.tagesgang(lok)
    if prof and werktage >= 5:
        minuten, korr = ub.tagesgang_verschiebung(prof, referenz)
        out["tagesgang"] = {"verschiebung_min": minuten, "korrelation": round(korr, 2),
                            "status": "bestaetigt" if abs(minuten) <= TAGESGANG_OK and korr >= 0.9 else "widerspricht" if abs(minuten) >= 90 else "offen"}
    t0, t1 = (seg["geraet_von"] + delta).date(), (seg["geraet_bis"] + delta).date()
    for jahr in range(t0.year, t1.year + 1):
        for monat in (3, 10):
            amtlich = d.letzter_sonntag(jahr, monat)
            if not t0 + 7 * TAG <= amtlich <= t1 - 7 * TAG:
                continue
            mitte = (amtlich - t0).days
            sprung = umstellungs_tag(seg["zeiten"], set(range(mitte - UMSTELLUNG_SUCHE, mitte + UMSTELLUNG_SUCHE + 1)))
            if not sprung:
                out["umstellung"] = {"amtlich": amtlich.isoformat(), "status": "offen"}
                continue
            tag = t0 + dt.timedelta(days=sprung[0])
            out["umstellung"] = {"sprung_tag": tag.isoformat(), "sprung_min": sprung[1], "amtlich": amtlich.isoformat(),
                                 "status": "bestaetigt" if abs((tag - amtlich).days) <= 1 else "widerspricht"}
    return out


def auslese_runden(je):
    """Tage, an denen mindestens AUSLESE_MIN_GERAETE Geraete eine Grenze gueltiger Daten einer Datei haben (Beginn oder Ende)."""
    schnitte = collections.defaultdict(set)
    for g, abschnitte in je.items():
        je_datei = collections.defaultdict(list)
        for a in abschnitte:
            if "utc_von" in a:
                je_datei[(a["rel"], a["datei"])].append(a)
        for teile in je_datei.values():
            schnitte[lokal(min(a["utc_von"] for a in teile)).date()].add(g)
            schnitte[lokal(max(a["utc_bis"] for a in teile)).date()].add(g)
    return {t for t, gs in schnitte.items() if len(gs) >= AUSLESE_MIN_GERAETE}


def kandidaten(seg, abbau, naechste, vorlage, referenz, runden, montagetage):
    """Delta-Kandidaten mit ihren Ankern und Proben (siehe Modulkopf)."""
    dauer = seg["geraet_bis"] - seg["geraet_von"]
    delta_e = naechste - seg["geraet_bis"] if naechste else None
    datum = dateidatum(seg["datei"])
    beste = (-2.0, delta_e) if delta_e is not None else None
    for j in range(7):
        delta0 = dt.datetime.combine((abbau + j * TAG).date(), dt.time(0)) - seg["geraet_von"]
        prof, werktage = d.tagesgang([lokal(t + delta0) for t in seg["zeiten"]])
        if not prof or werktage < 5:
            continue
        minuten, _ = ub.tagesgang_verschiebung(prof, referenz)
        delta = delta0 - dt.timedelta(minutes=minuten)
        if seg["geraet_von"] + delta < abbau:
            delta += 7 * TAG
        woche = proben(seg, delta, vorlage, referenz, abbau).get("woche") or {}
        r = woche.get("korrelation", -1) if woche.get("drehung") == 0 else -1
        if beste is None or r > beste[0]:
            beste = (r, delta)
    if not beste:
        return []
    schritt = (7 if beste[0] >= ub.SCHWELLEN["woche_min_korrelation"] else 1) * TAG
    delta = beste[1]
    while seg["geraet_von"] + delta - schritt >= abbau:
        delta -= schritt
    grenze = naechste or abbau + MAX_ENDE_TAGE * TAG
    deltas = []
    while seg["geraet_von"] + delta + dauer <= grenze + dt.timedelta(hours=2):
        deltas.append(delta)
        delta += schritt
    # der Endanker ist immer ein Kandidat (die Tagesgang-Schaetzung kann um Stunden daneben liegen, etwa bei schwachem Verkehr)
    if delta_e is not None and seg["geraet_von"] + delta_e >= abbau and not any(abs(x - delta_e) <= ENDE_TOLERANZ for x in deltas):
        deltas.append(delta_e)
    out = []
    for delta in sorted(deltas):
        p = proben(seg, delta, vorlage, referenz, abbau)
        anker = []
        if p["beginn"].date() in montagetage:
            anker.append("Beginn an Montagetag")
        if p["ende"].date() in runden:
            anker.append("Ende an Auslese-Runde")
        if datum and abs((p["ende"].date() - datum).days) <= 1:
            anker.append("Ende am Exportdatum")
        if delta_e is not None and abs(delta - delta_e) <= ENDE_TOLERANZ:
            anker.append("Ende an nächster Aufzeichnung")
        if (p.get("umstellung") or {}).get("status") == "bestaetigt":
            anker.append("Zeitumstellung")
        out.append({"delta": delta, "beginn": p["beginn"], "ende": p["ende"], "anker": anker, "proben": p})
    return out


def entscheiden(kand):
    """(Kandidat, Stufe) nach dem Modulkopf; ohne Entscheidung (None, 'offen')."""
    def status(c, k):
        return (c["proben"].get(k) or {}).get("status")

    gut = [c for c in kand if status(c, "woche") != "widerspricht" and status(c, "tagesgang") != "widerspricht"]
    if not gut:
        return None, "offen"
    best = max(gut, key=lambda c: (len(c["anker"]), (c["proben"].get("woche") or {}).get("korrelation", -1)))
    rivalen = [c for c in gut if c is not best]
    if len(best["anker"]) >= 2 and not any(len(c["anker"]) >= len(best["anker"]) for c in rivalen):
        return best, "belegt"
    if (len(best["anker"]) == 1 and status(best, "woche") == "bestaetigt" and status(best, "tagesgang") == "bestaetigt"
            and not any(c["anker"] and status(c, "woche") == "bestaetigt" for c in rivalen)):
        return best, "wahrscheinlich"
    return None, "offen"


def rekonstruieren(je, vorlage, referenz, montagetage):
    """Entscheidungen fuer alle Segmente mit zurueckgesetzter Uhr. je: {Geraet: [segment(...)]} aller Dateien des Geraets, montagetage:
    Menge der Tage mit sicherer Montage. Gibt [dict(geraet, rel, datei, abschnitt, fahrzeuge, tage, stufe, delta_s, beginn, ende, anker,
    proben, kandidaten)] zurueck; delta_s, beginn, ende nur bei belegt oder wahrscheinlich."""
    runden = auslese_runden(je)
    out = []
    for g in sorted(je):
        abschnitte = je[g]
        gueltig = [a for a in abschnitte if "utc_von" in a]
        for seg in (a for a in abschnitte if a["bewertung"] == "werksdatum"):
            tage = (seg["geraet_bis"] - seg["geraet_von"]).total_seconds() / 86400
            erg = {"geraet": g, "rel": seg["rel"], "datei": seg["datei"], "abschnitt": seg["nr"], "fahrzeuge": seg["n"], "tage": round(tage, 1)}
            out.append(erg)
            if tage < MIN_TAGE or seg["n"] < MIN_FAHRZEUGE:
                erg.update(stufe="nicht_rekonstruiert", grund="zu kurz (Uhr täglich neu gestartet?)")
                continue
            selbe = [a for a in gueltig if (a["rel"], a["datei"]) == (seg["rel"], seg["datei"])]
            # Abbau: letzter gueltiger Eintrag davor in derselben Datei; ohne ihn bleibt die Lage in der Zeit unbekannt
            abbau = max((a["utc_bis"] for a in selbe if a["erster_index"] < seg["erster_index"]), default=None)
            if abbau is None:
                erg.update(stufe="offen", grund="kein gültiger Eintrag davor in derselben Datei")
                continue
            naechste = min((a["utc_von"] for a in selbe if a["erster_index"] > seg["erster_index"]), default=None)
            if naechste is None:
                naechste = min((a["utc_von"] for a in gueltig if a["utc_von"] > abbau and (a["rel"], a["datei"]) != (seg["rel"], seg["datei"])),
                               default=None)
            kand = kandidaten(seg, abbau, naechste, vorlage, referenz, runden, montagetage)
            best, stufe = entscheiden(kand)
            erg.update(stufe=stufe, abbau=lokal(abbau).isoformat(), naechste_aufzeichnung=lokal(naechste).isoformat() if naechste else None,
                       kandidaten=[{"beginn": c["beginn"].isoformat(), "ende": c["ende"].isoformat(), "anker": c["anker"]} for c in kand if c["anker"]])
            if best:
                erg.update(delta_s=best["delta"].total_seconds(), beginn=best["beginn"].isoformat(), ende=best["ende"].isoformat(),
                           anker=best["anker"], proben={k: v for k, v in best["proben"].items() if k in ("woche", "tagesgang", "umstellung")})
    return out
