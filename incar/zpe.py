"""build_zpe() — ZPE correction via finite differences (IBRION=5)."""
from __future__ import annotations

from .defaults import common_base


def build_zpe(info: dict, spin: bool, nfree: int = 2) -> dict:
    tags = common_base(info, spin, ediff="1E-6")
    tags.update({
        "NSW":     "1",
        "IBRION":  "5",
        "ISIF":    "2",
        "POTIM":   "0.015",
        "NFREE":   str(nfree),
        "LWAVE":   ".FALSE.",
        "LCHARG":  ".FALSE.",
    })
    return tags
