# Patched WhateverXe for 12th/13th-gen Intel Xe-LP iGPUs (Alder Lake / Raptor Lake laptops) — unofficial patch set

> **Status: experimental pre-release, tested on one machine.**
> Metal works on the tested laptop, but there are known issues (see [Known issues](#known-issues-and-untested-features)).
> Keep a working backup of your EFI folder before trying anything here.
> So far it has been **verified only on an Alder Lake-U Core i3-1215U (`0x46B3`)**; other chips in the 12th/13th-gen Xe-LP family are untested (see [Compatibility](#compatibility)).

> **Warning — do not update Safari together with macOS updates.**
> In the tester's experience, updating Safari along with macOS updates introduces **more video-playback errors**.
> Stay on the macOS/Safari version you have verified, turn off automatic installs
> (System Settings → General → Software Update → ⓘ → turn off **Install macOS updates** and
> **Install Security Responses and system files**), and re-test video after any update.
> This is a precaution based on one tester's observation, not a fully diagnosed cause.

This is an unofficial community patch set on top of
[b00t0x/WhateverXe](https://github.com/b00t0x/WhateverXe) 0.6.1 (commit `68a2427`).
It is **not affiliated with or endorsed by the upstream author**. All driver work is upstream's;
this repository only adjusts two checks so a laptop with a 6-bit internal eDP panel can start the native
graphics driver on 12th/13th-gen Xe-LP (Display 13) laptop iGPUs. It has been verified on one Alder Lake-U machine only. Discussion: [Reddit thread](https://example.com/REPLACE-reddit-thread).

---

## Table of contents

0. [Important warnings](#important-warnings)
1. [What this fork changes](#what-this-fork-changes)
2. [Tested configuration](#tested-configuration)
3. [What you need to download](#what-you-need-to-download)
4. [Step-by-step setup](#step-by-step-setup)
5. [Verify it works](#verify-it-works)
6. [Troubleshooting](#troubleshooting)
7. [Known issues and untested features](#known-issues-and-untested-features)
8. [Compatibility](#compatibility)
9. [Build from source](#build-from-source)
10. [Reporting results](#reporting-results)
11. [Credits and license](#credits-and-license)

---

## Important warnings

| Warning | Details |
|---|---|
| **Do not update Safari with macOS updates** | In the tester's experience, updating Safari together with macOS updates introduces more video-playback errors. Turn off automatic installs of macOS updates and system files, and re-test video before and after any update |
| Experimental software | Verified on one machine. Sleep/wake and external displays are untested. A GPU hardware-error episode followed by a freeze was seen once |
| Keep a backup EFI | If a boot fails, restore your known-good EFI |
| Do not post private data | Never share your serial, MLB, ROM, SystemUUID or iMessage keys (blur them in screenshots) |

---

## What this fork changes

### What upstream 0.6.1 does not do on this hardware

On the tested machine the upstream plugin recognises the GPU (`0x46B3` is in its device table and is admitted),
but then **refuses to start the native driver**, so macOS stays on the firmware framebuffer:
7 MB VRAM, "No Kext Loaded", no Metal.

| # | What upstream 0.6.1 does | Why it blocks this machine | Observed symptom |
|---|---|---|---|
| 1 | Requires the firmware's boot display to use **8 bits per colour** (`TRANS_DDI_FUNC_CTL` bits 22:20 = 0) in `dpSource`, `linearPlan` and the framebuffer-memory `inspect` check | The tested panel runs at **6 bpc** (field value 2), so the boot handoff is rejected | `N97NativePreflight = No`, `N97NativeStartAllowed = No`, `WEXDisplay13BootReady = No` |
| 2 | `display13SSTPort()` requires the port object field at `+0x550` to equal `1` on Combo DDIs | The tested **eDP port object reports `0`** there, so the port is rejected and the DP adoption branch is skipped | Boot handoff ends `NotReady`, framebuffer start not accepted, accelerator never registers |

### What this fork adds

| Area | Upstream 0.6.1 | This fork |
|---|---|---|
| 6-bpc firmware eDP scanout | Rejected | **Accepted for eDP panels only** (8 bpc behaves as before; external DP and other depths are still rejected) |
| eDP port with `+0x550 == 0` on Combo DDI A/B | Rejected | **Accepted for panel ports only** (all other ports unchanged) |
| Native driver start on the tested machine | Blocked | **Starts** (`N97NativePreflight`, `N97NativeStartAllowed`, `WEXDisplay13BootReady` = Yes) |
| Accelerator / Metal | Not available | **Registers; System Information reports Metal 2** |
| CPU test coverage | — | Added a test for 6-bpc eDP in `tests/display13_linear_dp.cpp` |
| Hardware validation of Alder Lake-P/U eDP | Not tested on hardware (per upstream) | **Tested on one machine** (see below) |
| Everything else (GPU bring-up, display engine, Graphics package, Compat) | Upstream | **Unchanged** |

Neither upstream nor this fork has tested sleep/wake, external displays, or other chips (see [Known issues](#known-issues-and-untested-features)).

---

## Tested configuration

| Item | Value |
|---|---|
| CPU / GPU | Intel Core i3-1215U, Intel UHD Graphics, device ID `0x46B3`, revision `0x0C` |
| Machine | HP laptop (subsystem vendor `103C`), internal 1920×1080 eDP panel |
| Panel backlight (from firmware table) | PWM, controller 0, active-high |
| Firmware DVMT pre-allocation | 60 MB (GMS field `0xFE`) |
| macOS | Sonoma 14.8.9 (23J631) |
| OpenCore | 1.0.9 |
| Lilu | 1.7.3 |
| AMFIPass | v1.4.1 **Mod** |
| WhateverXe Graphics package | 0.3.2 |
| AppleIntelTGLCompat | 0.6.1 (unchanged from upstream) |
| SMBIOS used | `MacBookPro16,2` |

Other kexts on the tested machine (Wi-Fi, touchpad, audio, keyboard) are unrelated to graphics and are not listed here.

---

## What you need to download

All items are required unless marked optional. **This repository does not contain Apple driver files** and must not be used to redistribute them.

| Component | Version tested | Purpose | Download |
|---|---|---|---|
| **WhateverXe.kext (this fork)** | 0.6.1 + patches | The Lilu plugin with the two fixes | [This fork's release](https://example.com/REPLACE-this-fork-release) |
| **AMFIPass (Mod)** | v1.4.1 Mod | Lets macOS load the signed graphics bundles installed on the Data volume (upstream's Mod build, not the stock one) | [AMFIPass v1.4.1 Mod](https://github.com/b00t0x/WhateverXe-Graphics/raw/refs/heads/main/extras/AMFIPass-v1.4.1-Mod-RELEASE.zip) |
| **WhateverXe Graphics package** | 0.3.2 | Installs Apple's Tiger Lake driver payloads and shader fixes on macOS (upstream's installer) | [WhateverXe Graphics package](https://github.com/b00t0x/WhateverXe-Graphics/releases/tag/v0.3.2) |
| **Lilu** | 1.7.3 | Required by WhateverXe | [Lilu](https://github.com/dortania/build-repo/releases/tag/Lilu-0249c3a) |
| **AppleIntelTGLCompat** | 0.6.1 | Upstream's compatibility provider, unchanged. Use the copy that matches upstream 0.6.1 | [Upstream release](https://example.com/REPLACE-upstream-release) |
| **OpenCore** | 1.0.9 | Bootloader | [OpenCorePkg](https://github.com/dortania/build-repo/releases/tag/OpenCorePkg-dd5dc22) |
| **SSDTTime** | latest | Generates `SSDT-PNLF` for brightness | [SSDTTime](https://github.com/corpnewt/ssdttime) |
| `SSDT-PNLF` example (optional) | — | A sample for reference only; generate your own for your DSDT | [Sample SSDT-PNLF](https://example.com/REPLACE-sample-ssdt-pnlf) |
| BrightnessKeys (optional) | latest | Fn-key brightness hotkeys | [BrightnessKeys](https://github.com/acidanthera/BrightnessKeys/releases) |
| Hackintool (optional) | latest | Checking GPU / PCIe info | [Hackintool](https://github.com/benbaker76/Hackintool/releases) |

**Do not load WhateverGreen** with this plugin.

---

## Step-by-step setup

Follow the steps in order. Do not skip step 1.

### 1. Back up your EFI
Copy your working `EFI` folder somewhere safe (not on the same USB stick). If a boot fails, you restore this.

### 2. Check firmware settings
- Note your firmware's **DVMT pre-allocated** size. The values in step 5 are for **60 MB**. After your first macOS boot you can read it with  
  `ioreg -l -w0 -n IGPU | grep -E "fw-dvmt-gms-field-value|N97GGC"`  
  (`254` / `0xFE` = 60 MB). For other sizes follow the upstream README for the matching `framebuffer-stolenmem` value.
- **VT-d must not provide an active IOMapper.** Either disable VT-d in firmware or set `DisableIoMapper` (step 5). The plugin checks this and will not start otherwise.

### 3. Add the kexts to `EFI/OC/Kexts/`
Add these three, **in this order** in `Kernel > Add`:

1. `Lilu.kext`
2. `AMFIPass.kext` (the **Mod** build)
3. `WhateverXe.kext` (**this fork's** build; replace upstream's)

Remove or disable `WhateverGreen.kext` if present.

### 4. Create the brightness SSDT (laptops with a built-in panel)
The plugin's brightness profile only applies when the ACPI device `PNLF` has **`_UID` = `19`**.

1. Dump your DSDT and run [SSDTTime](https://github.com/corpnewt/ssdttime), choose the **PNLF** option and generate `SSDT-PNLF.aml`.
2. Put `SSDT-PNLF.aml` in `EFI/OC/ACPI/` and add it to `ACPI > Add`.
3. **If your DSDT already defines a `PNLF` device**, also add an `ACPI > Patch` rename so the two do not collide:  
   Find `504E4C46` (`PNLF`) → Replace `584E4C46` (`XNLF`). Keep the comment clear, e.g. `PNLF to XNLF`.
4. After booting, confirm with `ioreg -n PNLF -r -l` that `_UID` is `"19"` (see [Verify it works](#verify-it-works)).

### 5. Edit `config.plist`

**Kernel > Quirks**

| Key | Value |
|---|---|
| `DisableIoMapper` | `true` |

**boot-args**

| Argument | Required? | Notes |
|---|---|---|
| `-allow3d` | Yes | |
| `-disablegfxfirmware` | Yes | |
| `-igfxdvmt` | Yes for 60 MB DVMT | Needed together with the two properties below |
| `amfi_get_out_of_my_way=1` | Present on the tested machine | Upstream states the Mod AMFIPass does not need `amfi=0x80`; not verified here whether this one is needed |
| `-v debug=0x100 keepsyms=1` | Optional | Verbose boot and symbols for debugging |
| `-wexdbg`, `-wexbeta` | No | `-wexdbg` only affects debug builds; `-wexbeta` is not needed on Sonoma |

**DeviceProperties > Add > `PciRoot(0x0)/Pci(0x2,0x0)`** (values for **60 MB** DVMT)

| Key | Type | Value |
|---|---|---|
| `framebuffer-patch-enable` | Data | `01000000` |
| `framebuffer-stolenmem` | Data | `0000C003` |

Do **not** add a `device-id` spoof. The plugin selects its backend from the real `0x46B3` ID.

**Other values used on the tested machine** (not verified as required): `csr-active-config` = `03080000`, SMBIOS `MacBookPro16,2`.

### 6. First boot and install the Graphics package
1. Boot macOS. The first boot uses the firmware framebuffer (low VRAM, no Metal) until the package is installed.
2. Run the [WhateverXe Graphics package](https://github.com/b00t0x/WhateverXe-Graphics/releases/tag/v0.3.2) installer.
3. Reboot.

If acceleration disappears after a macOS update, reinstall the latest package.

### 7. Verify
Continue with [Verify it works](#verify-it-works).

---

## Verify it works

Run these in Terminal after the reboot in step 6.

| Check | Command | Expected |
|---|---|---|
| Kexts loaded | `kmutil showloaded \| grep -iE "WhateverXe\|TGL\|Lilu"` | Lilu, `WhateverXe` 0.6.1, `AppleIntelTGLCompat`, `AppleIntelTGLGraphicsFramebuffer`, and the accelerator kext |
| Plugin gate | `ioreg -l -w0 -n IGPU \| grep -E "N97Native\|WEXDisplay13BootReady"` | `N97NativePreflight = Yes`, `N97NativeStartAllowed = Yes`, `WEXDisplay13BootReady = Yes` |
| Metal | `system_profiler SPDisplaysDataType` | `Metal Support: Metal 2`, `Connection Type: Internal` |
| Brightness device | `ioreg -n PNLF -r -l` | `_UID = "19"` and an `AppleIntelPanelA` child with `WhateverXeBacklightProfile` |

Notes: the name "Intel(R) TGL Unknown" and 1536 MB VRAM are values reported by Apple's driver and are cosmetic.

---

## Troubleshooting

| Symptom | Likely cause | What to check |
|---|---|---|
| 7 MB VRAM, "No Kext Loaded", `N97NativePreflight = No` | You are running upstream's `WhateverXe.kext` (or a build without the fixes) | Replace with this fork's kext; confirm with `shasum -a 256` |
| `N97NativeStartAllowed = No` with this fork | Missing prerequisites | `DisableIoMapper`, boot-args, the two DVMT properties, Lilu → AMFIPass → WhateverXe order, WhateverGreen removed |
| Boots but screen is black / hangs | Wrong DVMT properties for your firmware value, or an untested panel/GPU | Boot your backup EFI; check `fw-dvmt-gms-field-value`; try verbose boot and post the last screen |
| Metal 2 shown but brightness slider does nothing | `PNLF` missing, duplicated, or `_UID` is not 19 | Redo step 4, then `ioreg -n PNLF -r -l` |
| Brightness hotkeys do nothing but the slider works | Hotkeys not mapped | Add [BrightnessKeys ((https://github.com/acidanthera/BrightnessKeys/releases)) |
| Graphics packages missing after a macOS update | Update replaced the installed bundles | Reinstall the [Graphics package](https://github.com/b00t0x/WhateverXe-Graphics/releases/tag/v0.3.2) |
| More video-playback errors after a macOS/Safari update | Updating Safari along with macOS updates (tester's report) | Avoid such updates; if already updated, re-test video and report your macOS and Safari versions |
| Streaming video stalls when seeking, local files are smooth | Likely network/Wi-Fi on the tested machine (not confirmed) | Test another connection; some Realtek Wi-Fi setups benefit from disabling ASPM on that device |

---

## Known issues and untested features

| Feature | Status |
|---|---|
| Native display and accelerated UI | Works on the tested machine |
| Metal reported (`Metal 2`) | Works |
| Internal panel brightness slider | Works after the `SSDT-PNLF` step above |
| Local video files (including seeking) | Smooth on the tested machine |
| Long mixed use (web, installing apps, about 3 hours) | One session ran without GPU errors |
| **GPU hardware-error episode** | **Seen once**: about 31 minutes into a session, shortly after video playback started, the accelerator logged repeated "hardware error" messages (GPU restart loop) and the system froze after about 5 minutes. Not reproduced or explained |
| Streaming video seeking (YouTube/Drive) | Stalls on the tested machine; probably network, not confirmed |
| Browser background blur | Artifacts seen in Safari; cause unknown |
| **Safari updated with macOS updates** | Reported by the tester to introduce more video-playback errors. Avoid updating Safari with macOS updates (see [Important warnings](#important-warnings)) |
| Hardware video decode | Unverified |
| Sleep / wake | **Not tested** |
| External displays, hot-plug | **Not tested** |
| Other 12th/13th-gen mobile chips, other macOS versions | **Not tested** |

Upstream marks Alder Lake-P/U internal-panel support as experimental and untested on hardware. Treat this release the same way.

---

## Compatibility

The two fixes only touch the **Display 13 internal-panel (eDP)** handling of upstream WhateverXe. Whether another chip needs them, or works with them, is unknown unless it appears as "Tested" below.

| Tier | GPU family | Device IDs (from upstream's table) | Status with this patch set |
|---|---|---|---|
| **Tested** | Alder Lake-U (Core i3-1215U) | `46B3` | **Tested on one machine** |
| Shares the patched code, untested | Alder Lake-H/P/U (other IDs) | `46A3`, `46A6`, `46A8`, `46AA`, `46C3` | Untested |
| Shares the patched code, untested | Raptor Lake-H/P/U | `A7A0`, `A7A1`, `A7A8`–`A7AD` | Untested |
| Shares the patched code, untested | Alder Lake-N / Twin Lake | `46D0`–`46D4` | Untested. The changes only apply to internal panels (eDP), so devices without one should behave as upstream |
| Not changed | Tiger Lake (11th gen) | `9A40`, `9A49`, `9A60`, `9A68`, `9A70`, `9A78` | Upstream behaviour; follow upstream |
| Not changed | Alder Lake-S/HX, Raptor Lake-S/HX | `4680`–`4693`, `A780`–`A78B` | Upstream behaviour (different display path); follow upstream |

If you try an untested chip, please [report your results](#reporting-results).

---

## Build from source

Requires macOS with Xcode Command Line Tools and Python 3.

```bash
git clone https://github.com/b00t0x/WhateverXe.git && cd WhateverXe
git checkout 68a2427
# Place Lilu.kext and MacKernelSDK in the repository root (see upstream's README)
python3 apply_functional_patches.py     # applies only the two fixes and the test
python3 tools/test.py                   # CPU tests
python3 tools/build.py --release        # output: build/WhateverXe.kext
```

Verify your own build before using it: boot it and run the checks in [Verify it works](#verify-it-works).

---

## Reporting results

Please include:

- CPU model, GPU device ID and revision, laptop model, firmware DVMT value
- macOS build, OpenCore version, Lilu version, Graphics package version
- The output of  
  `ioreg -l -w0 -n IGPU | grep -E "N97Native|WEXDisplay13BootReady"`  
  and `system_profiler SPDisplaysDataType`
- For hangs: a photo of the last verbose screen, and the output of  
  `log show --last 1h --predicate 'processID == 0' | grep -i -E "hardware error|GPURestart"`

**Contact:**

| Where | Link |
|---|---|
| Reddit (direct message) | [u/YOUR-USERNAME](https://example.com/REPLACE-reddit-profile) |
| Reddit discussion thread | [r/hackintosh thread](https://example.com/REPLACE-reddit-thread) |

**Privacy:** do not post your serial number, MLB, ROM, SystemUUID or iMessage keys. Blur them in screenshots.

---

## Credits and license

- All graphics driver work: **b00t0x** and contributors of [WhateverXe](https://example.com/REPLACE-upstream-whateverxe) and the [WhateverXe Graphics package](https://example.com/REPLACE-whateverxe-graphics-pkg).
- Lilu, OpenCore, MacKernelSDK, BrightnessKeys: the [Acidanthera](https://example.com/REPLACE-acidanthera) projects. SSDTTime: CorpNewt.
- Licensed under **BSD-3-Clause**, unchanged from upstream; see `LICENSE.txt`. Upstream copyright notices are retained.
- This project does not include or redistribute Apple driver files. Use at your own risk; no warranty.
