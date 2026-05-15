#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  VASP Tools Suite  ·  vasptools.sh
#  Usage: bash vasptools.sh
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INCAR_GEN="$SCRIPT_DIR/incar_gen.py"
POTCAR_GEN="$SCRIPT_DIR/potcar/potcar_gen.py"
MODULE14_SCRIPT="$SCRIPT_DIR/pbs/jobscript.sh"
BADER_SCRIPT="$SCRIPT_DIR/utils/bader.py"

# ── Colours ──────────────────────────────────────────────────────────────────
if [ -t 1 ] && command -v tput &>/dev/null && tput colors &>/dev/null; then
    CY='\033[0;36m'   # cyan
    GR='\033[0;32m'   # green
    YL='\033[1;33m'   # yellow
    RD='\033[0;31m'   # red
    DM='\033[2m'      # dim
    BD='\033[1m'      # bold
    RS='\033[0m'      # reset
else
    CY=''; GR=''; YL=''; RD=''; DM=''; BD=''; RS=''
fi

# ── Helpers ───────────────────────────────────────────────────────────────────
banner() {
    clear
    echo -e "${CY}${BD}"
    echo "  ╔══════════════════════════════════════════════╗"
    echo "  ║          VASP  Tools  Suite                  ║"
    echo "  ║          github: vasp-incar-generator        ║"
    echo "  ╚══════════════════════════════════════════════╝"
    echo -e "${RS}"
}

pause() { echo; read -rp "  Press Enter to continue..."; }

item()  { echo -e "    ${GR}$1${RS}  $2"; }        # green number, description
stub()  { echo -e "    ${DM}$1  $2  [coming soon]${RS}"; }  # dimmed placeholder
sep()   { echo -e "    ${DM}────────────────────────────────${RS}"; }

if [[ -f "$MODULE14_SCRIPT" ]]; then
    source "$MODULE14_SCRIPT"
else
    echo -e "  ${RD}[ERROR]${RS} Missing module 14 script: $MODULE14_SCRIPT"
    exit 1
fi

# ── Check python ──────────────────────────────────────────────────────────────
check_python() {
    if ! command -v python3 &>/dev/null; then
        echo -e "  ${RD}[ERROR]${RS} python3 not found. Please install Python 3."
        exit 1
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
        echo -e "  ${BD}12  KPOINTS Generator${RS}"
        sep
        item 21 "Generate KPOINTS  (reads INCAR, writes KPOINTS next to it)"
        echo
        item  0 "Back to main menu"
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
             *) echo -e "  ${RD}Unknown option.${RS}"; sleep 1 ;;
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
#  MODULE 15 ── VASP Utility Tools
# ─────────────────────────────────────────────────────────────────────────────

vasp_tool_status() {
    banner
    echo -e "  ${BD}VASP Quick Status${RS}"
    sep

    if [[ ! -f OUTCAR && ! -f OSZICAR ]]; then
        echo -e "  ${RD}[ERROR]${RS} OUTCAR/OSZICAR not found in current directory."
        pause
        return
    fi

    if [[ -f OUTCAR ]]; then
        if grep -q "reached required accuracy" OUTCAR; then
            echo -e "  Electronic convergence: ${GR}YES${RS}"
        else
            echo -e "  Electronic convergence: ${YL}NOT FOUND${RS}"
        fi

        toten=$(awk '/free  energy   TOTEN/{e=$5} END{print e}' OUTCAR)
        [[ -n "$toten" ]] && echo "  Final TOTEN (OUTCAR): $toten eV"
    fi

    if [[ -f OSZICAR ]]; then
        last_line=$(tail -n 1 OSZICAR)
        e0=$(awk 'END{for(i=1;i<=NF;i++) if($i=="E0=") {print $(i+1); exit}}' OSZICAR)
        [[ -n "$e0" ]] && echo "  Final E0 (OSZICAR):   $e0 eV"
        [[ -n "$last_line" ]] && echo "  Last OSZICAR line:    $last_line"
    fi

    pause
}

vasp_tool_backup_results() {
    banner
    echo -e "  ${BD}Backup Key VASP Files${RS}"
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

    echo -e "  ${GR}[OK]${RS} Backup folder: ${BD}$bdir${RS}"
    echo "  Copied items: $copied"
    pause
}

vasp_tool_clean_outputs() {
    banner
    echo -e "  ${BD}Clean VASP Outputs${RS}"
    sep
    echo -e "  ${YL}[WARN]${RS} This will remove common large output files in current directory."
    read -rp "  Type 'yes' to continue: " confirm
    [[ "$confirm" != "yes" ]] && { echo "  Canceled."; pause; return; }

    outputs=(
        CHG CHGCAR DOSCAR EIGENVAL ELFCAR IBZKPT LOCPOT
        OSZICAR OUTCAR PCDAT PROCAR REPORT vasprun.xml
        WAVECAR XDATCAR AECCAR0 AECCAR1 AECCAR2 BSEFATBAND
    )

    removed=0
    for f in "${outputs[@]}"; do
        if [[ -e "$f" ]]; then
            rm -rf "$f"
            removed=$((removed + 1))
        fi
    done

    echo -e "  ${GR}[OK]${RS} Removed items: $removed"
    pause
}

vasp_tool_bader() {
    banner
    echo -e "  ${BD}Bader Charge Transfer Analysis${RS}"
    sep
    read -rp "  Work directory [.]: " wdir
    wdir="${wdir:-.}"
    python3 "$BADER_SCRIPT" "$wdir"
    pause
}

utility_menu() {
    while true; do
        banner
        echo -e "  ${BD}15  VASP Utility Tools${RS}"
        sep
        item 51 "Quick status (convergence + final energy)"
        item 53 "Backup key VASP files"
        item 54 "Clean large VASP output files"
        item 55 "Bader charge transfer analysis"
        echo
        item  0 "Back to main menu"
        echo
        read -rp "  Enter option: " opt
        case "$opt" in
            51) vasp_tool_status ;;
            53) vasp_tool_backup_results ;;
            54) vasp_tool_clean_outputs ;;
            55) vasp_tool_bader ;;
             0) return ;;
             *) echo -e "  ${RD}Unknown option.${RS}"; sleep 1 ;;
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
        echo -e "  ${BD}Main Menu${RS}"
        sep
        item 11 "INCAR Generator        (interactive TUI)"
        item 12 "KPOINTS Generator      (writes KPOINTS file)"
        item 13 "POTCAR Selector        (MP PAW-PBE, from POSCAR)"
        item 14 "Job Script Generator   (PBS only)"
        item 15 "VASP Utility Tools     (status/backup/clean)"
        echo
        item  0 "Exit"
        echo
        read -rp "  Enter option: " opt
        case "$opt" in
            11) incar_interactive ;;
            12) kpoints_menu ;;
            13) potcar_interactive ;;
            14) jobscript_menu ;;
            15) utility_menu ;;
             0) echo -e "\n  ${CY}Goodbye!${RS}\n"; exit 0 ;;
             *) echo -e "  ${RD}Unknown option.${RS}"; sleep 1 ;;
        esac
    done
}

main_menu
