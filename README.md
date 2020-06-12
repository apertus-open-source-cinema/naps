# AXIOM nGateware
An attempt to rewrite the gateware for the AXIOM micro (and later the AXIOM Beta) in nMigen.
Mostly a place to experiment and figure out how to build things. 

This repo contains:

* various nMigen cores (in `src/cores/`) for:
    * AXI and AXI Lite
    * A CSR bank that can be wired to an AXI bus
    * HDMI (currently the DVI subset; derived from Litevideo)
    * ...
* tools for gluing together SOCs (currently supports the Xilinx Zynq) in `src/soc/`
    * Making heavy use of nMigen Platform
    * Provides a bus agnostic way to describe (low speed) peripherals
    * Emits Python code that can be used to access the designs CSRs
* platform definitions for both the AXIOM Beta and the AXIOM Micro in `src/devices/`
* test gateware to test connectors for their ability to transmit high speed data (via a loopback test) in `connector_test.py`
* ... and a variety of other smaller half-working experiments
 