# SPDX-License-Identifier: MIT
"""Pfade und numpy fuer die Verhaltensanalyse (tools/verhalten, docs/verhalten.md).

Die Skripte brauchen numpy (nicht Teil der Auswertung, die mit der Standardbibliothek auskommt). Wer numpy nicht installiert hat:
  pip install --target <Ordner> numpy   und   NUMPY_PFAD=<Ordner> setzen
Zwischenergebnisse landen in VERHALTEN_ORDNER (Standard: _verhalten/ im Repository, nicht versioniert).
"""
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.path.dirname(os.path.dirname(HIER))
DATEN = os.environ.get("VERHALTEN_ORDNER") or os.path.join(WURZEL, "_verhalten")
if os.environ.get("NUMPY_PFAD"):
    sys.path.insert(0, os.environ["NUMPY_PFAD"])
for _p in (HIER, WURZEL):
    if _p not in sys.path:
        sys.path.insert(0, _p)
for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")  # ein Rechenfaden je Prozess (die Skripte rechnen mit mehreren Prozessen)
