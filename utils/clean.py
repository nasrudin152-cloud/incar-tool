#!/usr/bin/env python3
"""
54 — Clean Large VASP Output Files

Removes common large VASP output files from the current directory.
Prompts for confirmation before deleting.
Can be called standalone or imported by the shell menu.
"""

import os
import shutil

OUTPUT_FILES = [
    "CHG", "CHGCAR", "DOSCAR", "EIGENVAL", "ELFCAR", "IBZKPT", "LOCPOT",
    "OSZICAR", "PCDAT", "PROCAR", "REPORT", "vasprun.xml",
    "WAVECAR", "XDATCAR", "AECCAR0", "AECCAR1", "AECCAR2", "BSEFATBAND",
]


def vasp_tool_clean_outputs(confirm=None):
    """Remove common large VASP output files after confirmation.

    Args:
        confirm: Pass 'yes' to skip the interactive prompt (useful for scripting).
    """
    if confirm is None:
        confirm = input("  Type 'yes' to remove large VASP output files: ").strip()

    if confirm != "yes":
        print("  Canceled.")
        return

    removed = 0
    for fname in OUTPUT_FILES:
        if os.path.exists(fname):
            if os.path.isdir(fname):
                shutil.rmtree(fname)
            else:
                os.remove(fname)
            removed += 1

    print(f"  [OK] Removed items : {removed}")


if __name__ == "__main__":
    vasp_tool_clean_outputs()
