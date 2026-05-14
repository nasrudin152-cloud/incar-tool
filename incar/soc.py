"""build_soc() — SOC non-self-consistent band structure.

Typical workflow:
  1. Run a collinear SCF to produce CHGCAR + WAVECAR
  2. Run this SOC step with ICHARG=11 reading that CHGCAR

Key tags set here:
  LSORBIT / LNONCOLLINEAR via add_soc()
  ISYM = -1     non-collinear calculations must disable symmetry
  SAXIS         spin quantization axis (default z = 0 0 1)
  NBANDS        doubled (spinor wavefunctions)
"""
from __future__ import annotations

from .defaults import common_base, add_soc


def build_soc(info: dict, saxis: str = "0 0 1") -> dict:
    tags = common_base(info, spin=True, ediff="1E-6")
    add_soc(tags)
    tags.update({
        "NSW":    "0",
        "IBRION": "-1",
        "ICHARG": "11",
        "ISYM":   "-1",
        "SAXIS":  saxis,
        "NBANDS": str(max(int(info["natoms"] * 8), 40)),
    })
    return tags
