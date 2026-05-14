"""potgen — generate POTCAR from POSCAR using MP-recommended pseudopotentials.

PP library  : /home/script/vasp_pp/potpaw_PBE/POTCAR_for_MP/<Element>/POTCAR
Override    : export VASP_PP_PATH=/path/to/POTCAR_for_MP

Each element folder already contains the MP-recommended variant (e.g. Li → Li_sv).
The variant label is read from the first line of the POTCAR.

Usage (interactive):
    python3 potcar_gen.py
    from potcar.potgen import potgen_mode; potgen_mode()
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    import questionary
    from rich.console import Console
    from rich.table import Table
    from rich import box as rich_box
    _RICH_OK = True
except ImportError:
    _RICH_OK = False

DEFAULT_PP_DIR = Path("/home/script/vasp_pp/potpaw_PBE/POTCAR_for_MP")


# ── helpers ───────────────────────────────────────────────────────────────────

def _pp_dir() -> Path:
    env = os.environ.get("VASP_PP_PATH")
    return Path(env) if env else DEFAULT_PP_DIR


def _potcar_path(element: str, pp_dir: Path) -> Path:
    return pp_dir / element / "POTCAR"


def _read_variant(potcar: Path) -> str:
    """Extract PP variant label from first line, e.g. 'PAW_PBE Li_sv 10Sep2004' → 'Li_sv'."""
    try:
        first = potcar.read_text(errors="replace").split("\n", 1)[0].strip()
        parts = first.split()
        return parts[1] if len(parts) >= 2 else first
    except Exception:
        return "?"


def _parse_poscar_elements(poscar: Path) -> list[str]:
    """Return element list from POSCAR (line 6, VASP5 format)."""
    lines = poscar.read_text().splitlines()
    if len(lines) < 6:
        raise ValueError(f"POSCAR too short: {poscar}")
    return lines[5].split()


# ── public API ────────────────────────────────────────────────────────────────

def build_potcar(elements: list[str], pp_dir: Path | None = None) -> tuple[str, list[tuple[str, str]]]:
    """
    Concatenate POTCAR files for elements in order.
    Returns (combined_text, [(element, variant), ...]).
    Raises FileNotFoundError if any element is missing from the library.
    """
    pp_dir = pp_dir or _pp_dir()
    parts: list[str] = []
    used: list[tuple[str, str]] = []
    for el in elements:
        p = _potcar_path(el, pp_dir)
        if not p.exists():
            raise FileNotFoundError(f"No POTCAR found for element '{el}' in {pp_dir}")
        text = p.read_text(errors="replace")
        parts.append(text)
        used.append((el, _read_variant(p)))
    return "".join(parts), used


# ── entry points ──────────────────────────────────────────────────────────────

def potgen_mode(poscar_path: str = "POSCAR", output: str = "POTCAR") -> None:
    if not _RICH_OK:
        _potgen_plain(poscar_path, output)
        return
    _potgen_rich(poscar_path, output)


# ── plain fallback ────────────────────────────────────────────────────────────

def _potgen_plain(poscar_path: str, output: str) -> None:
    poscar = Path(poscar_path)
    if not poscar.exists():
        poscar_path = input(f"POSCAR path [{poscar_path}]: ").strip() or poscar_path
        poscar = Path(poscar_path)
    if not poscar.exists():
        print(f"[ERROR] POSCAR not found: {poscar}")
        return

    elements = _parse_poscar_elements(poscar)
    print(f"Elements: {' '.join(elements)}")

    try:
        text, used = build_potcar(elements)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return

    for el, var in used:
        print(f"  {el:4s}  →  {var}")

    out = Path(output)
    out.write_text(text)
    print(f"[OK] POTCAR written → {out.resolve()}")


# ── rich TUI ──────────────────────────────────────────────────────────────────

def _potgen_rich(poscar_path: str, output: str) -> None:
    console = Console()
    console.print()
    console.rule("[bold cyan]VASP POTCAR Generator[/bold cyan]")
    console.print()

    # ── POSCAR path ───────────────────────────────────────────────────────────
    poscar_raw = questionary.text(
        "POSCAR path:",
        default=poscar_path,
    ).ask()
    if poscar_raw is None:
        sys.exit(0)
    poscar = Path(poscar_raw.strip())

    if not poscar.exists():
        console.print(f"  [bold red]POSCAR not found:[/bold red] {poscar.resolve()}")
        return

    # ── Parse elements ────────────────────────────────────────────────────────
    try:
        elements = _parse_poscar_elements(poscar)
    except Exception as e:
        console.print(f"  [bold red]Parse error:[/bold red] {e}")
        return

    # ── Resolve PPs ───────────────────────────────────────────────────────────
    pp_dir = _pp_dir()
    missing = [el for el in elements if not _potcar_path(el, pp_dir).exists()]
    if missing:
        console.print(
            f"  [bold red]Missing PP for:[/bold red] {', '.join(missing)}\n"
            f"  Library: {pp_dir}"
        )
        return

    used = [(el, _read_variant(_potcar_path(el, pp_dir))) for el in elements]

    # ── Summary table ─────────────────────────────────────────────────────────
    tbl = Table(box=rich_box.SIMPLE_HEAVY, show_header=True, header_style="bold")
    tbl.add_column("Element", style="cyan", no_wrap=True)
    tbl.add_column("PP variant", style="yellow")
    tbl.add_column("POTCAR path", style="dim")
    for el, var in used:
        tbl.add_row(el, var, str(_potcar_path(el, pp_dir)))
    console.print(tbl)

    # ── Output path ───────────────────────────────────────────────────────────
    out_dir = poscar.parent
    out_default = str(out_dir / output)
    out_raw = questionary.text("Output POTCAR path:", default=out_default).ask()
    if out_raw is None:
        sys.exit(0)
    out = Path(out_raw.strip())

    console.print()
    ok = questionary.confirm("Write POTCAR?", default=True).ask()
    if not ok:
        console.print("  [yellow]Cancelled.[/yellow]")
        return

    # ── Write ─────────────────────────────────────────────────────────────────
    try:
        text, _ = build_potcar(elements)
    except FileNotFoundError as e:
        console.print(f"  [bold red]{e}[/bold red]")
        return

    out.write_text(text)
    console.print(
        f"\n  [bold green]✓[/bold green] POTCAR written → [cyan]{out.resolve()}[/cyan]\n"
        f"  Elements: {' + '.join(f'[yellow]{v}[/yellow]' for _, v in used)}\n"
    )
