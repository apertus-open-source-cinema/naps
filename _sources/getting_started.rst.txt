Getting started
=================

Now that you have a :ref:`working installation of naps and decided on working either
in-tree or out-of-tree<Project Setup & Installation>`, you can start writing your first design.

For this, we create a new file named ``blinky.py`` (if you work in-tree in the ``applets/`` directory)
and put the following code in it::

    from amaranth import *
    from naps import *

    class Top(Elaboratable):
        runs_on = [Colorlight5a75b70Platform]

        def __init__(self):
            pass

        def elaborate(self, platform):
            m = Module()

            led = platform.request("user_led")
            counter = Signal(16)
            with m.If(counter == int(25e6)):
                m.d.sync += led.o.eq(~led.o)
                m.d.sync += counter.eq(0)
            with m.Else():
                m.d.sync += counter.eq(counter + 1)

            return m

    if __name__ == "__main__":
        cli(Top)


You can now "elaborate" and build this design using the naps cli. "Elaboration"
(``-e``) means that we execute all the python code and generate verilog / rtlil
that then could be fed into the vendor toolchain for building (``-b``)::

    pdm run python blinky.py -s JTAG -e -b

With the ``-s JTAG`` flag, we specify that we want to use the "JTAGSoc". What that means will be 
explained in the :ref:`naps.soc` section. 

To actually program the board, we can add the ``-p`` flag::

    pdm run python blinky.py -s JTAG -e -b -p

This should give you a blinking LED on your board.

The ``Colorlight5a75b70Platform`` class currently assumes that it is connected to a
jlink USB to JTAG adapter. If you have a different board, you can create a board description
similiar for it as described in the :ref:`naps.platform` section.

After this, you have everything set up to start exploring and using naps.
The rest of the documentation is organized by package and you can skip around.
Still, the documentation here is ordered in a somewhat sensible way and it is 
recomended that you read at least the documentation for the `naps.soc` package
before you go on. 
