naps.soc
========

The naps.soc package contains mainly infrastructure for accessing stuff in the FPGA at runtime
via a CPU. That CPU can currently be either the Zynq ARM CPU or a host computer via JTAG.
This is especially handy for debugging but also for runtime configuration of the FPGA.
There is also `a poster motivating and explaining the naps.soc functionality <https://raw.githubusercontent.com/apertus-open-source-cinema/naps/main/doc/NapsPosterFPGAIgnite2023.pdf>`__.


Control and Status Registers (CSRs)
-----------------------------------

The most striking part of the naps.soc package is the CSR infrastructure.
naps chooses a very easy to use approach to CSRs: The special types
``ContolSignal`` and ``StatusSignal`` beahve like normal Amaranth signals
but are wired up so that their values can be read (``StatusSignal``) or written (``ControlSignal``)
by the CPU. The CSRs are automatically collected during elaboration, 
assigned addresses, and connected to a bus.

If we change our blinky example to use CSRs, we can do the following::
    
    from amaranth import *
    from naps import *

    class Top(Elaboratable):
        runs_on = [Colorlight5a75b70Platform]

        def __init__(self):
            self.led = ControlSignal()

        def elaborate(self, platform):
            m = Module()
            m.d.comb += platform.request("user_led").o.eq(self.led)
            return m

    if __name__ == "__main__":
        cli(Top)

Thats all we have to do.

"Pydriver"
----------

If we now run our design with the additional ``--run`` flag, we are dropped into a
python shell that runs on the CPU side.
In this shell we can access all CSRs as normal python attributes on the
``design`` object. For example, we can do::

    >>> design.led = 1  # turn on the LED
    >>> design.led  # read the LED state
    1

If we now want to bring back the blinking LED, we can add a method annotated with 
``@pydriver`` to our design. This method could then toggle the LED every second::

    from amaranth import *
    from naps import *

    class Top(Elaboratable):
        runs_on = [Colorlight5a75b70Platform]

        def __init__(self):
            self.led = ControlSignal()

        def elaborate(self, platform):
            m = Module()
            m.d.comb += platform.request("user_led").o.eq(self.led)
            return m

        @pydriver
        def blink(self):
            from time import sleep
            while True:
                self.led = 1
                sleep(1)
                self.led = 0
                sleep(1)

    if __name__ == "__main__":
        cli(Top)

If we now run our design and enter ``design.blink()`` in the python shell, we can see the LED blink again.

During the elaboration phase, all functions with the ``@pydriver`` decorator are collected and added to the fatbitstream.


.. todo:: 
    explain the more general concept of peripherals and the handle_read and handle_write methods


Fatbitstreams
-------------

These functionalities are enabled by what we call "fatbitstreams".
Fatbitstreams bundle a bitstream for the FPGA with code to program the FPGA and python
driver code to interact with the design.

.. todo::
    elaborate what a fatbitsteam is
