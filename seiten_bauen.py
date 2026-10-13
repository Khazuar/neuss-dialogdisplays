# SPDX-License-Identifier: MIT
"""Baut je Standortordner eine Detailseite (standorte/<name>.html) fuer die GitHub Pages.

Aufruf (nach dsd2csv.py, das auswertung.json schreibt):
  python3 -I seiten_bauen.py --auswertung _site/auswertung.json --ziel _site

Eingaben:
  auswertung.json          Kennzahlen je DSD-Datei (dsd2csv.py)
  belege/metadaten.json    Angaben der Verwaltung und Geraete-Konfiguration (metadaten.py)
  belege/uhr-bewertung.json  Urteil zur Geraeteuhr je Abschnitt (uhr_belege.py)
  belege/neuss-adressen.csv  Hauskoordinaten fuer die Lageskizze (tools/adressen_laden.py), optional

Die Seiten sind statisches HTML ohne Verbindungen zu anderen Servern. Nur die Auswahl nach Zeit, Tagen und Gruppe braucht
ein kleines eigenes Skript (site/filter.js), das ausschliesslich die eingebettete Datentabelle liest. Alle Texte aus den
Daten werden maskiert. Der Wortlaut der Verwaltung steht als Auszug da; massgeblich ist das verlinkte Dokument.
"""
import argparse
import collections
import datetime
import html
import json
import math
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I nimmt das Skriptverzeichnis nicht auf
import gruppen  # noqa: E402
import standorte  # noqa: E402
from dsd2csv import aufprall_kmh, standort_slug  # noqa: E402
from uhr_belege import gesamturteil  # noqa: E402

REPO = "https://github.com/Khazuar/neuss-dialogdisplays"
MIN_FAHRZEUGE_ABSCHNITT = 2000  # kleinere Uhr-Abschnitte werden zusammengefasst

EINSTUFUNG = {
    "voellig_unkritisch": ("völlig unkritisch", "ok"), "unkritisch": ("unkritisch", "ok"), "unauffaellig": ("unauffällig", "ok"),
    "noch_akzeptabel": ("noch akzeptabel", "mid"), "ueberdurchschnittlich_hoch": ("überdurchschnittlich hoch", "bad"),
    "deutlich_zu_hoch": ("deutlich zu hoch", "bad"), "ueberhoeht": ("überhöht", "bad"),
}
URTEIL = {"plausibel": "ok", "eingeschraenkt": "mid", "unbrauchbar": "bad"}
URTEIL_TEXT = {"plausibel": "plausibel", "eingeschraenkt": "eingeschränkt", "unbrauchbar": "unbrauchbar"}
ART_TEXT = {"unzureichend_belegt": "nicht ausreichend belegt", "widerspruch": "Widerspruch in den Belegen",
            "zurueckgesetzt": "Uhr zurückgesetzt (Standarddatum 2020-01-01)"}
ZEITRAEUME = [("alle", "Alle ausgewerteten Fahrzeuge"), ("bereinigt", "Nur Fahrzeuge mit nutzbarer Zeit"),
              ("nacht", "Nacht (22–6 Uhr)"), ("vormittag", "Vormittag (6–12 Uhr)"), ("nachmittag", "Nachmittag (12–19 Uhr)"),
              ("abend", "Abend (19–22 Uhr)"), ("schulweg", "Schulweg (Mo–Fr, 7–8 Uhr)")]
METHODE_TEXT = {
    "name_zeitraum": "über Straßenname und Erfassungszeitraum",
    "name_werte": "über Straßenname, Sitzungsdatum und die Werte der DSD-Datei (Abgleich nicht unabhängig)",
    "name_werte_zeitraum_abweichend": "über Straßenname und die Werte der DSD-Datei; der genannte Zeitraum passt nicht (Abgleich nicht unabhängig)",
    "name_einzige_datei": "nur über Straßenname und Sitzungsdatum, es kommt keine andere Datei in Frage",
}


# ------------------------------------------------------------------ Formatierung

def e(x):
    return html.escape("" if x is None else str(x), quote=True)


def ganz(n):
    return f"{n:,}".replace(",", ".") if isinstance(n, int) else "–"


def dez(x, stellen=1):
    return f"{x:.{stellen}f}".replace(".", ",") if isinstance(x, (int, float)) else "–"


def iso_de(s):
    """'2025-10-26' -> '26.10.2025'"""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s or "")
    return f"{m.group(3)}.{m.group(2)}.{m.group(1)}" if m else (s or "–")


def zeit_de(s):
    """'2025-10-26 08:38:52' -> '26.10.2025 08:38'"""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})", s or "")
    return f"{m.group(3)}.{m.group(2)}.{m.group(1)} {m.group(4)}:{m.group(5)}" if m else (s or "–")


def bereinige(ordner):
    """'07_2024_ Einsteinstraße' -> 'Einsteinstraße', 'Stationär_Villestraße/FR GV' -> 'Stationär Villestraße / FR GV'"""
    teile = []
    for i, t in enumerate(ordner.split("/")):
        t = re.sub(r"^\d+(?:[-_]\d{4})?_\s*" if i == 0 else r"^\d{4}_", "", t)
        teile.append(t.replace("_", " ").strip())
    return " / ".join(teile)


def quote_pfad(p):
    return urllib.parse.quote(p, safe="/")


def klasse_quote(x):
    return "" if not isinstance(x, (int, float)) else (" bad" if x < 50 else " mid" if x < 75 else "")


def badge(text, art):
    return f'<span class="badge {art}">{e(text)}</span>'


# ------------------------------------------------------------------ Bausteine

def kennzahlen_tabelle(row, abschnitt=False):
    """Tabelle der Kennzahlen: alle Fahrzeuge, bereinigt und die Teilzeiträume (bei einem Abschnitt der Messung nur Fahrzeuge mit nutzbarer Zeit)."""
    quellen = {"alle": row, "bereinigt": row.get("bereinigt") or {}, **(row.get("teilzeitraeume") or {})}
    zeilen = []
    for key, label in ZEITRAEUME:
        if abschnitt and key == "bereinigt":
            continue
        if abschnitt and key == "alle":
            label = "Alle Fahrzeuge des Abschnitts (nutzbare Zeit)"
        q = quellen.get(key) or {}
        n = q.get("anzahl_fahrzeuge")
        g, h = q.get("geschwindigkeit_kmh") or {}, q.get("einhaltung") or {}
        if not n:
            zeilen.append(f'<tr><th scope="row">{e(label)}</th><td class="num">0</td><td colspan="6" class="muted">keine Fahrzeuge</td></tr>')
            continue
        qu, qq = h.get("einhaltungsquote_prozent"), h.get("qualifizierte_einhaltungsquote_prozent")
        zeilen.append(
            f'<tr><th scope="row">{e(label)}</th><td class="num">{ganz(n)}</td><td class="num">{dez(g.get("mittel"))}</td>'
            f'<td class="num">{ganz(g.get("v85"))}</td><td class="num">{ganz(g.get("v95"))}</td><td class="num">{ganz(g.get("v99"))}</td>'
            f'<td class="num{klasse_quote(qu)}">{dez(qu, 2)}&nbsp;%</td><td class="num{klasse_quote(qq)}">{dez(qq, 2)}&nbsp;%</td></tr>')
    return ('<div class="tablewrap"><table><caption class="muted">Kennzahlen dieser Messung nach Zeitraum, '
            'Tageszeiten in Ortszeit</caption><thead><tr><th>Zeitraum</th><th class="num">Fahrzeuge</th><th class="num">Ø km/h</th>'
            '<th class="num">V85</th><th class="num">V95</th><th class="num">V99</th><th class="num">Einhaltung</th>'
            '<th class="num">Qualifiziert</th></tr></thead><tbody>' + "".join(zeilen) + "</tbody></table></div>")


def uhr_abschnitt(row, abschnitte, rel):
    uhr = row.get("uhr") or {}
    ges = gesamturteil(abschnitte)
    if ges:
        bew, anteil = ges
        kopf = (f'{badge("Uhr " + URTEIL_TEXT[bew], URTEIL[bew])} {dez(100 * anteil, 1)}&nbsp;% der Fahrzeuge liegen in Abschnitten, '
                'deren Uhr anhand von Belegen als plausibel gelten kann (Tabelle unten).')
    else:
        kopf = "Für diese Datei liegt keine Prüfung der Uhr anhand von Belegen vor."
    nutzbar = {"nutzbar": "nutzbar", "teilweise_nutzbar": "teilweise nutzbar", "nicht_nutzbar": "nicht nutzbar"}.get(uhr.get("nutzbarkeit"))
    z = [f'<h4>Geräteuhr</h4><p>{kopf}</p>']
    if nutzbar:
        z.append(f'<p>Zeitstempel für die Auswertung nach Tageszeit: <strong>{nutzbar}</strong> '
                 f'({dez(uhr.get("fahrzeuge_mit_nutzbarer_zeit_prozent"), 1)}&nbsp;% der Fahrzeuge, kein Reset, keine Datumssprünge, '
                 'kein Versatz um Stunden). Das ist eine formale Prüfung und sagt nicht, dass die Uhrzeit stimmt; '
                 'das zeigen nur die Belege in der Tabelle.</p>')
    if uhr.get("hinweise"):
        z.append("<ul>" + "".join(f"<li>{e(h)}</li>" for h in uhr["hinweise"]) + "</ul>")
    gross = [a for a in abschnitte if a["fahrzeuge"] >= MIN_FAHRZEUGE_ABSCHNITT]
    klein = [a for a in abschnitte if a["fahrzeuge"] < MIN_FAHRZEUGE_ABSCHNITT]
    if gross or klein:
        zeilen = []
        for a in gross:
            art = ART_TEXT.get(a.get("art"), "") if a["urteil"] == "eingeschraenkt" else ""
            gruende = "".join(f"<li>{e(g)}</li>" for g in a.get("begruendung", []))
            zeilen.append(
                f'<tr><td>{e(zeit_de(a["start"]))} bis {e(zeit_de(a["ende"]))}</td><td class="num">{ganz(a["fahrzeuge"])}</td>'
                f'<td>{badge(URTEIL_TEXT[a["urteil"]], URTEIL[a["urteil"]])}{" – " + e(art) if art else ""}'
                f'{"<details><summary>Begründung</summary><ul>" + gruende + "</ul></details>" if gruende else ""}</td></tr>')
        if klein:
            urteile = ", ".join(sorted({URTEIL_TEXT[a["urteil"]] for a in klein}))
            zeilen.append(f'<tr><td>{len(klein)} weitere kurze Abschnitte</td><td class="num">{ganz(sum(a["fahrzeuge"] for a in klein))}</td>'
                          f'<td>{e(urteile)}</td></tr>')
        z.append('<div class="tablewrap"><table><caption class="muted">Abschnitte der Aufzeichnung (Gerätezeit) und Urteil zur Uhr</caption>'
                 '<thead><tr><th>Abschnitt</th><th class="num">Fahrzeuge</th><th>Urteil</th></tr></thead><tbody>' + "".join(zeilen) +
                 "</tbody></table></div>")
    z.append(f'<p class="muted">Alle Belege: <a href="{REPO}/blob/main/{quote_pfad(rel)}/uhr-analyse.md">uhr-analyse.md</a>, '
             f'Verfahren: <a href="{REPO}/blob/main/docs/uhr-bewertung.md">Bewertung der Geräteuhr</a>.</p>')
    return "".join(z)


def abgleich_tabelle(eintrag):
    ab = eintrag.get("abgleich_dsd")
    if not ab:
        return ""
    abw = ab.get("abweichung_dsd_minus_verwaltung", {})

    def zeile(name, verw, dsd, diff):
        return f'<tr><th scope="row">{e(name)}</th><td class="num">{verw}</td><td class="num">{dsd}</td><td class="num">{diff}</td></tr>'

    z = []
    if eintrag.get("v85_kmh") is not None:
        z.append(zeile("V85 (km/h)", ganz(eintrag["v85_kmh"]), ganz(ab.get("v85_kmh")), f'{abw.get("v85_kmh", 0):+d}'.replace("+0", "0")))
    if eintrag.get("mittel_kmh") is not None:
        z.append(zeile("Mittleres Tempo (km/h)", ganz(eintrag["mittel_kmh"]), dez(ab.get("mittel_kmh")), dez(abw.get("mittel_kmh"), 1)))
    je_tag = eintrag.get("fahrzeuge_je_tag")
    if je_tag:
        teile = " + ".join(f"{ganz(v)} ({k})" if k != "gesamt" else ganz(v) for k, v in je_tag.items())
        z.append(zeile("Fahrzeuge je Tag", teile, ganz(ab.get("fahrzeuge_je_tag")),
                       f'{abw["fahrzeuge_je_tag_prozent"]:+d}&nbsp;%' if "fahrzeuge_je_tag_prozent" in abw else "–"))
    if not z:
        return ""
    return ('<div class="tablewrap"><table><caption class="muted">Abgleich: Angabe der Verwaltung gegen die DSD-Datei (aus der DSD '
            'berechnet, nur Fahrzeuge mit nutzbarer Zeit, alle Geschwindigkeiten, ohne Abzug des Rauschbodens)</caption><thead><tr><th>Kennzahl</th><th class="num">Verwaltung</th>'
            '<th class="num">DSD</th><th class="num">Abweichung</th></tr></thead><tbody>' + "".join(z) + "</tbody></table></div>")


def verwaltung_karte(eintrag, mit_abgleich=True):
    q = eintrag.get("quellen") or []
    kopf = []
    if eintrag.get("zeitraum"):
        kopf.append(f'Erfassungszeitraum {iso_de(eintrag["zeitraum"][0])} bis {iso_de(eintrag["zeitraum"][1])}')
    elif eintrag.get("zeitraum_in_mitteilung"):
        kopf.append(f'Zeitraum laut Mitteilung {iso_de(eintrag["zeitraum_in_mitteilung"][0])} bis '
                    f'{iso_de(eintrag["zeitraum_in_mitteilung"][1])} (nicht verwendet)')
    else:
        kopf.append("kein Erfassungszeitraum genannt")
    z = [f'<article class="card"><h4>{e(eintrag.get("bezeichnung"))}</h4><p class="muted">{e("; ".join(kopf))}</p>']
    badges = []
    if eintrag.get("einstufung_verwaltung") in EINSTUFUNG:
        text, art = EINSTUFUNG[eintrag["einstufung_verwaltung"]]
        badges.append("Einstufung: " + badge(text, art))
    if eintrag.get("massnahmen_verwaltung"):
        badges.append("Maßnahmen: " + e(eintrag["massnahmen_verwaltung"]))
    if badges:
        z.append("<p>" + " &nbsp;·&nbsp; ".join(badges) + "</p>")
    if eintrag.get("stellungnahme_verwaltung"):
        z.append('<blockquote class="verw"><p>' + "</p><p>".join(e(s) for s in eintrag["stellungnahme_verwaltung"]) +
                 "</p></blockquote>")
    fakten = []
    if eintrag.get("tempolimit_kmh"):
        fakten.append(("Tempolimit laut Mitteilung", f'{eintrag["tempolimit_kmh"]}&nbsp;km/h'))
    if eintrag.get("v85_kmh") is not None:
        fakten.append(("V85", f'{eintrag["v85_kmh"]}&nbsp;km/h'))
    if eintrag.get("mittel_kmh") is not None:
        fakten.append(("Mittleres Tempo", f'{eintrag["mittel_kmh"]}&nbsp;km/h'))
    if eintrag.get("fahrzeuge_je_tag"):
        fakten.append(("Fahrzeuge je Tag", " + ".join(f"{ganz(v)} ({e(k)})" if k != "gesamt" else ganz(v)
                                                      for k, v in eintrag["fahrzeuge_je_tag"].items())))
    if eintrag.get("fahrzeuge_im_zeitraum"):
        fakten.append(("Fahrzeuge im Zeitraum", " + ".join(f"{ganz(v)} ({e(k)})" if k != "gesamt" else ganz(v)
                                                           for k, v in eintrag["fahrzeuge_im_zeitraum"].items())))
    if eintrag.get("anteil_unter"):
        a = eintrag["anteil_unter"]
        fakten.append(("Anteil", f'{dez(a["prozent"])}&nbsp;% fuhren unter {a["kmh"]}&nbsp;km/h'))
    if eintrag.get("anteil_ueber"):
        a = eintrag["anteil_ueber"]
        fakten.append(("Anteil", f'{dez(a["prozent"])}&nbsp;% fuhren über {a["kmh"]}&nbsp;km/h'))
    if fakten:
        z.append('<dl class="facts">' + "".join(f"<dt>{e(k)}</dt><dd>{v}</dd>" for k, v in fakten) + "</dl>")
    if eintrag.get("hinweise_verwaltung"):
        z.append("<p>Hinweise der Verwaltung: " + e("; ".join(eintrag["hinweise_verwaltung"])) + ".</p>")
    if mit_abgleich:
        z.append(abgleich_tabelle(eintrag))
    zu = eintrag.get("zuordnung") or {}
    z.append(f'<p class="muted">Zuordnung zu dieser DSD-Datei {e(METHODE_TEXT.get(zu.get("methode"), zu.get("methode")))}.</p>')
    if eintrag.get("zeitraum_hinweis"):
        z.append(f'<p class="muted">{e(eintrag["zeitraum_hinweis"])}.</p>')
    quellen = []
    for s in q:
        name = f'Mitteilung {s["vorlage"]}' if s.get("vorlage") else f'Mitteilung (Vorlage {s.get("ris_vorlage_id")})'
        quellen.append(f'<a href="{e(s["dokument"])}">{e(name)}</a> ({e(s.get("gremium"))}, Sitzung {e(iso_de(s.get("sitzung")))})')
    if quellen:
        z.append('<p class="muted">Quelle: ' + "; ".join(quellen) + " – Ratsinformationssystem der Stadt Neuss.</p>")
    z.append("</article>")
    return "".join(z)


HINWEIS = ("Eigene Berechnungen aus den Rohdaten, nicht amtlich. Fehler in der Auswertung (Skripte, Annahmen, Zuordnung der "
           "Angaben) können nicht ausgeschlossen werden; alle Angaben ohne Gewähr. Gefährdung, Lärm und Ereignisse sind "
           "Schätzungen und kein Gutachten.")


def gefaehrdung_tabelle(row):
    """Gefaehrdung je Zeitraum mit Erklaerung."""
    return _schaetzung(row, True, False)


def laerm_tabelle(row):
    """Laerm je Zeitraum mit Erklaerung."""
    return _schaetzung(row, False, True)


def schaetzung_tabellen(row):
    """Gefaehrdung und Laerm je Zeitraum (zwei kleine Tabellen mit Erklaerung)."""
    return _schaetzung(row, True, True)


def _schaetzung(row, mit_gefaehrdung, mit_laerm):
    quellen = {"alle": row, "bereinigt": row.get("bereinigt") or {}, **(row.get("teilzeitraeume") or {})}
    gz, lz = [], []
    for key, label in ZEITRAEUME:
        q = quellen.get(key) or {}
        g, l = q.get("gefaehrdung"), q.get("laerm")
        if g and mit_gefaehrdung:
            gz.append(f'<tr><th scope="row">{e(label)}</th><td class="num">{dez(g["risikoindex_nilsson"], 2)}</td>'
                      f'<td class="num">{dez(g.get("aufprall_anteil_prozent"), 1)}&nbsp;%</td>'
                      f'<td class="num">{dez(g.get("aufprall_mittel_kmh"))}</td>'
                      f'<td class="num">{dez(g.get("aufprall_mittel_der_aufprallenden_kmh"))}</td>'
                      f'<td class="num">{dez(g.get("aufprall_p95_kmh"))}</td><td class="num">{dez(g.get("aufprall_p99_kmh"))}</td></tr>')
        if l and mit_laerm:
            lz.append(f'<tr><th scope="row">{e(label)}</th><td class="num">{dez(l["mittelungspegel_gegenueber_limit_db"])}&nbsp;dB</td>'
                      f'<td class="num">{dez(l["spitzenpegel_p99_gegenueber_limit_db"])}&nbsp;dB</td>'
                      f'<td class="num">{dez(l["anteil_mind_3_db_lauter_prozent"], 1)}&nbsp;%</td>'
                      f'<td class="num">{dez(l["anteil_mind_6_db_lauter_prozent"], 1)}&nbsp;%</td></tr>')
    z = []
    if gz:
        anh = (row.get("gefaehrdung") or {}).get("anhaltestrecke_bei_limit_m")
        z.append('<h4>Gefährdung (Schätzung)</h4>'
                 '<p>Mit wie viel km/h träfen die gemessenen Fahrzeuge auf ein Hindernis? Angenommen: Ein Kind tritt genau dort auf die '
                 f'Fahrbahn, wo ein Auto mit dem Tempolimit gerade noch zum Stehen kommt{" (Anhaltestrecke " + dez(anh) + " m)" if anh else ""}. '
                 'Jedes gemessene Fahrzeug bremst mit derselben Reaktionszeit und Verzögerung wie dieses Auto; ein schnelleres Fahrzeug hat '
                 'die Strecke schon fast verbraucht und trifft mit der angegebenen Aufprallgeschwindigkeit auf. Der Risikoindex vergleicht die '
                 'Unfallschwere mit einer Straße, auf der alle genau das Tempolimit fahren (1,0); sie wächst grob mit der 4. Potenz der '
                 'Geschwindigkeit (Potenzmodell nach Nilsson).</p>'
                 '<div class="tablewrap"><table><caption class="muted">Aufprallgeschwindigkeit und Risikoindex nach Zeitraum</caption>'
                 '<thead><tr><th>Zeitraum</th><th class="num">Risikoindex</th><th class="num">Fahrzeuge, die auftreffen</th>'
                 '<th class="num">Ø Aufprall (alle Fahrzeuge), km/h</th><th class="num">Ø Aufprall (nur die auftreffen), km/h</th>'
                 '<th class="num">schnellste 5&nbsp;%: Aufprall, km/h</th><th class="num">schnellstes 1&nbsp;%: Aufprall, km/h</th></tr></thead>'
                 '<tbody>' + "".join(gz) + "</tbody></table></div>")
        z.append(umrechnung(row.get("tempolimit_kmh")))
    if lz:
        z.append('<h4>Lärm (grobe Schätzung)</h4>'
                 '<p>Nur der Anteil, der von der Geschwindigkeit der Pkw abhängt, und nur im Vergleich zu einem Fahrzeug mit dem '
                 'Tempolimit; absolute Pegel werden nicht angegeben. Der Spitzenpegel zeigt, wie viel lauter die schnellsten Fahrten '
                 '(das schnellste Prozent) vorbeifahren. Der Mittelungspegel ist das energetische Mittel aller Fahrten gegenüber '
                 'einer Straße, auf der alle das Tempolimit fahren, und eignet sich zum Vergleich zwischen Standorten.</p>'
                 '<div class="tablewrap"><table><caption class="muted">Lärm gegenüber Tempolimit, nach Zeitraum</caption><thead><tr>'
                 '<th>Zeitraum</th><th class="num">Mittelungspegel</th><th class="num">Spitzenpegel (schnellstes %)</th>'
                 '<th class="num">≥ 3 dB lauter</th><th class="num">≥ 6 dB lauter</th></tr></thead><tbody>' + "".join(lz) +
                 "</tbody></table></div>")
    if z:
        z.append(f'<p class="muted">Modelle, Annahmen und Grenzen: <a href="{REPO}/blob/main/docs/gefaehrdung.md">Gefährdung, Lärm '
                 'und nächtliche Ereignisse</a>. Schätzungen, kein Gutachten; Fehler können nicht ausgeschlossen werden.</p>')
    return "".join(z)


def umrechnung(limit):
    """Kleine Beispieltabelle: gemessenes Tempo -> Aufprallgeschwindigkeit bei diesem Tempolimit."""
    if not limit:
        return ""
    zeilen = []
    for plus in (0, 5, 10, 15, 20, 30, 40):
        v = limit + plus
        zeilen.append(f'<tr><td class="num">{v}</td><td class="num">{"Tempolimit" if plus == 0 else "+" + str(plus)}</td>'
                      f'<td class="num">{ganz(round(aufprall_kmh(v, limit)))}</td></tr>')
    return ('<details><summary>So rechnet das Modell: gemessenes Tempo und Aufprallgeschwindigkeit</summary>'
            f'<div class="tablewrap"><table><caption class="muted">Bei Tempolimit {limit}&nbsp;km/h (Reaktionszeit 1,0&nbsp;s, '
            'Verzögerung 7,0&nbsp;m/s²)</caption><thead><tr><th class="num">Gemessen, km/h</th><th class="num">Gegenüber Limit</th>'
            '<th class="num">Trifft auf mit, km/h</th></tr></thead><tbody>' + "".join(zeilen) + "</tbody></table></div></details>")


# ------------------------------------------------------------------ Histogramme

HIST_MIN_FAHRZEUGE = 50  # darunter kein Histogramm
HIST_BREITE_MAX = 5  # breiteste Klasse in km/h
HIST_B, HIST_H, HIST_L, HIST_R, HIST_T, HIST_U = 600, 290, 44, 12, 38, 38  # Zeichenflaeche des SVG (viewBox)


def quantil(anzahl, ab, p):
    """Kleinste Geschwindigkeit, bei der mindestens der Anteil p der Fahrzeuge erreicht ist."""
    ziel, k = p * sum(anzahl), 0
    for i, c in enumerate(anzahl):
        k += c
        if k >= ziel:
            return ab + i
    return ab + len(anzahl) - 1


def klassenbreite(anzahl, ab):
    """Klassenbreite in ganzen km/h nach Freedman-Diaconis (2 * Quartilsabstand * n^(-1/3)), mindestens 1 km/h
    (Aufloesung der Geraete) und hoechstens HIST_BREITE_MAX. Viele Fahrzeuge ergeben 1 km/h, wenige breitere Klassen."""
    n = sum(anzahl)
    iqr = quantil(anzahl, ab, 0.75) - quantil(anzahl, ab, 0.25)
    if n < 2 or iqr <= 0:
        return 1
    return max(1, min(HIST_BREITE_MAX, int(round(2 * iqr * n ** (-1 / 3)))))


def hist_klassen(anzahl, ab, breite, limit, von, bis):
    """[(erster Wert, letzter Wert, Fahrzeuge)] von..bis. Mit Tempolimit beginnt eine Klasse bei limit+1,
    keine Klasse enthaelt also Werte auf beiden Seiten des Limits."""
    versatz = ((limit + 1) if limit else 0) % breite
    summen = collections.Counter()
    for i, c in enumerate(anzahl):
        v = ab + i
        if c and von <= v <= bis:
            summen[v - ((v - versatz) % breite)] += c
    erster = von - ((von - versatz) % breite)
    return [(s, s + breite - 1, summen.get(s, 0)) for s in range(erster, bis + 1, breite)]


def schritt_nice(maximum, ziel=5):
    for s in (0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50):
        if maximum / s <= ziel:
            return s
    return 100


def hist_svg(serien, limit, v85=None):
    """Histogramm als Inline-SVG. serien: [(Name, CSS-Klasse, {"ab_kmh", "anzahl"})].

    Eine Reihe: Saeulen, gruen bis zum Tempolimit, darueber rot. Mehrere Reihen: Linien im Vergleich. Hoehe = Anteil der
    Fahrzeuge je km/h, damit Reihen mit verschieden vielen Fahrzeugen und Klassenbreiten vergleichbar sind.
    Gibt (svg, Text zur Darstellung) zurueck.
    """
    ns = [sum(h["anzahl"]) for _, _, h in serien]
    breite = max(klassenbreite(h["anzahl"], h["ab_kmh"]) for _, _, h in serien)
    kleinster = min(h["ab_kmh"] for _, _, h in serien)
    groesster = max(h["ab_kmh"] + len(h["anzahl"]) - 1 for _, _, h in serien)
    oben = max(quantil(h["anzahl"], h["ab_kmh"], 0.9999) for _, _, h in serien) + 3  # Ausreisser (Messfehler) schneiden wir ab
    oben = min(max(oben, (limit + 15) if limit else 0), groesster)
    von, bis = (kleinster // 10) * 10, -(-oben // 10) * 10
    bis = max(bis, von + 10)
    reihen, ymax = [], 0.0
    for (name, klasse, h), n in zip(serien, ns):
        kl = hist_klassen(h["anzahl"], h["ab_kmh"], breite, limit, von, bis)
        anteile = [100.0 * c / n / breite for _, _, c in kl]
        ymax = max(ymax, max(anteile))
        reihen.append((name, klasse, kl, anteile, n))
    schritt = schritt_nice(ymax)
    ytop = max(schritt, -(-ymax // schritt) * schritt)
    pw, ph = HIST_B - HIST_L - HIST_R, HIST_H - HIST_T - HIST_U
    sc = pw / (bis - von + 1)

    def x(v):  # linker Rand von Wert v (ein Wert belegt v-0,5 bis v+0,5)
        return HIST_L + (v - 0.5 - von) * sc

    def y(a):
        return HIST_T + ph * (1 - a / ytop)

    def zahl(a):
        return f"{a:.1f}".replace(".", ",") if schritt < 1 else str(int(round(a)))

    s = [f'<svg class="hist" viewBox="0 0 {HIST_B} {HIST_H}" role="img" '
         f'aria-label="Histogramm der gemessenen Geschwindigkeiten, Klassenbreite {breite} km/h">']
    k = int(ytop / schritt + 0.5)
    for i in range(k + 1):
        a = i * schritt
        s.append(f'<line class="hist-gitter" x1="{HIST_L}" x2="{HIST_B - HIST_R}" y1="{y(a):.1f}" y2="{y(a):.1f}"/>')
        s.append(f'<text class="hist-text" x="{HIST_L - 5}" y="{y(a) + 4:.1f}" text-anchor="end">{zahl(a)}&#8239;%</text>')
    tick = 10 if bis - von <= 130 else 20
    for v in range(von, bis + 1, tick):
        s.append(f'<line class="hist-gitter" x1="{x(v) + sc / 2:.1f}" x2="{x(v) + sc / 2:.1f}" y1="{HIST_T + ph}" y2="{HIST_T + ph + 4}"/>')
        s.append(f'<text class="hist-text" x="{x(v) + sc / 2:.1f}" y="{HIST_T + ph + 17}" text-anchor="middle">{v}</text>')
    s.append(f'<text class="hist-text" x="{HIST_L + pw / 2}" y="{HIST_H - 6}" text-anchor="middle">Geschwindigkeit in km/h</text>')
    if len(reihen) == 1:
        name, klasse, kl, anteile, n = reihen[0]
        for (a, b, c), anteil in zip(kl, anteile):
            if not c:
                continue
            art = "hist-ueber" if limit and a > limit else "hist-ok"
            bereich = f"{a}" if a == b else f"{a}–{b}"
            s.append(f'<rect class="{art}" x="{x(a):.1f}" y="{y(anteil):.1f}" width="{max(0.5, breite * sc - 0.6):.1f}" '
                     f'height="{HIST_T + ph - y(anteil):.1f}"><title>{bereich} km/h: {ganz(c)} Fahrzeuge ({dez(100.0 * c / n, 2)} %)</title></rect>')
    else:
        for name, klasse, kl, anteile, n in reihen:
            punkte = " ".join(f"{x(a) + breite * sc / 2:.1f},{y(anteil):.1f}" for (a, _, _), anteil in zip(kl, anteile))
            s.append(f'<polyline class="hist-linie {klasse}" points="{punkte}"/>')
    marken = []
    if limit and von <= limit <= bis:
        marken.append((x(limit + 1), f"Limit {limit}", "hist-limit"))
    if v85 is not None and len(reihen) == 1 and von <= v85 <= bis:
        marken.append((x(v85) + sc / 2, f"V85 {v85}", "hist-v85"))
    zeilen_y = [12, 25] if len(reihen) == 1 else [28]  # bei zwei Reihen steht die Legende in der ersten Zeile
    for (px, text, klasse), ty in zip(marken, zeilen_y):
        ende = px > HIST_B - 90
        s.append(f'<line class="{klasse}" x1="{px:.1f}" x2="{px:.1f}" y1="{ty - 9}" y2="{HIST_T + ph}"/>')
        s.append(f'<text class="hist-text {klasse}-text" x="{px + (-4 if ende else 4):.1f}" y="{ty}" '
                 f'text-anchor="{"end" if ende else "start"}">{e(text)}</text>')
    if len(reihen) > 1:
        for i, (name, klasse, _, _, n) in enumerate(reihen):
            s.append(f'<line class="hist-linie {klasse}" x1="{HIST_L + 8 + i * 190}" x2="{HIST_L + 30 + i * 190}" y1="12" y2="12"/>')
            s.append(f'<text class="hist-text" x="{HIST_L + 36 + i * 190}" y="16">{e(name)} ({ganz(n)})</text>')
    s.append("</svg>")
    ausserhalb = [n - sum(c for _, _, c in kl) for (_, _, kl, _, n) in reihen]
    text = f"Klassenbreite {breite}&nbsp;km/h"
    text += " (Auflösung der Geräte)" if breite == 1 else f" (zusammengefasst, weil nur {' bzw. '.join(ganz(n) for n in ns)} Fahrzeuge vorliegen)"
    if any(ausserhalb):
        schnell = max(h["ab_kmh"] + len(h["anzahl"]) - 1 for _, _, h in serien)
        mehr = max(ausserhalb)
        text += (f"; {ganz(mehr)} {'Fahrzeug' if mehr == 1 else 'Fahrzeuge'} über {bis}&nbsp;km/h "
                 f"{'ist' if mehr == 1 else 'sind'} nicht dargestellt (schnellstes: {schnell}&nbsp;km/h)")
    return "".join(s), text + "."


def rausch_svg(sp, breite=420, hoehe=190):
    """Fahrten je Stunde nach Geschwindigkeit: grau alle, rot davon verkehrsunabhaengig (Rauschboden)."""
    n = len(sp["alle"])
    rate = [x / 1000 for x in sp["alle"]]
    ymax = max(rate) * 1.1 or 1
    schritt = 10 ** math.floor(math.log10(ymax))
    for f in (1, 2, 5, 10):
        if ymax / (schritt * f) <= 4:
            schritt *= f
            break
    ol, orr, ot, ou = 36, 8, 10, 28
    sx = (breite - ol - orr) / n

    def y(w):
        return ot + (hoehe - ot - ou) * (1 - w / ymax)

    s = [f'<svg class="hist" viewBox="0 0 {breite} {hoehe}" role="img" aria-label="Fahrten je Stunde nach Geschwindigkeit, davon Rauschboden">']
    t = 0.0
    while t <= ymax:
        s.append(f'<line class="hist-gitter" x1="{ol}" x2="{breite - orr}" y1="{y(t):.1f}" y2="{y(t):.1f}"/>'
                 f'<text class="hist-text" x="{ol - 4}" y="{y(t) + 4:.1f}" text-anchor="end">{dez(t, 1 if schritt < 1 else 0)}</text>')
        t += schritt
    for i in range(n):
        v = sp["ab_kmh"] + i
        x = ol + i * sx
        ges, ra = rate[i], sp["rausch"][i] / 1000
        s.append(f'<rect class="rausch-alle" x="{x + 0.5:.1f}" y="{y(ges):.1f}" width="{max(sx - 1, 0.5):.1f}" height="{hoehe - ou - y(ges):.1f}">'
                 f'<title>{v} km/h: {dez(ges, 2)} Fahrten je Stunde, davon verkehrsunabhängig {dez(ra, 2)}</title></rect>')
        if ra > 0:
            s.append(f'<rect class="rausch-rot" x="{x + 0.5:.1f}" y="{y(ra):.1f}" width="{max(sx - 1, 0.5):.1f}" height="{hoehe - ou - y(ra):.1f}"/>')
        if n <= 14 or i % 2 == 0:
            s.append(f'<text class="hist-text" x="{x + sx / 2:.1f}" y="{hoehe - ou + 14}" text-anchor="middle">{v}</text>')
    s.append(f'<text class="hist-text" x="{ol + (breite - ol - orr) / 2:.1f}" y="{hoehe - 3}" text-anchor="middle">Geschwindigkeit in km/h</text></svg>')
    return "".join(s)


def rauschen_abschnitt(row, mit_filter=False):
    """Rauschboden: Anteil der Messwerte, die nicht vom Verkehr abhaengen (rauschen.py), mit Bild und Hinweis.

    mit_filter: Die Auswahl der Seite bietet den Rauschboden an und zeigt ihn im Histogramm; das Bild steht dann nur im noscript-Block."""
    r = row.get("rauschen")
    if not r:
        return ""
    z = ['<h4>Rauschboden (verkehrsunabhängige Messwerte)</h4>']
    if not r.get("geprueft"):
        z.append(f'<p>Nicht geprüft: {e(r.get("grund"))}. Die Kennzahlen enthalten alle aufgezeichneten Fahrzeuge.</p>')
    elif r.get("belegt"):
        z.append(f'<p>Bei {dez(r.get("abgezogen_anteil_prozent", r["anteil_prozent"]), 1)}&nbsp;% der Messwerte dieser Datei ({ganz(r["abgezogen_fahrzeuge"])} Fahrzeuge) hängt die Rate '
                 f'nicht vom Verkehr ab: Sie bleibt über den Tag gleich, während der Verkehr schwankt. Diese Werte liegen im Mittel bei '
                 f'{dez(r["mittel_kmh"], 1)}&nbsp;km/h, 95&nbsp;% davon unter {r["obergrenze_kmh"]}&nbsp;km/h. Sie sind aus allen Kennzahlen auf dieser '
                 'Seite herausgerechnet. Was dahintersteckt (Fußgänger, Tiere, Echos, Störungen), lässt sich aus den Daten nicht sagen.</p>')
    elif r.get("grund") and "nachweisbar" in r["grund"]:
        z.append('<p>Ein verkehrsunabhängiger Rauschboden lässt sich in dieser Datei nicht nachweisen. Es wurde nichts herausgerechnet.</p>')
    else:
        z.append(f'<p>Ein verkehrsunabhängiger Anteil von etwa {dez(r.get("anteil_prozent"), 1)}&nbsp;% wurde geschätzt, ist aber nicht belegt '
                 f'({e(r.get("grund"))}). Es wurde nichts herausgerechnet; die Kennzahlen enthalten alle aufgezeichneten Fahrzeuge.</p>')
    rg = r.get("regen")
    if rg and rg.get("belegt"):
        z.append(f'<p>Bei Regen kommen weitere langsame Datensätze hinzu, die nicht von Fahrzeugen stammen: In den {ganz(rg["regenstunden"])} Regenstunden '
                 f'dieser Datei sind es im Mittel {dez(rg["zusatz_je_regenstunde"], 1)} je Stunde, 95&nbsp;% davon unter {rg["obergrenze_kmh"]}&nbsp;km/h. '
                 f'Sie sind herausgerechnet ({ganz(rg.get("abgezogen_fahrzeuge", 0))} Fahrzeuge). Die Verkehrsmenge in Regenstunden bleibt unsicher, weil '
                 'jeder dieser Datensätze das Gerät kurz sperrt und Fahrzeuge verdecken kann. Niederschlag: Quelle: Deutscher Wetterdienst '
                 f'(<a href="{REPO}/blob/main/docs/wetter.md">Wetterdaten</a>).</p>')
    elif rg and rg.get("grund") and rg.get("regenstunden"):
        z.append(f'<p class="muted">Ein Regenanteil ist nicht belegt ({e(rg["grund"])}); bei Regen wurde nichts zusätzlich herausgerechnet. '
                 'Niederschlag: Quelle: Deutscher Wetterdienst.</p>')
    sp = r.get("spektrum")
    if sp and sp.get("alle"):
        bild = ('<figure class="histfig">' + rausch_svg(sp) + '<figcaption class="muted">Fahrten je Stunde nach Geschwindigkeit: grau alle, '
                'rot davon verkehrsunabhängig (geschätzt aus dem Verlauf über den Tag, nur Zeiten mit nutzbarer Uhr).</figcaption></figure>')
        # Wo die Auswahl den Rauschboden anbietet (Gruppe "Rauschboden"), zeigt sie ihn im Histogramm; das Bild bleibt ohne JavaScript.
        z.append("<noscript>" + bild + "</noscript>" if mit_filter else bild)
    z.append(f'<p class="muted">Verfahren und Grenzen: <a href="{REPO}/blob/main/docs/rauschen.md">Rauschboden</a>.</p>')
    return "".join(z)


ZEIT_OPTIONEN = [("alle", "Ganztägig (alle Stunden)"), ("nacht", "Nacht (22–6 Uhr)"), ("vormittag", "Vormittag (6–12 Uhr)"),
                 ("nachmittag", "Nachmittag (12–19 Uhr)"), ("abend", "Abend (19–22 Uhr)"), ("schulweg", "Schulweg (7–8 Uhr)")]
TAGE_OPTIONEN = [("alle", "Alle Tage"), ("werktag", "Werktage (Mo–Fr)"), ("samstag", "Samstage"), ("sonn", "Sonn- und Feiertage")] + \
    [(str(i), t if i < 7 else "Feiertage an Werktagen und Samstagen") for i, t in enumerate(gruppen.TAGE)]


MODELL_ABWEICHUNG_WARNUNG = 10  # ab so viel Prozent Abweichung zwischen Daten und angepasster Kurve warnt die Seite


def modell_warnung(row):
    """Hinweis, wenn die angepassten Kurven die Daten schlecht beschreiben (sonst leer)."""
    a = (row.get("gruppen") or {}).get("modellabweichung_prozent")
    if a is None or a <= MODELL_ABWEICHUNG_WARNUNG:
        return ""
    return (f'<p class="notice" role="note"><strong>Das Modell passt hier schlecht:</strong> Die angepassten Kurven weichen bei etwa {dez(a, 1)}&nbsp;% der '
            'Fahrzeuge von den Daten ab. Die Verteilung hat eine Form, die eine Lognormal-Glocke je Gruppe nicht gut trifft (zum Beispiel eine '
            'Schulter oder einen Gipfel dicht am Tempolimit). Anteile und Kennzahlen der Gruppen sind deshalb unsicher; die Gruppen sind '
            'eine Beschreibung der Daten und keine feste Größe.</p>')


def gruppen_zeile(name, anteil, modus, sichtbar, g):
    return (f'<tr><th scope="row">{name}</th><td class="num">{dez(anteil, 1)}&nbsp;%</td><td class="num">{modus}</td>'
            f'<td class="num">{sichtbar}</td>'
            f'<td class="num">{dez(g["mittel_kmh"], 1)}</td><td class="num">{ganz(g["v85_kmh"])}</td>'
            f'<td class="num{klasse_quote(g.get("einhaltungsquote_prozent"))}">{dez(g.get("einhaltungsquote_prozent"), 1)}&nbsp;%</td>'
            f'<td class="num{klasse_quote(g.get("qualifizierte_einhaltungsquote_prozent"))}">{dez(g.get("qualifizierte_einhaltungsquote_prozent"), 1)}&nbsp;%</td></tr>')


def gruppen_abschnitt(row, mit_auswahl=True):
    """Zerlegung in Gruppen (gruppen.py): Tabelle mit Anteil, Lage und Kennzahlen je Gruppe und Rest, auch ohne JavaScript sichtbar."""
    g = row.get("gruppen")
    if not g:
        return ""
    z = ['<h4>Gruppen in der Verteilung (Schätzung)</h4>']
    if not g.get("geprueft"):
        return z[0] + f'<p>Nicht zerlegt: {e(g.get("grund"))}.</p>'
    if g["anzahl"] == 1:
        return z[0] + ('<p>Die Verteilung lässt sich nicht stabil in voneinander getrennte Gruppen zerlegen: Mehr als eine Gruppe '
                       'verbessert die Beschreibung der jeweils anderen Messtage nicht deutlich, kehrt nicht in beiden Hälften der Messtage '
                       'wieder oder liegt zu dicht beieinander. Es gibt deshalb keine Zerlegung.</p>'
                       f'<p class="muted">Verfahren und Grenzen: <a href="{REPO}/blob/main/docs/gruppen.md">Gruppen</a>.</p>')
    zeilen = [gruppen_zeile(f'Gruppe {gr["nr"]}' + (f' <span class="muted">(aus {gr["kurven"]} Kurven)</span>' if gr.get("kurven", 1) > 1 else ""),
                            gr["anteil_prozent"], dez(gr["modus_kmh"], 1), f'{ganz(gr.get("sichtbar_prozent"))}&nbsp;%', gr)
              for gr in g["gruppen"]]
    if g.get("rest"):  # der Rest hat keine Form und keine Kennwerte: nur sein Anteil
        zeilen.append(f'<tr><th scope="row">Rest (nicht erklärt)</th><td class="num">{dez(g["rest"]["anteil_prozent"], 1)}&nbsp;%</td>'
                      '<td class="num">–</td><td class="num">–</td><td class="num">–</td><td class="num">–</td><td class="num">–</td><td class="num">–</td></tr>')
    z.append(f'<p>Die Verteilung setzt sich aus {g["anzahl"]} Gruppen zusammen. Die Zerlegung gilt für alle Tageszeiten und Tage. '
             'Gruppen sind angepasste Kurven (statistische Anteile der Verteilung) und keine Fahrzeugarten: Was sich dahinter verbirgt (etwa Radfahrer, '
             'abbiegende oder anfahrende Fahrzeuge, Fahrer, die sich am Tempolimit oder am Gefühl orientieren), lässt sich aus den Daten '
             'nicht sagen. Fahrzeuge werden den Gruppen nicht zugeordnet: Was die Kurven nicht erklären, steht im Rest.</p>')
    if g.get("kurven", g["anzahl"]) > g["anzahl"]:
        z.append(f'<p class="muted">Die Verteilung ist aus {g["kurven"]} Kurven angepasst. Wo eine Gruppe aus mehreren Kurven besteht, beschreibt '
                 'ihre Summe die Form der Gruppe; wie die Kurven innerhalb der Gruppe aufgeteilt sind, ist nicht belegt (die Aufteilung '
                 'wechselt zwischen den Hälften der Messtage) und wird nicht ausgewiesen.</p>')
    z.append('<div class="tablewrap"><table><caption class="muted">Gruppen, nach Anteil geordnet (Gruppe 1 ist die größte). Anteil, Mittel, V85 '
             'und Einhaltung gelten für die angepasste Kurve der Gruppe; „Sichtbar“ ist der Teil der Kurve im erfassten Bereich. '
             'Die Anteile müssen sich nicht zu 100&nbsp;% addieren.</caption>'
             '<thead><tr><th>Gruppe</th><th class="num">Anteil</th>'
             '<th class="num">Modus, km/h</th><th class="num">Sichtbar</th><th class="num">Ø km/h</th><th class="num">V85</th><th class="num">Einhaltung</th>'
             '<th class="num">Qualifiziert</th></tr></thead><tbody>' + "".join(zeilen) + "</tbody></table></div>")
    z.append(modell_warnung(row))
    if g.get("modellabweichung_prozent") is not None:
        z.append(f'<p class="muted">Die angepassten Kurven weichen von den Daten bei etwa {dez(g["modellabweichung_prozent"], 1)}&nbsp;% der Fahrzeuge ab '
                 '(Anteil der Fahrzeuge, die das Modell an einer anderen Geschwindigkeit sieht).</p>')
    if g.get("obere_gruppen_ueberlappen"):
        z.append('<p class="muted">Die oberen Gruppen überlappen stark; belegt ist nur, dass sich die langsamste Gruppe von den übrigen trennt.</p>')
    if g.get("fahrzeuge_unter_grenze"):
        z.append(f'<p class="muted">{ganz(g["fahrzeuge_unter_grenze"])} Fahrzeuge unter {g["angepasst_ab_kmh"]}&nbsp;km/h (Rand der Erfassung) '
                 'sind nicht angepasst und stehen im Rest.</p>')
    z.append(f'<p class="muted">Verfahren und Grenzen: <a href="{REPO}/blob/main/docs/gruppen.md">Gruppen</a>.'
             + (' Auswahl nach Zeit, Tagen und Gruppe: im Abschnitt „Auswertung nach Zeit, Tagen und Gruppe“ (benötigt JavaScript).' if mit_auswahl else '')
             + '</p>')
    return "".join(z)


def json_in_html(obj):
    """JSON fuer ein script-Element: kein vorzeitiges Ende durch '</' und keine Kommentarsequenzen."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/").replace("<!--", "<\\!--")


def filter_abschnitt(row, daten, sid):
    """Auswahl nach Tageszeit, Tagen und Gruppe. Die Daten stehen als Tabelle (JSON) im Seitentext, filter.js rechnet daraus.

    Das Feld "Gruppe" gibt es nur, wenn die Datei in Gruppen zerlegt ist."""
    if not daten or not daten.get("z"):
        return ""
    abschnitte_ = daten.get("abschnitte") or []
    abschnitt_opt = []
    if abschnitte_:
        abschnitt_opt = [("alle", "Ganze Messung")] + [(str(a["nr"]), f'Abschnitt {a["nr"]} ({iso_de(a["von"])} bis {iso_de(a["bis"])})')
                                                        for a in abschnitte_]
    gruppen_opt = []
    if daten.get("gruppen") or any(a.get("gruppen") for a in abschnitte_):
        gruppen_opt = [("alle", "Alle Daten")]
        for g in daten["gruppen"]:
            gruppen_opt.append((f'g{g["nr"]}', f'Gruppe {g["nr"]} (Modus {dez(g["modus"], 0)} km/h, {dez(g["anteil"], 0)} %)'))
        gruppen_opt.append(("rest", "Rest (nicht erklärt)"))
        if daten.get("r"):
            gruppen_opt.append(("rausch", "Rauschboden (herausgerechnet)"))

    def auswahl(name, label, opts):
        return (f'<div><label for="{sid}-{name}">{e(label)}</label><select id="{sid}-{name}" data-feld="{name}">' +
                "".join(f'<option value="{e(v)}">{e(t)}</option>' for v, t in opts) + "</select></div>")

    warnung = modell_warnung(row) if gruppen_opt else ""
    felder = (auswahl("zeit", "Tageszeit", ZEIT_OPTIONEN) + auswahl("tage", "Tage", TAGE_OPTIONEN) +
              (auswahl("abschnitt", "Abschnitt", abschnitt_opt) if abschnitt_opt else "") +
              (auswahl("gruppe", "Gruppe", gruppen_opt) if gruppen_opt else ""))
    return ('<noscript><p class="muted">Die Auswahl nach Tageszeit, Wochentag und Gruppe benötigt JavaScript. Ohne JavaScript zeigt diese Seite '
            'die Auswertung für alle Fahrzeuge (Tabellen und Histogramm) und die Zeiträume in den Tabellen.</p></noscript>'
            f'<section class="filter" data-filter hidden><h4>Auswertung nach Zeit, Tagen, Abschnitt und Gruppe</h4>'
            '<p class="muted">Wählen Sie Tageszeit, Tage' + (' und Gruppe' if gruppen_opt else '') + '; Kennzahlen und Verteilung gelten dann für diese Auswahl. '
            'Es zählen vollständig aufgezeichnete Stunden mit nutzbarer Uhrzeit (Ortszeit); der Rauschboden ist herausgerechnet, wo belegt. '
            + ('Bei einer Gruppe bleiben alle Fahrzeuge der Auswahl grau sichtbar, farbig ist, was die Kurve der Gruppe davon erklärt. '
               'Die Kurven werden für die Auswahl nachgepasst (Anteil, Lage und Breite, gebunden an die Anpassung über alle Daten); bei sehr '
               'wenigen Fahrzeugen bleiben sie fest.' if gruppen_opt else '') +
            '</p>' + warnung + '<div class="controls">' + felder + '</div>' +
            ('<p class="muted filter-abschnitt-info"></p>' if abschnitt_opt else '') +
            '<div class="filter-ergebnis" aria-live="polite"></div>'
            f'<script type="application/json" class="filter-daten">{json_in_html(daten)}</script></section>')


def histogramm_abschnitt(row, mit_filter=False):
    """Geschwindigkeitsverteilung: Histogramm aller Fahrzeuge der Datei.

    mit_filter: Die Seite hat den Abschnitt mit der Auswahl (JavaScript), der dasselbe Histogramm zeigt (auch Tag gegen Nacht
    laesst sich dort waehlen). Das feste Histogramm steht dann nur noch im noscript-Block fuer Besucher ohne JavaScript."""
    h = row.get("histogramm")
    if not h or sum(h["anzahl"]) < HIST_MIN_FAHRZEUGE:
        return ""
    limit = row.get("tempolimit_kmh")
    svg, text = hist_svg([("alle", "", h)], limit, (row.get("geschwindigkeit_kmh") or {}).get("v85"))
    z = ['<h4>Verteilung der Geschwindigkeiten</h4><figure class="histfig">' + svg +
         '<figcaption class="muted">Höhe der Säulen: Anteil der Fahrzeuge je km/h, alle ausgewerteten Fahrzeuge'
         f'{" (blau bis zum Tempolimit, orange darüber)" if limit else ""}. {text}</figcaption></figure>']
    if mit_filter:
        z = ["<noscript>" + z[0] + "</noscript>"]
    return "".join(z)


def nacht_abschnitt(row):
    n = row.get("nacht_ereignisse")
    if not n:
        return ""
    z = ['<h4>Ereignisse pro Nacht</h4>']
    if not n.get("naechte"):
        return z[0] + '<p>Keine vollständig aufgezeichnete Nacht mit nutzbarer Zeit; Auswertung nicht möglich.</p>'
    zeilen, saetze = [], []
    for s in n.get("schwellen", []):
        label = f'ab {s["ab_kmh"]}&nbsp;km/h' + (" (doppeltes Tempolimit)" if s.get("doppeltes_tempolimit") else "")
        zeilen.append(f'<tr><th scope="row">{label}</th><td class="num">{ganz(s["naechte_mit_fahrt"])} von {ganz(n["naechte"])}</td>'
                      f'<td class="num">{dez(s["anteil_naechte_prozent"], 1)}&nbsp;%</td><td class="num">{ganz(s["fahrten_gesamt"])}</td>'
                      f'<td class="num">{dez(s["fahrten_je_nacht"], 2)}</td></tr>')
        if s["naechte_mit_fahrt"]:
            saetze.append(f'In {ganz(s["naechte_mit_fahrt"])} von {ganz(n["naechte"])} Nächten ({dez(s["anteil_naechte_prozent"], 0)}&nbsp;%) '
                          f'fuhr mindestens ein Fahrzeug mit {s["ab_kmh"]}&nbsp;km/h oder mehr')
    if saetze:
        z.append("<p>" + ". ".join(saetze[:2]) + ".</p>")
    z.append(f'<p class="muted">Nacht: {e(n["definition"])}. Ausfälle des Geräts zählen als Nächte ohne Ereignis. Einzelne sehr hohe Werte '
             'können Messfehler des Radarsensors sein; die Uhrzeit ist nur auf etwa eine Stunde belegt.</p>')
    z.append('<div class="tablewrap"><table><caption class="muted">Nächtliche Fahrten mit sehr hohem Tempo</caption><thead><tr>'
             '<th>Tempo</th><th class="num">Nächte mit mindestens einer Fahrt</th><th class="num">Anteil der Nächte</th>'
             '<th class="num">Fahrten gesamt</th><th class="num">Fahrten je Nacht</th></tr></thead><tbody>' + "".join(zeilen) +
             "</tbody></table></div>")
    return "".join(z)


def widersprueche(row, meta_messung):
    """Widersprueche und Auffaelligkeiten zwischen DSD-Datei und Angaben der Verwaltung als Liste von Saetzen."""
    z = []
    for v in (meta_messung or {}).get("verwaltung", []):
        w = v.get("tempolimit_widerspruch")
        if w:
            if w["verwendet_kmh"] != w["dsd_kmh"]:
                z.append(f'Tempolimit: Die Mitteilung nennt {w["mitteilung_kmh"]}&nbsp;km/h, die Anzeige-Schwelle in der DSD-Konfiguration '
                         f'steht auf {w["dsd_kmh"]}&nbsp;km/h. Für die Einhaltungsquoten gilt {w["verwendet_kmh"]}&nbsp;km/h.')
            else:
                z.append(f'Tempolimit: Die Mitteilung nennt {w["mitteilung_kmh"]}&nbsp;km/h, die DSD-Konfiguration {w["dsd_kmh"]}&nbsp;km/h; '
                         f'gerechnet wird mit {w["dsd_kmh"]}&nbsp;km/h ({e(w["grund"])}).')
        ab = v.get("abgleich_dsd") or {}
        for seite_, a in (ab.get("ausserhalb_des_erfassungszeitraums") or {}).items():
            innen = f'V85 {ab.get("v85_kmh")}&nbsp;km/h, Ø {dez(ab.get("mittel_kmh"))}&nbsp;km/h'
            z.append(f'Die Datei enthält {ganz(a["fahrzeuge"])} Fahrzeuge {seite_} dem Erfassungszeitraum der Mitteilung '
                     f'({iso_de(a["von"])} bis {iso_de(a["bis"])}; V85 {a["v85_kmh"]}&nbsp;km/h, Ø {dez(a["mittel_kmh"])}&nbsp;km/h, innerhalb des Zeitraums '
                     f'{innen}). Sie sind in den Kennzahlen unten enthalten; woher sie stammen, lässt sich aus den Daten nicht belegen.')
        je_tag, dsd_tag = v.get("fahrzeuge_je_tag") or {}, ab.get("fahrzeuge_je_tag")
        if len(je_tag) == 2 and dsd_tag and 0.4 <= dsd_tag / sum(je_tag.values()) <= 0.75:
            z.append(f'Die Mitteilung nennt zwei Richtungen ({" + ".join(ganz(x) for x in je_tag.values())} Fahrzeuge je Tag), die DSD-Datei '
                     f'hat {ganz(dsd_tag)} je Tag, etwa so viel wie eine Richtung. Möglicherweise liegt nur die Datei einer Richtung vor.')
    for dd in (meta_messung or {}).get("doppelte_daten", []):
        z.append(f'Diese Datei enthält dieselben Fahrzeugdaten wie {e(dd["datei"])} ({dez(dd["anteil_dieser_datei_prozent"], 0)}&nbsp;% dieser Datei '
                 f'sind dort ebenfalls enthalten).')
    return z


def wahrscheinlichkeit_text(p):
    return "über 99,9&nbsp;%" if p >= 0.999 else f"{dez(100 * p, 1)}&nbsp;%"


def _tage_zwischen(a, b):
    return abs((datetime.date.fromisoformat(a) - datetime.date.fromisoformat(b)).days)


def bruch_begruendung(bruch, verw, gleich, standort_name):
    """Begründung eines Bruchs als Liste von HTML-Sätzen: Statistik, Lücke, Zeiträume der Verwaltung, Brüche an anderen Standorten am selben Tag."""
    z = [e(s) for s in bruch.get("begruendung", [])]
    for v in verw:
        zr = v.get("zeitraum")
        if not zr or len(zr) != 2:
            continue
        for rolle, tag, rest in (("Beginn", zr[0], bruch["datum"]), ("Ende", zr[1], bruch["vorher_bis"])):
            if _tage_zwischen(tag, rest) <= 3:
                z.append(f'Die Mitteilung nennt für „{e(v.get("bezeichnung"))}“ den Erfassungszeitraum {iso_de(zr[0])} bis {iso_de(zr[1])}; '
                         f'der {rolle.lower()} dieses Zeitraums ({iso_de(tag)}) liegt {_tage_zwischen(tag, rest)} Tage vom Bruch.')
    andere = sorted({s for (s, _), tage in gleich.items() if s != standort_name and any(_tage_zwischen(t, bruch["datum"]) <= 1 for t in tage)})
    if andere:
        z.append(f'Am selben Tag (±1 Tag) gibt es Brüche in Messreihen von {len(andere)} anderen Standorten. Das spricht für einen gemeinsamen Anlass '
                 '(Geräte wurden umgehängt), nicht für Wetter an einem Ort.')
    return z


def abschnitte_text(a):
    """Einleitung zu den Abschnitten einer Messreihe (oder warum es keine gibt). Leer ohne Block."""
    if not a:
        return ""
    if not a.get("geprueft"):
        return f'<p>Brüche nicht geprüft: {e(a.get("grund"))}.</p>'
    nachsatz = ""
    if a.get("ausschlaege"):
        nachsatz += (' Kurze Ausschläge, nach denen der Verkehr zum alten Niveau zurückkehrt (zum Beispiel Feiertage), sind keine Brüche: '
                     + ", ".join(f'{iso_de(x["von"])} bis {iso_de(x["bis"])}' for x in a["ausschlaege"]) + ".")
    if not a.get("liste"):
        return (f'<p>In den {ganz(a["tage"])} vollständig aufgezeichneten Tagen wurde kein Bruch erkannt: Die Geschwindigkeitsverteilung ändert sich '
                f'nicht so stark, dass die Messung getrennt ausgewertet werden müsste (Verfahren: <a href="{REPO}/blob/main/docs/abschnitte.md">Abschnitte</a>).'
                f'{nachsatz}</p>')
    return (f'<p>Das Verhalten des Verkehrs ändert sich in dieser Messreihe an {a["brueche"]} {"Stelle" if a["brueche"] == 1 else "Stellen"} so stark, '
            'dass die Teile getrennt ausgewertet werden: Wahrscheinlich hing das Gerät danach an einer anderen Stelle oder war anders eingestellt. '
            'Der Grund lässt sich aus den Daten nicht sagen. Die Wahrscheinlichkeit sagt, wie sicher ein Bruch an dieser Stelle im statistischen Modell '
            f'ist (Tageswerte, ohne Wochentagsunterschiede, Schulferien und Feiertage), nicht, was geschah.{nachsatz}</p>')


def bruch_uebersicht(row, meta_messung, gleich, standort_name, mid):
    """Reiter Messung: Abschnitte der Messreihe mit Zeitraum, Fahrzeugen und der Begründung jedes Bruchs."""
    a = row.get("abschnitte")
    if not a:
        return ""
    z = ["<h4>Abschnitte der Messung</h4>", abschnitte_text(a)]
    if not a.get("liste"):
        return "".join(z)
    verw = (meta_messung or {}).get("verwaltung", [])
    zeilen = []
    for ab in a["liste"]:
        beginn = ab["beginn"]
        grund = "Beginn der Messung" if beginn["art"] != "Bruch" else f'Bruch, {wahrscheinlichkeit_text(beginn["wahrscheinlichkeit"])}'
        zeilen.append(f'<tr><th scope="row">Abschnitt {ab["nr"]}</th><td>{iso_de(ab["von"])} bis {iso_de(ab["bis"])}</td>'
                      f'<td class="num">{ganz(ab["tage"])}</td><td class="num">{ganz(ab.get("anzahl_fahrzeuge"))}</td><td>{grund}</td></tr>')
    z.append('<div class="tablewrap"><table><caption class="muted">Abschnitte, an Brüchen getrennt (Fahrzeuge mit nutzbarer Zeit)</caption><thead><tr>'
             '<th>Abschnitt</th><th>Zeitraum</th><th class="num">Tage</th><th class="num">Fahrzeuge</th><th>Beginn</th></tr></thead><tbody>' +
             "".join(zeilen) + "</tbody></table></div>")
    for ab in a["liste"]:
        beginn = ab["beginn"]
        if beginn["art"] != "Bruch":
            continue
        sätze = bruch_begruendung(beginn, verw, gleich, standort_name)
        z.append(f'<p id="{e(mid)}-bruch-{ab["nr"]}"><strong>Bruch vor Abschnitt {ab["nr"]} am {iso_de(beginn["datum"])}</strong>, Wahrscheinlichkeit '
                 f'{wahrscheinlichkeit_text(beginn["wahrscheinlichkeit"])}:</p><ul>' + "".join(f"<li>{s}</li>" for s in sätze) + "</ul>")
    z.append(f'<p class="muted">Verfahren, Schwellen und Grenzen: <a href="{REPO}/blob/main/docs/abschnitte.md">Abschnitte</a>. Die Abschnitte lassen sich '
             'im Reiter „Analyse“ einzeln auswerten.</p>')
    return "".join(z)


def abschnitte_einzeln(row):
    """Reiter Analyse, ohne JavaScript: Kennzahlen, Verteilung und Gruppen je Abschnitt als aufklappbare Blöcke."""
    a = row.get("abschnitte") or {}
    if not a.get("liste"):
        return ""
    z = ['<h4>Abschnitte einzeln</h4><p class="muted">Dieselbe Auswertung je Abschnitt der Messung (Rauschboden wie für die ganze Datei herausgerechnet, '
         'Gruppen je Abschnitt neu angepasst). Mit JavaScript lässt sich ein Abschnitt oben in der Auswahl wählen.</p>']
    for ab in a["liste"]:
        zz = [f'<details class="abschnitt"><summary>Abschnitt {ab["nr"]}: {iso_de(ab["von"])} bis {iso_de(ab["bis"])} '
              f'({ganz(ab["tage"])} Tage, {ganz(ab.get("anzahl_fahrzeuge"))} Fahrzeuge)</summary>']
        if ab.get("anzahl_fahrzeuge"):
            sub = dict(ab, tempolimit_kmh=row.get("tempolimit_kmh"))
            zz.append(kennzahlen_tabelle(sub, abschnitt=True))
            zz.append(histogramm_abschnitt(sub))
            zz.append(gruppen_abschnitt(sub, mit_auswahl=False))
        else:
            zz.append("<p>Keine Fahrzeuge mit nutzbarer Zeit.</p>")
        zz.append("</details>")
        z.append("".join(zz).replace("<h4>", "<h5>").replace("</h4>", "</h5>"))
    return "".join(z)


def messung_fakten(row, meta_messung):
    g = (meta_messung or {}).get("geraet", {})
    limit = row.get("tempolimit_kmh")
    quelle = {"mitteilung_verwaltung": "laut Mitteilung der Verwaltung", "parameter": "vorgegeben"}.get(row.get("tempolimit_quelle"), "aus der DSD-Konfiguration")
    fakten = [("Datei", e(row["datei"])),
              ("Tempolimit", f'{limit}&nbsp;km/h ({quelle}{"; DSD-Konfiguration " + str(row["tempolimit_dsd_kmh"]) + " km/h" if row.get("tempolimit_dsd_kmh") else ""})' if limit else "unbekannt"),
              ("Fahrzeuge in der Datei", ganz(row.get("fahrzeuge_in_datei"))),
              ("Fahrzeuge in der Auswertung", ganz(row.get("anzahl_fahrzeuge")))]
    ab, unter = row.get("auswertung_ab_kmh"), row.get("fahrzeuge_unter_auswertung_ab")
    if ab:
        fakten.append(("Ausgewertet ab", f'{ab}&nbsp;km/h ({ganz(unter)} langsamere Fahrzeuge in der Datei sind nicht berücksichtigt)'))
    mz = row.get("messzeitraum")
    if mz:
        fakten.append(("Zeitstempel in der Datei", f'{zeit_de(mz["start"])} bis {zeit_de(mz["ende"])} (Gerätezeit)'))
    bz = (row.get("bereinigt") or {}).get("messzeitraum")
    if bz:
        fakten.append(("Davon mit nutzbarer Zeit", f'{zeit_de(bz["start"])} bis {zeit_de(bz["ende"])} (Ortszeit), '
                                                   f'{ganz((row.get("bereinigt") or {}).get("anzahl_fahrzeuge"))} Fahrzeuge'))
    if g.get("konfiguration"):
        fakten.append(("Gerät (Konfiguration)", e(g["konfiguration"])))
    if g.get("name"):
        fakten.append(("Name im Gerät", e(g["name"])))
    if g.get("tempolimit_anzeige_kmh"):
        fakten.append(("Anzeige-Schwelle", f'{g["tempolimit_anzeige_kmh"]}&nbsp;km/h'))
    if g.get("erfassung_ab_kmh") is not None:
        fakten.append(("Erfassung ab", f'{g["erfassung_ab_kmh"]}&nbsp;km/h'))
    if g.get("verdeckte_messung"):
        fakten.append(("Anzeige", "verdeckte Messung (Display zeigte nichts an)"))
    if row.get("warnungen"):
        fakten.append(("Übersprungene Datensätze", f'{ganz(row["warnungen"])} mit ungültigem Zeitstempel'))
    return '<dl class="facts">' + "".join(f"<dt>{e(k)}</dt><dd>{v}</dd>" for k, v in fakten) + "</dl>"


def ausfaelle(uhr_abschnitte):
    """Lücken zwischen den Abschnitten der Aufzeichnung (Gerätezeit), ab einer Stunde."""
    if len(uhr_abschnitte) < 2:
        return ""
    z = []
    ab = sorted(uhr_abschnitte, key=lambda a: a["start"])
    for a, b in zip(ab, ab[1:]):
        try:
            t0 = datetime.datetime.fromisoformat(a["ende"])
            t1 = datetime.datetime.fromisoformat(b["start"])
        except (ValueError, TypeError):
            continue
        dauer = (t1 - t0).total_seconds() / 3600
        if dauer >= 1:
            z.append(f'<li>{e(zeit_de(a["ende"]))} bis {e(zeit_de(b["start"]))}: {dez(dauer / 24, 1) + " Tage" if dauer >= 48 else dez(dauer, 0) + " Stunden"} '
                     'ohne Aufzeichnung</li>')
    if not z:
        return ""
    return ('<h4>Ausfälle</h4><p class="muted">Lücken zwischen den Abschnitten der Aufzeichnung (Gerätezeit; bei verstellter Uhr nur ungefähr).</p><ul>' +
            "".join(z) + "</ul>")


def messqualitaet(row, mit_filter):
    """Rauschboden, Regenphantome und die Wetterstation."""
    z = [rauschen_abschnitt(row, mit_filter=mit_filter)]
    rg = (row.get("rauschen") or {}).get("regen") or {}
    st = rg.get("wetterstation")
    if st:
        z.append(f'<p class="muted">Niederschlag von der Station {e(st["name"])} ({dez(st["abstand_km"], 1)}&nbsp;km von der geschätzten Lage); fehlen dort '
                 f'Werte, gilt die nächste weitere ({e(", ".join(st.get("weitere", [])))}). Quelle: Deutscher Wetterdienst.</p>')
    return "".join(z)


def vergleich_teil(row, meta_messung):
    """Reiter Vergleich: Angaben der Verwaltung gegen die DSD (roh, im Erfassungszeitraum) und gegen diese Auswertung (bereinigt)."""
    verw = (meta_messung or {}).get("verwaltung", [])
    z = []
    wid = widersprueche(row, meta_messung)
    if wid:
        z.append('<div class="notice" role="note"><strong>Widersprüche und Auffälligkeiten zwischen DSD und Mitteilung:</strong><ul>' +
                 "".join(f"<li>{w}</li>" for w in wid) + "</ul></div>")
    if not verw:
        z.append("<p>Zu dieser Messung liegen keine Angaben der Verwaltung vor, mit denen sich vergleichen ließe.</p>")
        return "".join(z)
    b = row.get("bereinigt") or {}
    gb = b.get("geschwindigkeit_kmh") or {}
    for v in verw:
        ab = v.get("abgleich_dsd") or {}

        def zeile(name, verw_, roh, unser):
            return f'<tr><th scope="row">{e(name)}</th><td class="num">{verw_}</td><td class="num">{roh}</td><td class="num">{unser}</td></tr>'
        zz = []
        if v.get("v85_kmh") is not None:
            zz.append(zeile("V85 (km/h)", ganz(v["v85_kmh"]), ganz(ab.get("v85_kmh")), ganz(gb.get("v85"))))
        if v.get("mittel_kmh") is not None:
            zz.append(zeile("Mittleres Tempo (km/h)", ganz(v["mittel_kmh"]), dez(ab.get("mittel_kmh")), dez(gb.get("mittel"))))
        je_tag = v.get("fahrzeuge_je_tag")
        if je_tag:
            teile = " + ".join(f"{ganz(x)} ({e(k)})" if k != "gesamt" else ganz(x) for k, x in je_tag.items())
            zz.append(zeile("Fahrzeuge je Tag", teile, ganz(ab.get("fahrzeuge_je_tag")), "–"))
        if not zz:
            continue
        z.append(f'<h4>{e(v.get("bezeichnung"))}</h4><div class="tablewrap"><table><caption class="muted">Verwaltung; DSD roh: aus der DSD im Erfassungszeitraum '
                 'der Mitteilung, alle Geschwindigkeiten, ohne Abzug des Rauschbodens (so rechnet offenbar die Verwaltung); diese Auswertung: ganze Datei, '
                 'nur Fahrzeuge mit nutzbarer Zeit, Rauschboden und Regenphantome herausgerechnet, wo belegt</caption><thead><tr><th>Kennzahl</th>'
                 '<th class="num">Verwaltung</th><th class="num">DSD roh</th><th class="num">Diese Auswertung</th></tr></thead><tbody>' + "".join(zz) +
                 "</tbody></table></div>")
        zu = v.get("zuordnung") or {}
        z.append(f'<p class="muted">Zuordnung zu dieser DSD-Datei {e(METHODE_TEXT.get(zu.get("methode"), zu.get("methode")))}.</p>')
    if (row.get("abschnitte") or {}).get("liste"):
        z.append('<p class="muted">Diese Messreihe hat Abschnitte (Reiter „Messung“); der Vergleich gilt für die ganze Datei, wie die Verwaltung sie berichtet.</p>')
    z.append(f'<p class="muted">Herkunft und Zuordnung der Angaben: <a href="{REPO}/blob/main/docs/metadaten.md">Metadaten</a>.</p>')
    return "".join(z)


def je_abschnitt(row, baustein, mid, art):
    """Ein Baustein (Gefährdung, Lärm) für die ganze Messung und je Abschnitt; eine Auswahl (seite.js) zeigt einen davon."""
    liste = (row.get("abschnitte") or {}).get("liste") or []
    ganz_ = baustein(row)
    if not liste or not ganz_:
        return ganz_
    opts = [("alle", "Ganze Messung")] + [(str(a["nr"]), f'Abschnitt {a["nr"]} ({iso_de(a["von"])} bis {iso_de(a["bis"])})') for a in liste]
    z = [f'<div class="controls" data-abschnittwahl hidden><div><label for="{e(mid)}-{art}-abschnitt">Abschnitt</label>'
         f'<select id="{e(mid)}-{art}-abschnitt">' + "".join(f'<option value="{v}">{e(t)}</option>' for v, t in opts) + "</select></div></div>",
         f'<div data-abschnitt="alle"><p class="muted abschnitt-titel">Ganze Messung</p>{ganz_}</div>']
    for a in liste:
        teil = baustein(dict(a, tempolimit_kmh=row.get("tempolimit_kmh")))
        z.append(f'<div data-abschnitt="{a["nr"]}"><p class="muted abschnitt-titel">Abschnitt {a["nr"]}: {iso_de(a["von"])} bis {iso_de(a["bis"])}</p>'
                 f'{teil or "<p>Keine Werte.</p>"}</div>')
    return "".join(z)


def analyse_teil(row, daten, mid):
    if not row.get("anzahl_fahrzeuge"):
        return "<p>Die Datei enthält keine Fahrzeugdaten.</p>"
    z = []
    auswahl = filter_abschnitt(row, daten, mid)
    tabelle = kennzahlen_tabelle(row)
    # Mit der Auswahl (JavaScript) zeigt sie die Kennzahlen je Tageszeit, Tage und Abschnitt; die feste Tabelle steht dann nur ohne JavaScript.
    z.append("<noscript>" + tabelle + "</noscript>" if auswahl else tabelle)
    z.append(auswahl)
    z.append(histogramm_abschnitt(row, mit_filter=bool(auswahl)))
    z.append(gruppen_abschnitt(row))
    z.append(abschnitte_einzeln(row))
    return "".join(z)


def gefaehrdung_teil(row):
    return gefaehrdung_tabelle(row) + nacht_abschnitt(row)


QUELLE_TEXT = {"ordnername": "Ordnername", "mitteilung": "Mitteilung der Verwaltung", "ris": "Ratsinformationssystem",
               "datacollect": "Bericht der Messsoftware (DataCollect)", "manuell": "von Hand korrigiert"}
LAGE_METHODE_TEXT = {"adresse": "Hausnummer", "zwischen_nr": "zwischen zwei Hausnummern", "kreuzung": "Kreuzung",
                "zwischen_strassen": "Abschnitt zwischen zwei Querstraßen", "strasse": "nur die Straße"}


def karte_svg(st, verz, breite=420, hoehe=300):
    """Lageskizze: Häuser der Umgebung (Hauskoordinaten), Kreis der Unsicherheit und Mittelpunkt. Ohne Kartenkacheln, ohne Abruf von außen."""
    ox, oy, r = st["utm32_ost"], st["utm32_nord"], st["unsicherheit_m"]
    halb = max(r * 1.35, 120.0)  # halbe Breite des Ausschnitts in Metern
    m = breite / (2 * halb)
    hoch = hoehe / m / 2
    strasse = standorte.schluessel(st.get("strasse") or "")
    punkte = []
    for lst in verz.je_name.values():
        for a in lst:
            if abs(a.ost - ox) <= halb and abs(a.nord - oy) <= hoch:
                punkte.append((a.ost, a.nord, standorte.schluessel(a.strasse) == strasse))

    def px(x, y):
        return (breite / 2 + (x - ox) * m, hoehe / 2 - (y - oy) * m)
    s = [f'<svg class="hist karte" viewBox="0 0 {breite} {hoehe}" role="img" aria-label="Lageskizze: geschätzter Standort mit Unsicherheitskreis und Häusern der Umgebung">',
         f'<rect class="karte-rahmen" x="0.5" y="0.5" width="{breite - 1}" height="{hoehe - 1}"/>']
    for x, y, eigene in sorted(punkte, key=lambda p: p[2]):
        cx, cy = px(x, y)
        s.append(f'<circle class="karte-haus{" karte-eigene" if eigene else ""}" cx="{cx:.1f}" cy="{cy:.1f}" r="{2.6 if eigene else 1.8}"/>')
    s.append(f'<circle class="karte-kreis" cx="{breite / 2}" cy="{hoehe / 2}" r="{r * m:.1f}"/>')
    s.append(f'<path class="karte-mitte" d="M{breite / 2 - 6} {hoehe / 2}H{breite / 2 + 6}M{breite / 2} {hoehe / 2 - 6}V{hoehe / 2 + 6}"/>')
    schritt = next(n for n in (10, 20, 50, 100, 200, 500, 1000, 2000) if n * m >= 40 or n == 2000)
    x0, y0 = 10, hoehe - 14
    s.append(f'<path class="karte-mitte" d="M{x0} {y0 - 4}V{y0}H{x0 + schritt * m:.1f}V{y0 - 4}"/>'
             f'<text class="hist-text" x="{x0 + 3}" y="{y0 - 6}">{schritt} m</text>')
    s.append(f'<text class="hist-text" x="{breite - 8}" y="14" text-anchor="end">N ↑</text></svg>')
    return "".join(s)


def standort_abschnitt(st, verz):
    """Geschätzte Lage der Messstelle (metadaten.json, standorte.py) mit Skizze, Unsicherheit und Belegen."""
    art = {"benannt": "ok", "manuell korrigiert": "ok", "vermutet": "mid", "widersprüchlich": "bad"}.get(st["sicherheit"], "mid")
    lat, lon = st["breite"], st["laenge"]
    osm = f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=17/{lat}/{lon}"
    t = [f'<h3>Geschätzte Lage</h3><p>{dez(lat, 5)}° N, {dez(lon, 5)}° O, Unsicherheit ±{ganz(st["unsicherheit_m"])} m '
         f'{badge(st["sicherheit"], art)}<br><span class="muted">{e(LAGE_METHODE_TEXT.get(st["methode"], st["methode"]))}: {e(st["beschreibung"])}'
         f' · <a href="{e(osm)}">auf OpenStreetMap ansehen</a> (öffnet eine fremde Seite)</span></p>']
    if verz is not None:
        t.append(karte_svg(st, verz))
        t.append('<p class="muted">Punkte: Hauskoordinaten der Stadt Neuss (dunkel: dieselbe Straße), gestrichelter Kreis: Unsicherheit. '
                 "Die Karte zeigt keine Straßen, nur Häuser.</p>")
    if st.get("mehrdeutig"):
        t.append(f'<p class="muted">{e(st["mehrdeutig"])}.</p>')
    if st.get("widerspruch"):
        t.append(f'<p class="muted">{e(st["widerspruch"])}.</p>')
    fr = st.get("fahrtrichtung")
    for f in ([fr] if isinstance(fr, dict) else fr or []):
        t.append(f'<p class="muted">Fahrtrichtung zur {e(f["ziel"])}: Kompassrichtung etwa {ganz(f["peilung_grad"])}° (±{ganz(f["unsicherheit_grad"])}°).</p>')
    zeilen = []
    for b in st["belege"]:
        q = b.get("quelle") or {}
        quelle = QUELLE_TEXT.get(q.get("typ"), q.get("typ") or "")
        if q.get("dokument"):
            quelle = f'<a href="{e(q["dokument"])}">{e(quelle)}</a>' + (f' ({e(q["vorlage"])}, {e(iso_de(q["sitzung"]))})' if q.get("sitzung") else "")
        else:
            quelle = e(quelle)
        zeilen.append(f'<tr><td>{e(b["text"] or "")}</td><td>{e(b["stufe"])}</td><td>{quelle}</td><td>±{ganz(b["radius_m"])} m</td>'
                      f'<td>{"gewählt" if b["verwendet"] else "widerspricht" if b["widerspricht"] else "bestätigt"}</td></tr>')
    t.append('<details><summary>Hinweise, aus denen die Lage folgt</summary><table><thead><tr><th>Hinweis</th><th>Stufe</th><th>Quelle</th>'
             "<th>Radius</th><th>Verwendung</th></tr></thead><tbody>" + "".join(zeilen) + "</tbody></table>"
             f'<p class="muted">Die Radien sind Annahmen, nicht gemessen; Verfahren und Grenzen in <a href="{REPO}/blob/main/docs/standorte.md">docs/standorte.md</a>.</p></details>')
    return "".join(t)


REITER = [("allgemein", "Allgemein"), ("verwaltung", "Verwaltung"), ("messung", "Messung"), ("analyse", "Analyse"), ("vergleich", "Vergleich"),
          ("gefaehrdung", "Gefährdung"), ("laerm", "Lärm")]


def messung_id(rel, datei):
    """Kennung einer Messung (Datei) auf der Standortseite: 'm-<ordner>-<datei>'."""
    return "m-" + standort_slug(f"{rel}-{os.path.splitext(datei)[0]}")


def fahrtrichtungen(meta_messung, rel):
    fr = []
    for v in (meta_messung or {}).get("verwaltung", []):
        if v.get("fahrtrichtung") and v["fahrtrichtung"] not in fr:
            fr.append(v["fahrtrichtung"])
    m = re.search(r"\bFR\.?\s+([^/]+)", rel)
    if m and not fr:
        fr.append(m.group(1).strip())
    return fr


def messung_label(m):
    bz = (m["row"].get("bereinigt") or {}).get("messzeitraum") or m["row"].get("messzeitraum") or {}
    zeit = f'{iso_de((bz.get("start") or "")[:10])} bis {iso_de((bz.get("ende") or "")[:10])}' if bz else "ohne Zeitraum"
    fr = fahrtrichtungen(m["meta_messung"], m["rel"])
    return f'{zeit} · {bereinige(m["rel"])} · {m["row"]["datei"]}' + (f' · FR {", ".join(fr)}' if fr else "")


def standortgruppen(auswertung, metadaten):
    """Messungen je Standort: gleiche Straße (geschätzte Lage) und sich überlappende Lagekreise; Ordner ohne Lage bleiben für sich.

    Gibt [(slug, Name, [Ordner])] zurück, nach Name geordnet; die Slugs sind eindeutig."""
    ordner = list(collections.OrderedDict((r["standort"], None) for r in auswertung["standorte"]))
    st = {rel: ((metadaten.get("standorte") or {}).get(rel) or {}).get("standort") for rel in ordner}
    eltern = {rel: rel for rel in ordner}

    def wurzel_(x):
        while eltern[x] != x:
            eltern[x] = eltern[eltern[x]]
            x = eltern[x]
        return x
    for i, a in enumerate(ordner):
        for b in ordner[i + 1:]:
            sa, sb = st[a], st[b]
            if not sa or not sb or not sa.get("strasse") or standorte.schluessel(sa["strasse"]) != standorte.schluessel(sb.get("strasse") or ""):
                continue
            if math.hypot(sa["utm32_ost"] - sb["utm32_ost"], sa["utm32_nord"] - sb["utm32_nord"]) <= sa["unsicherheit_m"] + sb["unsicherheit_m"]:
                eltern[wurzel_(a)] = wurzel_(b)
    gruppen_ = collections.OrderedDict()
    for rel in ordner:
        gruppen_.setdefault(wurzel_(rel), []).append(rel)
    erg, vergeben = [], collections.Counter()
    for rels in gruppen_.values():
        s = st[rels[0]]
        name = s["strasse"] if s and s.get("strasse") else bereinige(rels[0])
        if len(rels) == 1 and not (s and s.get("strasse")):
            name = bereinige(rels[0])
        erg.append([name, rels])
    erg.sort(key=lambda x: (standorte.schluessel(x[0]), x[1]))
    out = []
    for name, rels in erg:
        slug = standort_slug(name)
        vergeben[slug] += 1
        n = vergeben[slug]
        if n > 1:  # gleiche Straße, aber getrennte Lagen
            slug, name = f"{slug}-{n}", f"{name} ({n}. Lage)"
        out.append((slug, name, rels))
    return out


def allgemein_teil(name, messungen, verz):
    """Reiter Allgemein: nur Fakten über den Standort (Lage, Straße, Tempolimit, Messungen, Quellen)."""
    z = []
    rels = list(collections.OrderedDict((m["rel"], None) for m in messungen))
    limits = collections.OrderedDict()
    for m in messungen:
        lim = m["row"].get("tempolimit_kmh")
        if lim:
            limits.setdefault(lim, []).append(m)
    fakten = [("Straße", e(name)), ("Ordner in der Lieferung der Stadt", "<br>".join(f'<a href="{REPO}/tree/main/{quote_pfad(r)}">{e(r)}</a>' for r in rels))]
    if limits:
        fakten.append(("Tempolimit", "<br>".join(
            f'{l}&nbsp;km/h' + (f' ({e(", ".join(messung_label(m).split(" · ")[0] for m in ms))})' if len(limits) > 1 else "") for l, ms in limits.items())))
    bez = collections.OrderedDict()
    for m in messungen:
        for v in (m["meta_messung"] or {}).get("verwaltung", []):
            bez.setdefault(v.get("bezeichnung"), None)
    if bez:
        fakten.append(("Bezeichnung der Verwaltung", "<br>".join(e(b) for b in bez)))
    fr = []
    for m in messungen:
        for f in fahrtrichtungen(m["meta_messung"], m["rel"]):
            if f not in fr:
                fr.append(f)
    if fr:
        fakten.append(("Fahrtrichtungen", e(", ".join(fr))))
    z.append('<dl class="facts">' + "".join(f"<dt>{e(k)}</dt><dd>{v}</dd>" for k, v in fakten) + "</dl>")
    # Lage je Ordner (gleiche Lage nur einmal)
    gesehen = set()
    for rel in rels:
        st = ((messungen[0]["metadaten"] or {}).get("standorte") or {}).get(rel, {}).get("standort")
        if not st:
            continue
        k = (st["utm32_ost"], st["utm32_nord"], st["unsicherheit_m"])
        if k in gesehen:
            continue
        gesehen.add(k)
        if len(rels) > 1:
            z.append(f'<p class="muted">Ordner {e(rel)}:</p>')
        z.append(standort_abschnitt(st, verz))
    zeilen = []
    for m in messungen:
        r = m["row"]
        a = (r.get("abschnitte") or {}).get("liste") or []
        fr_m = fahrtrichtungen(m["meta_messung"], m["rel"])
        zeilen.append(f'<tr><td><a href="#{e(m["id"])}" data-messung-link="{e(m["id"])}">{e(messung_label(m).split(" · ")[0])}</a></td>'
                      f'<td>{e(m["rel"])}<br><span class="muted">{e(r["datei"])}</span></td><td>{e(", ".join(fr_m)) or "–"}</td>'
                      f'<td class="num">{ganz(r.get("tempolimit_kmh"))}</td><td class="num">{ganz(r.get("anzahl_fahrzeuge"))}</td>'
                      f'<td class="num">{len(a) or 1}</td></tr>')
    z.append('<h3>Messungen an diesem Standort</h3><div class="tablewrap"><table><thead><tr><th>Zeitraum (nutzbare Zeit)</th><th>Ordner und Datei</th>'
             '<th>Fahrtrichtung</th><th class="num">Limit km/h</th><th class="num">Fahrzeuge</th><th class="num">Abschnitte</th></tr></thead><tbody>' +
             "".join(zeilen) + "</tbody></table></div>")
    links = []
    for rel in rels:
        links.append(f'<a href="{REPO}/blob/main/{quote_pfad(rel)}/metadaten.yaml">metadaten.yaml ({e(bereinige(rel))})</a>')
    for m in messungen:
        basis = os.path.splitext(m["row"]["datei"])[0]
        links.append(f'<a href="../{quote_pfad(m["rel"])}/{urllib.parse.quote(basis)}.yaml">Auswertung {e(m["row"]["datei"])} (YAML)</a>')
    z.append('<h3>Daten und Quellen</h3><ul class="links">' + "".join(f"<li>{x}</li>" for x in links) + "</ul>")
    return "".join(z)


def verwaltung_teil(m):
    verw = (m["meta_messung"] or {}).get("verwaltung", [])
    if not verw:
        return ("<p>Zu dieser Messung hat die Verwaltung (soweit auffindbar) keine Einschätzung veröffentlicht. Sie berichtet Ergebnisse je Messstelle "
                "seit Februar 2024; für frühere Messungen gibt es nur den Namen des Ordners.</p>")
    z = ['<p class="muted">Auszüge aus den Mitteilungen der Verwaltung an die Bezirksausschüsse. Die Sätze stehen im Wortlaut da (Trennfehler des '
         'PDF-Textes repariert); maßgeblich ist das verlinkte Dokument. Den Vergleich mit den Daten zeigt der Reiter „Vergleich“.</p>']
    for v in verw:
        z.append(verwaltung_karte(v, mit_abgleich=False))
    return "".join(z)


def messung_teil(m, gleich):
    row = m["row"]
    daten = m["zellen"]
    z = [messung_fakten(row, m["meta_messung"])]
    z.append(uhr_abschnitt(row, m["uhr_abschnitte"], m["rel"]))
    z.append(ausfaelle(m["uhr_abschnitte"]))
    z.append(bruch_uebersicht(row, m["meta_messung"], gleich, m["rel"], m["id"]))
    z.append(messqualitaet(row, mit_filter=bool(daten and daten.get("z") and daten.get("r"))))
    for dd in (m["meta_messung"] or {}).get("doppelte_daten", []):
        z.append(f'<p class="notice" role="note">Diese Datei enthält dieselben Fahrzeugdaten wie {e(dd["datei"])} ({dez(dd["anteil_dieser_datei_prozent"], 0)}&nbsp;% '
                 'dieser Datei sind dort ebenfalls enthalten).</p>')
    return "".join(z)


def reiter_html(reiter_id, titel, teile, messungen):
    """Ein Reiter. teile: Funktion (Messung) -> HTML oder fester Text (Standort)."""
    z = [f'<section class="reiter-inhalt" id="r-{reiter_id}" role="tabpanel" aria-labelledby="t-{reiter_id}" data-reiter="{reiter_id}"><h2>{e(titel)}</h2>']
    if isinstance(teile, str):
        z.append(teile)
    else:
        for m in messungen:
            z.append(f'<div class="messung-teil" data-messung="{e(m["id"])}">' +
                     (f'<h3 class="messung-titel">{e(messung_label(m))}</h3>' if len(messungen) > 1 else "") + teile(m) + "</div>")
    z.append("</section>")
    return "".join(z)


def standortseite(name, messungen, verz=None, gleich=None):
    """Seite eines Standorts mit allen Messungen. messungen: [dict(id, rel, row, meta_messung, uhr_abschnitte, zellen, metadaten)]."""
    gleich = gleich or {}
    teile = [f"""<!doctype html>
<!-- SPDX-License-Identifier: MIT -->
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(name)} – Neuss Dialogdisplays</title>
<meta name="description" content="Geschwindigkeitsmessungen der Dialogdisplays: {e(name)} – Standort, Angaben der Verwaltung, Messung und Auswertung.">
<link rel="stylesheet" href="../style.css">
</head>
<body>
<main class="detail">
<nav class="muted" aria-label="Navigation"><a href="../index.html">← Übersicht aller Messungen</a></nav>
<h1>{e(name)}</h1>
<p class="notice" role="note"><strong>Hinweis:</strong> {e(HINWEIS)}</p>
"""]
    if len(messungen) > 1:
        teile.append('<div class="controls messwahl"><div><label for="messwahl">Messung</label><select id="messwahl" data-messwahl>' +
                     "".join(f'<option value="{e(m["id"])}">{e(messung_label(m))}</option>' for m in messungen) + "</select></div></div>"
                     f'<p class="muted" data-ohne-skript>An diesem Standort gibt es {len(messungen)} Messungen; ohne JavaScript stehen sie in jedem Reiter untereinander.</p>')
    teile.append('<nav class="reiter" role="tablist" aria-label="Themen" hidden>' + "".join(
        f'<button type="button" role="tab" id="t-{rid}" aria-controls="r-{rid}" data-ziel="{rid}">{e(t)}</button>' for rid, t in REITER) + "</nav>")
    teile.append(reiter_html("allgemein", "Allgemein", allgemein_teil(name, messungen, verz), messungen))
    teile.append(reiter_html("verwaltung", "Verwaltung", verwaltung_teil, messungen))
    teile.append(reiter_html("messung", "Messung", lambda m: messung_teil(m, gleich), messungen))
    teile.append(reiter_html("analyse", "Analyse", lambda m: analyse_teil(m["row"], m["zellen"], m["id"]), messungen))
    teile.append(reiter_html("vergleich", "Vergleich mit der Verwaltung", lambda m: vergleich_teil(m["row"], m["meta_messung"]), messungen))
    teile.append(reiter_html("gefaehrdung", "Gefährdung", lambda m: je_abschnitt(m["row"], gefaehrdung_teil, m["id"], "gefaehrdung"), messungen))
    teile.append(reiter_html("laerm", "Lärm", lambda m: je_abschnitt(m["row"], laerm_tabelle, m["id"], "laerm"), messungen))
    mit_filter = any((m["zellen"] or {}).get("z") for m in messungen)
    teile.append(f"""<footer class="muted">
<p>Rohdaten und Skripte: <a href="{REPO}">GitHub</a> · <a href="{REPO}/blob/main/docs/metadaten.md">Herkunft der Metadaten</a></p>
<p>{e(HINWEIS)}</p>
<p>Lizenz: Daten und Dokumentation <a href="https://creativecommons.org/publicdomain/zero/1.0/deed.de">CC0 1.0</a>, Skripte MIT. Wetterdaten: Quelle: Deutscher Wetterdienst (CC BY 4.0).</p>
<p><a href="../index.html">Übersicht</a><a href="../impressum.html">Impressum</a><a href="../datenschutz.html">Datenschutz</a></p>
</footer>
</main>
<script src="../seite.js" defer></script>
{'<script src="../filter.js" defer></script>' if mit_filter else ''}
</body>
</html>
""")
    return "".join(teile)


def messung_eintrag(rel, row, metadaten, uhr_dateien, zellen):
    meta_standort = (metadaten.get("standorte") or {}).get(rel) or {}
    meta_messung = next((m for m in meta_standort.get("messungen", []) if m["datei"] == row["datei"]), None)
    return {"id": messung_id(rel, row["datei"]), "rel": rel, "row": row, "meta_messung": meta_messung, "metadaten": metadaten,
            "uhr_abschnitte": (uhr_dateien.get(f'{rel}/{row["datei"]}') or {}).get("abschnitte", []), "zellen": (zellen or {}).get(row["datei"])}


def _beginn(m):
    bz = (m["row"].get("bereinigt") or {}).get("messzeitraum") or m["row"].get("messzeitraum") or {}
    return (bz.get("start") or "9999", m["rel"], m["row"]["datei"])


def seite(rel, rows, meta_standort, uhr_dateien, zellen=None, verz=None, gleich=None):
    """Seite für einen einzelnen Ordner (für Tests und Aufrufe ohne Standortgruppen)."""
    metadaten = {"standorte": {rel: meta_standort or {}}}
    messungen = sorted((messung_eintrag(rel, r, metadaten, uhr_dateien, zellen) for r in rows), key=_beginn)
    st = (meta_standort or {}).get("standort") or {}
    return standortseite(st.get("strasse") or bereinige(rel), messungen, verz, gleich)


def weiterleitung(ziel, titel):
    return (f'<!doctype html>\n<html lang="de">\n<head>\n<meta charset="utf-8">\n<title>{e(titel)} – Neuss Dialogdisplays</title>\n'
            f'<meta http-equiv="refresh" content="0; url={e(ziel)}">\n<link rel="canonical" href="{e(ziel)}">\n</head>\n<body>\n'
            f'<p>Diese Seite ist umgezogen: <a href="{e(ziel)}">{e(titel)}</a>.</p>\n</body>\n</html>\n')


def lade_zellen(ordner, rel, rows):
    """Zellendaten (<datei>.zellen.json von dsd2csv.py) der Messungen eines Standorts: {Dateiname: Daten}."""
    erg = {}
    for r in rows:
        pfad = os.path.join(ordner or "", rel, os.path.splitext(r["datei"])[0] + ".zellen.json")
        if ordner and os.path.exists(pfad):
            with open(pfad, encoding="utf-8") as fh:
                erg[r["datei"]] = json.load(fh)
    return erg


def bauen(auswertung, metadaten, uhr, ziel, zellen_ordner=None, adressen=None):
    """Eine Seite je Standort, Weiterleitungen von den alten Seiten je Ordner und uebersicht.json für die Übersichtsseite."""
    verz = standorte.Verzeichnis.laden(adressen) if adressen and os.path.exists(adressen) else None
    # Tage der Brüche je Messreihe, um Brüche am selben Tag an anderen Standorten zu nennen
    gleich = {(r["standort"], r["datei"]): [ab["beginn"]["datum"] for ab in (r.get("abschnitte") or {}).get("liste", []) if ab["beginn"]["art"] == "Bruch"]
              for r in auswertung["standorte"]}
    je_ordner = collections.OrderedDict()
    for row in auswertung["standorte"]:
        je_ordner.setdefault(row["standort"], []).append(row)
    os.makedirs(os.path.join(ziel, "standorte"), exist_ok=True)
    seiten, uebersicht, neue = {}, {}, set()
    gruppen_ = standortgruppen(auswertung, metadaten)
    for slug, name, rels in gruppen_:
        neue.add(slug)
    for slug, name, rels in gruppen_:
        messungen = []
        for rel in rels:
            rows = je_ordner[rel]
            zellen = lade_zellen(zellen_ordner, rel, rows)
            messungen += [messung_eintrag(rel, r, metadaten, uhr["dateien"], zellen) for r in rows]
        messungen.sort(key=_beginn)
        with open(os.path.join(ziel, "standorte", slug + ".html"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(standortseite(name, messungen, verz, gleich))
        seiten[slug] = rels
        for m in messungen:
            verw = [v.get("bezeichnung") for v in (m["meta_messung"] or {}).get("verwaltung", []) if v.get("bezeichnung")]
            uebersicht[f'{m["rel"]}/{m["row"]["datei"]}'] = {"seite": f"standorte/{slug}.html#{m['id']}", "standort": name, "verwaltung": verw}
        for rel in rels:  # alte Adresse je Ordner -> neue Seite
            alt = standort_slug(rel)
            if alt not in neue:
                erste = next(m for m in messungen if m["rel"] == rel)
                with open(os.path.join(ziel, "standorte", alt + ".html"), "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(weiterleitung(f"{slug}.html#{erste['id']}", name))
    with open(os.path.join(ziel, "uebersicht.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(uebersicht, fh, ensure_ascii=False, separators=(",", ":"))
    return seiten


def main():
    hier = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--auswertung", required=True, help="auswertung.json von dsd2csv.py")
    ap.add_argument("--metadaten", default=os.path.join(hier, "belege", "metadaten.json"))
    ap.add_argument("--uhr", default=os.path.join(hier, "belege", "uhr-bewertung.json"))
    ap.add_argument("--adressen", default=os.path.join(hier, "belege", "neuss-adressen.csv"), help="Hauskoordinaten fuer die Lageskizze")
    ap.add_argument("--ziel", required=True, help="Ausgabeordner (die Seiten landen in <ziel>/standorte/)")
    ap.add_argument("--zellen", help="Ordner mit den .zellen.json von dsd2csv.py (Standard: Ordner der auswertung.json)")
    a = ap.parse_args()
    daten = []
    for pfad in (a.auswertung, a.metadaten, a.uhr):
        with open(pfad, encoding="utf-8") as fh:
            daten.append(json.load(fh))
    slugs = bauen(*daten, a.ziel, a.zellen or os.path.dirname(os.path.abspath(a.auswertung)), a.adressen)
    print(f"{len(slugs)} Standortseiten in {os.path.join(a.ziel, 'standorte')}", file=sys.stderr)


if __name__ == "__main__":
    main()
