"""
Shared element data, global defaults, and base tag builders.
All INCAR types inherit from common_base().
"""
from __future__ import annotations

# ── Element data ──────────────────────────────────────────────────────────────

MAGNETIC_ELEMENTS: dict[str, float] = {
    "Fe": 4.0, "Co": 3.0, "Ni": 2.0,
    "Mn": 4.0, "Cr": 3.0, "V":  3.0,
    "Cu": 1.0, "Mo": 2.0, "W":  2.0,
    "Gd": 7.0, "Eu": 7.0, "Nd": 3.0,
}

HEAVY_ELEMENTS: set[str] = {
    "Bi", "Pb", "Tl", "Hg", "Au", "Pt", "Ir", "Os", "Re", "W",
    "Ta", "Hf", "La", "Ce", "Pr", "Nd", "Sm", "Eu", "Gd", "Tb",
    "Dy", "Ho", "Er", "Tm", "Yb", "Lu",
}

LDAU_U: dict[str, float] = {
    "Fe": 2.5, "Co": 2.5, "Ni": 2.5, "Mn": 2.5,
    "Cr": 3.5, "V":  3.1, "Cu": 2.5, "Mo": 4.0,
    "W":  4.0, "Ce": 4.5, "Gd": 6.0,
}

LDAU_L: dict[str, int] = {
    "Fe": 2, "Co": 2, "Ni": 2, "Mn": 2,
    "Cr": 2, "V":  2, "Cu": 2, "Mo": 2,
    "W":  2, "Ce": 3, "Gd": 3,
}

NO_DEFAULT_VDW_TYPES: set[str] = {"phonon", "dielectric"}

# ── Global defaults shared by ALL INCAR types ─────────────────────────────────

_BASE: dict[str, str] = {
    "ENCUT":  "450",
    "PREC":   "Normal",
    "EDIFF":  "1E-5",
    "NELM":   "300",
    "NELMIN": "5",
    "ALGO":   "Fast",
    "ISMEAR": "0",
    "SIGMA":  "0.05",
    "LWAVE":  ".FALSE.",
    "LCHARG": ".FALSE.",
    "ISYM":   "0",
    "EDIFFG": "-0.05",
    "LORBIT": "11",
}


# ── Base builder ──────────────────────────────────────────────────────────────

def common_base(info: dict, spin: bool, ediff: str = "1E-5") -> dict:
    """Return tag dict pre-loaded with all global defaults."""
    tags: dict[str, str] = {
        "SYSTEM": info["title"] or "VASP calculation",
        "ISTART": "0",
        "ICHARG": "2",
    }
    tags.update(_BASE)
    if ediff != "1E-5":
        tags["EDIFF"] = ediff
    if spin:
        tags["ISPIN"] = "2"
        tags["MAGMOM"] = info["magmom_str"]
    else:
        tags["ISPIN"] = "1"
    return tags


def apply_task_defaults(tags: dict, calc_type: str) -> dict:
    """Apply defaults that depend on the calculation type."""
    if calc_type not in NO_DEFAULT_VDW_TYPES:
        tags.setdefault("IVDW", "11")
    return tags


# ── Optional add-ons ──────────────────────────────────────────────────────────

def add_ldau(tags: dict, info: dict) -> None:
    """Append LDA+U tags when applicable."""
    if not info["ldau_elements"]:
        return
    u_vals = [str(LDAU_U.get(e, 0.0)) for e in info["elements"]]
    j_vals = ["0.0"] * len(info["elements"])
    l_vals = [str(LDAU_L.get(e, -1)) for e in info["elements"]]
    has_f = any(LDAU_L.get(e) == 3 for e in info["elements"])
    tags.update({
        "LDAU":      ".TRUE.",
        "LDAUTYPE":  "2",
        "LDAUL":     "  ".join(l_vals),
        "LDAUU":     "  ".join(u_vals),
        "LDAUJ":     "  ".join(j_vals),
        "LMAXMIX":   "6" if has_f else "4",
    })


def add_soc(tags: dict) -> None:
    """Append spin-orbit coupling tags."""
    tags.update({
        "LSORBIT":       ".TRUE.",
        "LNONCOLLINEAR": ".TRUE.",
        "ISPIN":         "2",
        "ISYM":          "-1",
        "GGA_COMPAT":    ".FALSE.",
    })
    tags.pop("MAGMOM", None)
