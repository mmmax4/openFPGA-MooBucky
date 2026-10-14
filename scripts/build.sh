#!/bin/bash
# Native, single-process Quartus flow using the existing installed toolchain.
set -euo pipefail
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
quartus_dir=${QUARTUS_BIN:-/opt/intelFPGA_lite/21.1/quartus/bin}
mode=${1:-compile}
mkdir -p "$root/evidence"
cd "$root/core/projects"
case "$mode" in
    compile) "$quartus_dir/quartus_sh" --flow compile moomesa_pocket.qpf ;;
    map) "$quartus_dir/quartus_map" moomesa_pocket --read_settings_files=on --write_settings_files=off ;;
    refit)
        # Reuse mapped netlist after a fitter-only setting change. Reassemble
        # and analyze every corner; never reuse the earlier bitstream/timing.
        "$quartus_dir/quartus_fit" moomesa_pocket --read_settings_files=on --write_settings_files=off
        "$quartus_dir/quartus_asm" moomesa_pocket --read_settings_files=on --write_settings_files=off
        "$quartus_dir/quartus_sta" moomesa_pocket --do_report_timing
        ;;
    *) echo "usage: bash scripts/build.sh [compile|map|refit]" >&2; exit 2 ;;
esac
