"""POSCAR parser — returns structure metadata used by all INCAR builders."""
from __future__ import annotations

import sys
from pathlib import Path

from .defaults import MAGNETIC_ELEMENTS, HEAVY_ELEMENTS, LDAU_U


def parse_poscar(poscar_path: str) -> dict:
    """Parse a VASP POSCAR/CONTCAR and return structure metadata."""
    path = Path(poscar_path)
    if not path.exists():
        sys.exit(f"[ERROR] POSCAR not found: {poscar_path}")

    with open(path) as f:
        lines = f.readlines()

    info: dict = {
        "title":              lines[0].strip(),
        "elements":           [],
        "counts":             [],
        "natoms":             0,
        "selective_dynamics": False,
        "is_magnetic":        False,
        "has_heavy":          False,
        "magmom_str":         "",
        "ldau_elements":      [],
    }

    # Lattice vectors
    lattice = [[float(x) for x in lines[i].split()] for i in range(2, 5)]
    info["lattice"] = lattice

    # Element / count lines (VASP5 vs VASP4)
    elem_line = lines[5].split()
    if elem_line[0].isalpha():
        info["elements"] = elem_line
        info["counts"]   = [int(c) for c in lines[6].split()]
        coord_start = 7
    else:
        info["elements"] = [f"X{i}" for i in range(len(elem_line))]
        info["counts"]   = [int(c) for c in elem_line]
        coord_start = 6

    info["natoms"] = sum(info["counts"])

    if lines[coord_start].strip()[0].upper() == "S":
        info["selective_dynamics"] = True
        coord_start += 1

    # Derived flags
    magmom_parts: list[str] = []
    ldau_elems:   list[str] = []
    has_heavy = False
    is_magnetic = False

    for elem, cnt in zip(info["elements"], info["counts"]):
        if elem in MAGNETIC_ELEMENTS:
            magmom_parts.append(f"{cnt}*{MAGNETIC_ELEMENTS[elem]}")
            is_magnetic = True
        else:
            magmom_parts.append(f"{cnt}*0")
        if elem in HEAVY_ELEMENTS:
            has_heavy = True
        if elem in LDAU_U:
            ldau_elems.append(elem)

    info["magmom_str"]    = "  ".join(magmom_parts)
    info["is_magnetic"]   = is_magnetic
    info["has_heavy"]     = has_heavy
    info["ldau_elements"] = ldau_elems

    return info


def gen_optcell_fix_z(lattice: list[list[float]], tol: float = 1e-3) -> str:
    """
    Generate OPTCELL content for a fix-Z slab/2D relaxation.

    Algorithm
    ---------
    * The lattice vector with the largest |z| component is treated as the
      out-of-plane vector and fully fixed (row = 0 0 0).
    * Each in-plane vector is allowed to relax only along Cartesian directions
      where it already has a non-trivial component (|val| > tol), but its z
      component is always fixed (column 2 = 0).

    Examples
    --------
    Orthogonal  a=(5,0,0)  b=(0,5,0)  c=(0,0,15):
        1 0 0
        0 1 0
        0 0 0

    Hexagonal   a=(3,0,0)  b=(-1.5,2.6,0)  c=(0,0,20):
        1 0 0
        1 1 0
        0 0 0
    """
    z_mags = [abs(v[2]) for v in lattice]
    oop_idx = z_mags.index(max(z_mags))

    rows: list[list[int]] = []
    for i, vec in enumerate(lattice):
        if i == oop_idx:
            rows.append([0, 0, 0])
        else:
            rows.append([
                1 if abs(vec[0]) > tol else 0,
                1 if abs(vec[1]) > tol else 0,
                0,
            ])

    return "\n".join(" " + " ".join(str(v) for v in row) for row in rows) + "\n"
