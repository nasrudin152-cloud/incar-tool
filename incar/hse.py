"""build_hse() — HSE06 hybrid functional (static or relax)."""
from __future__ import annotations

from .defaults import common_base


def build_hse(info: dict, spin: bool, calc: str = "scf") -> dict:
    tags = common_base(info, spin)
    tags.update({
        "GGA":      "PE",
        "LHFCALC":  ".TRUE.",
        "HFSCREEN": "0.2",
        "AEXX":     "0.25",
        "ALGO":     "Damped",
        "TIME":     "0.4",
        "PRECFOCK": "Fast",
        "NSW":      "0",
        "IBRION":   "-1",
        "ISIF":     "2",
        "LWAVE":    ".TRUE.",
        "LCHARG":   ".TRUE.",
    })
    if calc == "relax":
        tags.update({
            "NSW":    "100",
            "IBRION": "2",
            "POTIM":  "0.2",
            "LWAVE":  ".FALSE.",
            "LCHARG": ".FALSE.",
        })
    return tags
