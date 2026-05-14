"""build_dos() — density of states.

Default smearing: ISMEAR=0 (Gaussian) — safe for all systems.
Pass tetrahedron=True for ISMEAR=-5; only valid with a uniform
dense k-mesh (at least 4×4×4) and insulator/semiconductor.
"""
from __future__ import annotations

from .defaults import common_base, add_ldau, add_soc


def build_dos(
    info: dict,
    spin: bool,
    ldau: bool,
    soc: bool,
    tetrahedron: bool = False,
) -> dict:
    tags = common_base(info, spin)
    tags.update({
        "NSW":    "0",
        "IBRION": "-1",
        "ISIF":   "2",
        "ICHARG": "11",
        "NEDOS":  "1500",
        "EMIN":   "-30",
        "EMAX":   "10",
    })
    if tetrahedron:
        tags["ISMEAR"] = "-5"
    if ldau:
        add_ldau(tags, info)
    if soc:
        add_soc(tags)
    return tags
