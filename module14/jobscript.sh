generate_pbs_script() {
    banner
    echo -e "  ${BD}14  Generate PBS script (PBS only)${RS}"
    sep

    read -rp "  System name for #PBS -N [your-sys]: " sys_name
    sys_name="${sys_name:-your-sys}"

    if command -v pestat &>/dev/null; then
        echo
        pestat
        echo
    else
        echo -e "  ${YL}[WARN]${RS} pestat not found. Please input node manually."
    fi

    # --- Queue selection ---
    echo -e "  ${BD}Available queues:${RS}"
    echo -e "  ┌────────┬──────────┬────────────────────┬─────┬───────┐"
    echo -e "  │ No.    │ Queue    │ Walltime           │ PPN │ State │"
    echo -e "  ├────────┼──────────┼────────────────────┼─────┼───────┤"
    echo -e "  │  1     │ debug    │ 30 min             │  4  │ OPEN  │"
    echo -e "  │  2     │ short    │ 2 hours            │ 32  │ CLOSE │"
    echo -e "  │  3     │ normal   │ 72 hours (3 days)  │ 48  │ OPEN  │"
    echo -e "  │  4     │ fat      │ 1680 hours (70 d)  │ 64  │ OPEN  │"
    echo -e "  │  5     │ long     │ 720 hours (30 d)   │ 96  │ OPEN  │"
    echo -e "  └────────┴──────────┴────────────────────┴─────┴───────┘"
    echo

    read -rp "  Select queue [1-5, default 3 (normal)]: " queue_choice
    queue_choice="${queue_choice:-3}"

    case "$queue_choice" in
        1)
            queue_name="debug"
            ppn=4
            walltime="00:30:00"
            ;;
        2)
            queue_name="short"
            ppn=32
            walltime="02:00:00"
            echo -e "  ${YL}[WARN]${RS} Queue 'short' is currently CLOSED!"
            ;;
        3)
            queue_name="normal"
            ppn=48
            walltime="72:00:00"
            ;;
        4)
            queue_name="fat"
            ppn=64
            walltime="1680:00:00"
            ;;
        5)
            queue_name="long"
            ppn=96
            walltime="720:00:00"
            ;;
        *)
            echo -e "  ${YL}[WARN]${RS} Invalid choice, fallback to normal queue."
            queue_name="normal"
            ppn=48
            walltime="72:00:00"
            ;;
    esac

    echo -e "  ${GR}[INFO]${RS} Queue: ${BD}$queue_name${RS} | PPN: ${BD}$ppn${RS} | Walltime: ${BD}$walltime${RS}"
    echo

    # --- Node selection ---
    read -rp "  Node [1=default, or enter node number e.g. 24 -> node24.hpc.local]: " node_input
    node_input="${node_input:-1}"
    if ! [[ "$node_input" =~ ^[0-9]+$ ]]; then
        echo -e "  ${YL}[WARN]${RS} Invalid input, fallback to nodes=1"
        node_value="1"
    elif [[ "$node_input" == "1" ]]; then
        node_value="1"
    else
        node_value="node${node_input}.hpc.local"
    fi

    # --- VASP binary selection ---
    read -rp "  VASP binary type [std/gam, default std]: " vasp_type
    case "${vasp_type,,}" in
        ""|std) vasp_bin="vasp_std" ;;
        gam)    vasp_bin="vasp_gam" ;;
        *)
            echo -e "  ${YL}[WARN]${RS} Unknown choice, fallback to std."
            vasp_bin="vasp_std"
            ;;
    esac

    # --- Output file ---
    read -rp "  Output PBS file [vasp.pbs]: " pbs_out
    pbs_out="${pbs_out:-vasp.pbs}"

    cat > "$pbs_out" <<EOF
#!/bin/bash
#PBS -N $sys_name
#PBS -l nodes=$node_value:ppn=$ppn
#PBS -l walltime=$walltime
#PBS -q $queue_name
#PBS -j oe
cd \$PBS_O_WORKDIR

source /opt/modules/module.sh
module load vasp/6.3.2-all-intel2022.2
#module load vasp/5.4.4-all-intel17.5

mpirun -np $ppn $vasp_bin
EOF

    chmod +x "$pbs_out"
    echo -e "\n  ${GR}[OK]${RS} PBS script written to: ${BD}$pbs_out${RS}"
    pause
}

jobscript_menu() {
    generate_pbs_script
}
