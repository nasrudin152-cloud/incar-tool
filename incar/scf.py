"""build_scf() — static single-point SCF."""
from __future__ import annotations

from .defaults import common_base, add_ldau, add_soc


def build_scf(info: dict, spin: bool, ldau: bool, soc: bool) -> dict:
    tags = common_base(info, spin)
    tags.update({
        "NSW":    "0",
        "IBRION": "-1",
        "ISIF":   "2",
        "LWAVE":  ".TRUE.",
        "LCHARG": ".TRUE.",
    })
    if ldau:
        add_ldau(tags, info)
    if soc:
        add_soc(tags)
    return tags
