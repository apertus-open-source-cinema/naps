nMigen Apertus PackageS
=======================

Building Blocks & Tools for FPGA Design with Python & `nMigen <https://github.com/nmigen/nmigen>`__.
Mostly a place to experiment and figure out how to build things.
Also the incubator for the future AXIOM Beta camera gateware & the home of the current AXIOM micro gateware.

This repo contains:

-  Prototypes of the upcoming nmigen data types ``PackedStruct`` and ``Interface`` (here called ``Bundle``) (in ``src/lib/data_structure/``)
-  A stream Abstraction with various building Blocks: (in ``src/lib/stream/``)

   -  FIFOs
   -  A gearbox for changing the width
   -  Helpers for building other Stream cores
   -  Miscellaneous Debug and Inspection tools

-  various nMigen cores (in ``src/lib/``) for:

   -  AXI and AXI Lite including a Buffer reader and Writer
   -  A CSR bank that can be wired to an AXI bus
   -  HDMI (currently the DVI subset; derived from Litevideo)
   -  A HISPI reciever (for the use with aptina / onsemi image sensors)
   -  A core for streaming data over USB3 using the ft601
   -  Some utility video processing (like debayering)
   -  …

-  tools for gluing together SOCs (currently supports the Xilinx Zynq and JTAG based plattoforms) in ``src/soc/``

   -  Making heavy use of nMigen Platform abstractions (wrapping existing plattforms)
   -  Provides a bus agnostic way to describe (low speed) peripherals
   -  Emits Python code that can be used to access the designs CSRs (“pydriver”)
   -  Generate devicetree overlays for loading linux device drivers
   -  pack “fatbitstreams” that bundle setup logic, drivers and the bitstream

-  platform definitions for both the AXIOM Beta and the AXIOM Micro in ``src/devices/``
-  a variety of other smaller half-working experiments in ``src/experiments/``

   -  linux framebuffer HDMI output
   -  USB3 Plugin module gateware (wip)
   -  AXIOM micro camera gateware (wip)
   -  test gateware to test connectors for their ability to transmit high speed data (via a loopback test)
   -  test gateware for the axi writer & reader
