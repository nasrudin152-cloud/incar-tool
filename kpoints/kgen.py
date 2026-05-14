"""kgen — K-point setup for VASP calculations.

Decision table:
  band                 → write line-mode KPOINTS placeholder (edit manually)
  dos  + ISMEAR=-5     → write Monkhorst-Pack KPOINTS  (default 4×4×4)
  hse / hse-relax      → write Monkhorst-Pack KPOINTS  (default 4×4×4)
  everything else      → append KSPACING to INCAR       (default 0.20 Å⁻¹)

The INCAR # job_type comment (written by incar_gen) is read first; if absent,
calc type is detected heuristically from INCAR tags.

Usage (CLI):
    python3 incar_gen.py -k            # reads INCAR in cwd
    python3 incar_gen.py -k path/INCAR

Standalone:
    from kpoints.kgen import kgen_mode
    kgen_mode("INCAR")
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import questionary
    from rich.console import Console
    _RICH_OK = True
except ImportError:
    _RICH_OK = False

# ── Types that need a separate KPOINTS file ───────────────────────────────────
_KPOINTS_FILE_TYPES = {"band", "dos", "hse", "hse-relax"}

# Default KSPACING (Å⁻¹) for types that use INCAR KSPACING
DEFAULT_KSPACING = 0.20


# ── INCAR helpers ─────────────────────────────────────────────────────────────

def _tag(text: str, name: str) -> str:
    """Return the uppercase, space-stripped value of an INCAR tag, or ''."""
    m = re.search(rf"^\s*{name}\s*=\s*(.+)", text, re.IGNORECASE | re.MULTILINE)
    return (m.group(1).strip().upper().replace(" ", "") if m else "")


def detect_job_type(text: str) -> str:
    """Read # job_type = <type> comment; fall back to heuristic detection."""
    m = re.search(r"^#\s*job_type\s*=\s*(\S+)", text, re.IGNORECASE | re.MULTILINE)
    if m:
        return m.group(1).strip().lower()
    return detect_calc_type(text)


def detect_calc_type(text: str) -> str:
    """Heuristically detect calc type from INCAR tags."""
    if _tag(text, "IMAGES"):
        return "neb"
    if ".TRUE." in _tag(text, "LHFCALC"):
        return "hse-relax" if _tag(text, "NSW") not in ("0", "") else "hse"
    if ".TRUE." in _tag(text, "LSORBIT"):
        return "soc"
    if _tag(text, "ICHARG") == "11":
        return "dos" if _tag(text, "NEDOS") else "band"
    if _tag(text, "IBRION") == "0":
        return "md"
    if _tag(text, "IBRION") == "8":
        return "dielectric" if ".TRUE." in _tag(text, "LEPSILON") else "phonon"
    if _tag(text, "NSW") not in ("0", ""):
        return "relax"
    return "scf"


def detect_ismear(text: str) -> str:
    """Return ISMEAR value string from INCAR, or ''."""
    return _tag(text, "ISMEAR")


# ── KPOINTS file builders ─────────────────────────────────────────────────────

def kpoints_mp(nx: int, ny: int, nz: int, comment: str = "Automatic mesh") -> str:
    """Monkhorst-Pack explicit grid (VASP standard format)."""
    return (
        f"{comment}\n"
        "0\n"
        "Monkhorst-Pack\n"
        f"{nx}  {ny}  {nz}\n"
        "0. 0. 0.\n"
    )


def kpoints_band_placeholder(comment: str = "Line-mode KPOINTS — edit k-path for your structure") -> str:
    """Template line-mode KPOINTS. User must replace the k-path."""
    return (
        f"{comment}\n"
        "! Replace this file with the output of VASPKIT (option 303) or seekpath.\n"
        "! Example format for a simple cubic path (Γ–X–M–Γ):\n"
        "40\n"
        "Line-mode\n"
        "Reciprocal\n"
        "  0.000  0.000  0.000   ! Gamma\n"
        "  0.500  0.000  0.000   ! X\n"
        "\n"
        "  0.500  0.000  0.000   ! X\n"
        "  0.500  0.500  0.000   ! M\n"
        "\n"
        "  0.500  0.500  0.000   ! M\n"
        "  0.000  0.000  0.000   ! Gamma\n"
    )


def write_kpoints(kpoints_path: Path, content: str) -> None:
    """Write (or overwrite) a KPOINTS file."""
    kpoints_path.write_text(content)


# ── INCAR KSPACING writer ─────────────────────────────────────────────────────

def append_kspacing(incar_path: Path, kspacing: float) -> None:
    """Add/replace KSPACING tag in INCAR. Removes any old KSPACING/KGAMMA lines."""
    text = incar_path.read_text() if incar_path.exists() else ""
    text = re.sub(r"^\s*(KSPACING|KGAMMA)\s*=.*\n?", "", text,
                  flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text).rstrip()
    text += f"\n\n# --- K-mesh ---\n  KSPACING         = {kspacing:.2f}\n"
    incar_path.write_text(text)


# ── Decision logic ────────────────────────────────────────────────────────────

def _needs_kpoints_file(ct: str, ismear: str) -> tuple[bool, str]:
    """
    Returns (True, reason) if a KPOINTS file should be written,
    (False, reason) if KSPACING should be appended to INCAR.
    """
    if ct == "band":
        return True, "band structure requires a line-mode KPOINTS"
    if ct == "dos" and ismear == "-5":
        return True, "DOS + ISMEAR=-5 (tetrahedron) requires an explicit MP mesh"
    if ct in ("hse", "hse-relax"):
        return True, "HSE06 uses an explicit MP KPOINTS"
    return False, f"{ct} — append KSPACING to INCAR"


# ── Public entry point ────────────────────────────────────────────────────────

def kgen_mode(incar_path: str = "INCAR") -> None:
    """Interactive K-point setup wizard."""
    if not _RICH_OK:
        _kgen_plain(incar_path)
        return
    _kgen_rich(incar_path)


# ── Plain-text fallback ───────────────────────────────────────────────────────

def _kgen_plain(incar_path: str) -> None:
    ipath = Path(incar_path)
    kpath = ipath.parent / "KPOINTS"

    if not ipath.exists():
        print(f"[WARN] {ipath} not found — cannot detect calc type.")
        ks = input(f"KSPACING (Å⁻¹) [{DEFAULT_KSPACING}]: ").strip() or str(DEFAULT_KSPACING)
        append_kspacing(ipath, float(ks))
        print(f"[OK] KSPACING={float(ks):.2f} written to {ipath}")
        return

    text = ipath.read_text()
    ct = detect_job_type(text)
    ismear = detect_ismear(text)
    need_file, reason = _needs_kpoints_file(ct, ismear)

    print(f"INCAR: {ipath}  |  type: {ct}" + (f"  |  ISMEAR={ismear}" if ismear else ""))
    print(f"  → {reason}")

    if need_file:
        if ct == "band":
            content = kpoints_band_placeholder()
            write_kpoints(kpath, content)
            print(f"[OK] Line-mode KPOINTS placeholder → {kpath}")
            print("     ⚠  Edit the k-path for your structure (use VASPKIT/seekpath).")
        else:
            raw = input("MP grid (nx ny nz) [4 4 4]: ").strip() or "4 4 4"
            nx, ny, nz = (int(x) for x in raw.split())
            content = kpoints_mp(nx, ny, nz, comment=f"MP mesh for {ct}")
            write_kpoints(kpath, content)
            print(f"[OK] KPOINTS ({nx}×{ny}×{nz} MP) → {kpath}")
    else:
        ks = input(f"KSPACING (Å⁻¹) [{DEFAULT_KSPACING}]: ").strip() or str(DEFAULT_KSPACING)
        append_kspacing(ipath, float(ks))
        print(f"[OK] KSPACING={float(ks):.2f} written to {ipath}")


# ── Rich TUI ──────────────────────────────────────────────────────────────────

def _kgen_rich(incar_path: str) -> None:
    console = Console()
    ipath = Path(incar_path)
    kpath = ipath.parent / "KPOINTS"

    console.print()
    console.rule("[bold cyan]VASP K-Point Setup[/bold cyan]")
    console.print()

    # ── Read / detect INCAR ───────────────────────────────────────────────────
    if not ipath.exists():
        console.print(f"  [bold red]INCAR not found:[/bold red] {ipath.resolve()}")
        console.print()
        action = questionary.select(
            "INCAR does not exist — what would you like to do?",
            choices=[
                questionary.Choice("Generate INCAR first  (runs interactive INCAR wizard)", value="gen"),
                questionary.Choice("Write KSPACING to a new INCAR stub", value="ks"),
                questionary.Choice("Cancel", value="cancel"),
            ],
        ).ask()
        if action is None or action == "cancel":
            console.print("  [yellow]Cancelled.[/yellow]")
            return
        if action == "gen":
            from incar.interactive import interactive_mode
            interactive_mode()
            if not ipath.exists():
                console.print(f"\n  [dim]INCAR not written to '{ipath}'. Run -k again.[/dim]\n")
                return
        text = ipath.read_text() if ipath.exists() else ""
    else:
        text = ipath.read_text()

    ct = detect_job_type(text) if text else "scf"
    ismear = detect_ismear(text)
    need_file, reason = _needs_kpoints_file(ct, ismear)

    console.print(f"  INCAR   : [green]{ipath.resolve()}[/green]")
    console.print(f"  Type    : [yellow]{ct}[/yellow]" +
                  (f"   ISMEAR=[bold]{ismear}[/bold]" if ismear else ""))
    console.print(f"  Action  : {reason}")
    console.print()

    # ── Branch: KPOINTS file ──────────────────────────────────────────────────
    if need_file:
        console.print(f"  Output  : [cyan]{kpath.resolve()}[/cyan]")
        console.print()

        if ct == "band":
            console.print(
                "  [bold yellow]Band structure[/bold yellow] — writing a line-mode KPOINTS "
                "[bold]placeholder[/bold].\n"
                "  ⚠  You must replace the k-path with the correct high-symmetry path\n"
                "  for your structure (e.g. VASPKIT option 303, or seekpath).\n"
            )
            ok = questionary.confirm("Write placeholder KPOINTS?", default=True).ask()
            if not ok:
                console.print("  [yellow]Cancelled.[/yellow]")
                return
            write_kpoints(kpath, kpoints_band_placeholder())
            console.print(f"\n  [bold green]✓[/bold green] KPOINTS (line-mode placeholder) → [cyan]{kpath.resolve()}[/cyan]")
            console.print("  [dim]Edit the k-path section before running VASP.[/dim]\n")

        else:
            label = "DOS (ISMEAR=-5)" if ct == "dos" else f"HSE06 ({ct})"
            console.print(f"  [bold yellow]{label}[/bold yellow] — explicit Monkhorst-Pack grid.\n")
            raw_grid = questionary.text(
                "MP grid  (nx  ny  nz):",
                default="4 4 4",
                validate=lambda v: True if _valid_grid(v) else "Enter three positive integers",
            ).ask()
            if raw_grid is None:
                sys.exit(0)
            nx, ny, nz = (int(x) for x in raw_grid.split())
            content = kpoints_mp(nx, ny, nz, comment=f"MP mesh for {ct}")
            console.print()
            console.print(f"  [bold]KPOINTS[/bold]  →  Monkhorst-Pack  {nx}  {ny}  {nz}")
            console.print()
            ok = questionary.confirm("Write KPOINTS?", default=True).ask()
            if not ok:
                console.print("  [yellow]Cancelled.[/yellow]")
                return
            write_kpoints(kpath, content)
            console.print(f"\n  [bold green]✓[/bold green] KPOINTS written → [cyan]{kpath.resolve()}[/cyan]\n")

    # ── Branch: KSPACING in INCAR ─────────────────────────────────────────────
    else:
        console.print(f"  Target  : [cyan]{ipath.resolve()}[/cyan]  (KSPACING tag)\n")
        ks_raw = questionary.text(
            "KSPACING value (Å⁻¹):",
            default=f"{DEFAULT_KSPACING:.2f}",
            validate=lambda v: True if _is_pos_float(v) else "Enter a positive number",
        ).ask()
        if ks_raw is None:
            sys.exit(0)
        ks = float(ks_raw)
        console.print()
        console.print(f"  [bold]KSPACING[/bold] = {ks:.2f}  Å⁻¹  →  [cyan]{ipath.resolve()}[/cyan]")
        console.print()
        ok = questionary.confirm("Write KSPACING to INCAR?", default=True).ask()
        if not ok:
            console.print("  [yellow]Cancelled.[/yellow]")
            return
        append_kspacing(ipath, ks)
        console.print(f"\n  [bold green]✓[/bold green] KSPACING={ks:.2f} written to [cyan]{ipath.resolve()}[/cyan]\n")


def _valid_grid(v: str) -> bool:
    parts = v.strip().split()
    if len(parts) != 3:
        return False
    try:
        return all(int(p) > 0 for p in parts)
    except ValueError:
        return False


def _is_pos_float(v: str) -> bool:
    try:
        return float(v) > 0
    except ValueError:
        return False
