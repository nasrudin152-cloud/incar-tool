#!/usr/bin/env python3
"""
53 — Backup Key VASP Files

Copies common VASP input/output files into a timestamped folder.
Can be called standalone or imported by the shell menu.
"""

import os
import shutil
from datetime import datetime

BACKUP_FILES = [
    "INCAR", "POSCAR", "CONTCAR", "KPOINTS", "POTCAR",
    "OUTCAR", "OSZICAR", "XDATCAR", "vasprun.xml",
    "CHGCAR", "WAVECAR", "DOSCAR", "EIGENVAL", "PROCAR",
    "vasp.pbs",
]


def vasp_tool_backup_results(dest_dir=None):
    """Copy key VASP files into a timestamped backup directory."""
    if dest_dir is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_dir = f"vasp_backup_{ts}"

    os.makedirs(dest_dir, exist_ok=True)
    copied = 0
    for fname in BACKUP_FILES:
        if os.path.exists(fname):
            shutil.copy2(fname, dest_dir)
            copied += 1

    print(f"  [OK] Backup folder : {dest_dir}")
    print(f"  Copied items       : {copied}")


if __name__ == "__main__":
    vasp_tool_backup_results()
