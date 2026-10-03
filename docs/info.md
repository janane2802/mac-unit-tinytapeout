<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

Explain how your project works

## How to test

Explain how to use your project

## External hardware

List external hardware used in your project (e.g. PMOD, LED display, etc), if any

## Known limitations

Signoff STA reports max-slew violations isolated to the worst-case PVT corner
(`*_ss_100C_1v60` — slow process, 100°C, 1.60V): 44 violating pins at
`max_ss_100C_1v60` and `nom_ss_100C_1v60`, 22 at `min_ss_100C_1v60` (out of a
9-corner sweep; the typical `tt_025C_1v80` and fast `ff_n40C_1v95` corners are
fully clean). Violations are modest — actual slew of ~0.78-0.94ns against a
0.75ns hard limit from the PDK's standard cell library.

DRC, LVS, and Antenna checks all pass cleanly; this does not block
manufacturability. It means timing margin is tighter than ideal specifically
under worst-case slow/hot/low-voltage silicon.

Two LibreLane config levers were tried (`DESIGN_REPAIR_MAX_SLEW_PCT`,
`GRT_DESIGN_REPAIR_MAX_SLEW_PCT`, and enabling the experimental
`RUN_POST_GRT_DESIGN_REPAIR` post-routing repair pass — see `src/config.json`).
This gave a partial improvement (`nom_ss_100C_1v60` dropped from 44 to 22
violations) but did not clear the worst corner (`max_ss_100C_1v60` unchanged
at 44). Accepted as a known limitation rather than pursued further.

### Tiny Tapeout precheck verification

Ran the official `tt/precheck` tool locally against the hardened GDS
(`tt_submission/tt_um_janane2802_mac_unit.gds`). 14/15 checks pass: KLayout
FEOL/BEOL/offgrid/pin-label/zero-area, pin/boundary/power-pin/layer/cell-name/
urpm-nwell checks, analog pin check, and Verilog syntax check all clean.

The remaining failure (Magic DRC) is a local-environment artifact, not a
design issue: Ubuntu 24.04's `apt` package ships Magic 8.3.105 (2021), but the
PDK's techfile requires Magic >=8.3.411, so the older binary segfaults trying
to parse it. Confirmed this is redundant with an already-passing check:
hardening's own `OpenROAD`/`Magic.DRC` step (`runs/wokwi/63-magic-drc`,
`64-checker-magicdrc`) runs the identical `drc style drc(full)` ruleset inside
LibreLane's Docker container (Magic 8.3 revision 623) and reports
`magic__drc_error__count: 0`. Precheck's own `magic_drc.tcl` is line-for-line
the same DRC invocation. No separate check is actually missed.

Precheck does not check timing/STA at all (no slew/setup/hold checks in its
15-check suite) — the max-slew limitation above is caught solely by
LibreLane's own signoff STA, not by precheck.
