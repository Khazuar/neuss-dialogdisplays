// SPDX-License-Identifier: MIT
// Auswahl nach Tageszeit, Tagen und Gruppe auf den Detailseiten der Standorte.
// Liest ausschliesslich die Datentabelle (script.filter-daten) der eigenen Seite und rechnet daraus Kennzahlen und
// Histogramm. Keine Verbindungen zu anderen Servern, nichts wird gespeichert. Datenformat: gruppen.py (analysiere),
// Beschreibung in docs/gruppen.md. Eine Auswahl ist die Summe der Zellen (Tagschluessel, Stunde); ein Fahrzeug einer Gruppe
// zaehlt mit dem Anteil, den die Gruppe an seiner Geschwindigkeit hat (gilt fuer alle Stunden und Tage gleich).
(function (wurzel) {
  "use strict";

  var ZEIT = {
    alle: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23],
    nacht: [22, 23, 0, 1, 2, 3, 4, 5], vormittag: [6, 7, 8, 9, 10, 11], nachmittag: [12, 13, 14, 15, 16, 17, 18],
    abend: [19, 20, 21], schulweg: [7]
  };
  var TAGE = { alle: [0, 1, 2, 3, 4, 5, 6, 7], werktag: [0, 1, 2, 3, 4], samstag: [5], sonn: [6, 7] };
  for (var i = 0; i < 8; i++) { TAGE[String(i)] = [i]; }
  var HIST = { B: 600, H: 290, L: 44, R: 12, T: 38, U: 38, BREITE_MAX: 5, MIN_FAHRZEUGE: 50 };

  // Gewicht, mit dem ein Fahrzeug der Geschwindigkeit v zur Gruppe zaehlt (0 bis 1)
  function gewicht(daten, gruppe) {
    var w0 = daten.w0 || 0, gr = daten.gruppen || [];
    if (gruppe === "alle" || gruppe === "rausch") { return function () { return 1; }; }
    if (gruppe === "rand") { return function (v) { return v < w0 ? 1 : 0; }; }
    if (gruppe === "haupt") {
      var langsam = daten.langsam || [];
      return function (v) {
        if (v < w0) { return 0; }
        var s = 0;
        for (var k = 0; k < langsam.length; k++) { s += gr[langsam[k] - 1].w[v - w0] || 0; }
        return Math.max(0, 1 - s);
      };
    }
    var nr = parseInt(gruppe.slice(1), 10), g = gr[nr - 1];
    return function (v) { return v < w0 ? 0 : (g && g.w[v - w0]) || 0; };
  }

  // Histogramm {v: Anzahl} der Auswahl und die Summe der aufgezeichneten Stunden dieser Zellen
  function waehle(daten, zeit, tage, gruppe) {
    var quelle = gruppe === "rausch" ? daten.r : daten.z, w = gewicht(daten, gruppe);
    var hist = {}, stunden = 0;
    var ts = TAGE[tage] || [], hs = ZEIT[zeit] || [];
    for (var a = 0; a < ts.length; a++) {
      for (var b = 0; b < hs.length; b++) {
        var key = ts[a] + "|" + hs[b];
        stunden += (daten.tage && daten.tage[key]) || 0;
        var zelle = quelle && quelle[key];
        if (!zelle) { continue; }
        for (var j = 0; j < zelle.length; j += 2) {
          var v = zelle[j], c = zelle[j + 1] * w(v);
          if (c > 0) { hist[v] = (hist[v] || 0) + c; }
        }
      }
    }
    return { hist: hist, stunden: stunden };
  }

  function sortiert(hist) {
    return Object.keys(hist).map(Number).sort(function (a, b) { return a - b; });
  }

  function quantilWert(hist, vs, n, q) {
    var kum = 0;
    for (var i = 0; i < vs.length; i++) {
      kum += hist[vs[i]];
      if (kum >= q * n - 1e-9) { return vs[i]; }
    }
    return vs.length ? vs[vs.length - 1] : null;
  }

  function toleranz(v) { return v < 100 ? 3 : Math.ceil(0.03 * v); }

  function kennzahlen(hist, limit) {
    var vs = sortiert(hist), n = 0, summe = 0, ok = 0, okq = 0, i, v;
    for (i = 0; i < vs.length; i++) {
      v = vs[i]; n += hist[v]; summe += v * hist[v];
      if (limit && v <= limit) { ok += hist[v]; }
      if (limit && v - toleranz(v) <= limit) { okq += hist[v]; }
    }
    if (n <= 0) { return null; }
    return {
      n: n, mittel: summe / n, v85: quantilWert(hist, vs, n, 0.85), v95: quantilWert(hist, vs, n, 0.95), v99: quantilWert(hist, vs, n, 0.99),
      einhaltung: limit ? 100 * ok / n : null, qualifiziert: limit ? 100 * okq / n : null
    };
  }

  function klassenbreite(hist, n) {
    var vs = sortiert(hist), q1 = quantilWert(hist, vs, n, 0.25), q3 = quantilWert(hist, vs, n, 0.75), iqr = q3 - q1;
    if (n < 2 || iqr <= 0) { return 1; }
    return Math.max(1, Math.min(HIST.BREITE_MAX, Math.round(2 * iqr * Math.pow(n, -1 / 3))));
  }

  function de(x, stellen) {
    return x.toLocaleString("de-DE", { minimumFractionDigits: stellen, maximumFractionDigits: stellen });
  }

  function schrittNice(maximum) {
    var s = [0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50];
    for (var i = 0; i < s.length; i++) { if (maximum / s[i] <= 5) { return s[i]; } }
    return 100;
  }

  // Histogramm als SVG-Text (gleiche Klassen wie auf den uebrigen Seiten); Hoehe = Anteil der Fahrzeuge je km/h
  function histogrammSvg(hist, kz, limit) {
    var vs = sortiert(hist), n = kz.n, breite = klassenbreite(hist, n);
    var oben = quantilWert(hist, vs, n, 0.9999) + 3;
    oben = Math.min(Math.max(oben, limit ? limit + 15 : 0), vs[vs.length - 1]);
    var von = Math.floor(vs[0] / 10) * 10, bis = Math.max(Math.ceil(oben / 10) * 10, von + 10);
    var versatz = limit ? (limit + 1) % breite : 0, klassen = {}, i, v, start;
    for (i = 0; i < vs.length; i++) {
      v = vs[i];
      if (v < von || v > bis) { continue; }
      start = v - (((v - versatz) % breite) + breite) % breite;
      klassen[start] = (klassen[start] || 0) + hist[v];
    }
    var erster = von - (((von - versatz) % breite) + breite) % breite, liste = [], ymax = 0, a;
    for (start = erster; start <= bis; start += breite) {
      a = 100 * (klassen[start] || 0) / n / breite;
      ymax = Math.max(ymax, a);
      liste.push([start, klassen[start] || 0, a]);
    }
    var schritt = schrittNice(ymax), ytop = Math.max(schritt, Math.ceil(ymax / schritt) * schritt);
    var pw = HIST.B - HIST.L - HIST.R, ph = HIST.H - HIST.T - HIST.U, sc = pw / (bis - von + 1);
    function x(w) { return HIST.L + (w - 0.5 - von) * sc; }
    function y(p) { return HIST.T + ph * (1 - p / ytop); }
    var s = ['<svg class="hist" viewBox="0 0 ' + HIST.B + ' ' + HIST.H + '" role="img" aria-label="Histogramm der Auswahl, Klassenbreite ' + breite + ' km/h">'];
    var k = Math.round(ytop / schritt);
    for (i = 0; i <= k; i++) {
      a = i * schritt;
      s.push('<line class="hist-gitter" x1="' + HIST.L + '" x2="' + (HIST.B - HIST.R) + '" y1="' + y(a).toFixed(1) + '" y2="' + y(a).toFixed(1) + '"/>' +
             '<text class="hist-text" x="' + (HIST.L - 5) + '" y="' + (y(a) + 4).toFixed(1) + '" text-anchor="end">' + (schritt < 1 ? de(a, 1) : Math.round(a)) + ' %</text>');
    }
    var tick = bis - von <= 130 ? 10 : 20;
    for (v = von; v <= bis; v += tick) {
      s.push('<line class="hist-gitter" x1="' + (x(v) + sc / 2).toFixed(1) + '" x2="' + (x(v) + sc / 2).toFixed(1) + '" y1="' + (HIST.T + ph) + '" y2="' + (HIST.T + ph + 4) + '"/>' +
             '<text class="hist-text" x="' + (x(v) + sc / 2).toFixed(1) + '" y="' + (HIST.T + ph + 17) + '" text-anchor="middle">' + v + '</text>');
    }
    s.push('<text class="hist-text" x="' + (HIST.L + pw / 2) + '" y="' + (HIST.H - 6) + '" text-anchor="middle">Geschwindigkeit in km/h</text>');
    for (i = 0; i < liste.length; i++) {
      if (!liste[i][1]) { continue; }
      var klasse = limit && liste[i][0] > limit ? "hist-ueber" : "hist-ok", bisw = liste[i][0] + breite - 1;
      s.push('<rect class="' + klasse + '" x="' + x(liste[i][0]).toFixed(1) + '" y="' + y(liste[i][2]).toFixed(1) + '" width="' + Math.max(0.5, breite * sc - 0.6).toFixed(1) +
             '" height="' + (HIST.T + ph - y(liste[i][2])).toFixed(1) + '"><title>' + (breite === 1 ? liste[i][0] : liste[i][0] + "–" + bisw) + ' km/h: ' +
             de(liste[i][1], 0) + ' Fahrzeuge (' + de(100 * liste[i][1] / n, 2) + ' %)</title></rect>');
    }
    var marken = [];
    if (limit && limit >= von && limit <= bis) { marken.push([x(limit + 1), "Limit " + limit, "hist-limit"]); }
    if (kz.v85 >= von && kz.v85 <= bis) { marken.push([x(kz.v85) + sc / 2, "V85 " + kz.v85, "hist-v85"]); }
    for (i = 0; i < marken.length; i++) {
      var ty = [12, 25][i], ende = marken[i][0] > HIST.B - 90;
      s.push('<line class="' + marken[i][2] + '" x1="' + marken[i][0].toFixed(1) + '" x2="' + marken[i][0].toFixed(1) + '" y1="' + (ty - 9) + '" y2="' + (HIST.T + ph) + '"/>' +
             '<text class="hist-text ' + marken[i][2] + '-text" x="' + (marken[i][0] + (ende ? -4 : 4)).toFixed(1) + '" y="' + ty + '" text-anchor="' + (ende ? "end" : "start") + '">' + marken[i][1] + '</text>');
    }
    s.push("</svg>");
    return { svg: s.join(""), breite: breite };
  }

  function ergebnisHtml(daten, auswahl) {
    var limit = daten.limit, r = waehle(daten, auswahl.zeit, auswahl.tage, auswahl.gruppe), kz = kennzahlen(r.hist, limit);
    if (!kz || kz.n < 1) { return "<p>Für diese Auswahl liegen keine Fahrzeuge vor.</p>"; }
    var je = r.stunden ? de(kz.n / r.stunden, 1) : "–";
    var html = '<div class="tablewrap"><table><caption class="muted">Kennzahlen der Auswahl</caption><thead><tr><th class="num">Fahrzeuge</th><th class="num">je Stunde</th>' +
      '<th class="num">Ø km/h</th><th class="num">V85</th><th class="num">V95</th><th class="num">V99</th>' + (limit ? '<th class="num">Einhaltung</th><th class="num">Qualifiziert</th>' : "") +
      '</tr></thead><tbody><tr><td class="num">' + de(Math.round(kz.n), 0) + '</td><td class="num">' + je + '</td><td class="num">' + de(kz.mittel, 1) + '</td><td class="num">' + kz.v85 +
      '</td><td class="num">' + kz.v95 + '</td><td class="num">' + kz.v99 + '</td>';
    if (limit) {
      html += '<td class="num' + klasseQuote(kz.einhaltung) + '">' + de(kz.einhaltung, 2) + ' %</td><td class="num' + klasseQuote(kz.qualifiziert) + '">' + de(kz.qualifiziert, 2) + ' %</td>';
    }
    html += '</tr></tbody></table></div>';
    if (kz.n < HIST.MIN_FAHRZEUGE) { return html + "<p class=\"muted\">Zu wenige Fahrzeuge für ein Histogramm.</p>"; }
    var h = histogrammSvg(r.hist, kz, limit);
    return html + '<figure class="histfig">' + h.svg + '<figcaption class="muted">Anteil der Fahrzeuge der Auswahl je km/h (Klassenbreite ' + h.breite +
      ' km/h' + (limit ? ", blau bis zum Tempolimit, orange darüber" : "") + '). "je Stunde": Fahrzeuge je vollständig aufgezeichneter Stunde der Auswahl.</figcaption></figure>';
  }

  function klasseQuote(x) { return x === null ? "" : (x < 50 ? " bad" : x < 75 ? " mid" : ""); }

  function starten(abschnitt) {
    var tabelle = abschnitt.querySelector("script.filter-daten"), ziel = abschnitt.querySelector(".filter-ergebnis");
    if (!tabelle || !ziel) { return; }
    var daten;
    try { daten = JSON.parse(tabelle.textContent); } catch (fehler) { return; }
    var felder = abschnitt.querySelectorAll("select[data-feld]");
    function zeichnen() {
      var auswahl = {};
      for (var i = 0; i < felder.length; i++) { auswahl[felder[i].getAttribute("data-feld")] = felder[i].value; }
      ziel.innerHTML = ergebnisHtml(daten, auswahl);
    }
    for (var i = 0; i < felder.length; i++) { felder[i].addEventListener("change", zeichnen); }
    abschnitt.hidden = false;
    zeichnen();
  }

  var api = { waehle: waehle, kennzahlen: kennzahlen, klassenbreite: klassenbreite, histogrammSvg: histogrammSvg, ergebnisHtml: ergebnisHtml };
  if (typeof module !== "undefined" && module.exports) { module.exports = api; }
  if (wurzel.document) {
    var abschnitte = wurzel.document.querySelectorAll("[data-filter]");
    for (var n = 0; n < abschnitte.length; n++) { starten(abschnitte[n]); }
  }
})(typeof window !== "undefined" ? window : this);
