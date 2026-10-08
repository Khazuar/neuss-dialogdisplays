# SPDX-License-Identifier: MIT
"""Zerlegt die Mitteilungen der Verwaltung ("Ergebnisse von Verkehrsmessungen durch Dialog Displays")
in einzelne Messstellen und schreibt die genannten Angaben nach belege/ris-messstellen.json.

Aufruf:
  PYPDF_PFAD=<Ordner mit pypdf> python3 -I tools/ris_messstellen.py ris_roh belege/ris-messstellen.json

  ris_roh   Ordner von ris_sammeln.py

Je Messstelle werden nur Tatsachen uebernommen: Bezeichnung, Fahrtrichtung, Erfassungszeitraum,
Tempolimit, Fahrzeugzahlen, mittleres Tempo, V85, Anteile und die Einstufung der Verwaltung. Die
Zuordnung zu den DSD-Dateien macht metadaten.py. Was sich nicht eindeutig zerlegen laesst, steht
unter "nicht_ausgewertet" und geht nicht verloren.

Die Mitteilungen sind amtliche Dokumente der Stadt Neuss (amtliche Werke, 5 UrhG). Es werden nur
kurze Angaben und einzelne Saetze uebernommen, nicht die Dokumente.
"""
import json
import os
import re
import sys

ZAHL = r"\d{1,3}(?:\.\d{3})+|\d+"
DATUM = r"\d{2}\.\d{2}\.\d{4}"


def tol(wort):
    """Regex fuer ein Wort, das im PDF-Text durch einzelne Leerzeichen getrennt sein kann ("durchschnittlic he")."""
    return r"\s?".join(re.escape(c) for c in wort)


# Kopf einer Messstelle im neueren Format: "Strasse, FR X (beidseitige Messung): Der massgebliche ..."
KOPF = re.compile(r"(?P<kopf>(?!Folgende)(?![^:]{0,170}\b(?:gegeben|ergeben)\b)[A-ZÄÖÜ][^:.]{2,170}?)\s*:\s+(?=(?:Der maßgebliche|Bei vorgeschriebenen|Folgende Messungen))")
# aelteres Format: "Folgende Ergebnisse haben die Geschwindigkeitsmessungen im Bereich der X im Zeitraum vom A bis B ergeben:"
KOPF_ALT = re.compile(
    r"(?:Folgende Ergebnisse haben die|Die) (?:Geschwindigkeits)?[Mm]essungen "
    r"(?:im Bereich (?:auf der |der |des )?|auf der |im Bereich )(?P<kopf>[^:]*?)"
    rf"(?: im Zeitraum vom (?P<von>{DATUM}) bis (?P<bis>{DATUM}))?(?: haben folgende Ergebnisse)? ergeben")
ZEITRAUM_SATZ = re.compile(
    r"Der Erfassungs\s*zeitraum war (?:i\.d\.R\. )?vom (?P<von>\d\d\.\d\d\.(?:\d{4})?)\s*bis\s*(?P<bis>\d\d\.\d\d\.\d{4})")
ZEITRAUM_BLOCK = re.compile(
    r"Erfassungs\s*zeitraum\s*(?:\(|vom\s+)(?P<von>\d\d\.\d\d\.(?:\d{4})?)\s*bis\s*(?P<bis>\d\d\.\d\d\.\d{4})")
ZEITRAUM_IM = re.compile(rf"Im Zeitraum vom (?P<von>{DATUM}) bis (?P<bis>{DATUM})")
OHNE_DATEN = re.compile(r"Für die Messstelle (?P<ort>[^.]{2,60}?) liegen [^.]*keine Daten vor")
SATZENDE = re.compile(r"(?<=[a-zäöü\d)%/]{3})\.\s+(?=[A-ZÄÖÜ])")  # nicht nach "ca.", "o. g.", "Nr."

EINSTUFUNG = [  # Reihenfolge: spezifischere Formulierungen zuerst; verglichen wird ohne Leerzeichen
    ("völligunkritisch", "voellig_unkritisch"), ("unkritisch", "unkritisch"), ("unauffällig", "unauffaellig"),
    ("nochakzeptabel", "noch_akzeptabel"), ("überdurchschnittlichhoch", "ueberdurchschnittlich_hoch"),
    ("überdurchschnittlich", "ueberdurchschnittlich_hoch"), ("deutlichzuhoch", "deutlich_zu_hoch"),
    ("überhöht", "ueberhoeht"),
]
# Feste Formulierungen fuer Hinweise der Verwaltung (Suche im Satz ohne Leerzeichen, klein). Keine Zitate:
# die PDF-Texte enthalten Trennfehler, der Wortlaut steht im verlinkten Dokument.
HINWEISE = [
    ("radfahrer", "Hoher Anteil Radfahrende erfasst, die Geräte unterscheiden nicht zwischen Rad und Kfz"),
    ("baustelle", "Verwaltung nennt Baustelle oder Umleitung als Erklärung"),
    ("keineerklärung", "Verwaltung hat für das Verkehrsaufkommen keine Erklärung"),
    ("verdeckte", "Verdeckte Messung"),
    ("laserwagen", "Weitergehende Kontrollen (Laserwagen) vorgesehen oder genannt"),
    ("messungwirddaherin", "Wiederholung der Messung vorgesehen"),
    ("messungwiederholt", "Wiederholung der Messung vorgesehen"),
    ("messungwiederholtwerden", "Wiederholung der Messung vorgesehen"),
    ("beobachtung", "Bereich soll weiter beobachtet werden"),
    ("verkehrsberuhigterbereicherstvor", "Verkehrsberuhigter Bereich erst kürzlich angeordnet"),
    ("vordembeginndesverkehrsberuhigten", "Gemessen vor Beginn des verkehrsberuhigten Bereichs"),
    ("nichtlangeexistiert", "Geschwindigkeitsbegrenzung erst kürzlich angeordnet"),
    ("hauptfahrbahn", "Gerät erfasst auch Fahrzeuge der Hauptfahrbahn"),
    ("möglichkeiteninein", "Möglichkeiten für Maßnahmen im verkehrsberuhigten Bereich begrenzt"),
]

def normalisiere(text):
    """Text aus pypdf glaetten: Silbentrennung, getrennte Ziffern/Woerter, Leerraum."""
    t = re.sub(r"(?<=[a-zäöüß])-\s*\n\s*(?=[a-zäöüß])", "", text)
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"(\d) (?=\d\s*km/\s?h)", r"\1", t)  # "5 0 km/h"
    t = re.sub(r"km/\s+h", "km/h", t)
    t = re.sub(r"\(\s*k\s*o\s*m\s*m\s*e\s*n\s*d\s*\)", "(kommend)", t)
    t = re.sub(r"\(\s*g\s*e\s*h\s*e\s*n\s*d\s*\)", "(gehend)", t)
    t = re.sub(r"(\d{2}\.\d{2}\.\d{3}) (\d)\b", r"\1\2", t)  # "202 4"
    t = re.sub(r"Erfassungsz\s+eitraum", "Erfassungszeitraum", t)
    return t.strip()


def zahl(s):
    return int(s.replace(".", ""))


def prozent(s):
    return float(s.replace(",", "."))


def datum_iso(s, bezug=None):
    """'13.09.2023' -> '2023-09-13'; fehlt das Jahr ('16.09.'), wird es aus dem Bezugsdatum (Ende) abgeleitet."""
    teile = s.strip().split(".")
    tag, monat = int(teile[0]), int(teile[1])
    if len(teile) > 2 and teile[2]:
        return f"{int(teile[2]):04d}-{monat:02d}-{tag:02d}"
    if not bezug:
        return None
    jahr = int(bezug[:4])
    iso = f"{jahr:04d}-{monat:02d}-{tag:02d}"
    return iso if iso <= bezug else f"{jahr - 1:04d}-{monat:02d}-{tag:02d}"


def zeitraum(von, bis):
    b = datum_iso(bis)
    v = datum_iso(von, bezug=b)
    return [v, b] if v and b else None


REPARATUREN = {  # Trennfehler aus dem PDF-Text in Bezeichnungen
    "Aller heiligen": "Allerheiligen", "be idseitige": "beidseitige", "S traße": "Straße", "Berei ch": "Bereich",
}


def repariere(s):
    for falsch, richtig in REPARATUREN.items():
        s = s.replace(falsch, richtig)
    return re.sub(r"\s+-\s*|\s*-\s+(?=[A-ZÄÖÜ])", "-", s)  # "Konrad -Adenauer -Ring"


def kopf_zerlegen(kopf):
    """Bezeichnung der Messstelle zerlegen: Strasse, Fahrtrichtung, Zusaetze aus der Verwaltung."""
    k = repariere(re.sub(r"\s+", " ", kopf).strip(" ,;"))
    strasse = re.split(r",|\(", k)[0].strip()
    ergebnis = {"bezeichnung": k, "strasse": strasse}
    fr = re.search(r"\bFR\.?\s+([^,()]+)", k)
    if fr:
        ergebnis["fahrtrichtung"] = fr.group(1).strip()
    if re.search(r"beidseitig", k, re.I):
        ergebnis["beidseitig"] = True
    if re.search(r"Wiederholungsmessung", k):
        ergebnis["wiederholungsmessung"] = True
    t = re.search(r"Tempo (\d+)", k)
    if t:
        ergebnis["tempo_im_kopf_kmh"] = int(t.group(1))
    return ergebnis


def sauber(satz):
    return re.sub(r"\s+", " ", satz).strip()


def dicht(t):
    """Text ohne Leerraum und klein: fuer Stichwortsuchen, die von PDF-Trennfehlern unabhaengig sein sollen."""
    return re.sub(r"\s+", "", t).lower()


def felder(text):
    """Angaben einer Messstelle aus dem Fliesstext. Nur was ausdruecklich dasteht."""
    f = {}
    t = text
    # Tempolimit ("bei vorgeschriebenen 30 km/h", "bei einer vorgeschriebenen Geschwindigkeit von deutlich unter 20 km/h")
    m = re.search(rf"{tol('vorgeschrieben')}\w*\s+(?:{tol('Geschwindigkeit')}\s+)?(?:von\s+)?(deutlich\s+unter\s+)?(\d{{2}}) ?km/h", t, re.I)
    if m:
        f["tempolimit_kmh"] = int(m.group(2))
        if m.group(1):
            f["tempolimit_deutlich_unter"] = True
    # V85: erste Geschwindigkeit nach "V85" im selben Satz
    m = re.search(r"V ?85(.*?)(?:\.\s+[A-ZÄÖÜ]|$)", t, re.S)
    if m:
        z = re.search(r"(\d{2,3}) ?km/h", m.group(1))
        if z:
            f["v85_kmh"] = int(z.group(1))
    # mittleres Tempo
    m = re.search(rf"{tol('durchschnittliche')}\s+(?:{tol('Geschwindigkeit')}|{tol('Tempo')})\s+{tol('betrug')}\s+(?:[a-zäöü]+ ){{0,3}}?(\d{{1,3}}) ?km/h", t, re.I)
    if m:
        f["mittel_kmh"] = int(m.group(1))
    # Fahrzeugzahlen (absolut im Zeitraum oder je Tag; gesamt oder je Richtung)
    zahlen = {}
    for satz in SATZENDE.split(t):
        if not re.search(tol("Fahrzeugbewegu"), satz) and not re.search(tol("Fahrzeugbeweg"), satz):
            continue
        je_tag = bool(re.search(r"täglich|pro\s+Tag", satz))
        hat_richtung = bool(re.search(r"\(\s*(?:kommend|gehend)\s*\)", satz))
        for m in re.finditer(rf"(?P<n>{ZAHL})\s+{tol('Fahrzeugbeweg')}\w*(?:\s*\((?P<r>kommend|gehend)\))?", satz):
            richtung = m.group("r") or ("gesamt" if not hat_richtung or "beiden Fahrtrichtungen" in satz else None)
            if richtung:
                zahlen.setdefault("je_tag" if je_tag else "im_zeitraum", {})[richtung] = zahl(m.group("n"))
    f.update({f"fahrzeuge_{k}": v for k, v in zahlen.items()})
    # Anteile
    m = re.search(r"(?:ca\.|knapp|etwa)?\s*(\d+(?:,\d+)?)\s?(?:%|Prozent)[^.]{0,120}?unter (\d{2}) ?km/h", t, re.I)
    if m:
        f["anteil_unter"] = {"prozent": prozent(m.group(1)), "kmh": int(m.group(2))}
    m = re.search(r"mit (?:mehr als|über) (\d{2}) ?km/h[^.]*?betrug [^.]*?(\d+(?:,\d+)?)\s?(?:%|Prozent)", t)
    if m:
        f["anteil_ueber"] = {"prozent": prozent(m.group(2)), "kmh": int(m.group(1))}
    # Einstufung der Verwaltung (Satz mit dem V85-Wert) und Massnahmen
    for satz in SATZENDE.split(t):
        d = dicht(satz)
        if "v85" in d:
            for wort, schluessel in EINSTUFUNG:
                if wort in d:
                    f["einstufung_verwaltung"] = schluessel
                    break
            break
    d = dicht(t)
    if "maßnahmennichterforderlich" in d or "maßnahmensindnichterforderlich" in d:
        f["massnahmen_verwaltung"] = "nicht erforderlich"
    elif "kreispolizeibehörde" in d or "handlungsbedarf" in d:
        f["massnahmen_verwaltung"] = "Abstimmung mit der Kreispolizeibehörde vorgesehen oder genannt"
    elif "maßnahmenzurgeschwindigkeitsreduktion" in d:
        f["massnahmen_verwaltung"] = "Abstimmung mit der Kreispolizeibehörde vorgesehen oder genannt"
    hinweise = []
    for satz in SATZENDE.split(t):
        d = dicht(satz)
        for stichwort, text_ in HINWEISE:
            if stichwort in d and text_ not in hinweise:
                hinweise.append(text_)
    if hinweise:
        f["hinweise_verwaltung"] = hinweise
    return f

def zerlege(text):
    """Text einer Mitteilung -> (bloecke, nicht_ausgewertet)."""
    t = normalisiere(text)
    i = t.find("Inhalt der Mitteilung")
    inhalt = t[i + len("Inhalt der Mitteilung"):].lstrip(": ") if i >= 0 else t
    inhalt = re.sub(r"\d{2}/\d+(?:/\d{4})? Seite \d+ von \d+ ?", "", inhalt)  # Fusszeile "69/313/2024 Seite 2 von 2"
    marken = []  # (start, ende_des_kopfes, art, match)
    for m in KOPF_ALT.finditer(inhalt):
        marken.append((m.start(), m.end(), "alt", m))
    for m in KOPF.finditer(inhalt):
        if not any(a <= m.start() < b for a, b, _, _ in marken):
            marken.append((m.start("kopf"), m.end(), "neu", m))
    marken.sort(key=lambda x: x[0])
    # Zeitraum-Saetze "Der Erfassungszeitraum war ..." gelten fuer die folgenden Messstellen
    saetze = [(m.start(), zeitraum(m.group("von"), m.group("bis"))) for m in ZEITRAUM_SATZ.finditer(inhalt)]

    bloecke, offen = [], []
    for n, (start, kopf_ende, art, m) in enumerate(marken):
        ende = marken[n + 1][0] if n + 1 < len(marken) else len(inhalt)
        # Zeitraum-Satz vor dem naechsten Kopf gehoert zu diesem Satz nicht mehr
        stuecke = [(s, z) for s, z in saetze if kopf_ende <= s < ende]
        if stuecke:
            ende = stuecke[0][0]
        text_block = inhalt[kopf_ende:ende]
        satz_zeitraum = next((z for s, z in reversed(saetze) if s < start), None)
        kopf = m.group("kopf")
        k = kopf_zerlegen(kopf)
        zeitraum_kopf = zeitraum(m.group("von"), m.group("bis")) if art == "alt" and m.group("von") else None
        # Unterbloecke: "Fahrtrichtung X" und "Im Zeitraum vom A bis B" (aelteres Format, Villestrasse)
        teile = [(None, text_block)]
        if re.search(r"Fahrtrichtung \w+", text_block):
            teile = []
            pos = [(x.start(), x.group(1)) for x in re.finditer(r"Fahrtrichtung ([A-ZÄÖÜ]\w+)", text_block)]
            for j, (p, fr) in enumerate(pos):
                teile.append((fr, text_block[p:(pos[j + 1][0] if j + 1 < len(pos) else len(text_block))]))
        for fr, tb in teile:
            unter = list(ZEITRAUM_IM.finditer(tb))
            stucke = [(zeitraum(u.group("von"), u.group("bis")), tb[u.start():(unter[j + 1].start() if j + 1 < len(unter) else len(tb))])
                      for j, u in enumerate(unter)] or [(None, tb)]
            for z, tt in stucke:
                if z is None:
                    mz = ZEITRAUM_BLOCK.search(tt)
                    z = zeitraum(mz.group("von"), mz.group("bis")) if mz else (zeitraum_kopf or satz_zeitraum)
                b = dict(k)
                if fr:
                    b["fahrtrichtung"] = fr
                    b["bezeichnung"] = f"{k['strasse']}, Fahrtrichtung {fr}"
                if art == "alt" and "(" in kopf and "bezeichnung" in b and not fr:
                    b["bezeichnung"] = sauber(kopf) + (")" if kopf.count("(") > kopf.count(")") else "")
                b["zeitraum"] = z
                b.update(felder(tt))
                if "v85_kmh" not in b and "mittel_kmh" not in b and "fahrzeuge_je_tag" not in b and "fahrzeuge_im_zeitraum" not in b:
                    offen.append({"kopf": b["bezeichnung"], "grund": "keine Messwerte erkannt"})
                    continue
                bloecke.append(b)
    for m in OHNE_DATEN.finditer(inhalt):
        offen.append({"kopf": sauber(m.group("ort")), "grund": "technischer Defekt, keine Daten vorhanden"})
    if re.search(r"Nebenfahrbahn des Berghäuschensweg", inhalt):
        offen.append({"kopf": "Berghäuschensweg, Nebenstraße Hausnummer 323",
                      "grund": "Messung auf der Nebenfahrbahn nicht möglich, Gerät erfasst auch die Hauptfahrbahn"})
    return bloecke, offen


def main():
    roh, ziel = sys.argv[1:3]
    if os.environ.get("PYPDF_PFAD"):
        sys.path.insert(0, os.environ["PYPDF_PFAD"])
    try:
        from pypdf import PdfReader
    except ImportError:
        sys.exit("pypdf fehlt: pip install --target <Ordner> pypdf und PYPDF_PFAD=<Ordner> setzen")
    index = json.load(open(os.path.join(roh, "index.json"), encoding="utf-8"))
    sitzung = re.compile(r"(Bezirksausschuss[^0-9\n]{3,70}?)\s+(\d{2})\.(\d{2})\.(\d{4})")
    vorlage = re.compile(r"\b(\d{2}/\d{1,4}/\d{4})\b")
    dokumente = []
    for kvonr, v in sorted(index.items(), key=lambda x: int(x[0])):
        if not v["titel"].startswith("Ergebnisse von Verkehrs"):
            continue
        for dok in v["dokumente"]:
            text = "\n".join((p.extract_text() or "") for p in PdfReader(os.path.join(roh, f"do_{dok}.pdf")).pages)
            bloecke, offen = zerlege(text)
            s = sitzung.search(normalisiere(text))
            vl = vorlage.search(text)
            dokumente.append({
                "vorlage": vl.group(1) if vl else None, "ris_vorlage_id": int(kvonr), "betreff": v["titel"],
                "gremium": s.group(1).strip() if s else None,
                "sitzung": f"{s.group(4)}-{s.group(3)}-{s.group(2)}" if s else None,
                "dokument": f"{v['url'].split('vo0050')[0]}getfile.asp?id={dok}&type=do",
                "messstellen": bloecke, "nicht_ausgewertet": offen})
    os.makedirs(os.path.dirname(ziel) or ".", exist_ok=True)
    with open(ziel, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"erzeugt_von": "tools/ris_messstellen.py", "dokumente": dokumente}, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    n = sum(len(d["messstellen"]) for d in dokumente)
    print(f"{len(dokumente)} Dokumente, {n} Messstellen, "
          f"{sum(len(d['nicht_ausgewertet']) for d in dokumente)} nicht ausgewertet", file=sys.stderr)


if __name__ == "__main__":
    main()
