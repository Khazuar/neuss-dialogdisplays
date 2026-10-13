// SPDX-License-Identifier: MIT
// Auswahl nach Tageszeit, Tagen und Gruppe auf den Detailseiten der Standorte.
// Liest ausschliesslich die Datentabelle (script.filter-daten) der eigenen Seite und rechnet daraus Kennzahlen und
// Histogramm. Keine Verbindungen zu anderen Servern, nichts wird gespeichert. Datenformat: gruppen.py (analysiere),
// Beschreibung in docs/gruppen.md.
// Eine Auswahl ist die Summe der Zellen (Tagschluessel, Stunde). Die Gruppen sind die global angepassten Kurven (Lognormal);
// fuer eine Auswahl werden die Kurven nachgepasst (Anteile, Lage und Breite je Kurve) und dabei an die globale Anpassung
// zurueckgebunden: Je weniger Fahrzeuge die Auswahl hat, desto naeher bleiben die Kurven an der globalen Anpassung (Rueckbindung
// wie KAPPA Fahrzeuge); bei sehr wenigen Fahrzeugen bleiben sie fest. Fahrzeuge werden den Gruppen nicht zugeordnet: Eine Gruppe ist ihre Kurve, der Rest ist, was die Kurven von den Daten nicht erklaeren (Daten minus Kurven, nie
// negativ). Anteile von Gruppen und Rest muessen sich deshalb nicht zu 100 % addieren.
(function (wurzel) {
  "use strict";

  var ZEIT = {
    alle: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23],
    nacht: [22, 23, 0, 1, 2, 3, 4, 5], vormittag: [6, 7, 8, 9, 10, 11], nachmittag: [12, 13, 14, 15, 16, 17, 18],
    abend: [19, 20, 21], schulweg: [7]
  };
  var TAGE = { alle: [0, 1, 2, 3, 4, 5, 6, 7], werktag: [0, 1, 2, 3, 4], samstag: [5], sonn: [6, 7] };
  for (var i = 0; i < 8; i++) { TAGE[String(i)] = [i]; }
  var HIST = { B: 600, H: 290, L: 44, R: 12, T: 38, U: 38, BREITE_MAX: 5, MIN_FAHRZEUGE: 50, WENIG_FAHRZEUGE: 1000, VMAX: 255 };

  // Histogramm {v: Anzahl} der Auswahl (cleaned oder Rauschboden) und die Summe der aufgezeichneten Stunden dieser Zellen
  function waehle(daten, zeit, tage, rausch) {
    var quelle = rausch ? daten.r : daten.z, hist = {}, stunden = 0;
    var ts = TAGE[tage] || [], hs = ZEIT[zeit] || [];
    for (var a = 0; a < ts.length; a++) {
      for (var b = 0; b < hs.length; b++) {
        var key = ts[a] + "|" + hs[b];
        stunden += (daten.tage && daten.tage[key]) || 0;
        var zelle = quelle && quelle[key];
        if (!zelle) { continue; }
        for (var j = 0; j < zelle.length; j += 2) { hist[zelle[j]] = (hist[zelle[j]] || 0) + zelle[j + 1]; }
      }
    }
    return { hist: hist, stunden: stunden };
  }

  function summe(hist) {
    var s = 0;
    for (var v in hist) { s += hist[v]; }
    return s;
  }

  // Form der Summenkurve einer Gruppe: Anteil je km/h ab w0 (Summe 1). Eine Gruppe besteht aus einer oder mehreren Lognormal-Kurven
  // (mu und s des Logarithmus) mit festen Anteilen c innerhalb der Gruppe.
  function kurvenform(g, w0) {
    var gesamt = [], v, j;
    for (v = w0; v <= HIST.VMAX; v++) { gesamt.push(0); }
    for (j = 0; j < g.kurven.length; j++) {
      var k = g.kurven[j], p = [], z = 0;
      for (v = w0; v <= HIST.VMAX; v++) {
        var q = (Math.log(v) - k.mu) / k.s, d = Math.exp(-0.5 * q * q) / (k.s * v);
        p.push(d);
        z += d;
      }
      for (v = 0; v < p.length; v++) { gesamt[v] += k.c * p[v] / z; }
    }
    return gesamt;
  }

  // Normalverteilung: Fehlerfunktion (Fehler unter 1,2e-7), ueberleben(a) = P(Z > a), verhaeltnis(a) = phi(a) / Phi(a)
  function erfc(x) {
    var z = Math.abs(x), u = 1 / (1 + 0.5 * z);
    var r = u * Math.exp(-z * z - 1.26551223 + u * (1.00002368 + u * (0.37409196 + u * (0.09678418 + u * (-0.18628806 + u * (0.27886807 +
            u * (-1.13520398 + u * (1.48851587 + u * (-0.82215223 + u * 0.17087277)))))))));
    return x >= 0 ? r : 2 - r;
  }
  function ueberleben(a) { return 0.5 * erfc(a / Math.SQRT2); }
  function verhaeltnis(a) {
    if (a < -30) { return -a + 1 / -a; }
    return Math.exp(-0.5 * a * a) / Math.sqrt(2 * Math.PI) / (0.5 * erfc(-a / Math.SQRT2));
  }
  function summeListe(a) {
    var s = 0;
    for (var i = 0; i < a.length; i++) { s += a[i]; }
    return s;
  }

  // Kurven je Auswahl nachpassen (EM fuer eine Lognormal-Mischung, links bei w0 abgeschnitten, Startwerte und Rueckbindung an die
  // globale Anpassung). Gibt die Gruppen mit nachgepassten Kurven zurueck (Format wie daten.gruppen), null bei zu wenigen Fahrzeugen.
  // Rueckbindung: Mitte und Streuung jeder Kurve sind der Mittelwert aus den Daten der Auswahl und der globalen Kurve, die globale
  // Kurve zaehlt wie KAPPA Fahrzeuge. Gemessen an der Likelihood auf den jeweils anderen Tagen derselben Auswahl: docs/gruppen.md.
  var NACHPASSEN = { KAPPA: 500, MIN_FAHRZEUGE: 300, ITERATIONEN: 60, S_MIN: 0.03, S_MAX: 0.25, S_KLASSE: 0.8 };

  function verfeinere(daten, hist, optionen) {
    var opt = optionen || {}, kappa = opt.kappa === undefined ? NACHPASSEN.KAPPA : opt.kappa;
    var gr = daten.gruppen || [], w0 = daten.w0 || 1, xa = Math.log(w0 - 0.5), schranke = 0.8416;
    var kurven = [], werte = [], anz = [], n = 0, v, i, j, it;
    gr.forEach(function (g, gi) { g.kurven.forEach(function (k) { kurven.push({ gruppe: gi, mu: k.mu, s: k.s, pi: g.pi * k.c }); }); });
    for (v in hist) { if (Number(v) >= w0) { werte.push(Math.log(Number(v))); anz.push(hist[v]); n += hist[v]; } }
    var K = kurven.length;
    if (!K || n < NACHPASSEN.MIN_FAHRZEUGE) { return null; }
    var mu0 = kurven.map(function (c) { return c.mu; }), s0 = kurven.map(function (c) { return c.s; });
    var mu = mu0.slice(), s = s0.slice();
    var w = kurven.map(function (c) { return c.pi / Math.max(ueberleben((xa - c.mu) / c.s), 1e-9); }), sw = summeListe(w);
    w = w.map(function (x) { return x / sw; });
    var alt = null;
    for (it = 0; it < NACHPASSEN.ITERATIONEN; it++) {
      var obs = new Array(K).fill(0), s1 = new Array(K).fill(0), s2 = new Array(K).fill(0), ll = 0, p = new Array(K);
      for (i = 0; i < werte.length; i++) {
        var x = werte[i], den = 0;
        for (j = 0; j < K; j++) {
          var q = (x - mu[j]) / s[j];
          p[j] = w[j] * Math.exp(-0.5 * q * q) / s[j];
          den += p[j];
        }
        if (den <= 0) { continue; }
        ll += anz[i] * Math.log(den);
        for (j = 0; j < K; j++) {
          var r = anz[i] * p[j] / den;
          obs[j] += r; s1[j] += r * x; s2[j] += r * x * x;
        }
      }
      var z = 0, fehl = new Array(K).fill(0);
      for (j = 0; j < K; j++) { z += w[j] * ueberleben((xa - mu[j]) / s[j]); }
      for (j = 0; j < K; j++) {  // erwartete Fahrzeuge links von w0 (nicht erfasst) mit den Momenten der abgeschnittenen Normalverteilung
        var a = (xa - mu[j]) / s[j], lam = verhaeltnis(a), m1 = mu[j] - s[j] * lam;
        var vr = Math.max(s[j] * s[j] * (1 - a * lam - lam * lam), 1e-12);
        fehl[j] = n / z * w[j] * (1 - ueberleben(a));
        s1[j] += fehl[j] * m1;
        s2[j] += fehl[j] * (vr + m1 * m1);
      }
      var gesamt = obs.map(function (o, jj) { return o + fehl[jj]; }), sg = summeListe(gesamt);
      w = gesamt.map(function (g_) { return Math.max(g_ / sg, 1e-6); });
      for (j = 0; j < K; j++) {
        var nj = Math.max(gesamt[j], 1e-9), mj = (s1[j] + kappa * mu0[j]) / (nj + kappa);
        var ss = s2[j] - 2 * mj * s1[j] + nj * mj * mj;
        var vj = (ss + kappa * (s0[j] * s0[j] + (mj - mu0[j]) * (mj - mu0[j]))) / (nj + kappa);
        s[j] = Math.min(Math.max(Math.sqrt(Math.max(vj, 0)), NACHPASSEN.S_MIN, NACHPASSEN.S_KLASSE / Math.exp(Math.min(Math.max(mj, 0), 6))), NACHPASSEN.S_MAX);
        mu[j] = Math.max(mj, xa - schranke * s[j]);
      }
      if (alt !== null && Math.abs(ll - alt) < 1e-9 * Math.abs(ll)) { break; }
      alt = ll;
    }
    var anteile = w.map(function (x_, jj) { return x_ * ueberleben((xa - mu[jj]) / s[jj]); }), sa = summeListe(anteile);
    return gr.map(function (g, gi) {
      var teil = [], piG = 0;
      for (j = 0; j < K; j++) { if (kurven[j].gruppe === gi) { teil.push(j); piG += anteile[j] / sa; } }
      return { nr: g.nr, anteil: g.anteil, modus: g.modus, pi: piG, verfeinert: true,
               kurven: teil.map(function (jj) { return { mu: mu[jj], s: s[jj], c: piG > 0 ? (anteile[jj] / sa) / piG : 1 / teil.length }; }) };
    });
  }

  // Fortsetzung der Summenkurve einer Gruppe links vom Rand der Anpassung (v = 1 .. w0 - 1), gleiche Normierung wie kurvenform:
  // Anteil je km/h, bezogen auf den erfassten Bereich. Dort ist die Kurve nicht an Daten angepasst, sie zeigt nur, was sie erwarten laesst.
  function kurvenLinks(g, w0) {
    var links = [], v, j;
    for (v = 1; v < w0; v++) { links.push(0); }
    for (j = 0; j < g.kurven.length; j++) {
      var k = g.kurven[j], z = 0, q;
      for (v = w0; v <= HIST.VMAX; v++) { q = (Math.log(v) - k.mu) / k.s; z += Math.exp(-0.5 * q * q) / (k.s * v); }
      for (v = 1; v < w0; v++) { q = (Math.log(v) - k.mu) / k.s; links[v - 1] += k.c * Math.exp(-0.5 * q * q) / (k.s * v) / z; }
    }
    return links;
  }

  // Zerlegt das Histogramm einer Auswahl: Anteile der Gruppen werden bei festen Kurven neu geschaetzt (EM), jede Gruppe ist
  // dann ihre Kurve mal die Zahl der angepassten Fahrzeuge; der Rest ist Daten minus Kurven (nicht negativ), dazu alles unter w0.
  function zerlege(daten, hist, fest, optionen) {
    var w0 = daten.w0 || 1;
    var gr = fest ? (daten.gruppen || []) : (verfeinere(daten, hist, optionen) || daten.gruppen || []);
    var k = gr.length, nfit = 0, v, j, it;
    for (v in hist) { if (Number(v) >= w0) { nfit += hist[v]; } }
    var p = gr.map(function (g) { return kurvenform(g, w0); });
    var pi = gr.map(function (g) { return g.pi; });
    if (nfit > 0) {
      for (it = 0; it < 300; it++) {
        var neu = new Array(k).fill(0), delta = 0;
        for (v in hist) {
          var vi = Number(v) - w0;
          if (vi < 0) { continue; }
          var nenner = 0;
          for (j = 0; j < k; j++) { nenner += pi[j] * p[j][vi]; }
          if (nenner <= 0) { continue; }
          for (j = 0; j < k; j++) { neu[j] += hist[v] * pi[j] * p[j][vi] / nenner; }
        }
        for (j = 0; j < k; j++) { neu[j] /= nfit; delta += Math.abs(neu[j] - pi[j]); }
        pi = neu;
        if (delta < 1e-9) { break; }
      }
    }
    var kurven = [], rest = {}, fortsetzung = [];
    for (j = 0; j < k; j++) {
      var h = {}, l = {}, lk = kurvenLinks(gr[j], w0);
      for (v = 0; v < p[j].length; v++) { h[w0 + v] = nfit * pi[j] * p[j][v]; }
      for (v = 1; v < w0; v++) { l[v] = nfit * pi[j] * lk[v - 1]; }
      kurven.push(h);
      fortsetzung.push(l);
    }
    for (v in hist) {
      var vn = Number(v), modell = 0;
      if (vn >= w0) { for (j = 0; j < k; j++) { modell += kurven[j][vn] || 0; } }
      var r = hist[v] - modell;
      if (r > 1e-9) { rest[vn] = r; }
    }
    return { gruppen: kurven, rest: rest, pi: pi, nfit: nfit, links: fortsetzung, w0: w0, nachgepasst: k > 0 && !!gr[0].verfeinert, kurven: gr };
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
    var vs = sortiert(hist), n = 0, summeV = 0, ok = 0, okq = 0, i, v;
    for (i = 0; i < vs.length; i++) {
      v = vs[i]; n += hist[v]; summeV += v * hist[v];
      if (limit && v <= limit) { ok += hist[v]; }
      if (limit && v - toleranz(v) <= limit) { okq += hist[v]; }
    }
    if (n <= 0) { return null; }
    return {
      n: n, mittel: summeV / n, v85: quantilWert(hist, vs, n, 0.85), v95: quantilWert(hist, vs, n, 0.95), v99: quantilWert(hist, vs, n, 0.99),
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

  // Histogramm als SVG-Text (gleiche Klassen wie auf den uebrigen Seiten); Hoehe = Anteil der Fahrzeuge je km/h.
  // hist: alle Fahrzeuge der Auswahl; opt.vorder: Teil davon (Gruppe oder Rest), farbig bis zur Hoehe seiner Werte, der Rest grau;
  // opt.linie: Kurve der Gruppe als Linie; opt.v85: Marke (Standard: V85 der Fahrzeuge).
  function histogrammSvg(hist, kz, limit, opt) {
    opt = opt || {};
    var vs = sortiert(hist), n = kz.n, breite = klassenbreite(hist, n);
    var oben = quantilWert(hist, vs, n, 0.9999) + 3;
    oben = Math.min(Math.max(oben, limit ? limit + 15 : 0), vs[vs.length - 1]);
    var von = Math.floor(vs[0] / 10) * 10, bis = Math.max(Math.ceil(oben / 10) * 10, von + 10);
    var versatz = limit ? (limit + 1) % breite : 0, i, v, start, a;
    function nachKlassen(h) {
      var k = {}, s;
      for (var w in h) {
        v = Number(w);
        if (v < von || v > bis) { continue; }
        s = v - (((v - versatz) % breite) + breite) % breite;
        k[s] = (k[s] || 0) + h[w];
      }
      return k;
    }
    var klassen = nachKlassen(hist), vorder = opt.vorder ? nachKlassen(opt.vorder) : null, linie = opt.linie ? nachKlassen(opt.linie) : null;
    var erster = von - (((von - versatz) % breite) + breite) % breite, liste = [], ymax = 0;
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
      var bisw = liste[i][0] + breite - 1, bereich = breite === 1 ? liste[i][0] : liste[i][0] + "–" + bisw;
      var breiteX = Math.max(0.5, breite * sc - 0.6).toFixed(1), farbe = limit && liste[i][0] > limit ? "hist-ueber" : "hist-ok";
      var titel = bereich + ' km/h: ' + de(liste[i][1], 0) + ' Fahrzeuge (' + de(100 * liste[i][1] / n, 2) + ' %)';
      if (vorder) {  // alle Fahrzeuge grau, der Teil der Auswahl farbig bis zur Hoehe seiner Werte
        var teil = Math.min(vorder[liste[i][0]] || 0, liste[i][1]), at = 100 * teil / n / breite;
        s.push('<rect class="hist-grau" x="' + x(liste[i][0]).toFixed(1) + '" y="' + y(liste[i][2]).toFixed(1) + '" width="' + breiteX +
               '" height="' + (HIST.T + ph - y(liste[i][2])).toFixed(1) + '"><title>' + titel + '</title></rect>');
        if (teil > 0) {
          s.push('<rect class="' + farbe + '" x="' + x(liste[i][0]).toFixed(1) + '" y="' + y(at).toFixed(1) + '" width="' + breiteX +
                 '" height="' + (HIST.T + ph - y(at)).toFixed(1) + '"><title>' + bereich + ' km/h: ' + de(teil, 0) + ' von ' + de(liste[i][1], 0) + ' Fahrzeugen</title></rect>');
        }
      } else {
        s.push('<rect class="' + farbe + '" x="' + x(liste[i][0]).toFixed(1) + '" y="' + y(liste[i][2]).toFixed(1) + '" width="' + breiteX +
               '" height="' + (HIST.T + ph - y(liste[i][2])).toFixed(1) + '"><title>' + titel + '</title></rect>');
      }
    }
    if (linie) {
      var punkte = [], gestrichelt = [], fort = opt.linieLinks ? nachKlassen(opt.linieLinks) : null;
      var s0 = opt.rand ? opt.rand - (((opt.rand - versatz) % breite) + breite) % breite : null;  // Klasse am Rand der Anpassung
      for (start = erster; start <= bis; start += breite) {
        var punkt = (x(start) + breite * sc / 2).toFixed(1) + "," + y(100 * ((linie[start] || 0) + (fort ? (fort[start] || 0) : 0)) / n / breite).toFixed(1);
        if (fort && s0 !== null && start <= s0) { gestrichelt.push(punkt); }
        if (!fort || s0 === null || start >= s0) { punkte.push(punkt); }
      }
      if (gestrichelt.length > 1) { s.push('<polyline class="hist-modell-links" points="' + gestrichelt.join(" ") + '"/>'); }
      s.push('<polyline class="hist-modell" points="' + punkte.join(" ") + '"/>');
    }
    var v85 = opt.v85 === undefined ? kz.v85 : opt.v85, marken = [];
    if (limit && limit >= von && limit <= bis) { marken.push([x(limit + 1), "Limit " + limit, "hist-limit"]); }
    if (v85 !== null && v85 >= von && v85 <= bis) { marken.push([x(v85) + sc / 2, "V85 " + v85, "hist-v85"]); }
    for (i = 0; i < marken.length; i++) {
      var ty = [12, 25][i], ende = marken[i][0] > HIST.B - 90;
      s.push('<line class="' + marken[i][2] + '" x1="' + marken[i][0].toFixed(1) + '" x2="' + marken[i][0].toFixed(1) + '" y1="' + (ty - 9) + '" y2="' + (HIST.T + ph) + '"/>' +
             '<text class="hist-text ' + marken[i][2] + '-text" x="' + (marken[i][0] + (ende ? -4 : 4)).toFixed(1) + '" y="' + ty + '" text-anchor="' + (ende ? "end" : "start") + '">' + marken[i][1] + '</text>');
    }
    s.push("</svg>");
    return { svg: s.join(""), breite: breite };
  }

  function klasseQuote(x) { return x === null ? "" : (x < 50 ? " bad" : x < 75 ? " mid" : ""); }

  function ergebnisHtml(daten, auswahl) {
    var limit = daten.limit, gruppe = auswahl.gruppe || "alle", rausch = gruppe === "rausch";
    var basis = waehle(daten, auswahl.zeit, auswahl.tage, false), rauschHist = null, nBasis;
    if (rausch) {  // alle aufgezeichneten Fahrten (Fahrzeuge und Rauschboden) grau, der herausgerechnete Rauschboden farbig
      rauschHist = waehle(daten, auswahl.zeit, auswahl.tage, true).hist;
      var alle = {}, w;
      for (w in basis.hist) { alle[w] = basis.hist[w]; }
      for (w in rauschHist) { alle[w] = (alle[w] || 0) + rauschHist[w]; }
      basis = { hist: alle, stunden: basis.stunden };
    }
    nBasis = summe(basis.hist);
    if (nBasis < 1) { return "<p>Für diese Auswahl liegen keine Fahrzeuge vor.</p>"; }
    var hist = basis.hist, vorder = null, linie = null, linieLinks = null, anteil = false, titel = "Kennzahlen der Auswahl", z = null;
    if (rausch) { vorder = rauschHist; anteil = true; titel = "Kennzahlen des Rauschbodens (aus den Fahrten herausgerechnet)"; }
    if (/^g\d+$/.test(gruppe) || gruppe === "rest") {
      z = zerlege(daten, basis.hist);
      if (gruppe === "rest") { vorder = z.rest; titel = "Rest (was die Kurven nicht erklären)"; } else {
        var nr = parseInt(gruppe.slice(1), 10);
        vorder = linie = z.gruppen[nr - 1];
        linieLinks = z.w0 > 1 ? z.links[nr - 1] : null;
        titel = "Kennzahlen der angepassten Kurve von Gruppe " + nr + (z.nachgepasst ? " (für diese Auswahl nachgepasst)" : "");
      }
      hist = basis.hist;
      anteil = true;
    }
    var kzAlle = kennzahlen(basis.hist, limit), kz = vorder ? kennzahlen(vorder, limit) : kzAlle;
    if (!kz || kz.n < 0.5) { return rausch ? "<p>Für diese Auswahl wurde kein Rauschboden herausgerechnet.</p>" : "<p>Für diese Auswahl liegt nichts in dieser Gruppe.</p>"; }
    var je = basis.stunden ? de(kz.n / basis.stunden, 1) : "–";
    // Der Rest (was die Kurven nicht erklaeren) ist nicht zusammenhaengend und hat keine Form: nur Zahl, Anteil und je Stunde, keine Kennwerte.
    var nurZahl = gruppe === "rest";
    var html = '<div class="tablewrap"><table><caption class="muted">' + titel + '</caption><thead><tr><th class="num">Fahrzeuge</th>' +
      (anteil ? '<th class="num">Anteil an allen</th>' : "") + '<th class="num">je Stunde</th>' +
      (nurZahl ? "" : '<th class="num">Ø km/h</th><th class="num">V85</th><th class="num">V95</th><th class="num">V99</th>' + (limit ? '<th class="num">Einhaltung</th><th class="num">Qualifiziert</th>' : "")) +
      '</tr></thead><tbody><tr><td class="num">' + de(Math.round(kz.n), 0) + '</td>' + (anteil ? '<td class="num">' + de(100 * kz.n / nBasis, 1) + ' %</td>' : "") +
      '<td class="num">' + je + '</td>';
    if (!nurZahl) {
      html += '<td class="num">' + de(kz.mittel, 1) + '</td><td class="num">' + kz.v85 + '</td><td class="num">' + kz.v95 + '</td><td class="num">' + kz.v99 + '</td>';
      if (limit) {
        html += '<td class="num' + klasseQuote(kz.einhaltung) + '">' + de(kz.einhaltung, 2) + ' %</td><td class="num' + klasseQuote(kz.qualifiziert) + '">' + de(kz.qualifiziert, 2) + ' %</td>';
      }
    }
    html += '</tr></tbody></table></div>';
    if (anteil && nBasis < HIST.WENIG_FAHRZEUGE) {
      html += '<p class="muted">Wenige Fahrzeuge in dieser Auswahl: Die Anteile der Gruppen sind unsicher.</p>';
    }
    if (nBasis < HIST.MIN_FAHRZEUGE) { return html + "<p class=\"muted\">Zu wenige Fahrzeuge für ein Histogramm.</p>"; }
    var h = histogrammSvg(hist, kzAlle, limit, { vorder: vorder, linie: linie, linieLinks: linieLinks, rand: linieLinks ? z.w0 : null,
                                                 v85: nurZahl ? null : (vorder ? kz.v85 : undefined) });
    var unterschrift = 'Anteil der Fahrzeuge der Auswahl je km/h (Klassenbreite ' + h.breite + ' km/h' + (limit ? ", blau bis zum Tempolimit, orange darüber" : "") +
      '). "je Stunde": Fahrzeuge je vollständig aufgezeichneter Stunde der Auswahl.';
    if (vorder) {
      unterschrift += ' Grau: alle ' + (rausch ? 'aufgezeichneten Fahrten der Auswahl (Fahrzeuge und Rauschboden)' : 'Fahrzeuge der Auswahl') + '. Farbig: ' +
        (rausch ? 'der Rauschboden, der herausgerechnet wurde' : gruppe === "rest" ? 'der Rest, den die Kurven der Gruppen nicht erklären' : 'der Teil, den die angepasste Kurve der Gruppe erklärt (höchstens so hoch wie die Säule), Linie: die Kurve selbst') + '.';
      if (!rausch) { unterschrift += ' Die Anteile der Gruppen und des Rests müssen sich nicht zu 100 % addieren.'; }
      if (linieLinks) {
        unterschrift += ' Gestrichelt: Fortsetzung der Kurve links von ' + z.w0 + ' km/h, dem Rand der Anpassung. Dort ist sie nicht an Daten angepasst und zeigt nur, was sie erwarten lässt.';
      }
    }
    return html + '<figure class="histfig">' + h.svg + '<figcaption class="muted">' + unterschrift + '</figcaption></figure>';
  }

  function starten(abschnitt) {
    var tabelle = abschnitt.querySelector("script.filter-daten"), ziel = abschnitt.querySelector(".filter-ergebnis");
    if (!tabelle || !ziel) { return; }
    var daten;
    try { daten = JSON.parse(tabelle.textContent); } catch (fehler) { return; }
    var felder = abschnitt.querySelectorAll("select[data-feld]");
    var abWahl = abschnitt.querySelector('select[data-feld="abschnitt"]'), grWahl = abschnitt.querySelector('select[data-feld="gruppe"]');
    var abInfo = abschnitt.querySelector(".filter-abschnitt-info"), aktivNr = null;
    function aktiveDaten() {  // ganze Messung oder ein Abschnitt (eigene Zellen und eigene Gruppen, gleiches Tempolimit)
      if (!abWahl || abWahl.value === "alle" || !daten.abschnitte) { return daten; }
      var nr = parseInt(abWahl.value, 10);
      for (var i = 0; i < daten.abschnitte.length; i++) {
        if (daten.abschnitte[i].nr === nr) {
          var d = {}, k;
          for (k in daten.abschnitte[i]) { d[k] = daten.abschnitte[i][k]; }
          d.limit = daten.limit;
          d.v = daten.v;
          return d;
        }
      }
      return daten;
    }
    function gruppenOptionen(d) {  // die Gruppen gehoeren zur gewaehlten Messung oder zum Abschnitt
      if (!grWahl) { return; }
      var alt = grWahl.value, opts = [], i;
      if (d.gruppen && d.gruppen.length) {
        opts.push(["alle", "Alle Daten"]);
        for (i = 0; i < d.gruppen.length; i++) {
          var g = d.gruppen[i];
          opts.push(["g" + g.nr, "Gruppe " + g.nr + " (Modus " + de(g.modus, 0) + " km/h, " + de(g.anteil, 0) + " %)"]);
        }
        opts.push(["rest", "Rest (nicht erklärt)"]);
      } else {
        opts.push(["alle", "Alle Daten (nicht in Gruppen zerlegt)"]);
      }
      var r = d.r, hatRausch = false;
      for (i in r) { if (r.hasOwnProperty(i)) { hatRausch = true; break; } }
      if (hatRausch) { opts.push(["rausch", "Rauschboden (herausgerechnet)"]); }
      grWahl.innerHTML = "";
      var gefunden = false;
      for (i = 0; i < opts.length; i++) {
        var o = wurzel.document.createElement("option");
        o.value = opts[i][0];
        o.textContent = opts[i][1];
        if (opts[i][0] === alt) { o.selected = true; gefunden = true; }
        grWahl.appendChild(o);
      }
      if (!gefunden) { grWahl.value = "alle"; }
    }
    function zeichnen() {
      var d = aktiveDaten();
      var nr = abWahl ? abWahl.value : null;
      if (nr !== aktivNr) {
        aktivNr = nr;
        gruppenOptionen(d);
        if (abInfo) {
          abInfo.textContent = (d === daten || !d.von) ? "Ganze Messung." :
            "Abschnitt " + d.nr + ": " + d.von.split("-").reverse().join(".") + " bis " + d.bis.split("-").reverse().join(".") + ".";
        }
      }
      var auswahl = {};
      for (var i = 0; i < felder.length; i++) { auswahl[felder[i].getAttribute("data-feld")] = felder[i].value; }
      ziel.innerHTML = ergebnisHtml(d, auswahl);
    }
    for (var i = 0; i < felder.length; i++) { felder[i].addEventListener("change", zeichnen); }
    abschnitt.hidden = false;
    zeichnen();
  }

  var api = { waehle: waehle, zerlege: zerlege, verfeinere: verfeinere, ueberleben: ueberleben, kurvenform: kurvenform, kennzahlen: kennzahlen, klassenbreite: klassenbreite,
              histogrammSvg: histogrammSvg, ergebnisHtml: ergebnisHtml };
  if (typeof module !== "undefined" && module.exports) { module.exports = api; }
  if (wurzel.document) {
    var abschnitte = wurzel.document.querySelectorAll("[data-filter]");
    for (var n = 0; n < abschnitte.length; n++) { starten(abschnitte[n]); }
  }
})(typeof window !== "undefined" ? window : this);
