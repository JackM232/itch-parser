# Run from this folder with: make
# Options: make NUM_MSGS=0 (whole file), GAP_PCT=0 (no idle cycles), SEED=2, WAVES=1
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

VERILOG_SOURCES += $(PWD)/../rtl/itch_parser.sv
COCOTB_TOPLEVEL = itch_parser
COCOTB_TEST_MODULES = test_itch_parser

include $(shell cocotb-config --makefiles)/Makefile.sim
