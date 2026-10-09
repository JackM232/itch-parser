# Synthesize, place, and route itch_parser out of context on the Arty A7-100T
# part, then write timing and utilization reports to syn/reports.
#
# Run from the Vivado Tcl Shell:
#   cd C:/Users/jackm/Dev/fpga/itch-parser
#   source syn/run_synth.tcl

set root [file normalize [file join [file dirname [info script]] ..]]
set part xc7a100tcsg324-1
set rpt  [file join $root syn reports]
file mkdir $rpt

read_verilog -sv [file join $root rtl itch_parser.sv]
read_xdc [file join $root syn itch_parser.xdc]

synth_design -top itch_parser -part $part -mode out_of_context
opt_design
place_design
route_design

report_timing_summary -file [file join $rpt timing.rpt]
report_utilization    -file [file join $rpt utilization.rpt]

set wns [get_property SLACK [get_timing_paths -setup -max_paths 1]]
puts ""
puts "=============================================="
puts " Worst negative slack (WNS) at 100 MHz: $wns ns"
puts " Reports written to $rpt"
puts "=============================================="
