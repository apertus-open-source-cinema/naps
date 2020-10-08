# AXIOM nGateware
An attempt to rewrite the gateware for the AXIOM micro (and later the AXIOM Beta) in nMigen.
Mostly a place to experiment and figure out how to build things. 

This repo contains:

* various nMigen cores (in `src/cores/`) for:
    * AXI and AXI Lite
    * A CSR bank that can be wired to an AXI bus
    * HDMI (currently the DVI subset; derived from Litevideo)
    * A HISPI reciever (for the use with aptina / onsemi image sensors)
    * ...
* tools for gluing together SOCs (currently supports the Xilinx Zynq and JTAG based plattoforms) in `src/soc/`
    * Making heavy use of nMigen Platform abstractions (wrapping existing plattforms)
    * Provides a bus agnostic way to describe (low speed) peripherals
    * Emits Python code that can be used to access the designs CSRs ("pydriver")
    * Generate devicetree overlays for loading linux device drivers
    * pack "fatbitstreams" that bundle setup logic, drivers and the bitstream
* platform definitions for both the AXIOM Beta and the AXIOM Micro in `src/devices/`
* a variety of other smaller half-working experiments in `experiments/`
    * test gateware to test connectors for their ability to transmit high speed data (via a loopback test)
    * test gateware for the axi writer & reader
    * test gateware for hdmi
 