#!/usr/bin/env python3.11
"""potcar_gen.py — CLI entry point for VASP POTCAR generation.

Usage:
    python3 potcar_gen.py                    # interactive (default POSCAR in cwd)
    python3 potcar_gen.py -p path/POSCAR     # specify POSCAR
    python3 potcar_gen.py -p POSCAR -o /path/POTCAR
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from potcar import potgen_mode


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="potcar_gen.py",
        description="Generate POTCAR from POSCAR using MP-recommended PAW-PBE pseudopotentials.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 potcar_gen.py                    (interactive, reads ./POSCAR)
  python3 potcar_gen.py -p path/to/POSCAR
  python3 potcar_gen.py -p POSCAR -o POTCAR
""",
    )
    p.add_argument("-p", "--poscar", default="POSCAR", metavar="POSCAR",
                   help="Path to POSCAR  (default: ./POSCAR)")
    p.add_argument("-o", "--output", default="POTCAR", metavar="POTCAR",
                   help="Output POTCAR path  (default: ./POTCAR)")
    return p


def main() -> None:
    args = build_parser().parse_args()
    potgen_mode(args.poscar, args.output)


if __name__ == "__main__":
    main()
