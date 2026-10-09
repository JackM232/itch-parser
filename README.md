# ITCH 5.0 Add Order Parser (SystemVerilog)

Hardware parser for NASDAQ's ITCH 5.0 market data feed. Decodes Add Orders from a raw byte stream. Uses states to separate each message into its length and body.

## Results
- Verified against real Nasdaq data (Jan 30, 2019 capture, first 50 MB):
  **all 597,530 Add Orders** match the Python reference model on every field,
  with random idle cycles in the input (~48.7 million simulated clock cycles)
- Timing: meets **100 MHz** on Xilinx Artix-7 (xc7a100tcsg324-1) after place
  and route, **WNS +4.886 ns** (rough max ~196 MHz)
- Utilization: **51 LUTs, 317 flip-flops**, 0 BRAM, 0 DSP

## How it works

- ITCH messages are sent back to back, and each message begins with a two byte length prefix, which is stored in `msg_len`.
- The finite state machine has three states: `LEN_HI` -> `LEN_LO` -> `BODY` -> back to `LEN_HI`. Parsing the length prefix requires two states since the length is two bytes and only one byte arrives per clock, so the machine needs to know which half it is receiving. The machine then stays in `BODY` until it reaches the last byte of the message, based on the length value.
- The byte counter (`idx`) measures how far the parser is into the body of the message. Because the fields in an Add Order are always at the same byte positions (stock locate -> tracking -> timestamp, etc.), the parser must keep track of how far it is in the body to know where to store each piece of information.
- Because each field is a different fixed number of bytes and bytes are inputted one at a time, shift registers of appropriate sizes are used to capture each field to avoid creating logic for every single byte. Shifting each new byte in at the bottom also builds the big-endian number automatically.
- `out_valid` is a signal that pulses for one cycle when an Add Order is fully complete, signaling that the output fields hold a complete organized message.
- Non-Add messages are skipped by reading their length and counting through their body with `idx` until the last byte (`idx == msg_len - 1`), then returning to `LEN_HI` without pulsing `out_valid`.
- Input is valid/ready: `in_valid` is a flag to ensure that the parser only takes in a byte on cycles where a real one is present, to avoid parsing invalid / repeat bytes. `in_ready` is always 1, since the parser can take a byte every clock.

## Interface

| Port | Dir | Width | Description |
|---|---|---|---|
| `clk` | in | 1 | Clock (100 MHz target) |
| `rst` | in | 1 | Synchronous reset, active high |
| `in_valid` | in | 1 | A byte is present on `in_data` this cycle |
| `in_ready` | out | 1 | Parser can accept a byte. Always 1, since it handles one byte per clock |
| `in_data` | in | 8 | Raw ITCH byte stream, including the 2-byte length prefix on each message |
| `out_valid` | out | 1 | High for one cycle after the last byte of an Add Order; the fields below are valid on that cycle |
| `out_stock_locate` | out | 16 | Nasdaq's ID number for the stock that day |
| `out_tracking` | out | 16 | Nasdaq internal tracking number |
| `out_timestamp` | out | 48 | Nanoseconds since midnight |
| `out_order_ref` | out | 64 | Unique order ID, used by later cancel and execute messages |
| `out_side` | out | 8 | ASCII `B` (buy) or `S` (sell) |
| `out_shares` | out | 32 | Number of shares |
| `out_stock` | out | 64 | Stock symbol, 8 ASCII characters, padded with spaces |
| `out_price` | out | 32 | Price with 4 implied decimal places (1072600 = $107.26) |

## Verification
- Wrote a Python reference file which splits the messages into byte slices and creates a dictionary for each Add Order to keep track of information. Each dictionary is appended to a master list of all of the Add Orders. Used this final list as an answer key to verify results of the parser in SystemVerilog.
- cocotb testbench feeds the bytes into the RTL code, once per clock cycle. Every time `out_valid` is high, it compares all 8 output fields to the next order in the answer key. Also adds in random pauses to ensure that the parser doesn't read invalid bytes and include them in the parsed messages.
- Caught issue where the `out_stock` field wasn't capturing the entire field, since the shift only kept the bottom 24 bits of the 64-bit register, so only the last 4 of the 8 symbol bytes survived. Also caught issue where `out_valid` stayed high instead of pulsing, so the same order was reported twice.

## Repo layout
- `model/` Python reference parser
- `rtl/` SystemVerilog parser
- `tb/` cocotb testbench
- `syn/` Vivado out-of-context build script, constraints, reports

## Running it
Get the data (first 50 MB of Nasdaq's Jan 30, 2019 ITCH sample):
```bash
mkdir -p data && curl -s "https://emi.nasdaq.com/ITCH/Nasdaq%20ITCH/01302019.NASDAQ_ITCH50.gz" | gunzip | head -c 50000000 > data/itch_sample.bin
```

Run the Python reference model (writes `data/add_orders.csv`):
```bash
python model/itch_ref.py
```

Run the cocotb testbench (needs iverilog and cocotb):
```bash
cd tb
make                # first 20,000 messages
make NUM_MSGS=0     # whole file
```

Run Vivado synthesis and timing (from the Vivado Tcl Shell, in the repo folder):
```tcl
source syn/run_synth.tcl
```

## Next steps
- UART demo on the Arty A7: stream bytes in from a PC and send decoded orders back
- Parse more message types: Order Executed (E), Order Cancel (X), and Order Delete (D)
- Replace the byte stream input with Ethernet/UDP, the way the real feed arrives (MoldUDP64)
- Build an order book that tracks the best bid and ask per stock
- Measure latency from the first byte of a message to `out_valid`

*Testbench and build scripts written with AI assistance; RTL and reference model written by me.*