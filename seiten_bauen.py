# SPDX-License-Identifier: MIT
"""Baut je Standortordner eine Detailseite (standorte/<name>.html) fuer die GitHub Pages.

Aufruf (nach dsd2csv.py, das auswertung.json schreibt):
  python3 -I seiten_bauen.py --auswertung _site/auswertung.json --ziel _site

Eingaben:
  auswertung.json          Kennzahlen je DSD-Datei (dsd2csv.py)
  belege/metadaten.json    Angaben der Verwaltung und Geraete-Konfiguration (metadaten.py)
  belege/uhr-bewertung.json  Urteil zur Geraeteuhr je Abschnitt (uhr_belege.py)

Die Seiten sind statisches HTML ohne Verbindungen zu anderen Servern. Nur die Auswahl nach Zeit, Tagen und Gruppe braucht
ein kleines eigenes Skript (site/filter.js), das ausschliesslich die eingebettete Datentabelle liest. Alle Texte aus den
Daten werden maskiert. Der Wortlaut der Verwaltung steht als Auszug da; massgeblich ist das verlinkte Dokument.
"""
import argparse
import collections
import html
import json
import math
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I nimmt das Skriptverzeichnis nicht auf
import gruppen  # noqa: E402
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

def kennzahlen_tabelle(row):
    """Tabelle der Kennzahlen: alle Fahrzeuge, bereinigt und die Teilzeiträume."""
    quellen = {"alle": row, "bereinigt": row.get("bereinigt") or {}, **(row.get("teilzeitraeume") or {})}
    zeilen = []
    for key, label in ZEITRAEUME:
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


def schaetzung_tabellen(row):
    """Gefaehrdung und Laerm je Zeitraum (zwei kleine Tabellen mit Erklaerung)."""
    quellen = {"alle": row, "bereinigt": row.get("bereinigt") or {}, **(row.get("teilzeitraeume") or {})}
    gz, lz = [], []
    for key, label in ZEITRAEUME:
        q = quellen.get(key) or {}
        g, l = q.get("gefaehrdung"), q.get("laerm")
        if g:
            gz.append(f'<tr><th scope="row">{e(label)}</th><td class="num">{dez(g["risikoindex_nilsson"], 2)}</td>'
                      f'<td class="num">{dez(g.get("aufprall_anteil_prozent"), 1)}&nbsp;%</td>'
                      f'<td class="num">{dez(g.get("aufprall_mittel_kmh"))}</td>'
                      f'<td class="num">{dez(g.get("aufprall_mittel_der_aufprallenden_kmh"))}</td>'
                      f'<td class="num">{dez(g.get("aufprall_p95_kmh"))}</td><td class="num">{dez(g.get("aufprall_p99_kmh"))}</td></tr>')
        if l:
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
HIST_MIN_VERGLEICH = 100  # Tag/Nacht-Vergleich: so viele Fahrzeuge je Reihe mindestens
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


def rauschen_abschnitt(row):
    """Rauschboden: Anteil der Messwerte, die nicht vom Verkehr abhaengen (rauschen.py), mit Bild und Hinweis."""
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
    sp = r.get("spektrum")
    if sp and sp.get("alle"):
        z.append('<figure class="histfig">' + rausch_svg(sp) + '<figcaption class="muted">Fahrten je Stunde nach Geschwindigkeit: grau alle, '
                 'rot davon verkehrsunabhängig (geschätzt aus dem Verlauf über den Tag, nur Zeiten mit nutzbarer Uhr).</figcaption></figure>')
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


def gruppen_abschnitt(row):
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
    if g.get("rest"):
        zeilen.append(gruppen_zeile("Rest (nicht erklärt)", g["rest"]["anteil_prozent"], "–", "–", g["rest"]))
    z.append(f'<p>Die Verteilung setzt sich aus {g["anzahl"]} Gruppen zusammen. Die Zerlegung gilt für alle Tageszeiten und Tage. '
             'Gruppen sind angepasste Kurven (statistische Anteile der Verteilung) und keine Fahrzeugarten: Was sich dahinter verbirgt (etwa Radfahrer, '
             'abbiegende oder anfahrende Fahrzeuge, Fahrer, die sich am Tempolimit oder am Gefühl orientieren), lässt sich aus den Daten '
             'nicht sagen. Fahrzeuge werden den Gruppen nicht zugeordnet: Was die Kurven nicht erklären, steht im Rest.</p>')
    if g.get("kurven", g["anzahl"]) > g["anzahl"]:
        z.append(f'<p class="muted">Die Verteilung ist aus {g["kurven"]} Kurven angepasst. Wo eine Gruppe aus mehreren Kurven besteht, beschreibt '
                 'ihre Summe die Form der Gruppe; wie die Kurven innerhalb der Gruppe aufgeteilt sind, ist nicht belegt (die Aufteilung '
                 'wechselt zwischen den Hälften der Messtage) und wird nicht ausgewiesen.</p>')
    z.append('<div class="tablewrap"><table><caption class="muted">Gruppen, nach dem häufigsten Tempo (Modus) geordnet. Anteil, Mittel, V85 '
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
    z.append(f'<p class="muted">Verfahren und Grenzen: <a href="{REPO}/blob/main/docs/gruppen.md">Gruppen</a>. Auswahl nach Zeit, Tagen und Gruppe: '
             'im Abschnitt „Auswertung nach Zeit, Tagen und Gruppe“ (benötigt JavaScript).</p>')
    return "".join(z)


def json_in_html(obj):
    """JSON fuer ein script-Element: kein vorzeitiges Ende durch '</' und keine Kommentarsequenzen."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/").replace("<!--", "<\\!--")


def filter_abschnitt(row, daten, sid):
    """Auswahl nach Tageszeit, Tagen und Gruppe. Die Daten stehen als Tabelle (JSON) im Seitentext, filter.js rechnet daraus.

    Das Feld "Gruppe" gibt es nur, wenn die Datei in Gruppen zerlegt ist."""
    if not daten or not daten.get("z"):
        return ""
    gruppen_opt = []
    if daten.get("gruppen"):
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
    felder = auswahl("zeit", "Tageszeit", ZEIT_OPTIONEN) + auswahl("tage", "Tage", TAGE_OPTIONEN) + (auswahl("gruppe", "Gruppe", gruppen_opt) if gruppen_opt else "")
    return ('<noscript><p class="muted">Die Auswahl nach Tageszeit, Wochentag und Gruppe benötigt JavaScript. Ohne JavaScript zeigt diese Seite '
            'die Auswertung für alle Fahrzeuge (Tabellen und Histogramm) und die Zeiträume in den Tabellen.</p></noscript>'
            f'<section class="filter" data-filter hidden><h4>Auswertung nach Zeit, Tagen und Gruppe</h4>'
            '<p class="muted">Wählen Sie Tageszeit, Tage' + (' und Gruppe' if gruppen_opt else '') + '; Kennzahlen und Verteilung gelten dann für diese Auswahl. '
            'Es zählen vollständig aufgezeichnete Stunden mit nutzbarer Uhrzeit (Ortszeit); der Rauschboden ist herausgerechnet, wo belegt. '
            + ('Bei einer Gruppe bleiben alle Fahrzeuge der Auswahl grau sichtbar, farbig ist, was die Kurve der Gruppe davon erklärt.' if gruppen_opt else '') +
            '</p>' + warnung + '<div class="controls">' + felder + '</div>'
            '<div class="filter-ergebnis" aria-live="polite"></div>'
            f'<script type="application/json" class="filter-daten">{json_in_html(daten)}</script></section>')


def hist_summe(hists):
    """Summe von Histogrammen {"ab_kmh", "anzahl"}; None, wenn keines vorhanden ist."""
    hists = [h for h in hists if h]
    if not hists:
        return None
    lo = min(h["ab_kmh"] for h in hists)
    hi = max(h["ab_kmh"] + len(h["anzahl"]) - 1 for h in hists)
    summe = [0] * (hi - lo + 1)
    for h in hists:
        for i, c in enumerate(h["anzahl"]):
            summe[h["ab_kmh"] - lo + i] += c
    return {"ab_kmh": lo, "anzahl": summe}


def histogramm_abschnitt(row, mit_filter=False):
    """Geschwindigkeitsverteilung: Histogramm aller Fahrzeuge der Datei, dazu Tags und Nachts im Vergleich.

    mit_filter: Die Seite hat den Abschnitt mit der Auswahl (JavaScript), der dasselbe Histogramm zeigt. Das feste Histogramm steht
    dann nur noch im noscript-Block fuer Besucher ohne JavaScript; der Vergleich Tag/Nacht bleibt, weil die Auswahl ihn nicht zeigt."""
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
    tz = row.get("teilzeitraeume") or {}
    tag = hist_summe([tz.get(k, {}).get("histogramm") for k in ("vormittag", "nachmittag", "abend")])
    nacht = tz.get("nacht", {}).get("histogramm")
    if tag and nacht and min(sum(tag["anzahl"]), sum(nacht["anzahl"])) >= HIST_MIN_VERGLEICH:
        svg, text = hist_svg([("Tag", "hist-tags", tag), ("Nacht", "hist-nachts", nacht)], limit)
        z.append('<details><summary>Tag und Nacht im Vergleich</summary><figure class="histfig">' + svg +
                 '<figcaption class="muted">Anteil der Fahrzeuge je km/h, getrennt für Tag (6–22 Uhr) und Nacht (22–6 Uhr, Ortszeit). '
                 f'Nur Fahrzeuge mit nutzbarer Zeit. {text}</figcaption></figure></details>')
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


def messung_abschnitt(row, meta_messung, abschnitte, rel, daten=None):
    g = (meta_messung or {}).get("geraet", {})
    limit = row.get("tempolimit_kmh")
    verw = (meta_messung or {}).get("verwaltung", [])
    z = [f'<section class="messung" id="{e(standort_slug(row["datei"]))}"><h3>{e(row["datei"])}</h3>']
    quelle = {"mitteilung_verwaltung": "laut Mitteilung der Verwaltung", "parameter": "vorgegeben"}.get(row.get("tempolimit_quelle"), "aus der DSD-Konfiguration")
    fakten = [("Tempolimit", f'{limit}&nbsp;km/h ({quelle}{"; DSD-Konfiguration " + str(row["tempolimit_dsd_kmh"]) + " km/h" if row.get("tempolimit_dsd_kmh") else ""})' if limit else "unbekannt"),
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
        fakten.append(("Davon mit nutzbarer Zeit", f'{zeit_de(bz["start"])} bis {zeit_de(bz["ende"])}'))
    if g.get("konfiguration"):
        fakten.append(("Gerät (Konfiguration)", e(g["konfiguration"])))
    if g.get("name"):
        fakten.append(("Name im Gerät", e(g["name"])))
    if g.get("erfassung_ab_kmh") is not None:
        fakten.append(("Erfassung ab", f'{g["erfassung_ab_kmh"]}&nbsp;km/h'))
    if g.get("verdeckte_messung"):
        fakten.append(("Anzeige", "verdeckte Messung (Display zeigte nichts an)"))
    z.append('<dl class="facts">' + "".join(f"<dt>{e(k)}</dt><dd>{v}</dd>" for k, v in fakten) + "</dl>")
    wid = widersprueche(row, meta_messung)
    if wid:
        z.append('<div class="notice" role="note"><strong>Widersprüche und Auffälligkeiten zwischen DSD und Mitteilung:</strong><ul>' +
                 "".join(f"<li>{w}</li>" for w in wid) + "</ul></div>")
    if row.get("anzahl_fahrzeuge"):
        z.append(kennzahlen_tabelle(row))
        auswahl = filter_abschnitt(row, daten, standort_slug(row["datei"]))
        z.append(auswahl)
        z.append(histogramm_abschnitt(row, mit_filter=bool(auswahl)))
        z.append(rauschen_abschnitt(row))
        z.append(gruppen_abschnitt(row))
        z.append(schaetzung_tabellen(row))
        z.append(nacht_abschnitt(row))
    else:
        z.append("<p>Die Datei enthält keine Fahrzeugdaten.</p>")
    z.append(uhr_abschnitt(row, abschnitte, rel))
    abgl = "".join(f'<h5>{e(v.get("bezeichnung"))}</h5>' + t for v, t in ((v, abgleich_tabelle(v)) for v in verw) if t)
    if abgl:
        z.append("<h4>Abgleich mit den Angaben der Verwaltung</h4>" + abgl)
    z.append("</section>")
    return "".join(z)


def seite(rel, rows, meta_standort, uhr_dateien, zellen=None):
    name = bereinige(rel)
    meta_nach_datei = {m["datei"]: m for m in (meta_standort or {}).get("messungen", [])}
    eintraege = [(m["datei"], v) for m in (meta_standort or {}).get("messungen", []) for v in m.get("verwaltung", [])]
    kopf = f"""<!doctype html>
<!-- SPDX-License-Identifier: MIT -->
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(name)} – Neuss Dialogdisplays</title>
<meta name="description" content="Geschwindigkeitsmessungen der Dialogdisplays: {e(name)} – Kennzahlen, Geräteuhr und Angaben der Verwaltung.">
<link rel="stylesheet" href="../style.css">
</head>
<body>
<main class="detail">
<nav class="muted" aria-label="Navigation"><a href="../index.html">← Übersicht aller Messungen</a></nav>
<h1>{e(name)}</h1>
<p class="muted">Ordner in der Lieferung der Stadt: <a href="{REPO}/tree/main/{quote_pfad(rel)}">{e(rel)}</a></p>
<p class="notice" role="note"><strong>Hinweis:</strong> {e(HINWEIS)}</p>
"""
    teile = [kopf]
    # Standort laut Verwaltung
    bez = collections.OrderedDict()
    for _, v in eintraege:
        schl = v.get("bezeichnung")
        bez.setdefault(schl, set()).update(f'{(q.get("gremium") or "").strip()}' for q in v.get("quellen", []))
    teile.append("<section><h2>Standort</h2>")
    if bez:
        teile.append("<p>So bezeichnet die Verwaltung die Messstelle:</p><ul>" + "".join(
            f'<li>{e(b)}<span class="muted"> – berichtet im {e("; ".join(sorted(g for g in gr if g)))}</span></li>' for b, gr in bez.items()) + "</ul>")
    else:
        teile.append("<p>Zu dieser Messung liegt keine Beschreibung der Verwaltung vor. Die Verwaltung berichtet Ergebnisse "
                     "je Messstelle seit Februar 2024; für frühere Messungen gibt es nur den Namen des Ordners.</p>")
    limits = sorted({r["tempolimit_kmh"] for r in rows if r.get("tempolimit_kmh")})
    teile.append(f'<p class="muted">Tempolimit laut DSD-Konfiguration: {e(", ".join(str(l) + " km/h" for l in limits)) or "unbekannt"}.</p></section>')
    # Einschätzung und Maßnahmen
    teile.append("<section><h2>Einschätzung und Maßnahmen der Verwaltung</h2>")
    if eintraege:
        teile.append('<p class="muted">Auszüge aus den Mitteilungen der Verwaltung an die Bezirksausschüsse. Die Sätze stehen im '
                     "Wortlaut da (Trennfehler des PDF-Textes repariert); maßgeblich ist das verlinkte Dokument.</p>")
        for datei, v in eintraege:
            teile.append(verwaltung_karte(v, mit_abgleich=False))
    else:
        teile.append("<p>Zu dieser Messung hat die Verwaltung (soweit auffindbar) keine Einschätzung veröffentlicht.</p>")
    teile.append("</section>")
    teile.append("<section><h2>Messungen</h2>")
    for row in sorted(rows, key=lambda r: r["datei"]):
        teile.append(messung_abschnitt(row, meta_nach_datei.get(row["datei"]),
                                       (uhr_dateien.get(f'{rel}/{row["datei"]}') or {}).get("abschnitte", []), rel,
                                       (zellen or {}).get(row["datei"])))
    teile.append("</section>")
    teile.append(f"""<footer class="muted">
<p>Rohdaten und Skripte: <a href="{REPO}/tree/main/{quote_pfad(rel)}">GitHub</a> ·
<a href="{REPO}/blob/main/{quote_pfad(rel)}/metadaten.yaml">metadaten.yaml</a> ·
<a href="{REPO}/blob/main/docs/metadaten.md">Herkunft der Metadaten</a></p>
<p>{e(HINWEIS)}</p>
<p>Lizenz: Daten und Dokumentation <a href="https://creativecommons.org/publicdomain/zero/1.0/deed.de">CC0 1.0</a>, Skripte MIT.</p>
<p><a href="../index.html">Übersicht</a><a href="../impressum.html">Impressum</a><a href="../datenschutz.html">Datenschutz</a></p>
</footer>
</main>
{{FILTER_SKRIPT}}</body>
</html>
""".replace("{FILTER_SKRIPT}", '<script src="../filter.js" defer></script>\n' if any((zellen or {}).values()) else ""))
    return "".join(teile)


def lade_zellen(ordner, rel, rows):
    """Zellendaten (<datei>.zellen.json von dsd2csv.py) der Messungen eines Standorts: {Dateiname: Daten}."""
    erg = {}
    for r in rows:
        pfad = os.path.join(ordner or "", rel, os.path.splitext(r["datei"])[0] + ".zellen.json")
        if ordner and os.path.exists(pfad):
            with open(pfad, encoding="utf-8") as fh:
                erg[r["datei"]] = json.load(fh)
    return erg


def bauen(auswertung, metadaten, uhr, ziel, zellen_ordner=None):
    je_standort = collections.OrderedDict()
    for row in auswertung["standorte"]:
        je_standort.setdefault(row["standort"], []).append(row)
    slugs = {}
    os.makedirs(os.path.join(ziel, "standorte"), exist_ok=True)
    for rel, rows in je_standort.items():
        slug = standort_slug(rel)
        if slug in slugs:
            raise ValueError(f"Seitenname doppelt: {slug} ({rel} und {slugs[slug]})")
        slugs[slug] = rel
        for r in rows:
            if r.get("seite") != f"standorte/{slug}.html":
                raise ValueError(f"Seitenlink passt nicht zum Standort: {r.get('seite')} / {rel}")
        text = seite(rel, rows, metadaten["standorte"].get(rel), uhr["dateien"], lade_zellen(zellen_ordner, rel, rows))
        with open(os.path.join(ziel, "standorte", slug + ".html"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    return slugs


def main():
    hier = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--auswertung", required=True, help="auswertung.json von dsd2csv.py")
    ap.add_argument("--metadaten", default=os.path.join(hier, "belege", "metadaten.json"))
    ap.add_argument("--uhr", default=os.path.join(hier, "belege", "uhr-bewertung.json"))
    ap.add_argument("--ziel", required=True, help="Ausgabeordner (die Seiten landen in <ziel>/standorte/)")
    ap.add_argument("--zellen", help="Ordner mit den .zellen.json von dsd2csv.py (Standard: Ordner der auswertung.json)")
    a = ap.parse_args()
    daten = []
    for pfad in (a.auswertung, a.metadaten, a.uhr):
        with open(pfad, encoding="utf-8") as fh:
            daten.append(json.load(fh))
    slugs = bauen(*daten, a.ziel, a.zellen or os.path.dirname(os.path.abspath(a.auswertung)))
    print(f"{len(slugs)} Standortseiten in {os.path.join(a.ziel, 'standorte')}", file=sys.stderr)


if __name__ == "__main__":
    main()
