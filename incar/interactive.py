"""
Interactive TUI for the INCAR generator.
Requires:  pip install questionary rich

Back navigation: every Yes/No prompt has a "← Back" choice;
every text prompt accepts the literal input "b" to go back.
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import questionary
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich import box as rich_box
    _RICH_OK = True
except ImportError:
    _RICH_OK = False

from .poscar import parse_poscar, gen_optcell_fix_z
from .formatter import format_incar
from .relax import build_relax
from .scf import build_scf
from .band import build_band
from .dos import build_dos
from .md import build_md
from .hse import build_hse
from .dielectric import build_dielectric
from .phonon import build_phonon
from .neb import build_neb
from .soc import build_soc
from .zpe import build_zpe

# ── Constants ─────────────────────────────────────────────────────────────────

_BACK = "__back__"

CALC_DESCRIPTIONS: dict[str, str] = {
    "relax":      "Structural relaxation  (IBRION=2)",
    "scf":        "Static single-point SCF",
    "band":       "Band structure          (ICHARG=11)",
    "dos":        "Density of states       (ISMEAR=-5)",
    "md":         "Ab initio MD            (NVT/NVE/NPT)",
    "hse":        "HSE06 hybrid static",
    "hse-relax":  "HSE06 hybrid relaxation",
    "dielectric": "Dielectric function     (DFPT)",
    "phonon":     "Phonon force constants  (DFPT)",
    "neb":        "Nudged Elastic Band     (transition state)",
    "soc":        "Spin-orbit coupling band structure",
    "zpe":        "ZPE correction          (IBRION=5, finite diff)",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ask(prompt_fn, *args, **kwargs):
    """Run a questionary prompt; exit cleanly on Ctrl-C / EOF."""
    result = prompt_fn(*args, **kwargs).ask()
    if result is None:
        sys.exit(0)
    return result


def _yn_back(question: str, default: bool = False):
    """
    Yes / No / ← Back selection.
    Returns True, False, or _BACK.
    The default choice (pre-highlighted cursor) follows the `default` argument.
    """
    yes  = questionary.Choice("Yes",    value=True)
    no   = questionary.Choice("No",     value=False)
    back = questionary.Choice("← Back", value=_BACK)
    r = questionary.select(
        question,
        choices=[yes, no, back],
        default=yes if default else no,
    ).ask()
    if r is None:
        sys.exit(0)
    return r


def _text_back(question: str, default: str = "") -> str:
    """
    Text input with back support.
    Returns the entered string, or _BACK if the user types 'b'.
    """
    r = questionary.text(f"{question}  [b = back]", default=default).ask()
    if r is None:
        sys.exit(0)
    return _BACK if r.strip().lower() == "b" else r


def _int_or(s: str, default: int) -> int:
    return int(s) if s.strip().lstrip("-").isdigit() else default


def _float_or(s: str, default: float) -> float:
    try:
        return float(s)
    except ValueError:
        return default


# ── Step-based parameter wizard ───────────────────────────────────────────────

def _wizard(info: dict, calc_type: str, console) -> tuple | str:
    """
    Collect spin / LDA+U / SOC / smearing / ENCUT / type-specific parameters
    with full back navigation at every step.

    Returns (tags, fix_z, encut_override, metal) on success,
    or _BACK to signal that the caller should re-show the calc_type menu.
    """
    # ── Which steps are required for this calc_type ───────────────────────────
    # spin is prompted unless it is forced (soc → True, phonon/dielectric → auto)
    if calc_type == "soc":
        fixed_spin: bool | None = True
    elif calc_type in ("dielectric", "phonon", "zpe"):
        fixed_spin = info["is_magnetic"]
    else:
        fixed_spin = None  # will be prompted

    need_ldau  = calc_type not in ("md", "phonon", "dielectric", "zpe")
    need_soc   = calc_type in ("band", "scf", "relax", "soc")
    need_smear = calc_type not in ("dos", "md", "phonon", "dielectric", "zpe")

    # Build ordered step list (names only; execution is driven by index)
    step_names: list[str] = []
    if fixed_spin is None:
        step_names.append("spin")
    if need_ldau:
        step_names.append("ldau")
    if need_soc:
        step_names.append("soc")
    if need_smear:
        step_names.append("smear")
    elif calc_type == "dos":
        step_names.append("dos_ismear")  # DOS-specific smearing choice
    step_names.append("encut")
    if calc_type == "relax":
        step_names += ["nsw", "isif"]          # fix_z inserted dynamically after isif
    elif calc_type == "md":
        step_names += [
            "md_ensemble", "tebeg", "teend", "md_nsw", "potim",
            "langevin_gamma", "langevin_gamma_l", "pmass", "pstress",
        ]
    elif calc_type == "neb":
        step_names.append("images")
    elif calc_type == "soc":
        step_names.append("soc_saxis")  # spin quantization axis

    results: dict = {}  # step_name → collected value
    idx = 0

    while idx < len(step_names):
        name = step_names[idx]

        # ── spin ──────────────────────────────────────────────────────────────
        if name == "spin":
            r = _yn_back("Enable spin-polarized calculation? (ISPIN=2)",
                         default=False)
            if r == _BACK:
                if idx == 0:
                    return _BACK           # propagate back to calc_type menu
                idx -= 1; continue
            results["spin"] = r

        # ── LDA+U ─────────────────────────────────────────────────────────────
        elif name == "ldau":
            if info["ldau_elements"]:
                q = f"Enable LDA+U for {', '.join(info['ldau_elements'])}?"
            else:
                q = "Enable LDA+U?  (no d/f elements detected)"
            r = _yn_back(q, default=False)
            if r == _BACK:
                idx -= 1; continue
            results["ldau"] = r

        # ── SOC ───────────────────────────────────────────────────────────────
        elif name == "soc":
            r = _yn_back("Enable spin-orbit coupling? (LSORBIT=.TRUE.)",
                         default=False)
            if r == _BACK:
                idx -= 1; continue
            results["soc"] = r

        # ── Metallic smearing ─────────────────────────────────────────────────
        elif name == "smear":
            r = _yn_back(
                "Metallic smearing?  "
                "(no → ISMEAR=0, SIGMA=0.05  |  yes → ISMEAR=0，SIGMA=0.2)",
                default=False,
            )
            if r == _BACK:
                idx -= 1; continue
            results["smear"] = r

        # ── ENCUT ─────────────────────────────────────────────────────────────
        elif name == "encut":
            r = _text_back("ENCUT (eV):", default="450")
            if r == _BACK:
                idx -= 1; continue
            results["encut"] = r

        # ── NSW (relax) ───────────────────────────────────────────────────────
        elif name == "nsw":
            r = _text_back("Max ionic steps NSW:", default="300")
            if r == _BACK:
                idx -= 1; continue
            results["nsw"] = r

        # ── ISIF ──────────────────────────────────────────────────────────────
        elif name == "isif":
            isif_choices = [
                questionary.Choice("2  – ions only          (fixed cell)",            value="2"),
                questionary.Choice("3  – full relaxation    (ions + shape + volume)", value="3"),
                questionary.Choice("4  – ions + shape       (fixed volume)",          value="4"),
                questionary.Choice("7  – volume only        (fixed shape, no ions)",  value="7"),
                questionary.Choice("← Back", value=_BACK),
            ]
            r = questionary.select("Select ISIF (cell relaxation mode):",
                                   choices=isif_choices).ask()
            if r is None:
                sys.exit(0)
            if r == _BACK:
                idx -= 1; continue
            results["isif"] = int(r)
            # Dynamically insert fix_z step when ISIF=3
            if r == "3" and "fix_z" not in step_names:
                step_names.insert(idx + 1, "fix_z")

        # ── Fix Z (inserted when ISIF=3) ──────────────────────────────────────
        elif name == "fix_z":
            r = _yn_back("Fix Z-axis? (writes OPTCELL — useful for 2D/slab)",
                         default=False)
            if r == _BACK:
                idx -= 1; continue
            results["fix_z"] = r

        # ── MD params ─────────────────────────────────────────────────────────
        elif name == "md_ensemble":
            md_choices = [
                questionary.Choice("NVT  – Nosé-Hoover thermostat", value="nvt"),
                questionary.Choice("NVE  – microcanonical ensemble", value="nve"),
                questionary.Choice("NPT  – Langevin thermostat + cell dynamics", value="npt"),
                questionary.Choice("← Back", value=_BACK),
            ]
            r = questionary.select("Select MD ensemble:", choices=md_choices).ask()
            if r is None:
                sys.exit(0)
            if r == _BACK:
                idx -= 1; continue
            results["md_ensemble"] = r

        elif name == "tebeg":
            r = _text_back("Start temperature TEBEG (K):", default="300")
            if r == _BACK:
                idx -= 1; continue
            results["tebeg"] = r

        elif name == "teend":
            r = _text_back("End temperature TEEND (K):", default="300")
            if r == _BACK:
                idx -= 1; continue
            results["teend"] = r

        elif name == "md_nsw":
            r = _text_back("MD steps NSW:", default="5000")
            if r == _BACK:
                idx -= 1; continue
            results["md_nsw"] = r

        elif name == "potim":
            r = _text_back("Time step POTIM (fs):", default="2.0")
            if r == _BACK:
                idx -= 1; continue
            results["potim"] = r

        elif name == "langevin_gamma":
            if results.get("md_ensemble") != "npt":
                idx += 1; continue
            r = _text_back("LANGEVIN_GAMMA for each species:", default="10.0")
            if r == _BACK:
                idx -= 1; continue
            results["langevin_gamma"] = r

        elif name == "langevin_gamma_l":
            if results.get("md_ensemble") != "npt":
                idx += 1; continue
            r = _text_back("LANGEVIN_GAMMA_L:", default="1.0")
            if r == _BACK:
                idx -= 1; continue
            results["langevin_gamma_l"] = r

        elif name == "pmass":
            if results.get("md_ensemble") != "npt":
                idx += 1; continue
            r = _text_back("PMASS:", default="1000.0")
            if r == _BACK:
                idx -= 1; continue
            results["pmass"] = r

        elif name == "pstress":
            if results.get("md_ensemble") != "npt":
                idx += 1; continue
            r = _text_back("PSTRESS (kB):", default="0.0")
            if r == _BACK:
                idx -= 1; continue
            results["pstress"] = r
        # ── NEB images ────────────────────────────────────────────────────────
        elif name == "images":
            r = _text_back("Number of NEB images:", default="5")
            if r == _BACK:
                idx -= 1; continue
            results["images"] = r

        # ── DOS smearing (replaces generic smear for dos) ─────────────────────
        elif name == "dos_ismear":
            dos_choices = [
                questionary.Choice(
                    "Gaussian  (ISMEAR=0) — safe for all systems incl. metals",
                    value=False,
                ),
                questionary.Choice(
                    "Tetrahedron (ISMEAR=-5) — accurate for insulators/semiconductors;"
                    " requires uniform dense k-mesh (≥ 4×4×4)",
                    value=True,
                ),
                questionary.Choice("← Back", value=_BACK),
            ]
            r = questionary.select("DOS smearing method:", choices=dos_choices).ask()
            if r is None:
                sys.exit(0)
            if r == _BACK:
                idx -= 1; continue
            results["dos_ismear"] = r

        # ── SOC spin-quantization axis ────────────────────────────────────────
        elif name == "soc_saxis":
            r = _text_back(
                "Spin quantization axis SAXIS  (e.g. 0 0 1 for z, 1 0 0 for x):",
                default="0 0 1",
            )
            if r == _BACK:
                idx -= 1; continue
            results["soc_saxis"] = r

        idx += 1

    # ── Resolve collected values ──────────────────────────────────────────────
    spin  = results.get("spin",  fixed_spin if fixed_spin is not None else info["is_magnetic"])
    ldau  = results.get("ldau",  False)
    soc   = results.get("soc",   False)
    metal = results.get("smear", False)
    fix_z = results.get("fix_z", False)

    encut_str = results.get("encut", "450")
    encut_override = int(encut_str) if encut_str.strip().isdigit() and encut_str != "450" else None

    # ── Build tags ────────────────────────────────────────────────────────────
    if calc_type == "relax":
        tags = build_relax(info, spin, ldau, soc,
                           nsw=_int_or(results.get("nsw", "300"), 300),
                           isif=results.get("isif", 3))
    elif calc_type == "scf":
        tags = build_scf(info, spin, ldau, soc)
    elif calc_type == "band":
        tags = build_band(info, spin, ldau, soc)
    elif calc_type == "dos":
        tags = build_dos(info, spin, ldau, soc,
                         tetrahedron=results.get("dos_ismear", False))
    elif calc_type == "md":
        tags = build_md(info, spin,
                        tebeg=_int_or(results.get("tebeg", "300"),  300),
                        teend=_int_or(results.get("teend", "300"),  300),
                        nsw=  _int_or(results.get("md_nsw", "5000"), 5000),
                        potim=_float_or(results.get("potim", "2.0"), 2.0),
                        ensemble=results.get("md_ensemble", "nvt"),
                        langevin_gamma=_float_or(results.get("langevin_gamma", "10.0"), 10.0),
                        langevin_gamma_l=_float_or(results.get("langevin_gamma_l", "1.0"), 1.0),
                        pmass=_float_or(results.get("pmass", "1000.0"), 1000.0),
                        pstress=_float_or(results.get("pstress", "0.0"), 0.0))
    elif calc_type in ("hse", "hse-relax"):
        tags = build_hse(info, spin,
                         calc="relax" if calc_type == "hse-relax" else "scf",
                         ldau=ldau)
    elif calc_type == "dielectric":
        tags = build_dielectric(info, spin)
    elif calc_type == "phonon":
        tags = build_phonon(info, spin)
    elif calc_type == "neb":
        tags = build_neb(info, spin,
                         images=_int_or(results.get("images", "5"), 5),
                         ldau=ldau)
    elif calc_type == "soc":
        tags = build_soc(info, saxis=results.get("soc_saxis", "0 0 1"))
    elif calc_type == "zpe":
        tags = build_zpe(info, spin)
    else:
        tags = {}

    return tags, fix_z, encut_override, metal


# ── Main entry point ──────────────────────────────────────────────────────────

def interactive_mode() -> None:
    if not _RICH_OK:
        print("[ERROR] Interactive mode requires 'questionary' and 'rich'.")
        print("  Install: pip install questionary rich")
        sys.exit(1)

    console = Console()
    console.print()
    console.print(Panel.fit(
        "[bold cyan]VASP INCAR Generator[/bold cyan]  [dim]─  Interactive Mode[/dim]",
        border_style="cyan",
        padding=(0, 2),
    ))
    console.print()

    # ── Outer loop: POSCAR → calc_type → wizard (any step can go back) ────────
    while True:
        # ── POSCAR ────────────────────────────────────────────────────────────
        poscar_path = _ask(
            questionary.path, "Path to POSCAR file:", default="POSCAR",
            validate=lambda p: Path(p).exists() or f"File not found: {p}",
        )
        info = parse_poscar(poscar_path)

        # ── Structure summary ─────────────────────────────────────────────────
        tbl = Table(title="Structure Info", box=rich_box.ROUNDED,
                    border_style="blue", show_header=False)
        tbl.add_column(style="bold dim")
        tbl.add_column()
        tbl.add_row("Title", info["title"])
        tbl.add_row("Elements",
                    "  ".join(f"{e} ×{n}"
                              for e, n in zip(info["elements"], info["counts"])))
        tbl.add_row("Total atoms", str(info["natoms"]))
        tbl.add_row("Magnetic elements",
                    "[green]✓ YES[/green]" if info["is_magnetic"] else "[dim]no[/dim]")
        tbl.add_row("Heavy elements (SOC)",
                    "[yellow]✓ YES[/yellow]" if info["has_heavy"] else "[dim]no[/dim]")
        if info["ldau_elements"]:
            tbl.add_row("LDA+U candidates",
                        "[magenta]" + ", ".join(info["ldau_elements"]) + "[/magenta]")
        console.print(tbl)
        console.print()

        # ── Calc type (← Back re-asks POSCAR) ────────────────────────────────
        calc_choices = [
            questionary.Choice("← Back  (re-enter POSCAR path)", value=_BACK),
        ] + [
            questionary.Choice(f"{k:<12} {v}", value=k)
            for k, v in CALC_DESCRIPTIONS.items()
        ]
        calc_type = _ask(questionary.select,
                         "Select calculation type:", choices=calc_choices)
        if calc_type == _BACK:
            console.print()
            continue

        console.print(
            f"  [bold green]✓[/bold green] Calculation: [cyan]{calc_type}[/cyan]\n"
        )

        # ── Parameter wizard (first step's ← Back returns here) ──────────────
        result = _wizard(info, calc_type, console)
        if result == _BACK:
            console.print()
            continue  # back to POSCAR entry

        tags, fix_z, encut_override, metal = result
        if encut_override:
            tags["ENCUT"] = str(encut_override)
        if metal:
            tags["ISMEAR"] = "0"
            tags["SIGMA"]  = "0.2"

        incar_text = format_incar(tags, calc_type)

        # ── Preview ───────────────────────────────────────────────────────────
        console.print()
        console.print(Panel(
            Syntax(incar_text, "ini", theme="monokai", word_wrap=True),
            title="[bold white]INCAR Preview[/bold white]",
            border_style="green",
            padding=(1, 2),
        ))
        console.print()

        # ── Write ─────────────────────────────────────────────────────────────
        out_path = _ask(questionary.text, "Output file path:", default="INCAR")
        confirm  = _ask(questionary.confirm,
                        f"Write INCAR to '{out_path}'?", default=True)

        if confirm:
            Path(out_path).write_text(incar_text)
            console.print(
                f"\n  [bold green]✓[/bold green] INCAR written to: "
                f"[cyan]{Path(out_path).resolve()}[/cyan]"
            )
            if fix_z:
                optcell_path = Path(out_path).parent / "OPTCELL"
                optcell_path.write_text(gen_optcell_fix_z(info["lattice"]))
                console.print(
                    f"  [bold green]✓[/bold green] OPTCELL written to: "
                    f"[cyan]{optcell_path.resolve()}[/cyan]"
                )
                console.print(
                    "  [dim]  (Z-axis fixed: a·z, b·z, c-vector all constrained)[/dim]"
                )
            console.print()
            break  # done — exit the outer while loop
        else:
            console.print("  [yellow]Cancelled. Returning to output path prompt.[/yellow]\n")
