"""cocotb testbench for itch_parser.

Feeds real ITCH bytes into the RTL, one byte per clock with random idle
cycles, and checks every decoded Add Order against the Python reference
model in model/itch_ref.py.

Settings (environment variables):
    NUM_MSGS  messages to send, starting at the first Add Order (0 = rest of file)
    GAP_PCT   percent of cycles where in_valid is 0 (default 10)
    SEED      random seed for the idle cycles (default 1)
    ITCH_FILE path to the ITCH capture (default data/itch_sample.bin)
"""
import os
import random
import sys
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "model"))
from itch_ref import parse_add_orders  # noqa: E402  (the answer key)

DATA_FILE = Path(os.environ.get("ITCH_FILE", ROOT / "data" / "itch_sample.bin"))
NUM_MSGS = int(os.environ.get("NUM_MSGS", "20000"))
GAP_PCT = int(os.environ.get("GAP_PCT", "10"))
SEED = int(os.environ.get("SEED", "1"))

FIELDS = ["stock_locate", "tracking", "timestamp", "order_ref",
          "side", "shares", "stock", "price"]


def pick_window(data):
    """Start at the first Add Order and take NUM_MSGS whole messages.

    Returns (start, end, message_count, add_order_offsets). Any message
    boundary is a valid place to start, so the parser doesn't need the
    6 MB of start-of-day messages before the first order.
    """
    pos = 0
    while chr(data[pos + 2]) != "A":
        pos += 2 + int.from_bytes(data[pos:pos + 2], "big")
    start, count, add_offsets = pos, 0, []
    while pos + 2 <= len(data) and (NUM_MSGS == 0 or count < NUM_MSGS):
        end = pos + 2 + int.from_bytes(data[pos:pos + 2], "big")
        if end > len(data):
            break  # the last message was cut off by head -c
        if chr(data[pos + 2]) == "A":
            add_offsets.append(pos)
        pos, count = end, count + 1
    return start, pos, count, add_offsets


def read_int(handle):
    value = handle.value
    if not value.is_resolvable:
        raise AssertionError(f"{handle._name} has X or Z bits: {value}")
    return value.to_unsigned()


def read_outputs(dut):
    """Read the DUT's output fields in the same format as decode_add_order."""
    return {
        "stock_locate": read_int(dut.out_stock_locate),
        "tracking": read_int(dut.out_tracking),
        "timestamp": read_int(dut.out_timestamp),
        "order_ref": read_int(dut.out_order_ref),
        "side": chr(read_int(dut.out_side)),
        "shares": read_int(dut.out_shares),
        "stock": read_int(dut.out_stock).to_bytes(8, "big").decode("ascii", "replace"),
        "price": read_int(dut.out_price),
    }


async def drive_bytes(dut, payload, rng):
    """Send each byte with in_valid = 1, holding it until in_ready takes it.
    Random idle cycles (in_valid = 0) go in between."""
    for b in payload:
        while rng.randrange(100) < GAP_PCT:
            dut.in_valid.value = 0
            await RisingEdge(dut.clk)
        dut.in_valid.value = 1
        dut.in_data.value = b
        await RisingEdge(dut.clk)
        while not dut.in_ready.value:
            await RisingEdge(dut.clk)
    dut.in_valid.value = 0


async def check_outputs(dut, expected, offsets, seen):
    """On every clock, if out_valid is 1, compare the outputs to the next
    expected Add Order. Stops the test at the first mismatch."""
    while True:
        await RisingEdge(dut.clk)
        if not dut.out_valid.value.is_resolvable:
            raise AssertionError(f"out_valid is X or Z: {dut.out_valid.value}")
        if not dut.out_valid.value:
            continue
        n = seen[0]
        if n >= len(expected):
            raise AssertionError(f"out_valid pulsed {n + 1} times, but the window "
                                 f"only has {len(expected)} Add Orders")
        exp, got = expected[n], read_outputs(dut)
        bad = [f for f in FIELDS if got[f] != exp[f]]
        if bad:
            lines = [f"Add Order #{n} (file offset {offsets[n]:,}) does not match the model:"]
            for f in bad:
                lines.append(f"  {f:13} expected {repr(exp[f]):24} got {repr(got[f])}")
            lines.append(f"  See its bytes with: xxd -s {offsets[n]} -l 38 {DATA_FILE.name}")
            raise AssertionError("\n".join(lines))
        seen[0] = n + 1
        if seen[0] % 100_000 == 0:
            dut._log.info(f"{seen[0]:,} Add Orders checked")


@cocotb.test()
async def test_add_orders_match_model(dut):
    data = DATA_FILE.read_bytes()
    start, end, n_msgs, offsets = pick_window(data)
    window = data[start:end]
    expected = parse_add_orders(window)
    assert len(expected) == len(offsets)
    dut._log.info(f"Sending {n_msgs:,} messages ({len(window):,} bytes from offset "
                  f"{start:,}) with {GAP_PCT}% idle cycles, expecting {len(expected):,} Add Orders")

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst.value = 1
    dut.in_valid.value = 0
    dut.in_data.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst.value = 0

    seen = [0]
    cocotb.start_soon(check_outputs(dut, expected, offsets, seen))
    await drive_bytes(dut, window, random.Random(SEED))
    await ClockCycles(dut.clk, 5)

    assert seen[0] == len(expected), (
        f"Only {seen[0]:,} of {len(expected):,} Add Orders came out of the parser")
    dut._log.info(f"PASS: all {seen[0]:,} Add Orders match the Python model")
