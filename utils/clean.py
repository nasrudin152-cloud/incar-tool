#!/usr/bin/env python3
"""
54 — Clean Large VASP Output Files

Lists files that would be removed, lets the user exclude specific ones,
then deletes the rest. Prompts for confirmation before deleting.
Can be called standalone or imported by the shell menu.
"""

import os
import shutil

OUTPUT_FILES = [
    "CHG", "CHGCAR", "DOSCAR", "EIGENVAL", "ELFCAR", "IBZKPT", "LOCPOT",
    "OSZICAR", "OUTCAR", "PCDAT", "PROCAR", "REPORT", "vasprun.xml",
    "WAVECAR", "XDATCAR", "AECCAR0", "AECCAR1", "AECCAR2", "BSEFATBAND",
]


def vasp_tool_clean_outputs(exclude=None):
    """Remove common large VASP output files with optional exclusions.

    Args:
        exclude: Collection of filenames to keep. If None, prompts interactively.
    """
    existing = [f for f in OUTPUT_FILES if os.path.exists(f)]

    if not existing:
        print(f"  Nothing to clean in {os.getcwd()}.")
        return

    print("  [WARN] The following files will be removed:\n")
    for f in existing:
        print(f"    · {f}")
    print()

    if exclude is None:
        raw = input(
            "  To exclude files, enter names separated by spaces.\n"
            "  Press Enter to delete all, or type 'cancel' to abort: "
        ).strip()
        if raw.lower() == "cancel":
            print("  Canceled.")
            return
        exclude = set(raw.split()) if raw else set()
    else:
        exclude = set(exclude)

    removed = skipped = 0
    for f in existing:
        if f in exclude:
            print(f"  skipped : {f}")
            skipped += 1
        else:
            if os.path.isdir(f):
                shutil.rmtree(f)
            else:
                os.remove(f)
            print(f"  removed : {f}")
            removed += 1

    print(f"\n  [OK] Removed: {removed}  |  Skipped: {skipped}")


if __name__ == "__main__":
    vasp_tool_clean_outputs()
