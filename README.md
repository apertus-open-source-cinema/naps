# AXIOM nGateware
An attempt to rewrite the gateware for the AXIOM micro (and later the AXIOM Beta) in nMigen.
Mostly a place to experiment and figure out how to build things. 

This repo contains:

* some axi helper code in `modules/axi`
* A working but hacky implementation of axi lite CSRs in `modules/axi`
* a (rather nice) abstraction to interface with Xilinx blackbox primitives in `modules/xilinx`
* plattform definitions for both the Beta and the micro in `devices/`
* a crude, unfinished and conceptually flawed clocking helper (for setting plls and stuff) in `modules/clocking`
* some tests to use liteHdmi (non working) in `modules/hdmi.py`
* WIP test gateware to test connectors for their ability to transmit high speed data (via a loopback test) in `connector_test.py`
* ... and a verity of other smaller half-working experiments
 