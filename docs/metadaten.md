# Zusätzlich erhobene Metadaten

> Eigene Zusammenstellung, nicht amtlich. Fehler beim Zerlegen der Mitteilungen und bei der Zuordnung zu den DSD-Dateien
> können nicht ausgeschlossen werden (ohne Gewähr); die verlinkten Originaldokumente sind maßgeblich.

Die DSD-Dateien enthalten nur Zeit und Geschwindigkeit je Fahrzeug und die Gerätekonfiguration. Wo genau
gemessen wurde, in welcher Fahrtrichtung und was die Verwaltung dazu mitgeteilt hat, steht nicht darin. Diese
Angaben stammen aus den **Mitteilungen der Verwaltung** („Ergebnisse von Verkehrsmessungen durch Dialog Displays“)
im öffentlichen Ratsinformationssystem der Stadt Neuss und liegen als `metadaten.yaml` in jedem Standortordner,
neben den DSD-Dateien.

Die Mitteilungen sind amtliche Dokumente der Stadt. Übernommen werden nur kurze Angaben (Zahlen, Bezeichnungen,
Daten), keine Texte. Zu jeder Angabe steht der Link auf das Dokument.

## Inhalt von `metadaten.yaml`

Je DSD-Datei im Ordner:

| Feld | Inhalt | Quelle |
|------|--------|--------|
| `geraet` | Konfiguration, Name, Tempolimit der Anzeige (Smiley/Frowny), „Erfassung ab“ in km/h, verdeckte Messung | DSD |
| `verwaltung` | Liste der Angaben der Verwaltung zu dieser Messung (kann leer sein, siehe unten) | Mitteilungen |
| `verwaltung[].bezeichnung` | Messstelle wie in der Mitteilung („Mühlenstraße, FR Windmühlengasse (Wiederholungsmessung)“) | Mitteilung |
| `verwaltung[].fahrtrichtung`, `beidseitig`, `wiederholungsmessung` | aus der Bezeichnung | Mitteilung |
| `verwaltung[].zeitraum` | Erfassungszeitraum, wenn genannt | Mitteilung |
| `verwaltung[].tempolimit_kmh` | vorgeschriebene Geschwindigkeit, wenn genannt | Mitteilung |
| `verwaltung[].fahrzeuge_je_tag`, `fahrzeuge_im_zeitraum` | Fahrzeugbewegungen, gesamt oder `kommend`/`gehend` | Mitteilung |
| `verwaltung[].v85_kmh`, `mittel_kmh` | V85 und mittleres Tempo | Mitteilung |
| `verwaltung[].anteil_unter`, `anteil_ueber` | Anteil der Fahrzeuge unter bzw. über einer Geschwindigkeit | Mitteilung |
| `verwaltung[].einstufung_verwaltung`, `massnahmen_verwaltung` | Einstufung („unkritisch“, „noch akzeptabel“ …) und ob Maßnahmen genannt werden | Mitteilung |
| `verwaltung[].hinweise_verwaltung` | feste Formulierungen zu genannten Besonderheiten (z. B. Radfahrende, Baustelle, verdeckte Messung) | Mitteilung |
| `verwaltung[].quellen` | Vorlage, Gremium, Sitzung und Link auf das Dokument (mehrere, wenn dieselbe Messung mehrfach berichtet wurde) | Mitteilung |
| `verwaltung[].zuordnung` | warum die Angabe zu dieser Datei gehört (`methode`, siehe unten) | berechnet |
| `verwaltung[].abgleich_dsd` | V85, mittleres Tempo und Fahrzeuge je Tag, aus der DSD berechnet, und die Abweichung zur Verwaltung | berechnet |

Eine Angabe, die die Mitteilung nicht enthält, fehlt auch hier. Die Zahlen der Verwaltung stehen so wie
mitgeteilt (gerundet), sie werden nicht korrigiert.

## Zuordnung

Die Mitteilungen nennen weder Dateinamen noch Gerät. Die Zuordnung zu den DSD-Dateien macht `metadaten.py`
nach festen Regeln (Schwellen in `SCHWELLEN`), in dieser Reihenfolge:

1. **Name:** Der Straßenname der Mitteilung passt zum Ordnernamen (Nummer, Jahr und Hausnummer abgezogen). Nennt die
   Mitteilung eine Fahrtrichtung und steht eine im Ordner- oder Dateinamen („FR Norf“, „FR GV“, „FR Speck“), müssen
   sie übereinstimmen.
2. **`name_zeitraum`:** Die Mitteilung nennt einen Erfassungszeitraum, und die Tage, an denen die Datei Fahrzeuge mit
   glaubwürdiger Uhr enthält, liegen zu mindestens 80 % im Zeitraum (siehe [uhr-bewertung.md](uhr-bewertung.md)).
   Das ist die verlässlichste Zuordnung, unabhängig von den Messwerten.
3. **`name_werte`:** Ohne Zeitraum entscheiden V85 (höchstens 2 km/h Abweichung) und mittleres Tempo (höchstens
   3 km/h) sowie das Sitzungsdatum: Die Messung darf höchstens 15 Monate vor der Sitzung geendet haben und nicht
   danach. Gibt es mehrere gleich gute Dateien, bleibt die Angabe offen.
4. **`name_werte_zeitraum_abweichend`:** Der genannte Zeitraum passt nicht, die Werte aber (V85 ±1, Tempo ±2 km/h).
5. **`name_einzige_datei`:** Die Mitteilung nennt keinen verwendbaren Zeitraum, und nur eine Datei kommt nach Name,
   Richtung und Sitzungsdatum in Frage. Die Werte können stärker abweichen, das zeigt `abgleich_dsd`.

Ein Zeitraum, der **nach der Sitzung** endet, in der er berichtet wurde, wird nicht verwendet (vermutlich Tippfehler,
`zeitraum_in_mitteilung` hält ihn fest). Bei den Methoden 3 bis 5 stützt sich die Zuordnung (teilweise) auf die DSD-Werte;
der Abgleich ist dann nicht unabhängig. Alles, was sich nicht eindeutig zuordnen lässt, steht in
`belege/ris-zuordnung.json` unter `nicht_zugeordnet`.

## Abdeckung

Die Verwaltung berichtet Ergebnisse je Messstelle seit Februar 2024. Zu Messungen davor (Ende 2022 bis Sommer 2023)
gibt es im Ratsinformationssystem keine Mitteilung je Messstelle, nur einen allgemeinen Bericht (30.01.2024) zum
Stand der Geräte. Für die Dateien aus dieser Zeit ist `verwaltung` daher leer. Auch später fehlen Messungen, wenn die
Verwaltung nicht darüber berichtet hat. Zwei Messstellen der Mitteilungen haben keine Daten: `Further Straße`
(technischer Defekt) und `Berghäuschensweg, Nebenstraße Hausnummer 323` (Messung auf der Nebenfahrbahn nicht möglich,
das Gerät erfasst auch die Hauptfahrbahn). Sie stehen in `belege/ris-zuordnung.json` unter `nicht_ausgewertet`.

## Abgleich mit der DSD

`abgleich_dsd` rechnet V85, mittleres Tempo und Fahrzeuge je Tag aus der DSD über denselben Zeitraum, nur mit Fahrzeugen
mit glaubwürdiger Uhr. Bei den 32 Zuordnungen über den Zeitraum (`name_zeitraum`, unabhängig von den Werten) gilt:

- **V85:** In 28 von 32 Fällen weicht die DSD höchstens 1 km/h von der Mitteilung ab, in 4 Fällen um 2 bis 3 km/h.
  Wo sie abweicht, liegt die DSD meist niedriger (12 von 14 Fällen).
- **Mittleres Tempo:** Die DSD liegt in 26 von 31 Fällen niedriger (Median −1,3 km/h), in Einzelfällen um mehr als
  10 km/h (z. B. `Ruhrstraße` 109: DSD 18 km/h, Mitteilung 29 km/h).
- **Fahrzeuge je Tag:** Sie weichen in beide Richtungen ab, bei 18 von 23 um mehr als 5 % (nach oben und unten gleich
  häufig). Warum, ist nicht geklärt; die Verwaltungssoftware filtert offenbar nach Geschwindigkeit
  (siehe [dsd-format.md](dsd-format.md)).

Wo die Abweichung groß ist, kann auch die Mitteilung selbst Fehler enthalten: Bei `Villestraße (FR Norf)` nennt sie als
mittleres Tempo 58 km/h bei einer V85 von ebenfalls 58 km/h, was nicht zusammenpasst. Die Fahrzeuge je Tag rechnet die
Verwaltung vermutlich als Fahrzeuge geteilt durch (Ende minus Beginn) des Erfassungszeitraums: 47.453 Fahrzeuge geteilt
durch 90 Tage sind die 527 der Mitteilung zur Bauerbahn, `metadaten.py` rechnet deshalb ebenso.

## Reproduktion

```sh
# Mitteilungen holen und auswerten (Netz, ca. 5 Minuten; pypdf wird nur hierfür gebraucht)
python3 -I tools/ris_sammeln.py ris_roh
PYPDF_PFAD=<Ordner mit pypdf> python3 -I tools/ris_messstellen.py ris_roh belege/ris-messstellen.json

# Messstellen den DSD-Dateien zuordnen und metadaten.yaml schreiben (nur Standardbibliothek)
python3 -I metadaten.py .
```

`ris_roh/` steht nicht im Repository. Die Zerlegung (`tools/ris_messstellen.py`) und die Zuordnung (`metadaten.py`)
sind in `test_metadaten.py` getestet, auch mit den Trennfehlern aus dem PDF-Text der Mitteilungen.
