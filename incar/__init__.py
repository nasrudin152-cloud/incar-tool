"""
incar/ — VASP INCAR generation package.

Each calc type lives in its own module; all are re-exported here.
"""
from .defaults import (
    common_base, add_ldau, add_soc, apply_task_defaults,
    MAGNETIC_ELEMENTS, HEAVY_ELEMENTS, LDAU_U,
)
from .poscar import parse_poscar, gen_optcell_fix_z
from .formatter import format_incar
from .interactive import interactive_mode

from .relax      import build_relax
from .scf        import build_scf
from .band       import build_band
from .dos        import build_dos
from .md         import build_md
from .hse        import build_hse
from .dielectric import build_dielectric
from .phonon     import build_phonon
from .neb        import build_neb
from .soc        import build_soc
from .zpe        import build_zpe

CALC_BUILDERS: dict = {
    "relax":      lambda info, spin, ldau, soc: apply_task_defaults(build_relax(info, spin, ldau, soc), "relax"),
    "scf":        lambda info, spin, ldau, soc: apply_task_defaults(build_scf(info, spin, ldau, soc), "scf"),
    "band":       lambda info, spin, ldau, soc: apply_task_defaults(build_band(info, spin, ldau, soc), "band"),
    "dos":        lambda info, spin, ldau, soc: apply_task_defaults(build_dos(info, spin, ldau, soc), "dos"),
    "hse":        lambda info, spin, ldau, soc: apply_task_defaults(build_hse(info, spin, calc="scf",   ldau=ldau), "hse"),
    "hse-relax":  lambda info, spin, ldau, soc: apply_task_defaults(build_hse(info, spin, calc="relax", ldau=ldau), "hse-relax"),
    "dielectric": lambda info, spin, ldau, soc: apply_task_defaults(build_dielectric(info, spin), "dielectric"),
    "phonon":     lambda info, spin, ldau, soc: apply_task_defaults(build_phonon(info, spin), "phonon"),
    "md":         lambda info, spin, ldau, soc: apply_task_defaults(build_md(info, spin), "md"),
    "neb":        lambda info, spin, ldau, soc: apply_task_defaults(build_neb(info, spin, ldau=ldau), "neb"),
    "soc":        lambda info, spin, ldau, soc: apply_task_defaults(build_soc(info), "soc"),
    "zpe":        lambda info, spin, ldau, soc: apply_task_defaults(build_zpe(info, spin, ldau=ldau), "zpe"),
}

__all__ = [
    "common_base", "add_ldau", "add_soc", "apply_task_defaults",
    "MAGNETIC_ELEMENTS", "HEAVY_ELEMENTS", "LDAU_U",
    "parse_poscar", "gen_optcell_fix_z", "format_incar", "interactive_mode",
    "build_relax", "build_scf", "build_band", "build_dos", "build_md",
    "build_hse", "build_dielectric", "build_phonon", "build_neb", "build_soc", "build_zpe",
    "CALC_BUILDERS",
]
