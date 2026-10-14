// SPDX-License-Identifier: MIT
// Labor-Modus: Inhalte mit der Klasse "labor" (Forschungsstand, etwa die Verhaltensgruppen) sehen nur Besucher, die ihn einschalten.
// Einschalten: ?labor an eine Adresse der Seite hängen (merkt sich der Browser), ausschalten: ?labor=0. Das ist kein Schutz, nur
// ein Ausblenden; die Dateien sind öffentlich. Ohne JavaScript bleibt der Labor-Modus aus. Das Skript steht im head, damit nichts aufblitzt.
(function () {
  "use strict";
  var an = false, treffer = /[?&]labor(?:=([^&#]*))?(?=&|$)/.exec(window.location.search || "");
  var aus = treffer && (treffer[1] === "0" || treffer[1] === "aus");
  try {
    if (treffer) {
      if (aus) { window.localStorage.removeItem("labor"); } else { window.localStorage.setItem("labor", "1"); }
    }
    an = window.localStorage.getItem("labor") === "1";
  } catch (fehler) {
    an = !!treffer && !aus;  // ohne Speicher gilt der Schalter nur für diese Adresse
  }
  if (an) { document.documentElement.classList.add("labor"); }
})();
