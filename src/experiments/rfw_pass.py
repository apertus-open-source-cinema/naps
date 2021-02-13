# Pass through gateware to program the usb3 plugin module on the Beta
# basically a nMigen adaption of http://vserver.13thfloor.at/Stuff/AXIOM/BETA/pass_jtag/

from nmigen import *

from devices.beta_platform import BetaRFWPlatform
from devices.plugins.usb3_plugin_resource import usb3_plugin_connect
from soc.cli import cli


class Top(Elaboratable):
    def elaborate(self, platform):
        m = Module()

        usb3_plugin_connect(platform, "north", gpio=True, lvds=False, gpio_attrs=dict(IO_TYPE="LVCMOS33", PULLMODE="UP", DRIVE="4"))

        usb3 = platform.request("usb3_plugin", "north")
        pic_io = platform.request("pic_io")

        def connect(input, output):
            m.d.comb += output.o.eq(input.i)
            m.d.comb += output.oe.eq(1)
            m.d.comb += input.oe.eq(0)

        connect(pic_io.done, usb3.jtag.tms)
        connect(pic_io.sdi, usb3.jtag.tck)
        connect(pic_io.sn, usb3.jtag.tdi)
        connect(usb3.jtag.tdo, pic_io.pb22b)
        connect(pic_io.sdo, usb3.jtag_enb)
        connect(pic_io.sck, usb3.program)
        connect(pic_io.ss, usb3.init)
        connect(usb3.done, pic_io.initn)

        return m


if __name__ == "__main__":
    cli(Top, runs_on=(BetaRFWPlatform,))
