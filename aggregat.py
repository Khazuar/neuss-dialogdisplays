# SPDX-License-Identifier: MIT
"""Bereinigtes Aggregat je Datei: Fahrzeuge je Tag, Stunde und km/h in Ortszeit (docs/ und DATEN.md).

Grundlage sind genau die Fahrzeuge, die auch in die Kennzahlen eingehen: nur Fahrzeuge mit nutzbarer Zeit, auf Ortszeit umgerechnet
(Sommerzeit), nach Abzug des Rauschbodens und des Regenanteils (rauschen.py), je Fahrzeug einem Abschnitt der Messreihe zugeordnet
(bruch.py). Es zaehlt nur, was dsd2csv.py ohnehin berechnet; dieses Modul fasst es zusammen und rechnet nichts neu an.
Die Ausgabe ist JSON-faehig (Zwischenspeicher); daten_bauen.py macht daraus die CSV-Dateien.

Zeilen:
  stunden  [Datum, Stunde, Abschnitt, voll, [km/h, Anzahl, km/h, Anzahl, ...]]   voll = 1, wenn die Stunde vollstaendig in einem
           Zeitabschnitt mit nutzbarer Uhr aufgezeichnet ist (die Zellen der Detailseiten zaehlen nur solche Stunden)
  tage     [Abschnitt, Datum, Fahrzeuge, Mittel, V85, V95, V99, Einhaltung %, qualifizierte Einhaltung %]
  luecken  [erste Stunde, letzte Stunde, Zahl der Stunden]: Stunden zwischen erstem und letztem Fahrzeug, die nicht vollstaendig
           aufgezeichnet sind (Anfang und Ende der Messung, Luecken, Uhrspruenge)
"""
import bisect
import collections
import datetime as dt

import rauschen

SPALTEN_STUNDEN = ["messung_id", "abschnitt_nr", "datum", "wochentag", "stunde", "zeitraum", "ferien", "feiertag", "voll", "kmh", "anzahl"]
ISO_STUNDE = "%Y-%m-%d %H:00"


def zeitraum_je_stunde(zeitscheiben):
    """{Stunde: Name} aus gruppen.ZEITSCHEIBEN [(Name, von, bis)], etwa {22: 'nacht', 23: 'nacht', 0: 'nacht', ...}."""
    out = {}
    for name, von, bis in zeitscheiben:
        for i in range((bis - von) % 24 or 24):
            out[(von + i) % 24] = name
    return out


def bauen(bereinigt, spannen, grenzen, limit, stats, min_kmh=0):
    """Aggregat einer Datei (siehe Modulkopf).

    bereinigt: [(Ortszeit, v)] nach Abzug des Rauschbodens, spannen: [(erste, letzte Ortszeit)] je Abschnitt mit nutzbarer Zeit,
    grenzen: erste Tage der Abschnitte 2, 3, ... (aufsteigende Daten), stats: dsd2csv.stats (damit Tages- und Dateikennzahlen
    dieselbe Rechnung benutzen)."""
    abgedeckt = rauschen.abgedeckte_stunden(spannen)
    je_stunde = collections.defaultdict(collections.Counter)  # (Datum, Stunde) -> {v: Anzahl}
    je_tag = collections.defaultdict(list)  # (Abschnitt, Datum) -> [(Zeit, v)]
    for f in bereinigt:
        t, v = f
        d = t.date()
        je_stunde[(d, t.hour)][v] += 1
        je_tag[(1 + bisect.bisect_right(grenzen, d), d)].append(f)
    stunden = []
    for (d, h), z in sorted(je_stunde.items()):
        flach = []
        for v in sorted(z):
            flach += [v, z[v]]
        stunden.append([d.isoformat(), h, 1 + bisect.bisect_right(grenzen, d), 1 if (d, h) in abgedeckt else 0, flach])
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
        erste, letzte = min(je_stunde), max(je_stunde)
        h = dt.datetime.combine(erste[0], dt.time(erste[1]))
        ende = dt.datetime.combine(letzte[0], dt.time(letzte[1]))
        offen = None  # [erste Stunde, letzte Stunde, Zahl]
        while h <= ende:
            if (h.date(), h.hour) in abgedeckt:
                if offen:
                    luecken.append(offen)
                    offen = None
            elif offen:
                offen[1], offen[2] = h.strftime(ISO_STUNDE), offen[2] + 1
            else:
                offen = [h.strftime(ISO_STUNDE), h.strftime(ISO_STUNDE), 1]
            h += dt.timedelta(hours=1)
        if offen:
            luecken.append(offen)
    return {"stunden": stunden, "tage": tage, "luecken": luecken}
