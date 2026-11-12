# Changelog

All releases are unofficial and experimental. Each release is built on a specific upstream
WhateverXe version and needs a matching WhateverXe Graphics package.

## v0.2.0-latest
- Based on upstream WhateverXe **0.8.0**; requires WhateverXe Graphics **0.4.2**.
- Same functional fixes as v0.1.0, re-applied to 0.8.0 (upstream changed the code around two of them):
  6-bpc eDP boot scanout accepted for panels; eDP port with field `+0x550 == 0` accepted for panels on Combo DDI A/B.
- Added a CPU-only diagnostic: `N97NativeBlockReason` (IORegistry property on the GPU) and a log line that name why the
  native start is blocked. Decoded by `scripts/check_wex_setup.sh`. Build without it using `--no-diagnostic`.
- Added `scripts/check_wex_setup.sh` (read-only setup checker) and `scripts/collect_wex_report.sh` (privacy-filtered report).
- The patch script now supports both upstream 0.6.1 and 0.8.0 layouts.
- Tested on one machine (Core i3-1215U, `0x46B3`, macOS Sonoma 14.8.9).

## v0.1.0-initial
- Based on upstream WhateverXe **0.6.1**; requires WhateverXe Graphics 0.3.2.
- Two fixes so an Alder Lake-U laptop with a 6-bit internal eDP panel can start the native driver
  (see README, "What this fork changes").
- Tested on one machine (Core i3-1215U, `0x46B3`, macOS Sonoma 14.8.9).
