# SPDX-License-Identifier: MIT
"""Schulferien und Feiertage in Nordrhein-Westfalen.

Schulferien: Ferienordnung des Ministeriums fuer Schule und Bildung NRW (amtliche Termine, erster und letzter Ferientag), abgeglichen mit
der OpenHolidays-API (openholidaysapi.org, Abruf Oktober 2026). Bewegliche Ferientage einzelner Schulen sind nicht enthalten.
Gesetzliche Feiertage: rauschen.feiertage_nrw (berechnet).
"""
import datetime as dt

import rauschen

SCHULFERIEN_NRW = [
    ("2021-12-24", "2022-01-08", "Weihnachtsferien"),
    ("2022-04-11", "2022-04-23", "Osterferien"),
    ("2022-06-27", "2022-08-09", "Sommerferien"),
    ("2022-10-04", "2022-10-15", "Herbstferien"),
    ("2022-12-23", "2023-01-06", "Weihnachtsferien"),
    ("2023-04-03", "2023-04-15", "Osterferien"),
    ("2023-05-30", "2023-05-30", "Pfingstferien"),
    ("2023-06-22", "2023-08-04", "Sommerferien"),
    ("2023-10-02", "2023-10-14", "Herbstferien"),
    ("2023-12-21", "2024-01-05", "Weihnachtsferien"),
    ("2024-03-25", "2024-04-06", "Osterferien"),
    ("2024-05-21", "2024-05-21", "Pfingstferien"),
    ("2024-07-08", "2024-08-20", "Sommerferien"),
    ("2024-10-14", "2024-10-26", "Herbstferien"),
    ("2024-12-23", "2025-01-06", "Weihnachtsferien"),
    ("2025-04-14", "2025-04-26", "Osterferien"),
    ("2025-06-10", "2025-06-10", "Pfingstferien"),
    ("2025-07-14", "2025-08-26", "Sommerferien"),
    ("2025-10-13", "2025-10-25", "Herbstferien"),
    ("2025-12-22", "2026-01-06", "Weihnachtsferien"),
    ("2026-03-30", "2026-04-11", "Osterferien"),
    ("2026-05-26", "2026-05-26", "Pfingstferien"),
    ("2026-07-20", "2026-09-01", "Sommerferien"),
    ("2026-10-17", "2026-10-31", "Herbstferien"),
    ("2026-12-23", "2027-01-06", "Weihnachtsferien"),
]
_FERIEN = None
_FEIERTAGE = {}


def _ferien():
    global _FERIEN
    if _FERIEN is None:
        _FERIEN = {}
        for von, bis, name in SCHULFERIEN_NRW:
            t, ende = dt.date.fromisoformat(von), dt.date.fromisoformat(bis)
            while t <= ende:
                _FERIEN[t] = name
                t += dt.timedelta(days=1)
    return _FERIEN


def schulferien(tag):
    """Name der Schulferien in NRW an diesem Tag oder None. Ausserhalb 2022 bis 2026 immer None (keine Angabe)."""
    return _ferien().get(tag)


def feiertag(tag):
    if tag.year not in _FEIERTAGE:
        _FEIERTAGE[tag.year] = rauschen.feiertage_nrw(tag.year)
    return tag in _FEIERTAGE[tag.year]


def besonderer_tag(tag):
    """'ferien', 'feiertag' oder None. Ein Feiertag in den Ferien zaehlt als Feiertag."""
    if feiertag(tag):
        return "feiertag"
    if schulferien(tag):
        return "ferien"
    return None
