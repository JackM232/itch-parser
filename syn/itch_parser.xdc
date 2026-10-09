# 100 MHz clock, the same as the Arty A7's oscillator.
# Out-of-context run: no pin assignments, so this checks the parser's own
# register-to-register paths.
create_clock -period 10.000 -name clk [get_ports clk]
