# SPDX-License-Identifier: MIT
"""Villestrasse: offene gegen verdeckte Messung (Display ohne Anzeige, DSD-Flag verdeckte_messung) je Fahrtrichtung.

Die Verwaltung (Vorlage vom 14.11.2024) verglich die verdeckte Messung (Fruehjahr/Sommer 2024) mit der offenen vom Jahresanfang 2024
(Winter) und fand keinen Unterschied. Hier drei Vergleiche aus den bereinigten Stundendaten (DATEN.md; vollstaendig aufgezeichnete Stunden):
  A  gleiche Kalendertage: offen 2023 gegen verdeckt 2024 (schaltet die Jahreszeit aus)
  B  wie die Verwaltung: offen Jan-Maerz 2024 gegen verdeckt 2024
  C  Kontrolle (nur Norf): offen Winter 2023/24 gegen offen Winter 2024/25 (Unterschied von Jahr zu Jahr ohne Aenderung am Display)
Je Vergleich: alle Tage und nur Schultage (Werktage ohne Ferien und Feiertage). Spannen: Bootstrap ueber ganze Kalenderwochen (je Gruppe neu
gezogen), 90-%-Bereich des Unterschieds. Mit --html PFAD eine Seite mit den Histogrammen.
Aufruf: python3 -I tools/verdeckt_vergleich.py [_vorschau/daten] [--html exploration/verdeckt.html]"""
import collections
import csv
import datetime as dt
import gzip
import json
import math
import os
import random
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIMIT = 50
P = "m-stationaer-villestrasse-"
RICHTUNGEN = {
    "Norf": {"offen_2023": P + "fr-norf-ville-norf-3", "offen_2024": P + "fr-norf-ville-norf-4", "verdeckt": P + "fr-norf-ville-norf-30",
             "offen_2025": P + "fr-norf-ville-norf-12"},
    "Grevenbroich/Speck": {"offen_2023": P + "fr-gv-0000000000000000-3", "offen_2024": P + "fr-gv-0000000000000000-4",
                           "verdeckt": P + "fr-gv-l-142-fr-speck20-3"},
}


def toleranz(v):
    return 3 if v < 100 else math.ceil(0.03 * v)


def laden(ordner):
    """{messung_id: {datum: {"schultag": bool, "stunden": set, "h": Counter}}} aus vollstaendig aufgezeichneten Stunden."""
    ids = {m for r in RICHTUNGEN.values() for m in r.values()}
    out = collections.defaultdict(dict)
    with gzip.open(os.path.join(ordner, "stunden.csv.gz"), "rt", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["messung_id"] not in ids or r["voll"] != "1":
                continue
            d = dt.date.fromisoformat(r["datum"])
            t = out[r["messung_id"]].setdefault(d, {"schultag": r["wochentag"] in "12345" and r["ferien"] == "0" and r["feiertag"] == "0",
                                                    "stunden": set(), "h": collections.Counter()})
            t["stunden"].add((r["stunde"], r["utc_versatz_h"]))
            t["h"][int(r["kmh"])] += int(r["anzahl"])
    return out


def kennzahlen(h, stunden):
    n = sum(h.values())
    if not n:
        return None
    kum, v85, v95 = 0, None, None
    for v in sorted(h):
        kum += h[v]
        if v85 is None and kum >= 0.85 * n:
            v85 = v
        if v95 is None and kum >= 0.95 * n:
            v95 = v
    ueber = sum(c for v, c in h.items() if v - toleranz(v) > LIMIT)
    return {"n": n, "stunden": stunden, "je_stunde": n / stunden, "mittel": sum(v * c for v, c in h.items()) / n, "v85": v85, "v95": v95,
            "einhaltung": 100 * sum(c for v, c in h.items() if v <= LIMIT) / n, "zu_schnell_anteil": 100 * ueber / n,
            "zu_schnell_je_stunde": ueber / stunden}


def gruppe(tage, auswahl):
    """Tage einer Gruppe -> {Kalenderwoche: (Counter, Stunden)}."""
    wochen = collections.defaultdict(lambda: [collections.Counter(), 0])
    for d, t in tage.items():
        if auswahl(d, t):
            w = wochen[d.isocalendar()[:2]]
            w[0].update(t["h"])
            w[1] += len(t["stunden"])
    return dict(wochen)


def summe(wochen, schluessel=None):
    h, s = collections.Counter(), 0
    for k in (schluessel if schluessel is not None else wochen):
        h.update(wochen[k][0])
        s += wochen[k][1]
    return h, s


def vergleich(a, b, rnd, n=400):
    """Kennzahlen beider Gruppen, Unterschied b - a und 90-%-Bereich aus dem Bootstrap ueber Kalenderwochen."""
    ka, kb = kennzahlen(*summe(a)), kennzahlen(*summe(b))
    diffs = collections.defaultdict(list)
    wa, wb = list(a), list(b)
    for _ in range(n):
        x = kennzahlen(*summe(a, [rnd.choice(wa) for _ in wa]))
        y = kennzahlen(*summe(b, [rnd.choice(wb) for _ in wb]))
        for k in ("mittel", "v85", "v95", "einhaltung", "zu_schnell_anteil", "zu_schnell_je_stunde", "je_stunde"):
            diffs[k].append(y[k] - x[k])
    bereich = {k: (sorted(v)[int(0.05 * n)], sorted(v)[int(0.95 * n) - 1]) for k, v in diffs.items()}
    return ka, kb, bereich


def zeile(name, k):
    return "    %-34s %3d Wochen %7d Fz  %5.1f Fz/h  Mittel %4.1f  V85 %d  V95 %d  Einhaltung %4.1f %%  zu schnell %4.1f %% (%4.1f je h)" % (
        name, k["wochen"], k["n"], k["je_stunde"], k["mittel"], k["v85"], k["v95"], k["einhaltung"], k["zu_schnell_anteil"],
        k["zu_schnell_je_stunde"])


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    html = sys.argv[sys.argv.index("--html") + 1] if "--html" in sys.argv else None
    if html in args:
        args.remove(html)
    ordner = args[0] if args else os.path.join(WURZEL, "_vorschau", "daten")
    daten = laden(ordner)
    rnd = random.Random(1)
    seite = []
    for richtung, m in RICHTUNGEN.items():
        verdeckt = daten[m["verdeckt"]]
        v0, v1 = min(verdeckt), max(verdeckt)
        print("Fahrtrichtung %s: verdeckt %s bis %s" % (richtung, v0, v1))
        im_fenster = lambda d, jahr: (d.month, d.day) >= (v0.month, v0.day) and (d.month, d.day) <= (v1.month, v1.day) and d.year == jahr
        vergleiche = [("A gleiche Kalendertage", "offen 2023", m["offen_2023"], lambda d, t: im_fenster(d, 2023), "verdeckt 2024", m["verdeckt"], None),
                      ("B wie die Verwaltung", "offen Jan-Maerz 2024", m["offen_2024"], None, "verdeckt 2024", m["verdeckt"], None)]
        if "offen_2025" in m:
            o25 = daten[m["offen_2025"]]
            w0, w1 = min(o25), max(o25)
            winter = lambda d, jahr: dt.date(jahr, w0.month, w0.day) <= d <= dt.date(jahr + 1, w1.month, w1.day)
            vergleiche.append(("C Kontrolle: offen gegen offen", "offen Winter 2023/24", (m["offen_2023"], m["offen_2024"]),
                               lambda d, t: winter(d, 2023), "offen Winter 2024/25", m["offen_2025"], None))
        for titel, na, ida, sel_a, nb, idb, sel_b in vergleiche:
            tage_a = {}
            for i in (ida if isinstance(ida, tuple) else (ida,)):
                tage_a.update(daten[i])
            tage_b = daten[idb]
            print("  " + titel)
            for art, nur in (("alle Tage", lambda d, t: True), ("Schultage", lambda d, t: t["schultag"])):
                a = gruppe(tage_a, lambda d, t: (sel_a is None or sel_a(d, t)) and nur(d, t))
                b = gruppe(tage_b, lambda d, t: (sel_b is None or sel_b(d, t)) and nur(d, t))
                ka, kb, ber = vergleich(a, b, rnd)
                ka["wochen"], kb["wochen"] = len(a), len(b)
                print("   %s" % art)
                print(zeile(na, ka))
                print(zeile(nb, kb))
                print("    Unterschied (90-%%-Bereich): Mittel %+.1f (%+.1f bis %+.1f), V85 %+d (%+d bis %+d), V95 %+d (%+d bis %+d), "
                      "zu schnell %+.1f Prozentpunkte (%+.1f bis %+.1f), %+.1f je h (%+.1f bis %+.1f), Verkehr %+.1f Fz/h" % (
                          kb["mittel"] - ka["mittel"], *ber["mittel"], kb["v85"] - ka["v85"], *ber["v85"], kb["v95"] - ka["v95"], *ber["v95"],
                          kb["zu_schnell_anteil"] - ka["zu_schnell_anteil"], *ber["zu_schnell_anteil"],
                          kb["zu_schnell_je_stunde"] - ka["zu_schnell_je_stunde"], *ber["zu_schnell_je_stunde"], kb["je_stunde"] - ka["je_stunde"]))
                if art == "Schultage":
                    ha, hb = summe(a)[0], summe(b)[0]
                    seite.append({"richtung": richtung, "titel": titel, "a": {"name": na, "k": ka, "h": dict(ha)},
                                  "b": {"name": nb, "k": kb, "h": dict(hb)}, "bereich": ber})
    # Verlauf je Monat (Schultage): wann aendert sich das Fahrverhalten?
    verlauf = {}
    print("Verlauf je Monat (Schultage), Anteil zu schnell (ueber Limit plus Toleranz):")
    for richtung, m in RICHTUNGEN.items():
        monate = collections.defaultdict(lambda: [collections.Counter(), 0, set()])
        for art, mid in m.items():
            for d, t in daten[mid].items():
                if t["schultag"]:
                    k = monate[(d.year, d.month)]
                    k[0].update(t["h"])
                    k[1] += len(t["stunden"])
                    k[2].add("verdeckt" if art == "verdeckt" else "offen")
        punkte = []
        for (j, mo), (h, s, arten) in sorted(monate.items()):
            k = kennzahlen(h, s)
            if k["n"] < 5000:  # angebrochene Monate am Rand einer Datei
                continue
            punkte.append({"monat": "%d-%02d" % (j, mo), "phase": "/".join(sorted(arten)), "zu_schnell": round(k["zu_schnell_anteil"], 1),
                           "mittel": round(k["mittel"], 1), "v85": k["v85"], "n": k["n"]})
        verlauf[richtung] = punkte
        print("  %s: %s" % (richtung, ", ".join("%s %s %.1f %%" % (p["monat"], p["phase"][0], p["zu_schnell"]) for p in punkte)))
    if html:
        with open(html, "w", encoding="utf-8") as fh:
            fh.write(SEITE.replace("__DATEN__", json.dumps(seite, ensure_ascii=False)).replace("__VERLAUF__", json.dumps(verlauf, ensure_ascii=False)))
        print("Seite:", html)


SEITE = r"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Villestraße offen gegen verdeckt</title>
<style>
:root { --surface: #fcfcfb; --text: #0b0b0b; --text2: #52514e; --grid: #e4e3df; --s1: #2a78d6; --s2: #eb6834; --limit: #52514e; }
@media (prefers-color-scheme: dark) { :root { --surface: #1a1a19; --text: #ffffff; --text2: #c3c2b7; --grid: #383835; --s1: #3987e5; --s2: #d95926; --limit: #c3c2b7; } }
body { background: var(--surface); color: var(--text); font: 15px/1.45 system-ui, sans-serif; margin: 0; padding: 16px; }
main { max-width: 1000px; margin: 0 auto; }
h1 { font-size: 1.4rem; } h2 { font-size: 1.1rem; margin-top: 2rem; }
p, li { color: var(--text2); max-width: 75ch; }
.legende { display: flex; gap: 20px; flex-wrap: wrap; margin: 6px 0; font-size: 0.9rem; }
.legende span::before { content: ""; display: inline-block; width: 16px; height: 3px; border-radius: 2px; margin-right: 6px; vertical-align: middle; background: var(--c); }
svg { width: 100%; height: auto; display: block; }
svg text { fill: var(--text2); font-size: 11px; }
.gitter { stroke: var(--grid); } .limit { stroke: var(--limit); stroke-dasharray: 4 3; }
.linie { fill: none; stroke-width: 2; stroke-linejoin: round; }
table { border-collapse: collapse; font-size: 0.85rem; margin: 8px 0 4px; }
th, td { padding: 3px 10px; border-bottom: 1px solid var(--grid); text-align: right; } th:first-child, td:first-child { text-align: left; }
.tip { position: fixed; pointer-events: none; background: var(--surface); border: 1px solid var(--grid); padding: 6px 9px; border-radius: 6px;
       font-size: 0.85rem; box-shadow: 0 2px 8px rgba(0,0,0,.15); display: none; }
</style></head><body><main>
<h1>Villestraße: offene gegen verdeckte Messung</h1>
<p>Anteil der Fahrzeuge je km/h (Schultage, vollständig aufgezeichnete Stunden, Rauschboden abgezogen). „Verdeckt“: Das Display zeigte nichts an
(DSD-Flag <code>verdeckte_messung</code>). Vergleich A legt dieselben Kalendertage zweier Jahre nebeneinander, B ist der Vergleich der Verwaltung
(Winter offen gegen Sommer verdeckt), C ist eine Kontrolle ohne Änderung am Display. Erzeugt von <code>tools/verdeckt_vergleich.py</code>.</p>
<h2>Verlauf je Monat: Anteil der Fahrzeuge über Limit plus Toleranz (über 53 km/h)</h2>
<p>Schultage, Monate mit mindestens 5.000 Fahrzeugen. Grau hinterlegt: verdeckte Messung (Display ohne Anzeige). Lücken: keine Daten.</p>
<div class="legende"><span style="--c:var(--s1)">Fahrtrichtung Norf</span><span style="--c:var(--s2)">Fahrtrichtung Grevenbroich/Speck</span></div>
<div id="verlauf"></div>
<table id="verlauf-tabelle"></table>
<div id="inhalt"></div>
<div class="tip" id="tip"></div>
</main>
<script>
const DATEN = __DATEN__;
const VERLAUF = __VERLAUF__;
const f1 = new Intl.NumberFormat("de-DE", { maximumFractionDigits: 1, minimumFractionDigits: 1 });
const f0 = new Intl.NumberFormat("de-DE");
const tip = document.getElementById("tip");
(function verlauf() {
  const monate = [...new Set(Object.values(VERLAUF).flat().map((p) => p.monat))].sort();
  const idx = (m) => { const [j, mo] = m.split("-").map(Number); return j * 12 + mo; };
  const m0 = idx(monate[0]), m1 = idx(monate[monate.length - 1]);
  const W = 960, H = 260, L = 44, R = 12, T = 12, B = 30, ymin = 15, ymax = 40;
  const x = (m) => L + (idx(m) - m0) / (m1 - m0) * (W - L - R), y = (p) => T + (1 - (p - ymin) / (ymax - ymin)) * (H - T - B);
  let g = "";
  for (let p = ymin; p <= ymax; p += 5) g += `<line class="gitter" x1="${L}" x2="${W - R}" y1="${y(p)}" y2="${y(p)}"/><text x="${L - 6}" y="${y(p) + 4}" text-anchor="end">${p} %</text>`;
  const verdeckt = Object.values(VERLAUF).flat().filter((p) => p.phase === "verdeckt").map((p) => idx(p.monat));
  const v0 = Math.min(...verdeckt) - 0.5, v1 = Math.max(...verdeckt) + 0.5, xi = (i) => L + (i - m0) / (m1 - m0) * (W - L - R);
  g = `<rect x="${xi(v0)}" y="${T}" width="${xi(v1) - xi(v0)}" height="${H - T - B}" fill="var(--grid)" opacity="0.7"/>` + g;
  g += `<text x="${(xi(v0) + xi(v1)) / 2}" y="${T + 12}" text-anchor="middle">verdeckt</text>`;
  for (const m of monate) if (m.endsWith("-01") || m === monate[0]) g += `<text x="${x(m)}" y="${H - 10}" text-anchor="middle">${m.slice(5) === "01" ? m.slice(0, 4) : m}</text>`;
  const farben = ["var(--s1)", "var(--s2)"];
  Object.entries(VERLAUF).forEach(([r, punkte], i) => {
    let d = "", vorher = null;
    for (const p of punkte) { d += (vorher !== null && idx(p.monat) - vorher === 1 ? "L" : "M") + x(p.monat).toFixed(1) + "," + y(p.zu_schnell).toFixed(1); vorher = idx(p.monat); }
    g += `<path class="linie" style="stroke:${farben[i]}" d="${d}"/>`;
    for (const p of punkte) g += `<circle cx="${x(p.monat)}" cy="${y(p.zu_schnell)}" r="4" fill="${farben[i]}" stroke="var(--surface)" stroke-width="2"><title>${r}, ${p.monat}: ${f1.format(p.zu_schnell)} % zu schnell, Mittel ${f1.format(p.mittel)} km/h, V85 ${p.v85} (${p.phase})</title></circle>`;
  });
  document.getElementById("verlauf").innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Anteil zu schneller Fahrzeuge je Monat">${g}</svg>`;
  let t = "<thead><tr><th>Monat</th>" + Object.keys(VERLAUF).map((r) => `<th>${r}</th>`).join("") + "</tr></thead><tbody>";
  for (const m of monate) t += `<tr><td>${m}</td>` + Object.values(VERLAUF).map((ps) => { const p = ps.find((q) => q.monat === m); return `<td>${p ? f1.format(p.zu_schnell) + " % (" + p.phase + ")" : "–"}</td>`; }).join("") + "</tr>";
  document.getElementById("verlauf-tabelle").innerHTML = t + "</tbody>";
})();
function anteile(h) { const n = Object.values(h).reduce((a, b) => a + b, 0); const o = {}; for (const [v, c] of Object.entries(h)) o[v] = 100 * c / n; return o; }
for (const d of DATEN) {
  const sek = document.createElement("section");
  const a = anteile(d.a.h), b = anteile(d.b.h);
  const W = 960, H = 280, L = 44, R = 12, T = 12, B = 30, vmin = 20, vmax = 90;
  const ymax = Math.ceil(Math.max(...Object.values(a), ...Object.values(b)) + 0.5);
  const x = (v) => L + (v - vmin) / (vmax - vmin) * (W - L - R), y = (p) => T + (1 - p / ymax) * (H - T - B);
  const pfad = (o) => { let s = ""; for (let v = vmin; v <= vmax; v++) s += (s ? "L" : "M") + x(v).toFixed(1) + "," + y(o[v] || 0).toFixed(1); return s; };
  let g = "";
  for (let p = 0; p <= ymax; p++) g += `<line class="gitter" x1="${L}" x2="${W - R}" y1="${y(p)}" y2="${y(p)}"/><text x="${L - 6}" y="${y(p) + 4}" text-anchor="end">${p} %</text>`;
  for (let v = vmin; v <= vmax; v += 10) g += `<text x="${x(v)}" y="${H - 10}" text-anchor="middle">${v}</text>`;
  g += `<line class="limit" x1="${x(50)}" x2="${x(50)}" y1="${T}" y2="${H - B}"/><text x="${x(50) + 4}" y="${T + 10}">Tempolimit 50</text>`;
  g += `<path class="linie" style="stroke:var(--s1)" d="${pfad(a)}"/><path class="linie" style="stroke:var(--s2)" d="${pfad(b)}"/>`;
  g += `<rect x="${L}" y="${T}" width="${W - L - R}" height="${H - T - B}" fill="transparent" class="treffer"/>`;
  const k = (z) => `<td>${f0.format(z.n)}</td><td>${f1.format(z.je_stunde)}</td><td>${f1.format(z.mittel)}</td><td>${z.v85}</td><td>${z.v95}</td><td>${f1.format(z.einhaltung)} %</td><td>${f1.format(z.zu_schnell_anteil)} %</td><td>${f1.format(z.zu_schnell_je_stunde)}</td>`;
  const r = d.bereich, sp = (q, s) => `${s(q[0])} bis ${s(q[1])}`, pm = (v) => (v > 0 ? "+" : "") + f1.format(v);
  sek.innerHTML = `<h2>Fahrtrichtung ${d.richtung} – ${d.titel}</h2>
    <div class="legende"><span style="--c:var(--s1)">${d.a.name}</span><span style="--c:var(--s2)">${d.b.name}</span></div>
    <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Anteil der Fahrzeuge je km/h, ${d.a.name} gegen ${d.b.name}">${g}</svg>
    <table><thead><tr><th></th><th>Fahrzeuge</th><th>je Stunde</th><th>Mittel</th><th>V85</th><th>V95</th><th>Einhaltung</th><th>zu schnell</th><th>zu schnell je h</th></tr></thead>
    <tbody><tr><td>${d.a.name}</td>${k(d.a.k)}</tr><tr><td>${d.b.name}</td>${k(d.b.k)}</tr></tbody></table>
    <p>Unterschied (90-%-Bereich aus Bootstrap über Kalenderwochen): Mittel ${sp(r.mittel, pm)} km/h, V85 ${sp(r.v85, pm)},
    zu schnell ${sp(r.zu_schnell_anteil, pm)} Prozentpunkte, ${sp(r.zu_schnell_je_stunde, pm)} je Stunde.</p>`;
  document.getElementById("inhalt").append(sek);
  const svg = sek.querySelector("svg");
  svg.querySelector(".treffer").addEventListener("mousemove", (ev) => {
    const pt = svg.createSVGPoint(); pt.x = ev.clientX; pt.y = ev.clientY;
    const p = pt.matrixTransform(svg.getScreenCTM().inverse());
    const v = Math.round(vmin + (p.x - L) / (W - L - R) * (vmax - vmin));
    tip.style.display = "block"; tip.style.left = ev.clientX + 14 + "px"; tip.style.top = ev.clientY + 14 + "px";
    tip.innerHTML = `<b>${v} km/h</b><br>${d.a.name}: ${f1.format(a[v] || 0)} %<br>${d.b.name}: ${f1.format(b[v] || 0)} %`;
  });
  svg.querySelector(".treffer").addEventListener("mouseleave", () => { tip.style.display = "none"; });
}
</script></body></html>
"""

if __name__ == "__main__":
    main()
