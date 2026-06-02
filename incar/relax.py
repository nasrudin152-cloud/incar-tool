"""build_relax() — structural relaxation (IBRION=2)."""
from __future__ import annotations

from .defaults import common_base, add_ldau, add_soc


def build_relax(
    info: dict,
    spin: bool,
    ldau: bool,
    soc: bool,
    nsw: int = 300,
    isif: int = 2,
) -> dict:
    tags = common_base(info, spin)
    tags.update({
        "NSW":    str(nsw),
        "IBRION": "2",
        "POTIM":  "0.2",
        "ISIF":   str(isif),
    })
    if ldau:
        add_ldau(tags, info)
    if soc:
        add_soc(tags)
    return tags
