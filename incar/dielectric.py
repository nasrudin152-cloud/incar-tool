"""build_dielectric() — dielectric function via DFPT (IBRION=8)."""
from __future__ import annotations

from .defaults import common_base


def build_dielectric(info: dict, spin: bool, method: str = "dfpt") -> dict:
    tags = common_base(info, spin, ediff="1E-8")
    tags.update({
        "NSW":      "0",
        "IBRION":   "8" if method == "dfpt" else "-1",
        "ISIF":     "2",
        "LEPSILON": ".TRUE.",
        "LRPA":     ".FALSE.",
    })
    return tags
