# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

BAUD_RATE = 9600
BIT_PERIOD_NS = round(1_000_000_000 / 9600)  # = 104167 ns
# Must match pattern_player.v (CLK_FREQ / PLAY_RATE_HZ) and the RAM
# depth in ram_256x8.v / pattern_player.v.
PLAY_DIVISOR = 10_000
RAM_DEPTH = 32


async def uart_send_byte(dut, byte):
    """Bit-bang one 8N1 UART byte (LSB first) onto ui_in[0]."""
    # Start bit (low)
    dut.ui_in.value = int(dut.ui_in.value) & 0xFE
    await Timer(BIT_PERIOD_NS, units="ns")

    for i in range(8):
        bit = (byte >> i) & 1
        cur = int(dut.ui_in.value)
        if bit:
            dut.ui_in.value = cur | 0x01
        else:
            dut.ui_in.value = cur & 0xFE
        await Timer(BIT_PERIOD_NS, units="ns")

    # Stop bit (high)
    dut.ui_in.value = int(dut.ui_in.value) | 0x01
    await Timer(BIT_PERIOD_NS, units="ns")


@cocotb.test()
async def test_project(dut):
    dut._log.info("Start")

    # 100 ns period -> 10 MHz system clock
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    dut.ui_in.value = 0b0000_0001  # UART RX idle high, MODE = 0 (DAC)
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Filling RAM with 0x00-0x1F over UART")
    for i in range(RAM_DEPTH):
        await uart_send_byte(dut, i)
    await ClockCycles(dut.clk, 5)

    # Sample uo_out over one full pattern-player loop. RAM[i] == i for
    # i in 0..RAM_DEPTH-1, so uo_out (DAC mode) should sweep through
    # those values and must not be stuck at a constant value.
    dut._log.info("Sampling uo_out over one full playback loop")
    samples = set()
    for _ in range(RAM_DEPTH + 1):
        try:
            samples.add(int(dut.uo_out.value))
        except ValueError:
            pass  # skip uninitialized X values
        await ClockCycles(dut.clk, PLAY_DIVISOR)

    assert (RAM_DEPTH - 1) in samples, "last RAM byte written never appeared on uo_out"
    assert len(samples) > 1, "uo_out is stuck at a single value"

    # Switch to PWM mode and confirm the shared 8-bit PWM counter makes
    # uo_out toggle.
    dut._log.info("Switching to PWM mode")
    dut.ui_in.value = int(dut.ui_in.value) | 0b0000_0010
    await ClockCycles(dut.clk, 2)

    pwm_initial = int(dut.uo_out.value)
    toggled = False
    for _ in range(300):
        await ClockCycles(dut.clk, 1)
        if int(dut.uo_out.value) != pwm_initial:
            toggled = True
            break

    assert toggled, "uo_out did not toggle in PWM mode"
