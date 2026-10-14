# SPDX-License-Identifier: MIT
"""Bereinigtes Aggregat je Datei: Fahrzeuge je Tag, Stunde und km/h in Ortszeit mit UTC-Versatz (DATEN.md).

Grundlage sind genau die Fahrzeuge, die auch in die Kennzahlen eingehen: nur Fahrzeuge mit nutzbarer Zeit, auf Ortszeit umgerechnet
(Sommerzeit), nach Abzug des Rauschbodens und des Regenanteils (rauschen.py), je Fahrzeug einem Abschnitt der Messreihe zugeordnet
(bruch.py). Es zaehlt nur, was dsd2csv.py ohnehin berechnet; dieses Modul fasst es zusammen und rechnet nichts neu an.
Die Ausgabe ist JSON-faehig (Zwischenspeicher); daten_bauen.py macht daraus die CSV-Dateien.

Die Stunden sind UTC-Stunden (die Geraeteuhr ist UTC plus ein fester Versatz, die UTC-Zeit je Fahrzeug also eindeutig) und werden mit
Ortszeit-Datum, Ortszeit-Stunde und UTC-Versatz beschriftet. So ist auch die doppelte Stunde der Zeitumstellung im Herbst
(2 Uhr mit Versatz 2 und 2 Uhr mit Versatz 1) in zwei Zeilen getrennt; Berlin hat immer ganze Stunden Versatz, die Stundengrenzen
sind in UTC und Ortszeit dieselben.

Zeilen:
  stunden  [Datum, Stunde, UTC-Versatz, Abschnitt, voll, [km/h, Anzahl, km/h, Anzahl, ...]], nach UTC geordnet; Datum und Stunde in Ortszeit,
           voll = 1, wenn die Stunde vollstaendig in einem Zeitabschnitt mit nutzbarer Uhr aufgezeichnet ist (die Zellen der Detailseiten
           zaehlen nur solche Stunden)
  tage     [Abschnitt, Datum, Fahrzeuge, Mittel, V85, V95, V99, Einhaltung %, qualifizierte Einhaltung %]  (Ortszeit-Tage)
  luecken  [erste Stunde, letzte Stunde (UTC, JJJJ-MM-TTTHH:00Z), Zahl der Stunden]: Stunden zwischen erstem und letztem Fahrzeug, die nicht
           vollstaendig aufgezeichnet sind (Anfang und Ende der Messung, Luecken, Uhrspruenge)
"""
import bisect
import collections
import datetime as dt

SPALTEN_STUNDEN = ["messung_id", "abschnitt_nr", "datum", "wochentag", "stunde", "utc_versatz_h", "zeitraum", "ferien", "feiertag", "voll", "kmh", "anzahl"]
ISO_UTC = "%Y-%m-%dT%H:00Z"
STUNDE = dt.timedelta(hours=1)


def zeitraum_je_stunde(zeitscheiben):
    """{Stunde: Name} aus gruppen.ZEITSCHEIBEN [(Name, von, bis)], etwa {22: 'nacht', 23: 'nacht', 0: 'nacht', ...}."""
    out = {}
    for name, von, bis in zeitscheiben:
        for i in range((bis - von) % 24 or 24):
            out[(von + i) % 24] = name
    return out


def abgedeckte_stunden_utc(spannen_utc):
    """Menge der UTC-Stunden (Beginn), die vollstaendig in einem Abschnitt mit nutzbarer Uhr liegen."""
    s = set()
    for a, b in spannen_utc:
        h = a.replace(minute=0, second=0, microsecond=0)
        if h < a:
            h += STUNDE
        while h + STUNDE <= b:
            s.add(h)
            h += STUNDE
    return s


def bauen(bereinigt, utc, spannen_utc, versatz, grenzen, limit, stats, min_kmh=0):
    """Aggregat einer Datei (siehe Modulkopf).

    bereinigt: [(Ortszeit, v)] nach Abzug des Rauschbodens, utc: {id(Fahrzeug): UTC-Zeit} und spannen_utc: [(erste, letzte UTC-Zeit)] je
    Abschnitt mit nutzbarer Zeit (dsd2csv.analysiere_uhr mit mit_utc=True), versatz: Funktion UTC-Zeit -> UTC-Versatz der Ortszeit in Stunden
    (dsd2csv.utc_versatz_h), grenzen: erste Tage der Abschnitte 2, 3, ... (aufsteigende Daten), stats: dsd2csv.stats (damit Tages- und
    Dateikennzahlen dieselbe Rechnung benutzen)."""
    abgedeckt = abgedeckte_stunden_utc(spannen_utc)
    je_stunde = collections.defaultdict(collections.Counter)  # UTC-Stunde -> {v: Anzahl}
    je_tag = collections.defaultdict(list)  # (Abschnitt, Ortszeit-Datum) -> [(Zeit, v)]
    for f in bereinigt:
        t, v = f
        u = utc[id(f)]
        je_stunde[u.replace(minute=0, second=0, microsecond=0)][v] += 1
        je_tag[(1 + bisect.bisect_right(grenzen, t.date()), t.date())].append(f)
    stunden = []
    for h, z in sorted(je_stunde.items()):
        off = versatz(h)
        lokal = h + dt.timedelta(hours=off)
        flach = []
        for v in sorted(z):
            flach += [v, z[v]]
        stunden.append([lokal.date().isoformat(), lokal.hour, off, 1 + bisect.bisect_right(grenzen, lokal.date()), 1 if h in abgedeckt else 0, flach])
    tage = []
    for (nr, d), liste in sorted(je_tag.items()):
        s = stats(liste, limit, min_kmh)
        if not s:
            continue
        g, e = s["geschwindigkeit_kmh"], s.get("einhaltung") or {}
        tage.append([nr, d.isoformat(), s["anzahl_fahrzeuge"], g["mittel"], g["v85"], g["v95"], g["v99"],
                     e.get("einhaltungsquote_prozent"), e.get("qualifizierte_einhaltungsquote_prozent")])
    luecken = []
    if je_stunde:
        h, ende = min(je_stunde), max(je_stunde)
        offen = None  # [erste Stunde, letzte Stunde, Zahl]
        while h <= ende:
            if h in abgedeckt:
                if offen:
                    luecken.append(offen)
                    offen = None
            elif offen:
                offen[1], offen[2] = h.strftime(ISO_UTC), offen[2] + 1
            else:
                offen = [h.strftime(ISO_UTC), h.strftime(ISO_UTC), 1]
            h += STUNDE
        if offen:
            luecken.append(offen)
    return {"stunden": stunden, "tage": tage, "luecken": luecken}
