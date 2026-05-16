#!/usr/bin/env python3
"""
51 — Quick VASP Status

Checks convergence text in OUTCAR and prints final TOTEN / E0.
Can be called standalone or imported by the shell menu.
"""

import os
import re


def vasp_tool_status(outcar="OUTCAR", oszicar="OSZICAR"):
    """Print convergence status and final energies from OUTCAR / OSZICAR."""
    found_any = False

    if os.path.isfile(outcar):
        found_any = True
        converged = False
        toten = None
        with open(outcar) as f:
            for line in f:
                if "reached required accuracy" in line:
                    converged = True
                # TOTEN line: "  free  energy   TOTEN  =   -123.456 eV"
                m = re.search(r"free\s+energy\s+TOTEN\s*=\s*([-\d.eE+]+)", line)
                if m:
                    toten = m.group(1)

        status = "YES" if converged else "NOT FOUND"
        print(f"  Electronic convergence : {status}")
        if toten:
            print(f"  Final TOTEN (OUTCAR)   : {toten} eV")

    if os.path.isfile(oszicar):
        found_any = True
        e0 = None
        last_line = None
        with open(oszicar) as f:
            for line in f:
                last_line = line.rstrip()
                # E0= value may be directly adjacent: "E0= -123.456"
                m = re.search(r"E0=\s*([-\d.eE+]+)", line)
                if m:
                    e0 = m.group(1)
        if e0:
            print(f"  Final E0   (OSZICAR)   : {e0} eV")
        if last_line:
            print(f"  Last OSZICAR line      : {last_line}")

    if not found_any:
        print("  [ERROR] OUTCAR / OSZICAR not found in current directory.")


if __name__ == "__main__":
    vasp_tool_status()
