#!/usr/bin/env python3
"""
55 — Bader Charge Transfer Analysis

Auto-discovers directories with 1/ (total system) and 3/ (adsorbate)
subdirectories, then computes charge transfer per adsorbate atom.

  1/ACF.dat   — Bader charges for the total system
  1/POSCAR    — atomic structure of the total system
  3/POSCAR    — atomic structure of the adsorbate only
  3/POTCAR    — ZVAL (valence electrons) per element

Charge transfer per atom = Bader charge − ZVAL
  Positive = electron gain (anion-like)
  Negative = electron loss (cation-like)

Usage (standalone):
    python3 utils/bader.py [work_dir]

    work_dir defaults to the current working directory.
    Results are written to <work_dir>/bader_charge_transfer.txt
"""

import os
import re
import math
import sys

TOL = 0.05  # coordinate matching tolerance in fractional coords


# ── POSCAR parser ─────────────────────────────────────────────────────────────

def parse_poscar(path):
    """Parse POSCAR, return (elements, counts, coords) in Direct fractional."""
    with open(path) as f:
        lines = f.readlines()

    line0 = lines[0].strip().split()

    # Line 5 may be element names (VASP5) or counts (VASP4)
    line5 = lines[5].strip().split()
    if line5[0].isalpha():
        elem_line = line5
        count_line = lines[6].strip().split()
        coord_candidate = 7
    else:
        elem_line = line0
        count_line = line5
        coord_candidate = 6

    counts = [int(x) for x in count_line]
    n_total = sum(counts)

    # Locate coordinate block (skip Selective Dynamics line if present)
    coord_start = coord_candidate
    for skip in range(coord_start, len(lines)):
        ls = lines[skip].strip().lower()
        if ls.startswith("s"):
            continue
        elif ls.startswith("d") or ls.startswith("c") or ls.startswith("k"):
            coord_start = skip + 1
            break

    coords = []
    for i in range(coord_start, coord_start + n_total):
        parts = lines[i].strip().split()
        coords.append([float(parts[0]), float(parts[1]), float(parts[2])])

    elements = []
    for elem, cnt in zip(elem_line, counts):
        elements.extend([elem] * cnt)

    return elements, counts, coords


# ── ACF.dat parser ────────────────────────────────────────────────────────────

def parse_acf(path, n_atoms):
    """Parse ACF.dat, return list of (atom_id, charge) tuples (1-indexed)."""
    charges = []
    with open(path) as f:
        lines = f.readlines()
    data_lines = [l for l in lines
                  if re.match(r'^\s+\d+', l) and len(l.strip().split()) == 7]
    for line in data_lines[:n_atoms]:
        parts = line.strip().split()
        charges.append((int(parts[0]), float(parts[4])))
    return charges


# ── POTCAR ZVAL parser ────────────────────────────────────────────────────────

def get_zval(potcar_path):
    """Parse POTCAR, return {element: ZVAL} dict.

    Handles decorated names like 'Li_sv' → also stores under 'Li'.
    """
    zval = {}
    current_elem = None
    with open(potcar_path) as f:
        for line in f:
            m = re.search(r'ZVAL\s*=\s*([\d.]+)', line)
            if m and current_elem:
                z = float(m.group(1))
                zval[current_elem] = z
                base = re.match(r'([A-Z][a-z]?)', current_elem)
                if base:
                    zval[base.group(1)] = z

            t = re.search(r'TITEL\s*=\s*PAW[_\s]PBE\s+([\w_]+)', line)
            if not t:
                t = re.search(r'TITEL\s*=\s*PAW\s+([\w_]+)', line)
            if t:
                current_elem = t.group(1)
    return zval


# ── Coordinate matching ───────────────────────────────────────────────────────

def match_coords(probe_coords, target_coords, target_elements, tol=TOL):
    """Match each probe fractional coordinate to the nearest target coordinate."""
    matches = []
    used = set()
    for pi, pc in enumerate(probe_coords):
        best = None
        best_dist = float('inf')
        for ti, tc in enumerate(target_coords):
            if ti in used:
                continue
            dist = math.sqrt(
                min(abs(pc[0] - tc[0]), 1 - abs(pc[0] - tc[0])) ** 2 +
                min(abs(pc[1] - tc[1]), 1 - abs(pc[1] - tc[1])) ** 2 +
                min(abs(pc[2] - tc[2]), 1 - abs(pc[2] - tc[2])) ** 2
            )
            if dist < best_dist:
                best_dist = dist
                best = ti
        if best is not None and best_dist < tol:
            matches.append((pi, best, best_dist, target_elements[best]))
            used.add(best)
        else:
            matches.append((pi, None, best_dist, None))
    return matches


# ── Per-model processing ──────────────────────────────────────────────────────

def process_model(model_dir):
    """Process one model directory.

    Returns:
        (result_lines, total_by_elem, zval_dict)  on success
        list[str]                                  on error/skip
    """
    dir1 = os.path.join(model_dir, "1")
    dir3 = os.path.join(model_dir, "3")

    if not os.path.isdir(dir1) or not os.path.isdir(dir3):
        return ["  [SKIP] missing 1/ or 3/ subdirectory"]

    try:
        elements_1, _, coords_1 = parse_poscar(os.path.join(dir1, "POSCAR"))
    except Exception as e:
        return [f"  [ERROR] parsing 1/POSCAR: {e}"]
    try:
        elements_3, _, coords_3 = parse_poscar(os.path.join(dir3, "POSCAR"))
    except Exception as e:
        return [f"  [ERROR] parsing 3/POSCAR: {e}"]

    n_total_1 = len(elements_1)

    try:
        charges = parse_acf(os.path.join(dir1, "ACF.dat"), n_total_1)
    except Exception as e:
        return [f"  [ERROR] parsing 1/ACF.dat: {e}"]

    try:
        zval_dict = get_zval(os.path.join(dir3, "POTCAR"))
    except Exception as e:
        return [f"  [ERROR] parsing 3/POTCAR: {e}"]

    matches = match_coords(coords_3, coords_1, elements_1)

    total_by_elem = {}
    results = []
    results.append(f"  {'Atom':>4s} {'Element':>6s} {'ZVAL':>6s} "
                   f"{'Charge':>8s} {'Transfer':>8s} {'Dist':>8s}")
    results.append(f"  {'-'*42}")

    for pi, (probe_idx, target_idx, dist, elem) in enumerate(matches):
        if target_idx is None:
            results.append(f"  {pi+1:>4d} {'?':>6s} {'?':>6s} "
                           f"{'?':>8s} {'NO_MATCH':>8s} {dist:>8.4f}")
            continue

        charge_val = charges[target_idx][1]
        zval = zval_dict.get(elem, 0)
        transfer = charge_val - zval

        elem_ads = elements_3[probe_idx]
        if elem_ads not in total_by_elem:
            total_by_elem[elem_ads] = [0.0, 0]
        total_by_elem[elem_ads][0] += transfer
        total_by_elem[elem_ads][1] += 1

        results.append(f"  {target_idx+1:>4d} {elem:>6s} {zval:>6.2f} "
                       f"{charge_val:>8.4f} {transfer:>+8.4f} {dist:>8.4f}")

    return results, total_by_elem, zval_dict


# ── Directory discovery ───────────────────────────────────────────────────────

def discover_models(base):
    """Return list of directories that contain both 1/ and 3/ subdirs."""
    dirs = []

    def has_subdirs(d):
        return os.path.isdir(os.path.join(d, "1")) and \
               os.path.isdir(os.path.join(d, "3"))

    if has_subdirs(base):
        dirs.append(base)

    for item in sorted(os.listdir(base)):
        item_dir = os.path.join(base, item)
        if not os.path.isdir(item_dir):
            continue
        if has_subdirs(item_dir):
            dirs.append(item_dir)
            continue
        for child in sorted(os.listdir(item_dir)):
            child_dir = os.path.join(item_dir, child)
            if os.path.isdir(child_dir) and has_subdirs(child_dir):
                dirs.append(child_dir)

    return dirs


# ── Main ──────────────────────────────────────────────────────────────────────

def main(work_dir=None):
    """Run Bader charge transfer analysis.

    Args:
        work_dir: Root directory to search for model subdirectories.
                  Defaults to the current working directory.
    """
    if work_dir is None:
        work_dir = os.getcwd()

    output_path = os.path.join(work_dir, "bader_charge_transfer.txt")
    all_results = []

    for model_dir in discover_models(work_dir):
        all_results.append(f"\n{'='*60}")
        all_results.append(f"  {model_dir}")
        all_results.append(f"{'='*60}")

        out = process_model(model_dir)
        if not out:
            continue

        if isinstance(out[0], str):
            # Error / skip messages
            all_results.extend(out)
        else:
            results_list, total_by_elem, zval_dict = out
            all_results.extend(results_list)

            all_results.append("")
            all_results.append("  --- Charge Transfer Summary ---")
            grand_total = 0.0
            grand_count = 0
            for elem in sorted(total_by_elem.keys()):
                total, count = total_by_elem[elem]
                zval = zval_dict.get(elem, 0)
                grand_total += total
                grand_count += count
                all_results.append(
                    f"  {elem:>6s}: {count:>2d} atoms, ZVAL={zval:.2f}, "
                    f"total transfer={total:>+8.4f} e"
                )
            all_results.append(f"  {'─' * 46}")
            all_results.append(
                f"  {'Total':>6s}: {grand_count:>2d} atoms, "
                f"total transfer={grand_total:>+8.4f} e"
            )

    # Build cross-system summary table
    summary_lines = [
        f"\n{'='*90}",
        "  Summary: Charge Transfer per System",
        f"{'='*90}",
        f"  {'System':<20s} {'Elem':>6s} {'Count':>6s} {'ZVAL':>6s} {'Total(e)':>10s}",
        f"  {'-'*50}",
    ]

    current_label = ""
    for line in all_results:
        m = re.match(r'^\s{2}(\S[^=]+?)$', line)
        if m and not line.strip().startswith(("=", "-")):
            candidate = m.group(1).strip()
            if "/" in candidate or len(candidate) < 20:
                current_label = candidate

        m2 = re.match(
            r'^\s+(\w+):\s+(\d+) atoms, ZVAL=([\d.]+), total transfer=\s*([+-][\d.]+) e',
            line
        )
        if m2 and current_label:
            elem, count, zval, total = m2.groups()
            summary_lines.append(
                f"  {current_label:<20s} {elem:>6s} {count:>6s} {zval:>6s} {total:>10s}"
            )

        mt = re.match(
            r'^\s+Total:\s+(\d+) atoms,\s+total transfer=\s*([+-][\d.]+) e',
            line
        )
        if mt and current_label:
            count_all, total_all = mt.groups()
            summary_lines.append(f"  {'─' * 48}")
            summary_lines.append(
                f"  {current_label:<20s} {'Total':>6s} {count_all:>6s} {'—':>6s} {total_all:>10s}"
            )
            summary_lines.append("")

    summary_lines.append("")

    with open(output_path, "w") as f:
        f.write("Bader Charge Transfer Analysis\n")
        f.write("=" * 60 + "\n")
        f.write("Transfer = Bader charge - ZVAL (valence e-)\n")
        f.write("Positive = electron gain, Negative = electron loss\n")
        f.write("=" * 60 + "\n")
        f.write("\n".join(summary_lines))
        f.write("\n")
        f.write("\n".join(all_results))
        f.write("\n")

    print(f"  Results written to: {output_path}")


if __name__ == "__main__":
    work_dir = sys.argv[1] if len(sys.argv) > 1 else None
    main(work_dir)
