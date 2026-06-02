#!/usr/bin/env python3
"""
INCAR Generator for VASP calculations.
Usage:  python incar_gen.py -p POSCAR -t relax [options]
        python incar_gen.py -i                    (interactive TUI)
"""

import argparse
import sys
from pathlib import Path

from incar import (
    parse_poscar, format_incar, interactive_mode,
    build_relax, build_scf, build_band, build_dos, build_md,
    build_hse, build_dielectric, build_phonon, build_neb, build_soc, build_zpe,
    CALC_BUILDERS, apply_task_defaults,
)
from kpoints import kgen_mode


# ─── CLI ───────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Generate VASP INCAR from POSCAR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Calculation types (-t):
  relax       Structural relaxation (IBRION=2, ISIF=2)
  scf         Static single-point (saves WAVECAR+CHGCAR)
  band        Band structure (reads CHGCAR, ICHARG=11)
  dos         Density of states (ISMEAR=-5)
  md          Ab initio molecular dynamics (NVT)
  hse         HSE06 hybrid functional static
  hse-relax   HSE06 hybrid functional relaxation
  dielectric  Dielectric function (DFPT, IBRION=8)
  phonon      Phonon force constants (DFPT)
  neb         Nudged Elastic Band (transition state)
  soc         Spin-orbit coupling band structure

Examples:
  python incar_gen.py -p POSCAR -t relax
  python incar_gen.py -p POSCAR -t scf --spin --ldau
  python incar_gen.py -p POSCAR -t md --tebeg 300 --teend 1000 --nsw 10000
  python incar_gen.py -p POSCAR -t neb --images 7
  python incar_gen.py -p POSCAR -t band --soc
  python incar_gen.py -i                       (interactive mode)
  python incar_gen.py -k                       (append KSPACING to INCAR)
  python incar_gen.py -k path/to/INCAR         (specify INCAR path)
        """,
    )
    p.add_argument("-p", "--poscar", default="POSCAR",
                   help="Path to POSCAR file (default: POSCAR)")
    p.add_argument("-t", "--type", required=False, default=None,
                   choices=list(CALC_BUILDERS.keys()),
                   dest="calc_type",
                   help="Calculation type (required unless -i/--interactive)")
    p.add_argument("-o", "--output", default="INCAR",
                   help="Output file path (default: INCAR)")

    # Spin / magnetic
    spin_g = p.add_argument_group("Spin options")
    spin_g.add_argument("--spin", action="store_true",
                        help="Enable spin-polarized (auto-enabled if magnetic elements detected)")
    spin_g.add_argument("--no-spin", action="store_true",
                        help="Force non-spin-polarized regardless of elements")

    # LDA+U
    p.add_argument("--ldau", action="store_true",
                   help="Enable LDA+U for detected d/f-element candidates")
    p.add_argument("--no-ldau", action="store_true",
                   help="Disable LDA+U")

    # SOC
    p.add_argument("--soc", action="store_true",
                   help="Enable spin-orbit coupling (auto for heavy elements in soc/band)")

    # MD options
    md_g = p.add_argument_group("MD options")
    md_g.add_argument("--ensemble", choices=["nvt", "nve", "npt"], default="nvt",
                      help="MD ensemble: nvt, nve, or npt")
    md_g.add_argument("--tebeg", type=int, default=300, help="Start temperature (K)")
    md_g.add_argument("--teend", type=int, default=300, help="End temperature (K)")
    md_g.add_argument("--nsw", type=int, default=5000, help="MD steps")
    md_g.add_argument("--potim", type=float, default=2.0, help="Time step (fs)")
    md_g.add_argument("--langevin-gamma", type=float, default=10.0,
                      help="NPT Langevin friction for each species")
    md_g.add_argument("--langevin-gamma-l", type=float, default=1.0,
                      help="NPT Langevin friction for lattice degrees")
    md_g.add_argument("--pmass", type=float, default=1000.0,
                      help="NPT fictitious lattice mass")
    md_g.add_argument("--pstress", type=float, default=0.0,
                      help="NPT external pressure in kB")

    # NEB options
    p.add_argument("--images", type=int, default=5, help="Number of NEB images")

    # Relax options
    p.add_argument("--isif", type=int, choices=[2, 3, 4, 7], default=2,
                   help="Relaxation mode for -t relax (default: 2; use 3 for full cell relaxation)")

    # ENCUT override
    p.add_argument("--encut", type=int, help="Override ENCUT (eV)")

    # KPOINTS hint
    p.add_argument("--metal", action="store_true",
                   help="Use metallic smearing (ISMEAR=0, SIGMA=0.2)")

    p.add_argument("--preview", action="store_true",
                   help="Print INCAR to stdout instead of writing file")

    p.add_argument("-i", "--interactive", action="store_true",
                   help="Launch step-by-step interactive mode (requires questionary + rich)")

    p.add_argument("-k", "--kgen", nargs="?", const="INCAR", metavar="INCAR",
                   help="Append KSPACING/KGAMMA to an INCAR file (default: ./INCAR)")

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.interactive:
        interactive_mode()
        return

    if args.kgen is not None:
        kgen_mode(args.kgen)
        return

    if args.calc_type is None:
        parser.error("argument -t/--type is required (or use -i/--interactive)")

    print(f"[INFO] Parsing POSCAR: {args.poscar}")
    info = parse_poscar(args.poscar)

    print(f"[INFO] System : {info['title']}")
    print(f"[INFO] Elements: {' '.join(f'{e}({n})' for e, n in zip(info['elements'], info['counts']))}")
    print(f"[INFO] Natoms  : {info['natoms']}")
    print(f"[INFO] Magnetic elements detected: {info['is_magnetic']}")
    print(f"[INFO] Heavy elements detected   : {info['has_heavy']}")
    if info["ldau_elements"]:
        print(f"[INFO] LDA+U candidates: {', '.join(info['ldau_elements'])}")

    # Determine spin
    if args.no_spin:
        spin = False
    elif args.spin or info["is_magnetic"]:
        spin = True
    else:
        spin = False

    # Determine LDA+U
    if args.no_ldau:
        ldau = False
    elif args.ldau:
        ldau = True
    else:
        ldau = False

    # Determine SOC
    soc = args.soc or (args.calc_type == "soc") or \
          (info["has_heavy"] and args.calc_type in ("band", "soc"))

    print(f"[INFO] Spin-polarized: {spin} | LDA+U: {ldau} | SOC: {soc}")

    # Build INCAR tags
    ct = args.calc_type
    if ct == "relax":
        tags = build_relax(info, spin, ldau, soc, isif=args.isif)
    elif ct == "scf":
        tags = build_scf(info, spin, ldau, soc)
    elif ct == "band":
        tags = build_band(info, spin, ldau, soc)
    elif ct == "dos":
        tags = build_dos(info, spin, ldau, soc)
    elif ct == "md":
        tags = build_md(info, spin,
                        tebeg=args.tebeg,
                        teend=args.teend,
                        nsw=args.nsw,
                        potim=args.potim,
                        ensemble=args.ensemble,
                        langevin_gamma=args.langevin_gamma,
                        langevin_gamma_l=args.langevin_gamma_l,
                        pmass=args.pmass,
                        pstress=args.pstress)
    elif ct in ("hse", "hse-relax"):
        tags = build_hse(info, spin, calc="relax" if ct == "hse-relax" else "scf",
                         ldau=ldau)
    elif ct == "dielectric":
        tags = build_dielectric(info, spin)
    elif ct == "phonon":
        tags = build_phonon(info, spin)
    elif ct == "neb":
        tags = build_neb(info, spin, args.images, ldau=ldau)
    elif ct == "soc":
        tags = build_soc(info)
    elif ct == "zpe":
        tags = build_zpe(info, spin, ldau=ldau)

    # Post-processing overrides
    if args.encut:
        tags["ENCUT"] = str(args.encut)
    if args.metal:
        tags["ISMEAR"] = "0"
        tags["SIGMA"] = "0.2"
    apply_task_defaults(tags, ct)

    incar_text = format_incar(tags, ct)

    if args.preview:
        print("\n" + "=" * 60)
        print(incar_text)
    else:
        out = Path(args.output)
        out.write_text(incar_text)
        print(f"[INFO] INCAR written to: {out.resolve()}")


if __name__ == "__main__":
    main()
