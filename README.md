# VASP INCAR Generator

An interactive TUI tool for generating VASP INCAR files from a POSCAR.  
Packaged as `incar/` with `incar_gen.py` and the shell menu `incar-genner.sh`.

---

## Installation

```bash
git clone https://github.com/nasrudin152-cloud/incar-tool.git ~/vasp-incar-generator
cd ~/vasp-incar-generator
pip install questionary rich   # required for interactive mode only
```

Then add the following alias to your `~/.bashrc` for quick access:

```bash
echo "alias incar-genner='bash \$HOME/vasp-incar-generator/incar-genner.sh'" >> ~/.bashrc
source ~/.bashrc
```

Now you can run the tool from anywhere by typing `incar-genner`.

---

## Project Structure

```
incar_gen.py          ← Python entry point
incar/
├── __init__.py       ← re-exports all builders
├── defaults.py       ← shared element data & global INCAR defaults
├── poscar.py         ← POSCAR parser + OPTCELL generator
├── formatter.py      ← format_incar() → formatted string
├── interactive.py    ← step-by-step TUI (questionary + rich)
├── relax.py
├── scf.py
├── band.py
├── dos.py
├── md.py
├── hse.py
├── dielectric.py
├── phonon.py
├── neb.py
├── soc.py
└── zpe.py            ← ZPE correction (IBRION=5, NFREE=2)
kpoints/
├── __init__.py       ← re-exports kgen API
└── kgen.py           ← KPOINTS file / KSPACING wizard
notes/
├── INCAR-cheatsheet.md          ← INCAR tags quick reference
├── vasp-analysis-tutorials.md   ← post-processing & analysis notes
└── vasp-convergence-troubleshooting.md  ← convergence issue solutions
incar-genner.sh       ← interactive shell menu
```

---

## Global INCAR Defaults

All calculation types share these base parameters (overridden per type where needed):

| Tag | Default | Notes |
|-----|---------|-------|
| `ENCUT` | 450 eV | |
| `PREC` | Normal | |
| `EDIFF` | 1E-5 | uniform default for all types; 1E-8 for phonon/dielectric |
| `EDIFFG` | -0.05 | force convergence threshold |
| `NELM` | 300 | |
| `NELMIN` | 5 | |
| `ALGO` | Fast | |
| `ISMEAR` | 0 | Gaussian; metallic mode keeps ISMEAR=0 |
| `SIGMA` | 0.05 | metallic: 0.2 |
| `ISYM` | 0 | |
| `IVDW` | 11 | DFT-D3 dispersion correction |
| `LORBIT` | 11 | projected DOS |
| `NCORE` | 4 | no NPAR |
| `LWAVE` | .FALSE. | .TRUE. for scf, hse |
| `LCHARG` | .FALSE. | .TRUE. for scf, hse |

---

## Supported Calculation Types

| Type | Description | LWAVE | LCHARG |
|------|-------------|-------|--------|
| `relax` | Structural relaxation — IBRION=2, selectable ISIF | F | F |
| `scf` | Static single-point reference | **T** | **T** |
| `band` | Band structure — ICHARG=11 | F | F |
| `dos` | Density of states — ICHARG=11, ISMEAR=0 (Gaussian, default) or -5 (selectable) | F | F |
| `md` | Ab initio MD (NVT/NVE/NPT) | F | F |
| `hse` | HSE06 hybrid static | **T** | **T** |
| `hse-relax` | HSE06 hybrid relaxation | F | F |
| `dielectric` | Dielectric function (DFPT) | F | F |
| `phonon` | Phonon force constants (DFPT) | F | F |
| `neb` | CI-NEB transition state — LCLIMB=.TRUE. | F | F |
| `soc` | SOC non-SCF band structure — LSORBIT, LNONCOLLINEAR, ISYM=-1 | F | F |
| `zpe` | ZPE correction — IBRION=5 finite differences, NFREE=2 | F | F |

### Special conditions per type

**`relax`**
- ISIF controls what relaxes: 2 = ions only, 3 = full (ions+shape+volume), 4 = ions+shape (fixed vol), 7 = volume only
- Lower POTIM (0.1–0.3) for soft phonon modes or complex energy landscapes
- For 2D / slab: use ISIF=2 or fix-Z OPTCELL (interactive mode offers this automatically)

**`scf`**
- Produces CHGCAR + WAVECAR (LWAVE/LCHARG=.TRUE.) needed by all downstream non-SCF jobs
- Use a denser k-mesh than the relax step for an accurate reference charge density

**`band`**
- Requires CHGCAR from a prior SCF run (ICHARG=11 reads it; do **not** run SCF again)
- KPOINTS must follow a high-symmetry path (line-mode), **not** a regular Monkhorst-Pack grid
- NBANDS is set to ≥ 4×natoms to capture unoccupied bands

**`dos`**
- Also requires CHGCAR from SCF (ICHARG=11)
- **ISMEAR=0 (Gaussian)** is the default — safe for metals, semiconductors, and insulators
- **ISMEAR=-5 (Tetrahedron)** gives sharper DOS features for insulators/semiconductors but **requires a uniform dense k-mesh (≥ 4×4×4)**; never use with line-mode KPOINTS or metals
- NEDOS=1500, EMIN=-30, EMAX=10 by default; adjust the energy window when needed

**`md`**
- Supports NVT, NVE, and NPT ensembles
- NVT default: MDALGO=2 with Nosé-Hoover thermostat, SMASS=0
- NVE: SMASS=-3, no thermostat
- NPT: MDALGO=3 Langevin dynamics with ISIF=3, LANGEVIN_GAMMA, LANGEVIN_GAMMA_L, PMASS, and PSTRESS
- POTIM=2 fs is typical; use 0.5–1 fs for systems containing H, Li, or other light elements
- LREAL=Auto for large cells (>~50 atoms) to avoid memory issues
- Set NBLOCK/KBLOCK to control output frequency in OUTCAR/XDATCAR

**`hse`**
- ALGO=Damped is required (not Fast); All also works but is slower
- PRECFOCK=Fast reduces computational cost with acceptable accuracy
- Very expensive — always converge with PBE first; use WAVECAR for restart
- AEXX=0.25, HFSCREEN=0.2 are standard HSE06 parameters

**`hse-relax`**
- Same caveats as `hse`; additionally keep NSW small (≤ 100) due to cost
- Consider pre-relaxing with PBE, then refining with HSE06

**`dielectric`**
- Requires a well-converged SCF starting point
- LEPSILON=.TRUE. computes both electronic and ionic contributions
- IBRION=8 (DFPT) is default; tighter EDIFF (1E-8) is set automatically

**`phonon`**
- EDIFF=1E-8 is mandatory for accurate force constants
- LREAL=.FALSE. required for correct forces (no real-space projection errors)
- Use a supercell for better Brillouin-zone sampling (phonopy workflow)
- ADDGRID=.TRUE. improves FFT accuracy

**`neb`**
- Initial and final images **must be fully relaxed** before running NEB
- LCLIMB=.TRUE. activates Climbing Image NEB for accurate saddle-point energy
- SPRING=-5 eV/Å²: increase magnitude for stiffer path
- IOPT=1 uses the VTST optimizer (requires VTST-patched VASP)
- Each image is a separate subdirectory (00/, 01/, …, N+1/)

**`soc`**
- Typical workflow: collinear SCF → SOC non-SCF (ICHARG=11 reads CHGCAR)
- LSORBIT=.TRUE. + LNONCOLLINEAR=.TRUE. set automatically
- **ISYM=-1** is enforced (symmetry must be fully disabled for non-collinear)
- SAXIS defines the spin quantization axis (default 0 0 1 = z); change for in-plane magnetization
- NBANDS doubled (spinor wavefunctions require twice as many bands)
- Ordinary collinear MAGMOM is removed automatically for SOC mode; set full non-collinear vectors manually if needed

**`zpe`**
- IBRION=5: finite differences for force constants
- NFREE=2: central differences (recommended for ZPE)
- POTIM=0.015: typical displacement for accurate force constants
- NSW=1: single ionic step computes the Hessian
- Use a supercell for better Brillouin-zone sampling

---

## Interactive Mode (TUI)

```bash
python3 incar_gen.py -i
```

Arrow-key menus and back navigation at every step:

1. **POSCAR path** — tab-completion, validates file existence  
2. **Structure summary** — elements, atom counts, magnetic / heavy / LDA+U detection  
3. **Calculation type** — arrow-key select (← Back re-enters POSCAR path)  
4. **Spin / LDA+U / SOC / Smearing** — Yes / No / ← Back at each step (default: No)  
5. **ENCUT** — text input, default 450, type `b` to go back  
6. **Type-specific params** — NSW, ISIF, temperatures, NEB images …  
   - ISIF=3 → optional **fix-Z** prompt → writes `OPTCELL` derived from actual lattice vectors  
7. **INCAR preview** — syntax-highlighted panel  
8. **Write** — confirm output path

### OPTCELL (fix-Z slab/2D)

When ISIF=3 and fix-Z is selected, `OPTCELL` is generated from the POSCAR lattice:

- The vector with the largest |z| component is fully fixed (`0 0 0`)
- In-plane vectors allow relaxation only along directions where they have non-zero components; z-column is always 0

Example — hexagonal cell `a=(3,0,0)`, `b=(-1.5,2.6,0)`, `c=(0,0,20)`:
```
 1 0 0
 1 1 0
 0 0 0
```

---

## Shell Menu

```bash
bash incar-genner.sh
```

The shell menu provides common VASP setup helpers:

| Option | Action |
|--------|--------|
| `11` | Launch the interactive INCAR generator |
| `12` | Generate KPOINTS or append KSPACING from an INCAR |
| `13` | Generate POTCAR from POSCAR elements |
| `14` | PBS script generator (queue selection + auto ppn/walltime) |
| `15` | VASP utility tools (status/restart/backup/clean) |

### PBS script generator

Option `14` asks for the system name, runs `pestat` when available, then presents a queue selection menu:

| Queue | Walltime | PPN | State |
|-------|----------|-----|-------|
| debug | 30 min | 4 | OPEN |
| short | 2 hours | 32 | CLOSE |
| normal | 72 hours (3 days) | 48 | OPEN |
| fat | 1680 hours (70 days) | 64 | OPEN |
| long | 720 hours (30 days) | 96 | OPEN |

After selecting a queue, `ppn` and `walltime` are set automatically. Then asks for:

- Node: input `1` (default) → `nodes=1`, input other number (e.g. `24`) → `nodes=node24.hpc.local`
- VASP binary type: `std` or `gam`, default `std`
- Output file name, default `vasp.pbs`

The generated PBS script loads:

```bash
module load vasp/6.3.2-all-intel2022.2
```

and writes either `vasp_std` or `vasp_gam` in the `mpirun` command.

### VASP utility tools

Option `15` opens a utility submenu with practical post-processing helpers:

- `51` Quick status: check convergence text in `OUTCAR`, and print final `TOTEN`/`E0`
- `52` Restart prep: backup `POSCAR` then copy `CONTCAR -> POSCAR`
- `53` Backup: save key input/output files into a timestamped folder
- `54` Clean outputs: remove common large VASP output files (requires typing `yes`)

---

## KPOINTS Generator

```bash
python3 incar_gen.py -k              # reads ./INCAR, writes KPOINTS or appends KSPACING
python3 incar_gen.py -k path/INCAR   # specify INCAR path
```

The tool reads `# job_type = <type>` written at the top of every generated INCAR,
then decides automatically:

| Calc type | Action |
|-----------|--------|
| `band` | Write line-mode **KPOINTS placeholder** (edit k-path manually) |
| `dos` + ISMEAR=-5 | Write **Monkhorst-Pack KPOINTS** (default 4×4×4) |
| `hse` / `hse-relax` | Write **Monkhorst-Pack KPOINTS** (default 4×4×4) |
| everything else | Append **KSPACING** to INCAR (default 0.20 Å⁻¹) |

### KSPACING formula

KSPACING (Å⁻¹) sets the maximum k-point spacing in reciprocal space:

```
n_i = ceil( |b_i| / KSPACING )
```

where **b_i** are the reciprocal lattice vectors (Å⁻¹) and **n_i** are the
number of subdivisions along each direction. VASP calculates the mesh automatically — no KPOINTS file needed.

| KSPACING | Density | Typical use |
|----------|---------|-------------|
| 0.15 | dense | SOC, DOS fine features |
| 0.20 | standard | SCF, relax, most calculations |
| 0.30 | coarse | pre-relax, large cells |
| 0.40+ | very coarse | MD, NEB |

> **Tip:** smaller KSPACING = denser mesh = more accurate but more expensive.

### Band structure KPOINTS (line-mode)

Band structure requires a **line-mode** KPOINTS with a high-symmetry k-path.
The generator writes a placeholder; replace it with the correct path for your structure:

- **VASPKIT**: option 303 (auto k-path from POSCAR)
- **seekpath** / **pymatgen `HighSymmKpath`**: programmatic generation

Line-mode format:
```
k-path comment
40          ← points between each pair
Line-mode
Reciprocal
  0.000  0.000  0.000   ! Gamma
  0.500  0.000  0.000   ! X

  0.500  0.000  0.000   ! X
  0.500  0.500  0.000   ! M
```

### DOS ISMEAR=-5 KPOINTS

Tetrahedron method needs a uniform **Monkhorst-Pack** mesh:

```
Automatic mesh
0
Monkhorst-Pack
4  4  4
0. 0. 0.
```

Minimum 4×4×4; use 6×6×6 or denser for smooth DOS features.

---

## Auto-detection

| Feature | Elements | Effect |
|---------|----------|--------|
| Magnetic | Fe Co Ni Mn Cr V Cu Mo W Gd Eu Nd | ISPIN=2, MAGMOM per element |
| Heavy (SOC) | Bi Pb Tl Hg Au Pt Ir Os Re W Ta Hf La–Lu | Enables SOC for SOC/band workflows; ISYM=-1 and collinear MAGMOM is removed |
| LDA+U | Fe Co Ni Mn Cr V Cu Mo W Ce Gd | LDAU=.TRUE.; d elements use LDAUL=2, Ce/Gd use LDAUL=3 and LMAXMIX=6 |
