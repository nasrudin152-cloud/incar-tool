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

    read -rp "  Node number [24] (will use node<number>.hpc.local): " node_num
    node_num="${node_num:-24}"
    if [[ "$node_num" =~ ^[0-9]+$ ]]; then
        node_name="node${node_num}.hpc.local"
    else
        echo -e "  ${YL}[WARN]${RS} Invalid number, fallback to node24.hpc.local"
        node_name="node24.hpc.local"
    fi

    read -rp "  Core count ppn / mpirun -np [48]: " ppn
    ppn="${ppn:-48}"

    read -rp "  VASP binary type [std/gam, default std]: " vasp_type
    case "${vasp_type,,}" in
        ""|std) vasp_bin="vasp_std" ;;
        gam)    vasp_bin="vasp_gam" ;;
        *)
            echo -e "  ${YL}[WARN]${RS} Unknown choice, fallback to std."
            vasp_bin="vasp_std"
            ;;
    esac

    read -rp "  Output PBS file [vasp.pbs]: " pbs_out
    pbs_out="${pbs_out:-vasp.pbs}"

    cat > "$pbs_out" <<EOF
#!/bin/bash
#PBS -N $sys_name
#PBS -l nodes=$node_name:ppn=$ppn
#PBS -l walltime=9999:59:59
#PBS -q batch
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
