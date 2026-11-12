#!/bin/bash
# Collects a privacy-filtered diagnostic report for the unofficial WhateverXe patch set.
# It does NOT dump the full IORegistry, SMBIOS, serials, MLB, ROM or iMessage keys.
# Usage:  bash collect_wex_report.sh      (creates ~/Desktop/wex_report_<date>.zip)
set -u
ts=$(date +%Y%m%d_%H%M%S)
dir="$HOME/Desktop/wex_report_$ts"
mkdir -p "$dir"
{ sw_vers; echo "cpu: $(sysctl -n machdep.cpu.brand_string)"; echo "model: $(sysctl -n hw.model)"; echo "ram_bytes: $(sysctl -n hw.memsize)"; uname -v; } > "$dir/os.txt" 2>&1
nvram boot-args > "$dir/boot_args.txt" 2>&1
kmutil showloaded 2>/dev/null | grep -iE "WhateverXe|TGL|Lilu|AMFIPass|IOAccelerator|AppleIntel" | cut -c1-200 > "$dir/kexts.txt"
pkgutil --pkgs 2>/dev/null | grep -iE "whateverxe|b00t0x" > "$dir/packages.txt"
# IGPU identity and plugin gate flags (simple values only)
ioreg -l -w0 -n IGPU 2>/dev/null | grep -E '"(device-id|revision-id|vendor-id|model|fw-dvmt-gms-field-value)"|"(N97|WEX|WhateverXe|TGL)[A-Za-z0-9_]*" = (Yes|No|[0-9]+$|"[^"]*"$)' | cut -c1-200 > "$dir/igpu_flags.txt"
# A few short plugin records (hex, truncated)
ioreg -l -w0 2>/dev/null | grep -E '"(N97FBFirstResourceFault|N97FBFirstPowerError|N97NativeBootSource|N97FBBootHandoffCheck|N97FBMailbox)"' | cut -c1-420 > "$dir/plugin_records.txt"
system_profiler SPDisplaysDataType > "$dir/displays.txt" 2>&1
ioreg -n PNLF -r -l 2>/dev/null | head -40 > "$dir/pnlf.txt"
# GPU error signatures in the current boot's kernel log (first 200 lines)
log show --last boot --info --debug --predicate 'processID == 0' 2>/dev/null | grep -i -E "hardware error|GPURestart|IGFB.*ERROR|IGPU.*(fail|error)|panic" | cut -c1-260 | head -200 > "$dir/gpu_errors.txt"
ls -t /Library/Logs/DiagnosticReports 2>/dev/null | head -10 > "$dir/crash_report_names.txt"
cat > "$dir/WHAT_I_WAS_DOING.txt" <<'NOTE'
Describe the bug here: what you were doing, how long after boot, what you saw (freeze, black screen, lag).
NOTE
( cd "$HOME/Desktop" && zip -qr "wex_report_$ts.zip" "wex_report_$ts" )
echo "Done. Edit $dir/WHAT_I_WAS_DOING.txt if you like, re-zip, then send: $HOME/Desktop/wex_report_$ts.zip"
echo "Please check the files contain no private data before sharing."
