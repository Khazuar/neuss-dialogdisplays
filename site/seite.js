// SPDX-License-Identifier: MIT
// Standortseiten: Reiter, Auswahl der Messung und Auswahl des Abschnitts (Gefährdung, Lärm). Ohne JavaScript stehen alle Reiter und
// Messungen untereinander. Adresse: #<messung> oder #<messung>/<reiter>, etwa #m-47-bonner-strasse-12/analyse.
(function () {
  "use strict";
  var d = document;
  var nav = d.querySelector(".reiter");
  if (!nav) { return; }
  var knoepfe = nav.querySelectorAll('[role="tab"]');
  var flaechen = d.querySelectorAll('[role="tabpanel"]');
  var messwahl = d.querySelector("select[data-messwahl]");
  var reiter = knoepfe.length ? knoepfe[0].getAttribute("data-ziel") : null;
  var messung = messwahl ? messwahl.value : null;
  var i;

  function adresse() {
    var teile = [];
    if (messung && messwahl) { teile.push(messung); }
    if (reiter) { teile.push(reiter); }
    var neu = "#" + teile.join("/");
    if (window.history && window.history.replaceState && window.location.hash !== neu) { window.history.replaceState(null, "", neu); }
  }

  function zeige() {
    for (i = 0; i < knoepfe.length; i++) {
      var an = knoepfe[i].getAttribute("data-ziel") === reiter;
      knoepfe[i].setAttribute("aria-selected", an ? "true" : "false");
      knoepfe[i].tabIndex = an ? 0 : -1;
    }
    for (i = 0; i < flaechen.length; i++) { flaechen[i].hidden = flaechen[i].getAttribute("data-reiter") !== reiter; }
    if (messwahl) {
      var teile = d.querySelectorAll("[data-messung]");
      for (i = 0; i < teile.length; i++) {
        if (teile[i].classList.contains("messung-teil")) { teile[i].hidden = teile[i].getAttribute("data-messung") !== messung; }
      }
      messwahl.value = messung;
    }
    adresse();
  }

  function ausAdresse() {
    var h = decodeURIComponent((window.location.hash || "").replace(/^#/, ""));
    if (!h) { return; }
    var teile = h.split("/");
    for (var k = 0; k < teile.length; k++) {
      var t = teile[k];
      if (messwahl && messwahl.querySelector('option[value="' + t.replace(/"/g, "") + '"]')) { messung = t; }
      for (var j = 0; j < knoepfe.length; j++) { if (knoepfe[j].getAttribute("data-ziel") === t) { reiter = t; } }
    }
  }

  for (i = 0; i < knoepfe.length; i++) {
    knoepfe[i].addEventListener("click", function () { reiter = this.getAttribute("data-ziel"); zeige(); });
    knoepfe[i].addEventListener("keydown", function (ev) {  // Pfeiltasten zwischen den Reitern
      var liste = Array.prototype.slice.call(knoepfe), k = liste.indexOf(this);
      if (ev.key === "ArrowRight" || ev.key === "ArrowLeft") {
        k = (k + (ev.key === "ArrowRight" ? 1 : liste.length - 1)) % liste.length;
        reiter = liste[k].getAttribute("data-ziel");
        zeige();
        liste[k].focus();
        ev.preventDefault();
      }
    });
  }
  if (messwahl) { messwahl.addEventListener("change", function () { messung = messwahl.value; zeige(); }); }
  var verweise = d.querySelectorAll("[data-messung-link]");
  for (i = 0; i < verweise.length; i++) {
    verweise[i].addEventListener("click", function (ev) {
      messung = this.getAttribute("data-messung-link");
      reiter = "messung";
      zeige();
      ev.preventDefault();
    });
  }
  window.addEventListener("hashchange", function () { ausAdresse(); zeige(); });

  // Abschnitt in Gefährdung und Lärm
  var wahlen = d.querySelectorAll("[data-abschnittwahl]");
  for (i = 0; i < wahlen.length; i++) {
    (function (w) {
      var sel = w.querySelector("select"), behaelter = w.parentNode;
      function abschnitt() {
        var bloecke = behaelter.querySelectorAll(":scope > [data-abschnitt]");
        for (var j = 0; j < bloecke.length; j++) { bloecke[j].hidden = bloecke[j].getAttribute("data-abschnitt") !== sel.value; }
      }
      sel.addEventListener("change", abschnitt);
      w.hidden = false;
      abschnitt();
    })(wahlen[i]);
  }

  var hinweise = d.querySelectorAll("[data-ohne-skript]");
  for (i = 0; i < hinweise.length; i++) { hinweise[i].hidden = true; }
  var titel = d.querySelectorAll(".messung-titel");
  for (i = 0; i < titel.length; i++) { titel[i].hidden = true; }  // die Auswahl oben nennt die Messung
  nav.hidden = false;
  ausAdresse();
  zeige();
})();
