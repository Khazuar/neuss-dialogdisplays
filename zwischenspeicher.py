# SPDX-License-Identifier: MIT
"""Zwischenspeicher fuer Ergebnisse je Datei (wie Ebenen beim Bau von Containern).

Jede Ebene hat Schluessel aus dem Inhalt ihrer Eingaben und dem Hash des Skripts, das sie berechnet. Aendert sich nichts davon,
wird das gespeicherte Ergebnis wiederverwendet. Ebenen: "datei" (alles zu einer DSD-Datei) und "gruppen" (die aufwendige
Zerlegung, abhaengig nur von den Zaehlwerten und gruppen.py). Der Ordner liegt nicht im Repository (GitHub Actions haelt ihn
zwischen den Laeufen vor). Nach einem vollstaendigen Lauf raeumt aufraeumen() alles weg, was nicht benutzt wurde.
"""
import hashlib
import json
import os


def code_hash(*pfade):
    h = hashlib.sha256()
    for p in pfade:
        with open(p, "rb") as fh:
            h.update(fh.read())
    return h.hexdigest()[:16]


def inhalts_hash(daten, *zusatz):
    h = hashlib.sha256(daten)
    for z in zusatz:
        h.update(repr(z).encode("utf-8"))
    return h.hexdigest()[:24]


class Zwischenspeicher:
    def __init__(self, ordner):
        self.ordner = ordner
        self.benutzt = set()

    def _pfad(self, ebene, schluessel):
        return os.path.join(self.ordner, ebene, schluessel + ".json")

    def holen(self, ebene, schluessel):
        """Gespeichertes Ergebnis oder None."""
        try:
            with open(self._pfad(ebene, schluessel), encoding="utf-8") as fh:
                erg = json.load(fh)
        except (OSError, ValueError):
            return None
        self.benutzt.add((ebene, schluessel))
        return erg

    def speichern(self, ebene, schluessel, obj):
        pfad = self._pfad(ebene, schluessel)
        os.makedirs(os.path.dirname(pfad), exist_ok=True)
        tmp = pfad + f".{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(obj, fh, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, pfad)
        self.benutzt.add((ebene, schluessel))

    def aufraeumen(self, benutzt):
        """Entfernt alle Eintraege, die nicht in 'benutzt' stehen. Gibt die Zahl der entfernten zurueck."""
        weg = 0
        for ebene in sorted(os.listdir(self.ordner)) if os.path.isdir(self.ordner) else []:
            pfad = os.path.join(self.ordner, ebene)
            if not os.path.isdir(pfad):
                continue
            for f in os.listdir(pfad):
                if f.endswith(".json") and (ebene, f[:-5]) not in benutzt:
                    os.remove(os.path.join(pfad, f))
                    weg += 1
                elif f.endswith(".tmp"):
                    os.remove(os.path.join(pfad, f))
        return weg
