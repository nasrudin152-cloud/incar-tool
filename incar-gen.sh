#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  VASP Tools Suite  ·  incar-gen.sh
#  Usage: bash incar-gen.sh   or   incar-gen  (via alias)
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INCAR_GEN="$SCRIPT_DIR/incar_gen.py"
POTCAR_GEN="$SCRIPT_DIR/potcar/potcar_gen.py"
MODULE14_SCRIPT="$SCRIPT_DIR/pbs/jobscript.sh"
BADER_SCRIPT="$SCRIPT_DIR/utils/bader.py"
VERSION="1.0"

# ── Colours ───────────────────────────────────────────────────────────────────
if [ -t 1 ] && command -v tput &>/dev/null && tput colors &>/dev/null 2>&1; then
    CY='\033[0;36m'   # cyan
    GR='\033[0;32m'   # green
    YL='\033[1;33m'   # yellow
    RD='\033[0;31m'   # red
    DM='\033[2m'      # dim
    BD='\033[1m'      # bold
    RS='\033[0m'      # reset
    BL='\033[0;34m'   # blue
else
    CY=''; GR=''; YL=''; RD=''; DM=''; BD=''; RS=''; BL=''
fi

# ── Helpers ───────────────────────────────────────────────────────────────────
banner() {
    clear
    echo -e "${CY}${BD}  ╔══════════════════════════════════════════════╗${RS}"
    echo -e "${CY}${BD}  ║        VASP  Tools  Suite  v${VERSION}              ║${RS}"
    echo -e "${CY}${BD}  ║        github: nasrudin152-cloud/incar-tool  ║${RS}"
    echo -e "${CY}${BD}  ╚══════════════════════════════════════════════╝${RS}"
    echo -e "  ${DM}  dir: $(pwd)${RS}"
    echo
}

pause() { echo; read -rp "  Press Enter to continue..."; }

# item <number> <description>  — fixed-width number column
item() { printf "    ${GR}%-4s${RS}  %s\n" "$1" "$2"; }
sep()  { echo -e "  ${DM}  ──────────────────────────────────────${RS}"; }

# ── Check python ──────────────────────────────────────────────────────────────
check_python() {
    if ! command -v python3 &>/dev/null; then
        echo -e "  ${RD}[ERROR]${RS} python3 not found. Please install Python 3."
        exit 1
    fi
}

# ── Lazy-load module 14 ───────────────────────────────────────────────────────
load_module14() {
    if [[ -f "$MODULE14_SCRIPT" ]]; then
        # shellcheck source=/dev/null
        source "$MODULE14_SCRIPT"
    else
        echo -e "  ${RD}[ERROR]${RS} Missing PBS module: $MODULE14_SCRIPT"
        pause
        return 1
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
#  MODULE 11 ── INCAR Generator
# ─────────────────────────────────────────────────────────────────────────────

incar_interactive() {
    python3 "$INCAR_GEN" -i
    pause
}

# ─────────────────────────────────────────────────────────────────────────────
#  MODULE 12 ── KPOINTS Generator
# ─────────────────────────────────────────────────────────────────────────────

kpoints_menu() {
    while true; do
        banner
        echo -e "  ${BD}  12  KPOINTS Generator${RS}"
        sep
        item 21 "Generate KPOINTS  (reads INCAR, writes KPOINTS next to it)"
        echo
        item  0  "Back to main menu"
        echo
        read -rp "  Enter option: " opt
        case "$opt" in
            21)
                read -rp "  INCAR path [INCAR]: " ipath
                ipath="${ipath:-INCAR}"
                python3 "$INCAR_GEN" -k "$ipath"
                pause
                ;;
             0) return ;;
             *) echo -e "  ${RD}  Unknown option.${RS}"; sleep 1 ;;
        esac
    done
}

# ─────────────────────────────────────────────────────────────────────────────
#  MODULE 13 ── POTCAR Selector
# ─────────────────────────────────────────────────────────────────────────────

potcar_interactive() {
    python3 "$POTCAR_GEN"
    pause
}

# ─────────────────────────────────────────────────────────────────────────────
#  MODULE 14 ── PBS Job Script Generator
# ─────────────────────────────────────────────────────────────────────────────

pbs_menu() {
    load_module14 || return
    jobscript_menu
}

# ─────────────────────────────────────────────────────────────────────────────
#  MODULE 15 ── VASP Utility Tools
# ─────────────────────────────────────────────────────────────────────────────

vasp_tool_status() {
    banner
    echo -e "  ${BD}  51  VASP Quick Status${RS}"
    sep

    if [[ ! -f OUTCAR && ! -f OSZICAR ]]; then
        echo -e "  ${RD}  [ERROR]${RS} OUTCAR / OSZICAR not found in current directory."
        pause
        return
    fi

    if [[ -f OUTCAR ]]; then
        if grep -q "reached required accuracy" OUTCAR; then
            echo -e "  Electronic convergence : ${GR}YES${RS}"
        else
            echo -e "  Electronic convergence : ${YL}NOT FOUND${RS}"
        fi
        toten=$(awk '/free  energy   TOTEN/{print $(NF-1)}' OUTCAR | tail -1)
        [[ -n "$toten" ]] && echo -e "  Final TOTEN (OUTCAR)   : ${BD}$toten eV${RS}"
    fi

    if [[ -f OSZICAR ]]; then
        e0=$(grep -oP 'E0=\s*\K[-\d.E+]+' OSZICAR | tail -1)
        last_line=$(tail -n 1 OSZICAR)
        [[ -n "$e0" ]]        && echo -e "  Final E0   (OSZICAR)   : ${BD}$e0 eV${RS}"
        [[ -n "$last_line" ]] && echo -e "  Last OSZICAR line      : ${DM}$last_line${RS}"
    fi

    pause
}

vasp_tool_backup_results() {
    banner
    echo -e "  ${BD}  53  Backup Key VASP Files${RS}"
    sep

    bdir="vasp_backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$bdir"

    files=(
        INCAR POSCAR CONTCAR KPOINTS POTCAR
        OUTCAR OSZICAR XDATCAR vasprun.xml
        CHGCAR WAVECAR DOSCAR EIGENVAL PROCAR
        vasp.pbs
    )

    copied=0
    for f in "${files[@]}"; do
        if [[ -e "$f" ]]; then
            cp -r "$f" "$bdir/"
            copied=$((copied + 1))
        fi
    done

    echo -e "  ${GR}  [OK]${RS} Backup folder : ${BD}$bdir${RS}"
    echo    "         Copied items  : $copied"
    pause
}

vasp_tool_clean_outputs() {
    banner
    echo -e "  ${BD}  54  Clean VASP Outputs${RS}"
    sep

    # 找出当前目录中实际存在的目标文件
    outputs=(
        CHG CHGCAR DOSCAR EIGENVAL ELFCAR IBZKPT LOCPOT
        OSZICAR OUTCAR PCDAT PROCAR REPORT vasprun.xml
        WAVECAR XDATCAR AECCAR0 AECCAR1 AECCAR2 BSEFATBAND
    )

    existing=()
    for f in "${outputs[@]}"; do
        [[ -e "$f" ]] && existing+=("$f")
    done

    if [[ ${#existing[@]} -eq 0 ]]; then
        echo -e "  ${DM}  Nothing to clean in $(pwd).${RS}"
        pause
        return
    fi

    echo -e "  ${YL}  [WARN]${RS} The following files will be removed:"
    echo
    for f in "${existing[@]}"; do
        echo -e "    ${DM}·${RS} $f"
    done
    echo
    echo -e "  To ${BD}exclude${RS} files, enter their names separated by spaces."
    echo -e "  Press ${BD}Enter${RS} to delete all listed files, or type ${BD}cancel${RS} to abort."
    echo
    read -rp "  Exclude (e.g. OUTCAR OSZICAR): " exclude_input

    [[ "${exclude_input,,}" == "cancel" ]] && { echo -e "  ${DM}  Canceled.${RS}"; pause; return; }

    # 构建排除集合
    declare -A exclude_set
    for item in $exclude_input; do
        exclude_set["$item"]=1
    done

    removed=0
    skipped=0
    for f in "${existing[@]}"; do
        if [[ -n "${exclude_set[$f]+_}" ]]; then
            echo -e "  ${DM}  skipped : $f${RS}"
            skipped=$((skipped + 1))
        else
            rm -rf "$f"
            echo -e "  ${RD}  removed : $f${RS}"
            removed=$((removed + 1))
        fi
    done

    echo
    echo -e "  ${GR}  [OK]${RS} Removed: ${BD}$removed${RS}  |  Skipped: ${BD}$skipped${RS}"
    pause
}

vasp_tool_bader() {
    banner
    echo -e "  ${BD}  55  Bader Charge Transfer Analysis${RS}"
    sep
    read -rp "  Work directory [.]: " wdir
    wdir="${wdir:-.}"
    if [[ ! -d "$wdir" ]]; then
        echo -e "  ${RD}  [ERROR]${RS} Directory not found: $wdir"
        pause
        return
    fi
    python3 "$BADER_SCRIPT" "$wdir"
    pause
}

utility_menu() {
    while true; do
        banner
        echo -e "  ${BD}  15  VASP Utility Tools${RS}"
        sep
        item 51 "Quick status  (convergence + final energy)"
        item 53 "Backup key VASP files"
        item 54 "Clean large VASP output files"
        item 55 "Bader charge transfer analysis"
        echo
        item  0  "Back to main menu"
        echo
        read -rp "  Enter option: " opt
        case "$opt" in
            51) vasp_tool_status ;;
            53) vasp_tool_backup_results ;;
            54) vasp_tool_clean_outputs ;;
            55) vasp_tool_bader ;;
             0) return ;;
             *) echo -e "  ${RD}  Unknown option.${RS}"; sleep 1 ;;
        esac
    done
}

# ─────────────────────────────────────────────────────────────────────────────
#  MAIN MENU
# ─────────────────────────────────────────────────────────────────────────────

main_menu() {
    check_python
    while true; do
        banner
        echo -e "  ${BD}  Main Menu${RS}"
        sep
        item 11 "INCAR Generator        (interactive TUI)"
        item 12 "KPOINTS Generator      (writes KPOINTS file)"
        item 13 "POTCAR Selector        (MP PAW-PBE, from POSCAR)"
        item 14 "Job Script Generator   (PBS)"
        item 15 "VASP Utility Tools     (status / backup / clean / bader)"
        echo
        item  0  "Exit"
        echo
        read -rp "  Enter option: " opt
        case "$opt" in
            11) incar_interactive ;;
            12) kpoints_menu ;;
            13) potcar_interactive ;;
            14) pbs_menu ;;
            15) utility_menu ;;
             0) echo -e "\n  ${CY}${BD}  Goodbye!${RS}\n"; exit 0 ;;
             *) echo -e "  ${RD}  Unknown option.${RS}"; sleep 1 ;;
        esac
    done
}

main_menu
