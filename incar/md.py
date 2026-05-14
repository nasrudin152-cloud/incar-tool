"""build_md() — ab initio molecular dynamics (NVT/NVE/NPT)."""
from __future__ import annotations

from .defaults import common_base


def build_md(
    info: dict,
    spin: bool,
    tebeg: int = 300,
    teend: int = 300,
    nsw: int = 5000,
    potim: float = 2.0,
    ensemble: str = "nvt",
    langevin_gamma: float = 10.0,
    langevin_gamma_l: float = 1.0,
    pmass: float = 1000.0,
    pstress: float = 0.0,
) -> dict:
    tags = common_base(info, spin)
    tags.update({
        "IBRION": "0",
        "NSW":    str(nsw),
        "POTIM":  str(potim),
        "TEBEG":  str(tebeg),
        "TEEND":  str(teend),
        "ISIF":   "2",
        "LREAL":  "Auto",
        "NBLOCK": "1",
        "KBLOCK": "10",
    })
    ensemble = ensemble.lower()
    if ensemble == "nve":
        tags["SMASS"] = "-3"
    elif ensemble == "npt":
        tags.update({
            "MDALGO":           "3",
            "ISIF":             "3",
            "LANGEVIN_GAMMA":   " ".join([str(langevin_gamma)] * len(info["elements"])),
            "LANGEVIN_GAMMA_L": str(langevin_gamma_l),
            "PMASS":            str(pmass),
            "PSTRESS":          str(pstress),
        })
    else:
        tags.update({
            "MDALGO": "2",
            "SMASS":  "0",
        })
    return tags
