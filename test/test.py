# SPDX-FileCopyrightText: © 2026 Srija Nane
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer


def make_uio(mac_enable=0, acc_clear=0, byte_select=0, operand_b=0):
    return (
        ((operand_b & 0xF) << 4)
        | ((byte_select & 1) << 3)
        | ((acc_clear & 1) << 1)
        | (mac_enable & 1)
    )


def overflow_bit(dut):
    return (int(dut.uio_out.value) >> 2) & 1


async def reset(dut):
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)


async def mac_pulse(dut, a, b):
    """Drive operand_a/operand_b and pulse mac_enable for exactly one clock cycle."""
    dut.ui_in.value = a
    dut.uio_in.value = make_uio(mac_enable=1, operand_b=b)
    await ClockCycles(dut.clk, 1)
    dut.uio_in.value = make_uio(mac_enable=0, operand_b=b)


async def clear_pulse(dut):
    dut.uio_in.value = make_uio(acc_clear=1)
    await ClockCycles(dut.clk, 1)
    dut.uio_in.value = make_uio(acc_clear=0)


async def clear_and_mac_pulse(dut, a, b):
    """Assert acc_clear and mac_enable together for one cycle (clear should win)."""
    dut.ui_in.value = a
    dut.uio_in.value = make_uio(mac_enable=1, acc_clear=1, operand_b=b)
    await ClockCycles(dut.clk, 1)
    dut.uio_in.value = make_uio(mac_enable=0, acc_clear=0, operand_b=b)


async def read_acc_byte(dut, byte_select):
    """Read a byte of the accumulator through uo_out without affecting state.

    The settle delay must exceed worst-case combinational propagation through
    the byte_select mux. In RTL (delta-cycle) sim this is irrelevant; in
    gate-level sim with UNIT_DELAY=#1, real per-gate delay applies, so this
    stays generous (negligible next to the 10us clock period either way).
    """
    dut.uio_in.value = make_uio(byte_select=byte_select)
    await Timer(50, unit="ns")
    return int(dut.uo_out.value)


async def read_acc16(dut):
    low = await read_acc_byte(dut, 0)
    high = await read_acc_byte(dut, 1)
    return (high << 8) | low


async def start_clock(dut):
    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())


@cocotb.test()
async def test_basic_mac(dut):
    """1. A single multiply-accumulate, checked via both accumulator bytes."""
    await start_clock(dut)
    await reset(dut)

    a, b = 5, 3
    await mac_pulse(dut, a, b)

    expected = a * b
    acc = await read_acc16(dut)
    assert acc == expected, f"expected acc={expected}, got {acc}"
    assert overflow_bit(dut) == 0

    low = await read_acc_byte(dut, 0)
    high = await read_acc_byte(dut, 1)
    assert low == (expected & 0xFF), f"low byte mismatch: {low} != {expected & 0xFF}"
    assert high == ((expected >> 8) & 0xFF), f"high byte mismatch: {high} != {(expected >> 8) & 0xFF}"

    dut._log.info("test_basic_mac PASSED")


@cocotb.test()
async def test_running_sum(dut):
    """2. Multiple consecutive accumulations build a running sum."""
    await start_clock(dut)
    await reset(dut)

    ops = [(10, 5), (20, 2), (3, 3), (167, 5)]
    running = 0
    for a, b in ops:
        await mac_pulse(dut, a, b)
        running += a * b
        acc = await read_acc16(dut)
        assert acc == running, f"after ({a},{b}) expected acc={running}, got {acc}"
        assert overflow_bit(dut) == 0

    dut._log.info("test_running_sum PASSED")


@cocotb.test()
async def test_overflow(dut):
    """3. Accumulator overflow past 16 bits asserts the overflow flag,
    which then clears on the next non-overflowing accumulation."""
    await start_clock(dut)
    await reset(dut)

    a, b = 255, 15  # max product = 3825
    product = a * b
    running = 0
    n = 0
    overflowed = False
    while not overflowed:
        await mac_pulse(dut, a, b)
        running += product
        n += 1
        overflowed = running >= (1 << 16)

    expected_acc = running & 0xFFFF
    acc = await read_acc16(dut)
    assert acc == expected_acc, f"after overflow expected acc={expected_acc}, got {acc}"
    assert overflow_bit(dut) == 1, "overflow flag should be asserted"
    dut._log.info(f"overflow reached after {n} accumulations, acc wrapped to {acc}")

    # overflow should still read high without a new operation
    acc_again = await read_acc16(dut)
    assert acc_again == expected_acc
    assert overflow_bit(dut) == 1, "overflow flag should remain asserted until next op/clear"

    # a subsequent non-overflowing accumulation should clear the flag
    await mac_pulse(dut, 1, 1)
    expected_acc = (expected_acc + 1) & 0xFFFF
    acc = await read_acc16(dut)
    assert acc == expected_acc
    assert overflow_bit(dut) == 0, "overflow flag should clear after a non-overflowing op"

    dut._log.info("test_overflow PASSED")


@cocotb.test()
async def test_acc_clear(dut):
    """4. acc_clear resets acc/overflow, and wins over a simultaneous mac_enable."""
    await start_clock(dut)
    await reset(dut)

    # Build up some state, stopping right at the accumulation that overflows,
    # then clear mid-sequence.
    a, b = 255, 15
    product = a * b
    running = 0
    while running < (1 << 16):
        await mac_pulse(dut, a, b)
        running += product
    await Timer(50, unit="ns")
    assert overflow_bit(dut) == 1

    await clear_pulse(dut)
    acc = await read_acc16(dut)
    assert acc == 0, f"expected acc=0 after acc_clear, got {acc}"
    assert overflow_bit(dut) == 0, "overflow should clear on acc_clear"

    # Build up a nonzero value, then assert acc_clear and mac_enable together.
    await mac_pulse(dut, 10, 10)
    acc = await read_acc16(dut)
    assert acc == 100

    await clear_and_mac_pulse(dut, 200, 10)
    acc = await read_acc16(dut)
    assert acc == 0, f"acc_clear should win over simultaneous mac_enable, got {acc}"
    assert overflow_bit(dut) == 0

    dut._log.info("test_acc_clear PASSED")


@cocotb.test()
async def test_byte_select(dut):
    """5. byte_select correctly switches uo_out between the low and high accumulator bytes."""
    await start_clock(dut)
    await reset(dut)

    # Build acc = 0x1234 via two accumulations: 255*15 + 167*5 = 3825 + 835 = 4660 = 0x1234
    await mac_pulse(dut, 255, 15)
    await mac_pulse(dut, 167, 5)

    acc = await read_acc16(dut)
    assert acc == 0x1234, f"expected acc=0x1234, got {hex(acc)}"

    low = await read_acc_byte(dut, 0)
    assert low == 0x34, f"expected low byte 0x34, got {hex(low)}"

    high = await read_acc_byte(dut, 1)
    assert high == 0x12, f"expected high byte 0x12, got {hex(high)}"

    # Toggle back and forth to make sure it isn't sticky/latched.
    low_again = await read_acc_byte(dut, 0)
    assert low_again == 0x34

    dut._log.info("test_byte_select PASSED")
