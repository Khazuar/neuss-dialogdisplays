# Villestraße: offene und verdeckte Messung

> Eigene Auswertung, nicht amtlich. Fehler im Verfahren und in der Auswertung können nicht ausgeschlossen werden (ohne Gewähr).

An der stationären Messstelle Villestraße (Tempo 50, zwei Fahrtrichtungen) lief das Dialogdisplay ab März 2023 offen, also mit Anzeige.
Von Ende März bzw. Ende April bis 24.07.2024 maß es **verdeckt**: Das Gerät zeichnete auf, zeigte aber nichts an. In den DSD-Dateien ist dafür
das Flag `hidden_measurement_on` gesetzt (`verdeckte_messung` in `metadaten.yaml` und `messungen.csv`); es kommt in keiner anderen Datei vor.
Ab Ende November 2024 maß das Gerät in Fahrtrichtung Norf wieder offen.

Die Verwaltung schreibt dazu (Mitteilung zur Sitzung des Bezirksausschusses III am 14.11.2024): „Bei den Standorten auf der Villestraße wurde
diesmal eine ‚verdeckte Messung‘ vorgenommen. Ein Unterschied zu den Ergebnissen der ‚offenen Messung‘ vom Jahresanfang ist nicht festzustellen.“
Verglichen sind dort V85 und Mittel der offenen Messung von Januar bis März 2024 mit der verdeckten Messung im Frühjahr und Sommer 2024.

## Befund

Zahlen aus `tools/verdeckt_vergleich.py` (bereinigte Stundendaten, vollständig aufgezeichnete Stunden, Rauschboden abgezogen; „zu schnell“ =
über Limit plus Toleranz, also über 53 km/h; Spannen: 90-%-Bereich eines Bootstraps über ganze Kalenderwochen).

**Verlauf je Monat (Schultage), Anteil zu schnell:** In 13 Monaten offener Messung (März 2023 bis März 2024) lag er in beiden Richtungen
zwischen 21,5 und 27,3 %, ohne erkennbaren Gang über die Jahreszeit. Mit dem ersten verdeckten Monat (April 2024) springt er in beiden
Richtungen (Norf 24,3 → 31,1 %, Grevenbroich/Speck 24,5 → 28,4 %) und steigt während der verdeckten Messung weiter bis Juli (37,5 bzw. 33,7 %).
Nach dem Wiedereinschalten (Norf, Dezember 2024 bis März 2025) bleibt er hoch (31,0 bis 35,2 %).

**Gleiche Kalendertage, offen 2023 gegen verdeckt 2024 (schaltet die Jahreszeit aus), Schultage:**

| Fahrtrichtung | | Mittel | V85 | zu schnell | zu schnell je Stunde | Fahrzeuge je Stunde |
|---|---|---|---|---|---|---|
| Norf | offen 2023 | 50,1 | 56 | 25,1 % | 34,4 | 137,4 |
| | verdeckt 2024 | 51,3 | 57 | 34,5 % | 47,1 | 136,7 |
| | Unterschied | +1,2 (+0,9 bis +1,6) | +1 (+1 bis +2) | +9,4 Pp. (+8,0 bis +10,9) | +12,7 (+10,2 bis +15,1) | −0,7 |
| Grevenbroich/Speck | offen 2023 | 48,5 | 55 | 23,5 % | 24,9 | 106,1 |
| | verdeckt 2024 | 50,6 | 57 | 31,6 % | 32,1 | 101,7 |
| | Unterschied | +2,0 (+1,6 bis +2,4) | +2 (+1 bis +2) | +8,1 Pp. (+7,0 bis +9,1) | +7,2 (+5,9 bis +8,4) | −4,4 |

Der Vergleich der Verwaltung (offen Januar bis März 2024 gegen verdeckt) ergibt dasselbe Bild: V85 +1 bis +2 km/h, Anteil zu schnell +8 bis
+12 Prozentpunkte. Die Verkehrsmenge ist nahezu gleich.

**Was das heißt:** Die V85 ändert sich nur um 1 bis 2 km/h, weil sie in ganzen km/h angegeben wird und die Verteilung um das Limit herum sehr
dicht ist. In derselben Zeit steigt aber die Zahl der Fahrzeuge über 53 km/h um gut ein Drittel (Norf 25 → 35 %, 34 → 47 je Stunde). Die Verteilung
ist als Ganzes um etwa 1 bis 2 km/h nach oben verschoben; mit Anzeige lag ihr Gipfel genau am Tempolimit, ohne Anzeige knapp darüber. „Kein
Unterschied“ trifft für die V85 in ganzen km/h zu, für den Anteil zu schneller Fahrzeuge nicht.

## Grenzen und andere Erklärungen

- **Das Experiment misst die Wirkung eines bekannten Displays.** Es lief vor der verdeckten Messung schon ein Jahr. Was ein neu aufgestelltes
  Display bewirkt, zeigt dieser Vergleich nicht. Dafür hätte man zuerst verdeckt und dann offen messen müssen, oder mit einem unabhängigen
  Messgerät vor, während und nach dem Einsatz.
- **Nach dem Wiedereinschalten geht der Anteil nicht zurück.** Zwei Deutungen sind möglich: Die Fahrenden haben gelernt, dass das Display „nichts
  tut“, und behalten das Tempo bei. Oder mit der Umstellung auf verdeckt hat sich etwas an der Messung selbst geändert. Bei der Umstellung wurde
  das Gerät neu konfiguriert (die Anzeige-Schwelle in der DSD steht in den verdeckten Dateien auf 30 bzw. 20 statt 50 km/h); wurde es dabei
  anders montiert, misst ein Radar unter anderem Winkel andere Geschwindigkeiten (Kosinuseffekt, bei 50 km/h etwa 1 km/h je 2 % Unterschied).
  Gegen eine reine Messverschiebung spricht, dass der Anteil während der verdeckten Messung von Monat zu Monat weiter steigt; eine neue Montage
  wäre ein einzelner Sprung. Belegen lässt sich das nur mit Angaben der Verwaltung (Montage, Winkel, Wartung).
- **Fahrtrichtung Grevenbroich/Speck:** Die verdeckte Datei heißt „L 142 FR Speck“, liegt aber im Ordner „FR GV“; die Verwaltung nennt sie
  „FR Speck“. Die Verkehrsmenge (rund 100 Fahrzeuge je Stunde wie bei FR GV, nicht 130 wie bei FR Norf) spricht für dieselbe Fahrtrichtung.
- **Andere Einflüsse 2024** (Baustellen in der Umgebung, Umleitungen) sind nicht ausgeschlossen. Die Verkehrsmenge blieb aber gleich, und beide
  Fahrtrichtungen springen im selben Monat.
- **Angaben der Verwaltung:** Für die verdeckte Messung FR Norf nennt die Mitteilung „V85 58 km/h, Mittel 58 km/h“. Ein Mittel gleich der V85
  ist bei dieser Verteilung nicht möglich; die DSD ergibt ein Mittel von 47,4 km/h (ohne Abzug des Rauschbodens). Vermutlich ein Übertragungsfehler.
  Den Zeitraum der verdeckten Messung gibt sie mit 11.01. bis 24.07.2024 an, er überschneidet sich damit mit der offenen Messung bis 19.03.2024.

## Reproduktion

```sh
python3 -I tools/verdeckt_vergleich.py _vorschau/daten --html verdeckt.html   # Tabellen, Monatsverlauf und Histogramme
```
