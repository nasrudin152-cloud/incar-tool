"""build_neb() — nudged elastic band transition-state search."""
from __future__ import annotations

from .defaults import common_base


def build_neb(info: dict, spin: bool, images: int = 5) -> dict:
    tags = common_base(info, spin)
    tags.update({
        "IBRION": "3",
        "POTIM":  "0",
        "NSW":    "500",
        "IOPT":   "1",
        "SPRING": "-5",
        "IMAGES": str(images),
        "LCLIMB": ".TRUE.",
    })
    return tags
