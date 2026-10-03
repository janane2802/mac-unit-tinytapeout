<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

An 8x4 multiply-accumulate (MAC) unit: a structural array multiplier feeding a
16-bit accumulator.

- **Multiplier** (`mult_array.v`): `operand_a[7:0] x operand_b[3:0]`, built as
  an AND-gate partial-product array reduced by a ripple of adders (the
  classic array-multiplier structure), producing a 12-bit product
  combinationally.
- **Accumulator** (`mac_accumulator.v`): a 16-bit register. On `mac_enable`,
  adds the current product into the running total. On `acc_clear`, resets to
  0; `acc_clear` takes priority if both are asserted the same cycle.
  `overflow` latches high whenever an addition carries out past bit 15, and
  stays high until the next accumulation that doesn't overflow, or a clear.
- **Top level** (`project.v`): wires these together and muxes the 16-bit
  accumulator onto the 8-bit `uo_out[7:0]` a byte at a time, selected by
  `byte_select`.

Pinout (also in the auto-generated table from `info.yaml`):

| Pin | Signal |
|---|---|
| `ui_in[7:0]` | `operand_a[7:0]` |
| `uio_in[7:4]` | `operand_b[3:0]` |
| `uio_in[0]` | `mac_enable` (in) |
| `uio_in[1]` | `acc_clear` (in) |
| `uio_out[2]` | `overflow` (out) |
| `uio_in[3]` | `byte_select` (in) — 0 = low byte, 1 = high byte |
| `uo_out[7:0]` | selected accumulator byte |

Note operand_b is 4 bits, not 8 — see the pin-budget note in
`info.yaml`'s pinout comments: `uio` only has 8 pins total, and 4 of them
are needed for `mac_enable`/`acc_clear`/`overflow`/`byte_select`, so a full
8-bit second operand didn't fit without dropping one of those control
signals.

## How to test

1. Hold `rst_n` low for a few clock cycles, then release it.
2. Drive `ui_in` with `operand_a` and `uio_in[7:4]` with `operand_b`.
3. Pulse `uio_in[0]` (`mac_enable`) high for exactly one clock cycle to
   accumulate `operand_a * operand_b` into the running total. Repeat with new
   operands to build up a sum.
4. Read the result: set `uio_in[3]` (`byte_select`) to 0 and read `uo_out`
   for the low byte of the 16-bit accumulator, or set it to 1 for the high
   byte.
5. Check `uio_out[2]` (`overflow`) — it reads high if the last accumulation
   carried out past bit 15, and clears on the next non-overflowing
   accumulation or on `acc_clear`.
6. Pulse `uio_in[1]` (`acc_clear`) high for one clock cycle to reset the
   accumulator and `overflow` to 0. If `mac_enable` and `acc_clear` are both
   high the same cycle, `acc_clear` wins.

The full behavior above is exercised by the cocotb test suite in
`test/test.py` (basic MAC, running sums, overflow assert/clear, acc_clear
priority, byte_select switching) — run with `python test/run_tests.py` for
RTL simulation, or `python test/run_tests_gl.py` for gate-level simulation
against the hardened netlist. Both pass all 5 test cases.

## External hardware

None — all inputs and outputs are driven directly from the TT demo board's
digital I/O.

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
