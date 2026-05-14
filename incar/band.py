"""build_band() — band structure (ICHARG=11)."""
from __future__ import annotations

from .defaults import common_base, add_ldau, add_soc


def build_band(info: dict, spin: bool, ldau: bool, soc: bool) -> dict:
    tags = common_base(info, spin)
    tags.update({
        "NSW":    "0",
        "IBRION": "-1",
        "ISIF":   "2",
        "ICHARG": "11",
        "NBANDS": str(max(int(info["natoms"] * 4), 20)),
    })
    if ldau:
        add_ldau(tags, info)
    if soc:
        add_soc(tags)
    return tags
