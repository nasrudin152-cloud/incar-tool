"""build_phonon() — phonon force constants via DFPT (IBRION=8)."""
from __future__ import annotations

from .defaults import common_base


def build_phonon(info: dict, spin: bool) -> dict:
    tags = common_base(info, spin, ediff="1E-8")
    tags.update({
        "NSW":     "1",
        "IBRION":  "8",
        "ISIF":    "2",
        "POTIM":   "0.015",
        "LREAL":   ".FALSE.",
        "ADDGRID": ".TRUE.",
    })
    return tags
