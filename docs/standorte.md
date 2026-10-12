# Standort der Messstellen

> Geschätzt, nicht vermessen. Die DSD-Dateien enthalten keine Position, und die Verwaltung nennt nur Straßen,
> gelegentlich Hausnummern. Koordinaten und Unsicherheit sind eigene Rechnung (ohne Gewähr); es gibt keine Vergleichskoordinaten,
> mit denen sie sich prüfen ließen.

Zu jedem Standortordner steht in der `metadaten.yaml` ein Block `standort`: Koordinaten, ein Radius der Unsicherheit in Metern,
wie der Wert zustande kam und welche Angaben dafür herangezogen wurden. Die Geräte hängen an Laternenmasten am Straßenrand;
die Rechnung sucht deshalb den Abschnitt der Straße, nicht den Mast.

## Quellen

| Quelle | Was sie liefert | Wo |
|--------|-----------------|----|
| **Hauskoordinaten** der Stadt Neuss (Geobasis NRW, Gebäudereferenzen, [Datenlizenz Deutschland – Zero – Version 2.0](https://www.govdata.de/dl-de/zero-2-0)) | die Karte: 34.019 Adressen mit Lage in Metern (ETRS89 / UTM 32, EPSG:25832). Straßenachsen und Orte gibt es darin nicht, nur die Häuser | `belege/neuss-adressen.csv`, erzeugt von `tools/adressen_laden.py` |
| **Ordnername** | Straße, oft Hausnummer („Hauptstraße 13a“, „Cyriakusstraße 86-88“), „ggü. Nr.“, „Ecke“, „Höhe“, „zwischen A und B“ | die Ordner |
| **Mitteilungen der Verwaltung** | Bezeichnung der Messstelle („Kreitzweg (Höhe Ludgerusring)“), Fahrtrichtung („FR Hertzstraße“), „beidseitige Messung“ | `metadaten.yaml`, `verwaltung[].bezeichnung` |
| **Berichte der Messsoftware** (DataCollect-PDF der Verwaltung, nicht im Repository) | Name der Messstelle mit Hausnummer („Bataverstr. 103“) und die Querstraßen an den Enden der Messstrecke | `belege/standort-hinweise.json`, Quelle `datacollect` |
| **Vorlagen und Anträge** im Ratsinformationssystem | Standortvorschläge der Bezirksausschüsse („Kaarster Straße, Höhe Nr. 71, FR Kaarst“) und ein Antrag mit der Fahrtrichtung zur Daimlerstraße 140 | `belege/standort-hinweise.json`, Quelle `ris`, mit Vorlage, Sitzung und Link |

In den Beschlussvorlagen der Bezirksausschüsse, die festlegen sollen, welche der Vorschläge umgesetzt werden, sind die Plätze für die
gewählten Standorte nicht ausgefüllt („1. …“). Ein Vorschlag belegt also nicht, dass dort gemessen wurde.

## Verfahren

Jeder Hinweis wird zu einem **Kreis** (Mittelpunkt, Radius). Der Radius ist die angenommene Unsicherheit; gemeint ist ungefähr der 90-%-Bereich.

| Hinweis (`methode`) | Mittelpunkt | Radius |
|---------------------|-------------|--------|
| `adresse` – Hausnummer („Höhe Nr. 4“, „Nr. 86-88“) | die Hauskoordinate (bei mehreren Nummern ihr Mittel) | 30 m, bei „ggü.“ 45 m, plus die halbe Spanne mehrerer Nummern. Fehlt die Nummer im Verzeichnis: Mitte der beiden Nachbarnummern, der Radius wächst um den Abstand der Nachbarn |
| `zwischen_nr` – „zwischen Nr. 116 und 126“ | Mittel der Häuser dazwischen | 25 m plus halbe Spanne |
| `kreuzung` – „Ecke“, „Höhe“ einer Querstraße | Mitte des nächsten Häuserpaars der beiden Straßen | 40 m plus halber Abstand dieses Paars |
| `zwischen_strassen` – Abschnitt zwischen zwei Querstraßen | das Haus der Straße, das der Mitte der beiden Kreuzungen am nächsten liegt | größerer Abstand zu den beiden Kreuzungen plus 25 m |
| `strasse` – nur der Straßenname | das Haus mit der kleinsten Abstandssumme zu den übrigen (liegt an der Straße, anders als ein Schwerpunkt in einer Kurve) | der Abstand, der 90 % der Häuser der Straße enthält, mindestens 40 m (bei weniger als vier Häusern 60 m) |

Die Zahlen 30, 40 und 25 m sind angenommen. Sie stützen sich darauf, wie die Häuser liegen: An 218 nahezu geraden Straßen
(mindestens 12 Adressen) liegen die Hauskoordinaten im Median 12 m (90 %: 46 m) neben der Geraden, die durch die Häuser der Straße
verläuft, und aufeinanderfolgende Adressen entlang der Straße
sind im Median 6 m (90 %: 19 m) voneinander entfernt. Ein Mast „in Höhe“ eines Hauses steht also meist innerhalb von 20 bis 30 m
neben dessen Koordinate; die Gegenseite kommt mit 15 m dazu. Wer andere Werte für richtig hält, ändert `ANNAHMEN` in `standorte.py`.

**Entscheidung.** Das Ergebnis ist der Hinweis mit dem kleinsten Radius. Die übrigen werden gegengeprüft: Liegt das Ergebnis
innerhalb ihres Bereichs (bei einer ganzen Straße: bei einem ihrer Häuser), bestätigen sie es; sonst steht `widerspricht: true` in
`belege`. Ein Hinweis zählt nicht, wenn sich die Straße nicht finden lässt oder eine Querstraße nicht an der Straße beginnt
(`nicht_verwendet` nennt den Grund). Die Straßennamen werden ohne Rücksicht auf ß/ss, Umlaute, Leerzeichen und „Str.“ verglichen;
eine Abweichung um einen Buchstaben („Eichendorfstraße“ statt „Eichendorffstraße“) gilt bei genau einem Treffer.

**`sicherheit`:**

- `benannt` – die Verwaltung (Ordnername, Mitteilung, Bericht der Messsoftware) nennt den Ort.
- `vermutet` – nur ein Standortvorschlag oder Antrag nennt die Hausnummer, und sie liegt auf der Straße des Ordners. Der Radius ist dann
  mindestens 60 m. Das trifft sieben Ordner; ob der Vorschlag umgesetzt wurde, steht nirgends.
- `widersprüchlich` – zwei gleichrangige Angaben schließen sich aus. Das ist nur `07_Lupinen_Nierenhofstraße`: der Ordner nennt beide Straßen,
  sie liegen 600 m auseinander. Der Kreis umfasst beide.

**`mehrdeutig`** steht, wenn die Straße aus getrennten Abschnitten besteht (mehr als 400 m ohne Haus) und die Angabe nicht klärt,
in welchem gemessen wurde (sechs Ordner, darunter beide Bonner Straßen und die Villestraße).

**Fahrtrichtung.** Nennt die Mitteilung „FR X“ und beginnt die Straße X an der Straße des Ordners (Häuser höchstens 120 m auseinander),
steht `fahrtrichtung` mit der Kompassrichtung des Verkehrs (`peilung_grad`, 0 = Nord, 90 = Ost) und ihrer Unsicherheit. Die Richtung der
Straße kommt aus den zwölf nächsten Häusern (Hauptachse), das Vorzeichen aus der Lage der Querstraße. Das gibt es nur bei Standorten mit
höchstens 300 m Radius und nicht bei „beidseitiger Messung“ (`beidseitige_messung: true`). Ziele, die Orte sind („FR Kaarst“, „FR Norf“) oder
nicht an der Straße beginnen, ergeben keine Richtung. Das sind drei Ordner (Salzstraße, Gohrer Straße, Mühlenstraße 87).

Die Querstraßen in den Berichten der Messsoftware („Rtg. kommend/gehend“) benennen oft nur das Ziel in der Ferne, nicht die
Kreuzung am Ende der Messstrecke: Bei der Nordkanalallee (Berghäuschensweg 309 m entfernt), der Neuenberger Straße (Horremer Straße 1.034 m)
und dem Konrad-Adenauer-Ring (Jülicher Straße 1.021 m) beginnt die Straße nicht an der Messstelle; die Hinweise werden dann nicht verwendet.
Gerechnet werden sie nur, wenn beide Straßen die Straße des Ordners berühren (Feldstraße, Holunderweg, Thywissenstraße); den Ausschlag geben sie
nur bei der Feldstraße, bei den anderen beiden ist die ganze Straße genauer.

## Ergebnis

94 Standortordner, alle mit Standort. Der Radius liegt zwischen 30 und 1.387 m, im Median bei 237 m.

| Hinweis | Ordner | `sicherheit` |
|---------|--------|--------------|
| `adresse` | 12 | 6 benannt (Hausnummer im Ordnernamen oder Bericht), 6 vermutet (Vorschlag) |
| `zwischen_nr` | 1 | vermutet |
| `kreuzung` | 3 | benannt |
| `zwischen_strassen` | 2 | benannt |
| `strasse` | 76 | 75 benannt, 1 widersprüchlich |

| Radius bis | Ordner |
|------------|--------|
| 50 m | 8 |
| 100 m | 26 |
| 200 m | 42 |
| 300 m | 59 |
| 500 m | 74 |
| 1.000 m | 89 |

Bei 76 von 94 Ordnern steht nur die Straße fest. Das ist der Kern der Unsicherheit: Der Radius ist dann die Ausdehnung der Straße,
nicht ein Messfehler. Eine Hausnummer, „Ecke“, „Höhe“ oder „zwischen“ im Namen verkleinert ihn auf 30 bis 110 m.

## Format

```yaml
standort:
  breite: 51.160833          # Grad, WGS84 (ETRS89 weicht um weniger als einen Meter ab)
  laenge: 6.666808
  utm32_ost: 336857          # Meter, ETRS89 / UTM 32 (EPSG:25832), wie die Hauskoordinaten
  utm32_nord: 5670298
  unsicherheit_m: 30         # Radius um den Punkt, ungefähr 90 %
  methode: "adresse"         # adresse | zwischen_nr | kreuzung | zwischen_strassen | strasse
  sicherheit: "benannt"      # benannt | vermutet | widersprüchlich
  strasse: "Hauptstraße"
  beschreibung: "Hausnummer 13a im Verzeichnis"
  mehrdeutig: "…"            # nur wenn die Straße aus getrennten Abschnitten besteht
  beidseitige_messung: true  # nur wenn so berichtet
  fahrtrichtung: {ziel: "Neumarkt", peilung_grad: 159, unsicherheit_grad: 29}
  belege:                    # alle Hinweise, auch die nicht verwendeten, mit Quelle
    - art: "adresse"
      text: "Hauptstraße 13a"
      stufe: "benannt"       # benannt | vorschlag
      quelle: {typ: "ordnername", name: "03_2024_Hauptstraße 13a"}
      ort: "Hausnummer 13a im Verzeichnis"
      radius_m: 30
      abstand_zum_ergebnis_m: 0
      verwendet: true
      widerspricht: false
  nicht_verwendet: […]       # Hinweise, die sich nicht auswerten ließen, mit Grund
  nicht_auswertbar: […]      # Teile des Namens ohne Ort im Verzeichnis („Eingang“, „Görresschule“)
```

Dieselben Angaben stehen in `belege/metadaten.json`.

## Grenzen

- **Straßenseite und Mast** sind nicht bekannt. Hauskoordinaten liegen im Gebäude, nicht an der Straße; eine Straßenachse gibt es in den Daten nicht.
- **Ein Ordner kann mehrere Positionen enthalten.** Die Verwaltung nennt für jeden Standort 4 bis 6 Wochen bis rund 3 Monate; das Gerät kann in
  dieser Zeit versetzt worden sein, und ein Ordner enthält mitunter mehrere Dateien aus verschiedenen Zeiträumen. Der Standort gilt für den Ordner
  als Ganzes. Ein Beispiel für Abweichungen vom Plan ist der Lanzerather Buschweg: Laut Antrag der Fraktionen (März 2024) wurde das Gerät im September 2023
  am Straßenende statt in Höhe der Nr. 101 aufgehängt. Die Messung im Ordner stammt von April bis Juli 2024; ob sie an der geplanten Stelle stand, ist
  offen (Vorschlag, `vermutet`).
- **Gleichnamige Straßen** in anderen Stadtteilen sind nur dort getrennt, wo die Häuser mehr als 400 m auseinander liegen. Eine Hausnummer, die in zwei
  Abschnitten vorkommt, wird als `mehrdeutig` mit einem entsprechend großen Kreis geführt.
- **Orte** („Pomona“, „Görresschule“, „Stiftskeller“, „Stadion“) stehen nicht im Verzeichnis und ergeben keine Koordinate.
- Die **Fahrtrichtung** aus den Mitteilungen bezeichnet das Ziel („FR Kaarst“); bei „beidseitig“ ist sie nur ein Name.

## Erzeugen

```sh
python3 -I tools/adressen_laden.py belege/neuss-adressen.csv      # Netz, rund 100 MB; oder: ... belege/neuss-adressen.csv gebref.zip
python3 -I metadaten.py .                                         # schreibt Standort und alles übrige in die metadaten.yaml
python3 -I standorte.py                                           # nur die Tabelle, ohne die DSD-Dateien zu lesen
```

Die Hinweise aus Anträgen und Berichten stehen mit Zitat und Quelle in `belege/standort-hinweise.json`; neue Hinweise dort ergänzen und
`metadaten.py` neu starten. `test_standorte.py` prüft die Rechnung an einem kleinen Verzeichnis und die Hinweise gegen das echte.

## Lizenz und Quelle

Die Hauskoordinaten stehen unter der Datenlizenz Deutschland – Zero – Version 2.0 (keine Einschränkung, keine Bedingung). Quelle:
Geobasis NRW, Gebäudereferenzen, <https://www.opengeodata.nrw.de/produkte/geobasis/lk/akt/gebref_txt/>. `belege/neuss-adressen.csv`
enthält davon nur Straße, Hausnummer, Zusatz, Lage und Qualitätsstufe der Adressen der Stadt Neuss.

## Was noch ginge

- **Straßenachsen** aus einem Open-Data-Bestand (zum Beispiel das Basis-DLM von Geobasis NRW; vorher die Lizenz prüfen) statt der Häuserpunkte: Dann ließe
  sich „zwischen zwei Querstraßen“ und „Ende der Straße“ genau rechnen, und der Mast läge auf der Straße. Daten aus OpenStreetMap (Straßenlaternen,
  Orte) stehen unter der ODbL und passen nicht zu CC0.
- **Wetterstation je Messstelle** statt je Stadt ([wetter.md](wetter.md)): Die Koordinaten erlauben, die nächste DWD-Station zu wählen.
- Wer einzelne Standorte kennt (oder prüft), kann die Radien an echten Positionen eichen; ohne solche Vergleichswerte bleibt `ANNAHMEN` eine Annahme.
