#!/usr/bin/env python3
"""
Calculate Bader charge transfer for adsorbate systems.

Auto-discovers directories with 1/ (total) and 3/ (adsorbate) subdirectories.
  - Reads 1/ACF.dat  (Bader charges for total system)
  - Reads 1/POSCAR   (atomic structure of total system)
  - Reads 3/POSCAR   (atomic structure of adsorbate only)
  - Reads 3/POTCAR   (ZVAL = valence electrons per element)

Charge transfer per atom = Bader charge - ZVAL
  Positive = electron gain (anion)
  Negative = electron loss (cation)
"""

import os
import re
import math

BASE = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(BASE, "bader_charge_transfer.txt")

TOL = 0.05  # coordinate matching tolerance in fractional coords


def parse_poscar(path):
    """Parse POSCAR, return (elements, counts, coords) where coords are Direct fractional."""
    with open(path) as f:
        lines = f.readlines()
    # Line 0: element names
    line0 = lines[0].strip().split()

    # Find the counts line (may be line 5 or line 6 if line 5 has element names)
    # Check if line 5 contains numbers (counts) or text (element names)
    line5 = lines[5].strip().split()
    if line5[0].isalpha():
        # Format with element names on both line 0 and line 5
        elem_line = line5
        count_line = lines[6].strip().split()
        coord_candidate = 7
    else:
        elem_line = line0
        count_line = line5
        coord_candidate = 6

    counts = [int(x) for x in count_line]
    n_total = sum(counts)

    # Find where coordinates start
    coord_start = coord_candidate
    coord_type = "direct"
    for skip in range(coord_start, len(lines)):
        ls = lines[skip].strip().lower()
        if ls.startswith("s"):
            continue  # Selective dynamics
        elif ls.startswith("d") or ls.startswith("c") or ls.startswith("k"):
            coord_type = "direct" if ls.startswith("d") else "cartesian"
            coord_start = skip + 1
            break

    # Check if selective dynamics: if first coord line has T/F flags (= 6+ columns)
    first_coord = lines[coord_start].strip().split()
    if len(first_coord) >= 6:
        # Has Selective Dynamics T/F flags
        sel_coords = []
        for i in range(coord_start, coord_start + n_total):
            parts = lines[i].strip().split()
            sel_coords.append([float(parts[0]), float(parts[1]), float(parts[2])])
        coords = sel_coords
    else:
        coords = []
        for i in range(coord_start, coord_start + n_total):
            parts = lines[i].strip().split()
            coords.append([float(parts[0]), float(parts[1]), float(parts[2])])

    # Expand elements by counts
    elements = []
    for elem, cnt in zip(elem_line, counts):
        elements.extend([elem] * cnt)

    return elements, counts, coords


def parse_acf(path, n_atoms):
    """Parse ACF.dat, return list of (atom_id, charge) for each atom (1-indexed)."""
    charges = []
    with open(path) as f:
        lines = f.readlines()
    # Data starts from line 3 (after header and separator)
    data_lines = [l for l in lines if re.match(r'^\s+\d+', l) and len(l.strip().split()) == 7]
    for line in data_lines[:n_atoms]:
        parts = line.strip().split()
        atom_id = int(parts[0])
        charge = float(parts[4])
        charges.append((atom_id, charge))
    return charges


def get_zval(potcar_path):
    """Parse POTCAR, return dict of {element: ZVAL}.

    Handles POTCAR element names like "Li_sv", "S", mapping to base symbol.
    """
    zval = {}
    current_elem = None
    with open(potcar_path) as f:
        for line in f:
            # Match ZVAL line
            m = re.search(r'ZVAL\s*=\s*([\d.]+)', line)
            if m and current_elem:
                z = float(m.group(1))
                zval[current_elem] = z
                # Also store under base element (e.g. "Li" from "Li_sv")
                base = re.match(r'([A-Z][a-z]?)', current_elem)
                if base:
                    zval[base.group(1)] = z
            # Match TITEL line for PAW_PBE or PAW (older format)
            t = re.search(r'TITEL\s*=\s*PAW[_\s]PBE\s+([\w_]+)', line)
            if not t:
                t = re.search(r'TITEL\s*=\s*PAW\s+([\w_]+)', line)
            if t:
                current_elem = t.group(1)
    return zval


def match_coords(probe_coords, target_coords, target_elements, tol=TOL):
    """Match each probe coordinate to a target coordinate within tolerance."""
    matches = []
    used = set()
    for pi, pc in enumerate(probe_coords):
        best = None
        best_dist = float('inf')
        for ti, tc in enumerate(target_coords):
            if ti in used:
                continue
            # Euclidean distance in fractional space (wrapping since periodic)
            dist = math.sqrt(
                min(abs(pc[0] - tc[0]), 1 - abs(pc[0] - tc[0]))**2 +
                min(abs(pc[1] - tc[1]), 1 - abs(pc[1] - tc[1]))**2 +
                min(abs(pc[2] - tc[2]), 1 - abs(pc[2] - tc[2]))**2
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


def process_model(model_dir):
    """Process one model directory. Return list of result strings."""
    dir1 = os.path.join(model_dir, "1")
    dir3 = os.path.join(model_dir, "3")
    results = []

    if not os.path.isdir(dir1) or not os.path.isdir(dir3):
        return [f"  [SKIP] missing 1/ or 3/ subdirectory"]

    # Parse POSCAR files
    try:
        elements_1, counts_1, coords_1 = parse_poscar(os.path.join(dir1, "POSCAR"))
    except Exception as e:
        return [f"  [ERROR] parsing 1/POSCAR: {e}"]
    try:
        elements_3, counts_3, coords_3 = parse_poscar(os.path.join(dir3, "POSCAR"))
    except Exception as e:
        return [f"  [ERROR] parsing 3/POSCAR: {e}"]

    n_total_1 = len(elements_1)
    n_ads = len(elements_3)

    # Parse ACF.dat
    try:
        charges = parse_acf(os.path.join(dir1, "ACF.dat"), n_total_1)
    except Exception as e:
        return [f"  [ERROR] parsing 1/ACF.dat: {e}"]

    # Get ZVAL from 3/POTCAR
    try:
        zval_dict = get_zval(os.path.join(dir3, "POTCAR"))
    except Exception as e:
        return [f"  [ERROR] parsing 3/POTCAR: {e}"]

    # Match adsorbate coordinates (from 3/) to total system (from 1/)
    matches = match_coords(coords_3, coords_1, elements_1)

    total_by_elem = {}  # {element: [total_transfer, n_atoms]}

    results.append(f"  {'Atom':>4s} {'Element':>6s} {'ZVAL':>6s} {'Charge':>8s} {'Transfer':>8s} {'Dist':>8s}")
    results.append(f"  {'-'*42}")

    for pi, (probe_idx, target_idx, dist, elem) in enumerate(matches):
        if target_idx is None:
            results.append(f"  {probe_idx+1:>4d} {'?':>6s} {'?':>6s} {'?':>8s} {'NO_MATCH':>8s} {dist:>8.4f}")
            continue

        atom_id = target_idx + 1  # 1-indexed
        charge_val = charges[target_idx][1]
        zval = zval_dict.get(elem, 0)
        transfer = charge_val - zval

        elem_ads = elements_3[probe_idx]
        if elem_ads not in total_by_elem:
            total_by_elem[elem_ads] = [0.0, 0]
        total_by_elem[elem_ads][0] += transfer
        total_by_elem[elem_ads][1] += 1

        results.append(f"  {atom_id:>4d} {elem:>6s} {zval:>6.2f} {charge_val:>8.4f} {transfer:>+8.4f} {dist:>8.4f}")

    return results, total_by_elem, zval_dict


def main():
    all_results = []
    dirs_to_process = []

    # Check if BASE itself contains 1/ and 3/ subdirectories
    if os.path.isdir(os.path.join(BASE, "1")) and os.path.isdir(os.path.join(BASE, "3")):
        dirs_to_process.append(BASE)

    # Auto-discover all directories with 1/ and 3/ subdirectories
    items = sorted(os.listdir(BASE))
    for item in items:
        item_dir = os.path.join(BASE, item)
        if not os.path.isdir(item_dir):
            continue
        # Check if this directory itself contains 1/ and 3/
        if os.path.isdir(os.path.join(item_dir, "1")) and os.path.isdir(os.path.join(item_dir, "3")):
            dirs_to_process.append(item_dir)
            continue
        # Check child directories (e.g. h/li2s, m/li2s)
        for child in sorted(os.listdir(item_dir)):
            child_dir = os.path.join(item_dir, child)
            if not os.path.isdir(child_dir):
                continue
            if os.path.isdir(os.path.join(child_dir, "1")) and os.path.isdir(os.path.join(child_dir, "3")):
                dirs_to_process.append(child_dir)

    for model_dir in dirs_to_process:
            all_results.append(f"\n{'='*60}")
            all_results.append(f"  {model_dir}")
            all_results.append(f"{'='*60}")

            out = process_model(model_dir)
            if out:
                # out is a list of strings if ERROR/SKIP, or [results_list, total_by_elem, zval_dict]
                if isinstance(out[0], str):
                    all_results.extend(out)
                else:
                    results_list, total_by_elem, zval_dict = out
                    all_results.extend(results_list)

                    # Summary per element + overall total
                    all_results.append(f"")
                    all_results.append(f"  --- Charge Transfer Summary ---")
                    grand_total = 0.0
                    grand_count = 0
                    for elem in sorted(total_by_elem.keys()):
                        total, count = total_by_elem[elem]
                        zval = zval_dict.get(elem, 0)
                        grand_total += total
                        grand_count += count
                        all_results.append(f"  {elem:>6s}: {count:>2d} atoms, ZVAL={zval:.2f}, "
                                           f"total transfer={total:>+8.4f} e")
                    all_results.append(f"  {'─' * 46}")
                    all_results.append(f"  {'Total':>6s}: {grand_count:>2d} atoms, "
                                       f"total transfer={grand_total:>+8.4f} e")
    # Build summary table
    summary_lines = []
    summary_lines.append(f"\n{'='*90}")
    summary_lines.append(f"  Summary: Charge Transfer per System")
    summary_lines.append(f"{'='*90}")
    summary_lines.append(f"  {'System':<20s} {'Elem':>6s} {'Count':>6s} {'ZVAL':>6s} {'Total(e)':>10s}")
    summary_lines.append(f"  {'-'*50}")

    # Parse all_results to build summary
    current_label = ""
    current_totals = {}  # {label: {elem: (count, total, zval)}}
    for line in all_results:
        # Match model header lines like "  h/li2s" or "  mydir/mymodel"
        m = re.match(r'^\s{2}(\S[^=]+?)$', line)
        if m and not line.strip().startswith("=") and not line.strip().startswith("-"):
            candidate = m.group(1).strip()
            # Only treat as label if it looks like a path (contains / or is simple)
            if "/" in candidate or len(candidate) < 20:
                current_label = candidate
        # Match per-element summary lines
        m2 = re.match(r'^\s+(\w+):\s+(\d+) atoms, ZVAL=([\d.]+), total transfer=\s*([+-][\d.]+) e', line)
        if m2 and current_label:
            elem, count, zval, total = m2.groups()
            summary_lines.append(f"  {current_label:<20s} {elem:>6s} {count:>6s} {zval:>6s} {total:>10s}")
            # Track for total
            if current_label not in current_totals:
                current_totals[current_label] = []
            z = float(zval)
            t = float(total)
            c = int(count)
            current_totals[current_label].append((c, t, z))
        # Match total line
        mt = re.match(r'^\s+Total:\s+(\d+) atoms,\s+total transfer=\s*([+-][\d.]+) e', line)
        if mt and current_label:
            count_all, total_all = mt.groups()
            summary_lines.append(f"  {'─' * 48}")
            summary_lines.append(f"  {current_label:<20s} {'Total':>6s} {count_all:>6s} {'—':>6s} {total_all:>10s}")
            summary_lines.append(f"")

    summary_lines.append("")

    with open(OUTPUT, "w") as f:
        f.write("Bader Charge Transfer Analysis\n")
        f.write("=" * 60 + "\n")
        f.write("Transfer = Bader charge - ZVAL (valence e-)\n")
        f.write("Positive = electron gain, Negative = electron loss\n")
        f.write("=" * 60 + "\n")
        f.write("\n".join(summary_lines))
        f.write("\n")
        f.write("\n".join(all_results))
        f.write("\n")

    print(f"Results written to: {OUTPUT}")


if __name__ == "__main__":
    main()
