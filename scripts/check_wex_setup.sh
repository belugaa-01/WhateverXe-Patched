#!/bin/bash
# check_wex_setup.sh — read-only setup checker for the unofficial WhateverXe patch set.
# Changes nothing, collects no serials/MLB/ROM/UUID. Usage: bash check_wex_setup.sh
pass=0; warn=0; fail=0
ok()  { echo "  [ OK ] $1"; pass=$((pass+1)); }
bad() { echo "  [FAIL] $1"; [ -n "${2:-}" ] && echo "         -> $2"; fail=$((fail+1)); }
wr()  { echo "  [WARN] $1"; [ -n "${2:-}" ] && echo "         -> $2"; warn=$((warn+1)); }
IGPU=$(ioreg -r -n IGPU -l -w0 2>/dev/null)   # subtree rooted at the GPU only (not its PCI neighbours)
prop() { printf '%s\n' "$IGPU" | grep -m1 "\"$1\" = " | sed 's/.*" = //'; }
echo "== System =="; sw_vers | sed 's/^/  /'; echo "  CPU: $(sysctl -n machdep.cpu.brand_string 2>/dev/null)"
echo; echo "== GPU =="
did=$(prop device-id | tr -d '<>')
if [ ${#did} -ge 4 ]; then echo "  GPU device ID: 0x$(echo ${did:2:2}${did:0:2} | tr a-f A-F)"; else bad "No IGPU device found in the registry" "Is this the right machine / is the GPU visible?"; fi
rid=$(prop revision-id | tr -d '<>'); [ ${#rid} -ge 2 ] && echo "  Revision: 0x$(echo ${rid:0:2} | tr a-f A-F)"
echo; echo "== Boot arguments =="
ba=$(nvram boot-args 2>/dev/null | cut -f2-)
echo "  boot-args: ${ba:-<none>}"
case " $ba " in *" -allow3d "*) ok "-allow3d present";; *) bad "-allow3d missing" "Add it to boot-args";; esac
case " $ba " in *" -disablegfxfirmware "*) ok "-disablegfxfirmware present";; *) bad "-disablegfxfirmware missing" "Add it to boot-args";; esac
echo; echo "== Kexts =="
K=$(kmutil showloaded --list-only 2>/dev/null)
echo "$K" | grep -q "as.vit9696.Lilu" && ok "Lilu loaded" || bad "Lilu not loaded" "Check Kernel > Add order and that the file exists"
echo "$K" | grep -q "org.b00t0x.WhateverXe " && ok "WhateverXe loaded" || { echo "$K" | grep -q "org.b00t0x.WhateverXe" && ok "WhateverXe loaded" || bad "WhateverXe not loaded" "Kernel > Add: Lilu, AMFIPass (Mod), WhateverXe, in that order"; }
echo "$K" | grep -q "org.b00t0x.AppleIntelTGLCompat" && ok "AppleIntelTGLCompat loaded" || wr "AppleIntelTGLCompat not loaded" "Normal before the Graphics package is installed"
echo "$K" | grep -q "as.vit9696.WhateverGreen" && bad "WhateverGreen is loaded" "Remove it; it must not be used with WhateverXe"
echo "$K" | grep -qi "amfipass" && ok "AMFIPass loaded" || wr "AMFIPass not detected by name" "Use the Mod build; the bundle name may differ"
echo "$K" | grep -q "AppleIntelTGLGraphicsFramebuffer" && ok "Apple TGL framebuffer kext loaded" || wr "Apple TGL framebuffer kext not loaded" "Install the Graphics package and reboot"
pk=$(pkgutil --pkgs 2>/dev/null | grep -i -E "whateverxe|b00t0x")
[ -n "$pk" ] && ok "Graphics package receipts: $(echo $pk | tr '\n' ' ')" || bad "No WhateverXe Graphics package receipt" "Install the Graphics package (use the latest release) and reboot"
echo; echo "== Plugin gate (IGPU) =="
for k in N97Admission N97GTTopologyReady N97NativePreflight N97NativeStartAllowed WEXDisplay13BootReady; do
  v=$(prop $k); [ "$v" = "Yes" ] && ok "$k = Yes" || bad "$k = ${v:-<missing>}" "See troubleshooting in the README; send this output with your report"
done
br=$(prop N97NativeBlockReason | tr -d '<>')
if [ ${#br} -ge 128 ]; then
  le() { local h=$1 r="" i; for ((i=${#h}-2;i>=0;i-=2)); do r+=${h:i:2}; done; echo $((16#$r)); }
  mask=$(le ${br:16:16}); lp=$(le ${br:32:16})
  if [ "$mask" -eq 0 ]; then ok "Plugin recorded no blocking reason"; else
    echo "  Plugin block-reason mask: $(printf '0x%X' $mask)  (boot-display check status: $lp)"
    explain() { [ $(( (mask>>$1)&1 )) -eq 1 ] && bad "$2" "$3"; }
    explain 0  "GPU memory aperture (BAR2) not found" "Check Above-4G / BAR settings in firmware"
    explain 1  "Aperture is not 256 MB" "Resizable BAR may have changed the BAR size; the plugin requires 256 MB"
    explain 2  "System page size is not 4096" "Unexpected; report this"
    explain 3  "IOMapper is active" "Turn VT-d off or set Kernel > Quirks > DisableIoMapper = true"
    explain 4  "PCI memory-space/bus-master not both enabled" "Firmware left the GPU disabled; report your firmware version"
    explain 5  "-allow3d missing" "Add it to boot-args"
    explain 6  "-disablegfxfirmware missing" "Add it to boot-args"
    explain 7  "-wex-adln-scanout is set" "Remove this experimental boot-arg"
    explain 8  "-wex-adln-gpu is set" "Remove this experimental boot-arg"
    explain 16 "Boot display (panel) state not accepted" "The firmware screen state differs from what the plugin accepts; share this report"
    explain 17 "GPU topology / eDRAM check failed" "Share your report; GPU readout is in N97GTReadout"
  fi
else wr "No N97NativeBlockReason property" "Older kext, or built without the optional diagnostic"; fi
bs=$(prop N97NativeBootSource | tr -d '<>')
if [ -n "$bs" ] && [ ${#bs} -ge 32 ]; then
  st=$((16#${bs:30:2}${bs:28:2}${bs:26:2}${bs:24:2}))
  names=(NotAdmitted Ready Success NotSingleHDMI NotLinearFHD OtherPlaneActive StateChanged NoVblank DisableTimeout EnableTimeout RollbackFailed InvalidDPSource InvalidTCSource)
  echo "  boot-display check status: $st (${names[$st]:-unknown}) [numbering of 0.6.1; 1 = Ready]"
fi
ma=$(prop N97NativeMapperAdmission | tr -d '<>')
if [ -n "$ma" ] && [ ${#ma} -ge 64 ]; then
  [ "${ma:48:16}" = "0100000000000000" ] && ok "IOMapper not in use (VT-d handled)" || bad "IOMapper looks active" "Turn VT-d off in firmware or set Kernel > Quirks > DisableIoMapper = true"
fi
ggc=$(prop N97GGC)
if [ -n "$ggc" ] && [ "$ggc" -eq "$ggc" ] 2>/dev/null; then
  gms=$(( (ggc>>8)&255 ))
  if [ $gms -ge 240 ] && [ $gms -le 254 ]; then mb=$(( (gms-240+1)*4 )); echo "  Firmware DVMT pre-allocation: ${mb} MB (GMS field $(printf '0x%X' $gms))"
    if [ $mb -eq 60 ]; then
      printf '%s\n' "$IGPU" | grep -q '"framebuffer-stolenmem"' && ok "framebuffer-stolenmem property present" || bad "framebuffer-stolenmem missing" "60 MB DVMT needs framebuffer-patch-enable=01000000 and framebuffer-stolenmem=0000C003"
      case " $ba " in *" -igfxdvmt "*) ok "-igfxdvmt present";; *) bad "-igfxdvmt missing" "Needed together with the DVMT properties for 60 MB";; esac
    else wr "DVMT is ${mb} MB, not 60 MB" "The README values are for 60 MB; see upstream's README for other sizes"; fi
  else echo "  Firmware DVMT: GMS field $(printf '0x%X' $gms) (not in the common range)"; fi
fi
echo; echo "== Metal and brightness =="
system_profiler SPDisplaysDataType 2>/dev/null | grep -q "Metal Support: Metal" && ok "$(system_profiler SPDisplaysDataType | grep -m1 'Metal Support' | sed 's/^ *//')" || bad "Metal not reported" "The native driver did not start; see the gate checks above"
uid=$(ioreg -n PNLF -r -l 2>/dev/null | grep -m1 '"_UID"' | sed 's/.*= //' | tr -d '"')
if [ -n "$uid" ]; then [ "$uid" = "19" ] && ok "PNLF _UID = 19" || bad "PNLF _UID = $uid" "The brightness profile needs _UID 19; regenerate SSDT-PNLF"; else wr "No PNLF device found" "Needed for brightness on laptops; see README step 4"; fi
echo; echo "Summary: $pass OK, $warn warnings, $fail failures."
[ $fail -gt 0 ] && echo "Fix the [FAIL] lines first; if all else looks right, run collect_wex_report.sh and share the zip."
exit 0
