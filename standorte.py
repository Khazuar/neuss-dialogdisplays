# SPDX-License-Identifier: MIT
"""Standort der Messstellen: Koordinaten und Unsicherheit aus Strassennamen, Hausnummern und Ortsangaben.

Die DSD-Dateien enthalten keine Position. Bekannt sind die Strasse (Ordnername), oft eine Hausnummer, "Ecke X" oder
"Hoehe X", die Fahrtrichtung ("FR Kaarst") und Angaben in den Mitteilungen der Verwaltung und den Antraegen im
Ratsinformationssystem. Die Geraete haengen an Laternenmasten am Strassenrand.

Als Karte dienen die Hauskoordinaten der Stadt Neuss (belege/neuss-adressen.csv, Geobasis NRW, Gebaeudereferenzen,
dl-de/zero-2-0; tools/adressen_laden.py). Eine Strassenachse liegt nicht vor, nur die Punkte der Haeuser.

Hinweise (je Ordner), nach Genauigkeit:
  adresse            Hausnummer ("Hauptstrasse 13a", "Hoehe Nr. 4", "ggue. Nr. 3", "Nr. 86-88")
  zwischen_nr        zwischen zwei Hausnummern
  kreuzung           Ecke oder Hoehe einer Querstrasse
  zwischen_strassen  Abschnitt zwischen zwei Querstrassen
  strasse            nur der Strassenname: Mitte der Strasse, Unsicherheit = Ausdehnung der Strasse
Jeder Hinweis liefert einen Kreis (Mittelpunkt, Radius). Der Radius ist die angenommene Unsicherheit (siehe ANNAHMEN),
kein gemessener Wert: es gibt keine Vergleichskoordinaten. Das Ergebnis ist der Hinweis mit dem kleinsten Radius; die
anderen Hinweise werden gegengeprueft (liegen sie im Kreis?) und bei Widerspruch vermerkt.

Hinweise aus dem Ordnernamen liest der Code selbst; weitere (Mitteilungen, Antraege, Berichte der Verwaltung) stehen
mit Zitat und Quelle in belege/standort-hinweise.json. Eine Hausnummer in einem blossen Standortvorschlag der
Bezirksausschuesse ("vorschlag") wird nur uebernommen, wenn sie innerhalb des Kreises der belegten Angaben liegt; das
Ergebnis gilt dann als "vermutet".

Aufruf:
  python3 -I standorte.py [--adressen belege/neuss-adressen.csv] [--hinweise belege/standort-hinweise.json]
                          [--metadaten belege/metadaten.json]
    -> Tabelle aller Standortordner. metadaten.py schreibt dieselben Ergebnisse in die metadaten.yaml.
"""
import argparse
import collections
import csv
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I nimmt das Skriptverzeichnis nicht auf
from uhr_belege import messort_namen, schluessel  # noqa: E402

# Angenommene Unsicherheiten (Radius in Metern, ungefaehr 90 %-Bereich). Sie stammen aus der Anordnung der Haeuser
# (Abstand benachbarter Hausnummern, Haus zur Strassenmitte), nicht aus einem Vergleich mit bekannten Standorten.
ANNAHMEN = {
    "adresse_m": 30,             # Laterne in der Naehe des Hauses; die Hauskoordinate liegt im Gebaeude
    "gegenueber_zuschlag_m": 15,  # "ggue. Nr.": andere Strassenseite
    "luecke_anteil": 0.5,        # fehlende Hausnummer: halber Abstand der Nachbarnummern kommt dazu
    "zwischen_nr_m": 25,         # plus halber Abstand der beiden Hausnummern
    "kreuzung_m": 40,            # naechstes Haeuserpaar der beiden Strassen liegt an der Kreuzung, nicht auf ihr
    "zwischen_strassen_m": 25,   # plus Abstand zu den beiden Kreuzungen
    "strasse_perzentil": 90,     # Radius um die Mitte der Strasse, der 90 % der Haeuser enthaelt
    "strasse_min_m": 40,
    "vorschlag_min_m": 60,       # blosse Standortvorschlaege: mindestens so unsicher
    "anschluss_max_m": 60,       # Querstrasse zaehlt nur, wenn sie hoechstens so weit von der Strasse beginnt
    "cluster_m": 400,            # Haeuser gleichen Namens mit mehr Abstand sind getrennte Strassenabschnitte
    "peilung_max_radius_m": 300,  # die Fahrtrichtung wird nur angegeben, wenn der Standort so genau bekannt ist
}
BEWERTUNG = {"manuell": 0, "belegt": 1, "benannt": 2, "vorschlag": 3}  # manuell: vom Betreiber dieses Repositories korrigiert


# ------------------------------------------------------------------ Koordinaten (ETRS89 / UTM 32 <-> WGS84)

_A, _F = 6378137.0, 1 / 298.257222101  # GRS80, fuer die Zwecke hier gleich WGS84 (< 1 m)
_N = _F / (2 - _F)
_AA = _A / (1 + _N) * (1 + _N ** 2 / 4 + _N ** 4 / 64)
_K0, _E0, _LON0 = 0.9996, 500000.0, math.radians(9.0)
_ALPHA = (_N / 2 - 2 * _N ** 2 / 3 + 5 * _N ** 3 / 16 + 41 * _N ** 4 / 180,
          13 * _N ** 2 / 48 - 3 * _N ** 3 / 5 + 557 * _N ** 4 / 1440,
          61 * _N ** 3 / 240 - 103 * _N ** 4 / 140,
          49561 * _N ** 4 / 161280)
_BETA = (_N / 2 - 2 * _N ** 2 / 3 + 37 * _N ** 3 / 96 - _N ** 4 / 360,
         _N ** 2 / 48 + _N ** 3 / 15 - 437 * _N ** 4 / 1440,
         17 * _N ** 3 / 480 - 37 * _N ** 4 / 840,
         4397 * _N ** 4 / 161280)
_DELTA = (2 * _N - 2 * _N ** 2 / 3 - 2 * _N ** 3 + 116 * _N ** 4 / 45,
          7 * _N ** 2 / 3 - 8 * _N ** 3 / 5 - 227 * _N ** 4 / 45,
          56 * _N ** 3 / 15 - 136 * _N ** 4 / 35,
          4279 * _N ** 4 / 630)


def utm32_zu_wgs84(ost, nord):
    """(Breite, Laenge) in Grad aus ETRS89 / UTM 32 (EPSG:25832)."""
    xi = nord / (_K0 * _AA)
    eta = (ost - _E0) / (_K0 * _AA)
    xi2 = xi - sum(b * math.sin(2 * j * xi) * math.cosh(2 * j * eta) for j, b in enumerate(_BETA, 1))
    eta2 = eta - sum(b * math.cos(2 * j * xi) * math.sinh(2 * j * eta) for j, b in enumerate(_BETA, 1))
    chi = math.asin(math.sin(xi2) / math.cosh(eta2))
    breite = chi + sum(dl * math.sin(2 * j * chi) for j, dl in enumerate(_DELTA, 1))
    laenge = _LON0 + math.atan2(math.sinh(eta2), math.cos(xi2))
    return math.degrees(breite), math.degrees(laenge)


def wgs84_zu_utm32(breite, laenge):
    """(Ost, Nord) in Metern, ETRS89 / UTM 32."""
    phi, dl = math.radians(breite), math.radians(laenge) - _LON0
    c = 2 * math.sqrt(_N) / (1 + _N)
    t = math.sinh(math.atanh(math.sin(phi)) - c * math.atanh(c * math.sin(phi)))
    xi = math.atan2(t, math.cos(dl))
    eta = math.atanh(math.sin(dl) / math.sqrt(1 + t * t))
    ost = _E0 + _K0 * _AA * (eta + sum(a * math.cos(2 * j * xi) * math.sinh(2 * j * eta) for j, a in enumerate(_ALPHA, 1)))
    nord = _K0 * _AA * (xi + sum(a * math.sin(2 * j * xi) * math.cosh(2 * j * eta) for j, a in enumerate(_ALPHA, 1)))
    return ost, nord


# ------------------------------------------------------------------ Adressverzeichnis

Adresse = collections.namedtuple("Adresse", "schluessel strasse nr zusatz ost nord")


def abstand(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _editierabstand_hoechstens_1(a, b):
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    kurz, lang = (a, b) if len(a) < len(b) else (b, a)
    i = 0
    while i < len(kurz) and kurz[i] == lang[i]:
        i += 1
    return kurz[i:] == lang[i + 1:]


class Verzeichnis:
    """Hauskoordinaten, gefunden ueber den Strassennamen (schluessel(): ss/sz, Umlaute, Leerzeichen egal)."""

    def __init__(self, adressen):
        self.je_name = collections.defaultdict(list)
        self.namen = {}
        for a in adressen:
            k = schluessel(a.strasse)
            self.je_name[k].append(a)
            self.namen.setdefault(k, a.strasse)

    @classmethod
    def laden(cls, pfad):
        with open(pfad, encoding="utf-8", newline="") as fh:
            r = csv.DictReader(fh, delimiter=";")
            return cls(Adresse(z["schluessel"], z["strasse"], int(z["hausnr"] or 0), z["zusatz"].lower(),
                               float(z["ost"]), float(z["nord"])) for z in r)

    def strasse(self, name):
        """(Adressen, gefundener Name, Hinweis) oder ([], None, None). Eine Abweichung um einen Buchstaben
        ("Eichendorfstrasse" statt "Eichendorffstrasse") gilt, wenn es genau einen Treffer gibt."""
        k = schluessel(name)
        if k in self.je_name:
            return self.je_name[k], self.namen[k], None
        if len(k) >= 9:
            nah = [n for n in self.je_name if _editierabstand_hoechstens_1(n, k)]
            if len(nah) == 1:
                return self.je_name[nah[0]], self.namen[nah[0]], "Schreibweise weicht um einen Buchstaben ab"
        return [], None, None


def abschnitte(punkte, grenze):
    """Gruppen von Punkten, die ueber Luecken von hoechstens `grenze` Metern zusammenhaengen."""
    rest = list(range(len(punkte)))
    gruppen = []
    while rest:
        stapel, gruppe = [rest.pop()], []
        while stapel:
            i = stapel.pop()
            gruppe.append(i)
            nah = [j for j in rest if abstand((punkte[i].ost, punkte[i].nord), (punkte[j].ost, punkte[j].nord)) <= grenze]
            for j in nah:
                rest.remove(j)
            stapel += nah
        gruppen.append([punkte[i] for i in gruppe])
    return sorted(gruppen, key=len, reverse=True)


def mitte(punkte):
    """Das Haus, das die kleinste Abstandssumme zu den anderen hat (liegt an der Strasse, anders als der Schwerpunkt)."""
    xy = [(p.ost, p.nord) for p in punkte]
    return min(xy, key=lambda a: sum(abstand(a, b) for b in xy))


def perzentil(werte, p):
    w = sorted(werte)
    return w[min(len(w) - 1, int(math.ceil(p / 100.0 * len(w))) - 1)]


def naechstes_paar(a, b):
    """Das Haeuserpaar (eins aus a, eins aus b) mit dem kleinsten Abstand: (Abstand, Punkt aus a, Punkt aus b)."""
    beste = None
    for p in a:
        for q in b:
            d = abstand((p.ost, p.nord), (q.ost, q.nord))
            if beste is None or d < beste[0]:
                beste = (d, p, q)
    return beste


# ------------------------------------------------------------------ Hinweise bewerten

def _ergebnis(art, xy, radius, beschreibung, **extra):
    e = {"art": art, "ost": xy[0], "nord": xy[1], "radius_m": radius, "beschreibung": beschreibung}
    e.update(extra)
    return e


def _hausnummer_text(nr, zusatz):
    return "%d%s" % (nr, zusatz)


def _teile_nr(text):
    """"13a" -> (13, "a"); "86" -> (86, "")."""
    m = re.match(r"^(\d+)\s*([a-z]?)$", text.strip().lower())
    return (int(m.group(1)), m.group(2)) if m else None


def bewerte_adresse(h, verz):
    adr, name, abw = verz.strasse(h["strasse"])
    if not adr:
        return None, "Straße nicht im Adressverzeichnis"
    von = _teile_nr(str(h["nr"]))
    bis = _teile_nr(str(h["bis"])) if h.get("bis") else von
    if not von or not bis:
        return None, "Hausnummer nicht lesbar"
    treffer = [a for a in adr if von[0] <= a.nr <= bis[0] and (von[0] != a.nr or not von[1] or a.zusatz.startswith(von[1]))]
    if von[0] == bis[0] and von[1]:
        treffer = [a for a in treffer if a.zusatz.startswith(von[1])] or [a for a in adr if a.nr == von[0]]
    grund = "Hausnummer %s im Verzeichnis" % (_hausnummer_text(*von) if bis == von else "%s–%s" % (_hausnummer_text(*von), _hausnummer_text(*bis)))
    luecke = 0.0
    if not treffer:
        # Nummer fehlt: Mittel der naechsten kleineren und groesseren Nummer
        kleiner = [a for a in adr if a.nr < von[0]]
        groesser = [a for a in adr if a.nr > bis[0]]
        nachbarn = []
        if kleiner:
            nachbarn += [a for a in kleiner if a.nr == max(k.nr for k in kleiner)]
        if groesser:
            nachbarn += [a for a in groesser if a.nr == min(g.nr for g in groesser)]
        if not nachbarn:
            return None, "Hausnummer nicht im Verzeichnis"
        treffer = nachbarn
        luecke = max(abstand((p.ost, p.nord), (q.ost, q.nord)) for p in treffer for q in treffer) * ANNAHMEN["luecke_anteil"]
        grund = "Hausnummer %s fehlt im Verzeichnis, Mittel der Nachbarnummern" % _hausnummer_text(*von)
    gruppen = abschnitte(treffer, ANNAHMEN["cluster_m"])
    if len(gruppen) > 1:
        # gleiche Nummer in getrennten Abschnitten: nicht entscheidbar
        xy = mitte(treffer)
        spanne = max(abstand((p.ost, p.nord), (q.ost, q.nord)) for p in treffer for q in treffer)
        return _ergebnis("adresse", xy, round(spanne / 2 + ANNAHMEN["adresse_m"]), grund + ", aber in %d getrennten Abschnitten" % len(gruppen),
                         mehrdeutig=True, strasse=name, abweichung=abw), None
    punkte = [(a.ost, a.nord) for a in treffer]
    xy = (sum(p[0] for p in punkte) / len(punkte), sum(p[1] for p in punkte) / len(punkte))
    spanne = max(abstand(p, q) for p in punkte for q in punkte) / 2
    radius = ANNAHMEN["adresse_m"] + spanne + luecke
    rolle = h.get("rolle", "hoehe")
    if rolle == "gegenueber":
        radius += ANNAHMEN["gegenueber_zuschlag_m"]
    return _ergebnis("adresse", xy, round(radius), grund + (", gegenüber" if rolle == "gegenueber" else ""),
                     strasse=name, abweichung=abw), None


def bewerte_zwischen_nr(h, verz):
    adr, name, abw = verz.strasse(h["strasse"])
    if not adr:
        return None, "Straße nicht im Adressverzeichnis"
    punkte = [(a.ost, a.nord) for a in adr if h["von"] <= a.nr <= h["bis"]]
    if not punkte:
        return None, "Hausnummern nicht im Verzeichnis"
    xy = (sum(p[0] for p in punkte) / len(punkte), sum(p[1] for p in punkte) / len(punkte))
    spanne = max(abstand(p, q) for p in punkte for q in punkte) / 2
    return _ergebnis("zwischen_nr", xy, round(ANNAHMEN["zwischen_nr_m"] + spanne),
                     "zwischen Nr. %d und %d" % (h["von"], h["bis"]), strasse=name, abweichung=abw), None


def _kreuzung(adr, quer, verz):
    """(Mittelpunkt, Abstand der Haeuser, Name der Querstrasse) oder (None, Grund)."""
    adr_q, name_q, abw_q = verz.strasse(quer)
    if not adr_q:
        return None, "Querstraße „%s“ nicht im Adressverzeichnis" % quer
    d, p, q = naechstes_paar(adr, adr_q)
    if d > ANNAHMEN["anschluss_max_m"] * 2:
        return None, "Querstraße „%s“ beginnt nicht an dieser Straße (nächstes Haus %d m entfernt)" % (name_q, round(d))
    return ((p.ost + q.ost) / 2, (p.nord + q.nord) / 2, d, name_q), None


def bewerte_kreuzung(h, verz):
    adr, name, abw = verz.strasse(h["strasse"])
    if not adr:
        return None, "Straße nicht im Adressverzeichnis"
    k, grund = _kreuzung(adr, h["quer"], verz)
    if k is None:
        return None, grund
    return _ergebnis("kreuzung", (k[0], k[1]), round(ANNAHMEN["kreuzung_m"] + k[2] / 2),
                     "an der Kreuzung mit %s" % k[3], strasse=name, abweichung=abw), None


def bewerte_zwischen_strassen(h, verz):
    adr, name, abw = verz.strasse(h["strasse"])
    if not adr:
        return None, "Straße nicht im Adressverzeichnis"
    ka, grund = _kreuzung(adr, h["a"], verz)
    if ka is None:
        return None, grund
    kb, grund = _kreuzung(adr, h["b"], verz)
    if kb is None:
        return None, grund
    mx, my = (ka[0] + kb[0]) / 2, (ka[1] + kb[1]) / 2
    # auf ein Haus der Strasse legen, das der Mitte am naechsten ist (die Strasse kann gekruemmt sein)
    haus = min(adr, key=lambda p: abstand((p.ost, p.nord), (mx, my)))
    xy = (haus.ost, haus.nord)
    radius = max(abstand(xy, ka[:2]), abstand(xy, kb[:2])) + ANNAHMEN["zwischen_strassen_m"]
    return _ergebnis("zwischen_strassen", xy, round(radius), "zwischen %s und %s" % (ka[3], kb[3]), strasse=name, abweichung=abw), None


def bewerte_strasse(h, verz):
    adr, name, abw = verz.strasse(h["strasse"])
    if not adr:
        return None, "Straße nicht im Adressverzeichnis"
    xy = mitte(adr)
    d = [abstand((a.ost, a.nord), xy) for a in adr]
    radius = max(ANNAHMEN["strasse_min_m"], perzentil(d, ANNAHMEN["strasse_perzentil"]))
    if len(adr) < 4:
        radius = max(radius, 60)
    n = sum(1 for g in abschnitte(adr, ANNAHMEN["cluster_m"]) if len(g) >= 3)  # einzelne abseits gelegene Nummern zaehlen nicht
    return _ergebnis("strasse", xy, round(radius), "Mitte der Straße (%d Hausnummern)" % len(adr), strasse=name, abweichung=abw,
                     abschnitte=n, punkte=[(a.ost, a.nord) for a in adr]), None


BEWERTER = {"adresse": bewerte_adresse, "zwischen_nr": bewerte_zwischen_nr, "kreuzung": bewerte_kreuzung,
            "zwischen_strassen": bewerte_zwischen_strassen, "strasse": bewerte_strasse}


# ------------------------------------------------------------------ Hinweise aus Namen

def _vorspann_ab(name):
    erster = name.split("/")[0]
    return re.sub(r"^\d+(?:[-_]\d{4})?_\s*", "", erster).replace("_", " ").strip()


_NR = r"(\d+\s?[a-zA-Z]?)"
# Fahrtrichtung und Messart stehen nicht im Ortsteil des Namens (die Fahrtrichtung kommt aus den Mitteilungen)
IGNORIERT = re.compile(r"^(FR\b|Tempo\b|beidseitig|Wiederholungsmessung|Stationär)", re.I)


def hinweise_aus_text(text, verz, nur_zusatz=False):
    """Hinweise aus einer Ortsangabe wie "Bauerbahn, ggü. Nr. 3", "Cyriakusstraße 86-88", "Krokusstraße (Ecke Tulpenstraße)".

    Gibt (hinweise, unbekannt) zurueck; unbekannt sind Teile, die nichts Verwertbares ergaben (Schulen, Eingaenge ...).
    """
    hinweise, unbekannt = [], []
    zusaetze = re.findall(r"\(([^)]*)\)", text)
    rest = re.sub(r"\([^)]*\)", " ", text)
    if "," in rest:
        rest, nach = rest.split(",", 1)
        zusaetze += [t for t in re.split(r",", nach) if t.strip()]
    rest = rest.strip()
    strasse, nr, bis = rest, None, None
    m = re.match(r"^(.*?)\s+" + _NR + r"(?:\s*-\s*" + _NR + r")?$", rest)
    if m and not nur_zusatz:
        strasse, nr, bis = m.group(1).strip(), m.group(2).replace(" ", ""), (m.group(3) or "").replace(" ", "") or None
    if not strasse:
        return [], [text]
    for z in zusaetze:
        z = z.strip()
        g = re.match(r"^(?:gg[üu]\.?|gegenüber)\s*(?:Nr\.?)?\s*" + _NR + r"$", z, re.I)
        e = re.match(r"^(?:Ecke|Höhe|Hoehe)\s+(.+)$", z, re.I)
        zw = re.match(r"^zwischen\s+(.+?)\s+und\s+(.+)$", z, re.I)
        if g:
            hinweise.append({"art": "adresse", "strasse": strasse, "nr": g.group(1).replace(" ", ""), "rolle": "gegenueber", "text": z})
        elif zw:
            hinweise.append({"art": "zwischen_strassen", "strasse": strasse, "a": zw.group(1).strip(), "b": zw.group(2).strip(), "text": z})
        elif e:
            hinweise.append({"art": "kreuzung", "strasse": strasse, "quer": e.group(1).strip(), "text": z})
        elif verz.strasse(z)[0] and schluessel(z) != schluessel(strasse):
            hinweise.append({"art": "kreuzung", "strasse": strasse, "quer": z, "text": z})
        elif not IGNORIERT.match(z):
            unbekannt.append(z)
    if nr:
        hinweise.append({"art": "adresse", "strasse": strasse, "nr": nr, "bis": bis, "rolle": "hoehe", "text": rest})
    hinweise.append({"art": "strasse", "strasse": strasse, "text": strasse})
    return hinweise, unbekannt


def hinweise_aus_ordner(rel, verz):
    """Hinweise, die im Ordnernamen stehen. Mehrere Strassen im Namen ("Lupinen_Nierenhofstraße") ergeben je einen Hinweis."""
    name = _vorspann_ab(rel)
    if name.lower().startswith("stationär") or name.lower().startswith("station"):
        name = re.sub(r"^\S+\s+", "", name)
    hinweise, unbekannt = hinweise_aus_text(name, verz)
    if not verz.strasse(hinweise[-1]["strasse"])[0]:
        # Name ohne Treffer: "Lupinen_Nierenhofstraße" sind zwei Strassen, die sich vermutlich treffen
        teile = [t for t in re.sub(r"^\d+(?:[-_]\d{4})?_\s*", "", rel.split("/")[0]).split("_") if t.strip()]
        gefunden = []
        for t in teile:
            for kandidat in (t, t + "straße", t + "weg"):
                if verz.strasse(kandidat)[0]:
                    gefunden.append(kandidat)
                    break
        if len(gefunden) >= 2:
            hinweise = [{"art": "kreuzung", "strasse": gefunden[0], "quer": gefunden[1], "text": " / ".join(gefunden)}]
            hinweise += [{"art": "strasse", "strasse": g, "text": g} for g in gefunden]
            unbekannt = []
        elif gefunden:
            hinweise, unbekannt = hinweise_aus_text(gefunden[0], verz)
    for h in hinweise:
        h["quelle"] = {"typ": "ordnername", "name": rel.split("/")[0]}
        h["stufe"] = "benannt"
    return hinweise, unbekannt


# ------------------------------------------------------------------ Fahrtrichtung

def achse(punkte, xy, k=12):
    """Richtung der Strasse bei `xy` aus den naechsten Haeusern: (Winkel in Grad von Nord, 0..180, Streuung quer/laengs)."""
    nah = sorted(punkte, key=lambda p: abstand((p.ost, p.nord), xy))[:k]
    if len(nah) < 5:
        return None
    mx = sum(p.ost for p in nah) / len(nah)
    my = sum(p.nord for p in nah) / len(nah)
    sxx = sum((p.ost - mx) ** 2 for p in nah) / len(nah)
    syy = sum((p.nord - my) ** 2 for p in nah) / len(nah)
    sxy = sum((p.ost - mx) * (p.nord - my) for p in nah) / len(nah)
    tr, det = sxx + syy, sxx * syy - sxy * sxy
    l1 = tr / 2 + math.sqrt(max(tr * tr / 4 - det, 0))
    l2 = tr / 2 - math.sqrt(max(tr * tr / 4 - det, 0))
    if l1 <= 0:
        return None
    theta = 0.5 * math.atan2(2 * sxy, sxx - syy)  # Winkel der Hauptachse gegen die Ost-Achse
    grad = (90 - math.degrees(theta)) % 180      # als Kompasswinkel (von Nord im Uhrzeigersinn)
    return grad, math.sqrt(max(l2, 0) / l1)


def fahrtrichtung(ziel, strasse, xy, verz):
    """Kompassrichtung des Verkehrs bei `xy`, wenn "FR ziel" eine Querstrasse ist, die an der Strasse beginnt."""
    adr, _, _ = verz.strasse(strasse)
    adr_z, name_z, _ = verz.strasse(ziel)
    if not adr or not adr_z:
        return None
    d, p, q = naechstes_paar(adr, adr_z)
    if d > ANNAHMEN["anschluss_max_m"] * 2:
        return None
    zx, zy = (p.ost + q.ost) / 2, (p.nord + q.nord) / 2
    if abstand((zx, zy), xy) < 40:
        return None
    a = achse(adr, xy)
    if a is None or a[1] > 0.5:
        return None
    grad, quer = a
    # die Hauptachse zeigt in zwei Richtungen; die Seite des Ziels waehlen
    dx, dy = zx - xy[0], zy - xy[1]
    rx, ry = math.sin(math.radians(grad)), math.cos(math.radians(grad))
    if rx * dx + ry * dy < 0:
        grad = (grad + 180) % 360
    return {"ziel": name_z, "peilung_grad": round(grad), "unsicherheit_grad": round(10 + math.degrees(math.atan(quer)))}


# ------------------------------------------------------------------ Entscheidung

def _vereinigung(a, b):
    """Kleinster Kreis um die Kreise a und b (Mittelpunkt ost/nord, radius_m); sonst wie a."""
    d = abstand((a["ost"], a["nord"]), (b["ost"], b["nord"]))
    if d + b["radius_m"] <= a["radius_m"]:
        return a
    if d + a["radius_m"] <= b["radius_m"]:
        return dict(a, ost=b["ost"], nord=b["nord"], radius_m=b["radius_m"])
    r = (d + a["radius_m"] + b["radius_m"]) / 2.0
    t = (r - a["radius_m"]) / d
    return dict(a, ost=a["ost"] + t * (b["ost"] - a["ost"]), nord=a["nord"] + t * (b["nord"] - a["nord"]), radius_m=round(r),
                beschreibung=a["beschreibung"] + " und " + b["beschreibung"])


def _abstand_zum_bereich(e, xy):
    """Wie weit `xy` ausserhalb des Bereichs liegt, den der Hinweis `e` zulaesst (negativ oder 0: innerhalb).
    Bei einer ganzen Strasse ist es die Strasse selbst (die Haeuser plus Spielraum), sonst der Kreis."""
    if e.get("punkte"):
        return min(abstand(p, xy) for p in e["punkte"]) - ANNAHMEN["strasse_min_m"]
    return abstand((e["ost"], e["nord"]), xy) - e["radius_m"]


def bestimme(rel, verz, hinweise=(), fahrtrichtungen=(), texte=()):
    """Standort eines Ordners.

    hinweise        weitere Hinweise (belege/standort-hinweise.json): Dicts wie von hinweise_aus_text, mit "stufe" und "quelle"
    fahrtrichtungen Namen der Fahrtrichtung aus den Mitteilungen ("Kaarst", "Hertzstraße")
    texte           Bezeichnungen der Messstelle aus den Mitteilungen ("Kreitzweg (Höhe Ludgerusring)")
    Ergebnis: dict fuer die metadaten.yaml (siehe docs/standorte.md) oder None, wenn keine Strasse bekannt ist.
    """
    alle, unbekannt = hinweise_aus_ordner(rel, verz)
    for t in texte:
        zusatz, unb = hinweise_aus_text(t, verz)
        for h in zusatz:
            h["quelle"] = {"typ": "mitteilung", "bezeichnung": t}
            h["stufe"] = "benannt"
        alle += zusatz
        unbekannt += unb
    alle += [dict(h) for h in hinweise]
    gesehen, eindeutig = set(), []
    for h in alle:  # derselbe Hinweis aus Ordnername und Mitteilung zaehlt einmal (die erste Quelle bleibt)
        k = json.dumps({x: y for x, y in h.items() if x not in ("quelle", "stufe", "text")}, sort_keys=True, ensure_ascii=False)
        if k not in gesehen:
            gesehen.add(k)
            eindeutig.append(h)
    alle = eindeutig
    beidseitig = any("beidseitig" in t.lower() for t in list(texte) + [rel])
    fr_belege = {}
    for h in alle:
        if h["art"] == "fahrtrichtung":
            fr_belege.setdefault(h["ziel"], h.get("quelle"))
    fahrtrichtungen = list(fahrtrichtungen) + [z for z in fr_belege if z not in fahrtrichtungen]

    bewertet, verworfen = [], []
    for h in alle:
        fn = BEWERTER.get(h["art"])
        if fn is None:
            continue
        e, grund = fn(h, verz)
        if e is None:
            verworfen.append({"hinweis": h.get("text"), "art": h["art"], "grund": grund})
            continue
        e["stufe"] = h.get("stufe", "benannt")
        e["quelle"] = h.get("quelle")
        e["text"] = h.get("text")
        bewertet.append(e)
    if not bewertet:
        return None
    # Genauigkeit: kleinster Radius; "vorschlag" nur wenn er im Kreis der anderen liegt
    manuell = [e for e in bewertet if e["stufe"] == "manuell"]  # von Hand korrigiert: geht allem anderen vor
    fest = [e for e in bewertet if e["stufe"] not in ("vorschlag", "manuell")]
    vorschlaege = [e for e in bewertet if e["stufe"] == "vorschlag"]
    haupt = min(manuell or fest or vorschlaege, key=lambda e: (e["radius_m"], BEWERTUNG[e["stufe"]]))
    gewaehlt, vermutet, benutzt = haupt, haupt["stufe"] == "vorschlag", [haupt]
    for v in sorted([] if manuell else vorschlaege, key=lambda e: e["radius_m"]):
        if fest and v["radius_m"] < haupt["radius_m"] and _abstand_zum_bereich(haupt, (v["ost"], v["nord"])) <= 0:
            gewaehlt = dict(v, radius_m=max(v["radius_m"], ANNAHMEN["vorschlag_min_m"]))
            vermutet, benutzt = True, [v]
            break
    widerspruch = []
    if not vermutet and not manuell:
        # zwei gleichrangige Angaben, die sich ausschliessen ("Lupinen_Nierenhofstraße"): beide Kreise zusammenfassen
        for e in sorted(fest, key=lambda e: e["radius_m"]):
            if e is not haupt and _abstand_zum_bereich(e, (gewaehlt["ost"], gewaehlt["nord"])) > gewaehlt["radius_m"]:
                gewaehlt = _vereinigung(gewaehlt, e)
                benutzt.append(e)
                widerspruch.append(e["text"])
    belege = []
    for e in bewertet:
        xy = (gewaehlt["ost"], gewaehlt["nord"])
        d = abstand((e["ost"], e["nord"]), xy)
        belege.append({"art": e["art"], "text": e["text"], "stufe": e["stufe"], "quelle": e["quelle"], "ort": e["beschreibung"],
                       "radius_m": e["radius_m"], "abstand_zum_ergebnis_m": round(d),
                       "verwendet": any(e is b for b in benutzt),
                       "widerspricht": _abstand_zum_bereich(e, xy) > gewaehlt["radius_m"]})
    breite, laenge = utm32_zu_wgs84(gewaehlt["ost"], gewaehlt["nord"])
    erg = collections.OrderedDict()
    erg["breite"] = round(breite, 6)
    erg["laenge"] = round(laenge, 6)
    erg["utm32_ost"] = round(gewaehlt["ost"])
    erg["utm32_nord"] = round(gewaehlt["nord"])
    erg["unsicherheit_m"] = gewaehlt["radius_m"]
    erg["methode"] = gewaehlt["art"]
    erg["sicherheit"] = ("manuell korrigiert" if manuell else "vermutet" if vermutet else "widersprüchlich" if widerspruch else "benannt")
    erg["strasse"] = gewaehlt.get("strasse")
    erg["beschreibung"] = gewaehlt["beschreibung"]
    if widerspruch:
        erg["widerspruch"] = "Angaben schließen sich aus (%s); der Kreis umfasst beide" % "; ".join([haupt["text"]] + widerspruch)
    if gewaehlt.get("mehrdeutig") or gewaehlt.get("abschnitte", 1) > 1:
        erg["mehrdeutig"] = "Straße besteht aus getrennten Abschnitten; der Standort kann in jedem liegen"
    if beidseitig:
        erg["beidseitige_messung"] = True
    elif gewaehlt["radius_m"] <= ANNAHMEN["peilung_max_radius_m"]:
        # Peilung nur, wenn die Strasse an der Stelle gut bekannt ist; bei langen Strassen aendert sich ihre Richtung
        fr = []
        for ziel in fahrtrichtungen:
            f = fahrtrichtung(ziel, gewaehlt.get("strasse") or "", (gewaehlt["ost"], gewaehlt["nord"]), verz)
            if f:
                fr.append(f)
        if fr:
            erg["fahrtrichtung"] = fr[0] if len(fr) == 1 else fr
    erg["belege"] = belege
    if verworfen:
        erg["nicht_verwendet"] = verworfen
    if unbekannt:
        erg["nicht_auswertbar"] = unbekannt
    return erg


# ------------------------------------------------------------------ Aufruf

def lade_hinweise(pfad):
    if not os.path.exists(pfad):
        return {}
    with open(pfad, encoding="utf-8") as fh:
        return json.load(fh).get("hinweise", {})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--adressen", default="belege/neuss-adressen.csv")
    ap.add_argument("--hinweise", default="belege/standort-hinweise.json")
    ap.add_argument("--metadaten", default="belege/metadaten.json")
    a = ap.parse_args()
    verz = Verzeichnis.laden(a.adressen)
    hinweise = lade_hinweise(a.hinweise)
    with open(a.metadaten, encoding="utf-8") as fh:
        meta = json.load(fh)["standorte"]
    for rel in sorted(set(hinweise) - set(meta)):
        print("Hinweise für einen Ordner, den es nicht gibt:", rel, file=sys.stderr)
    for rel, s in sorted(meta.items()):
        ver = [v for m in s["messungen"] for v in m.get("verwaltung", [])]
        fr = sorted({v["fahrtrichtung"] for v in ver if v.get("fahrtrichtung")})
        texte = sorted({v["bezeichnung"] for v in ver if v.get("bezeichnung")})
        e = bestimme(rel, verz, hinweise.get(rel, []), fr, texte)
        if e is None:
            print("%-60s keine Straße im Verzeichnis" % rel)
            continue
        print("%-60s %s ±%d m %s %s" % (rel, e["methode"], e["unsicherheit_m"], e["sicherheit"], e["beschreibung"]))


if __name__ == "__main__":
    main()
