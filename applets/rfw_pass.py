# Pass through gateware to program the usb3 plugin module on the Beta
# basically a nMigen adaption of http://vserver.13thfloor.at/Stuff/AXIOM/BETA/pass_jtag/
from nmigen import *
from naps import *


class Top(Elaboratable):
    def elaborate(self, platform):
        m = Module()

        usb3_plugin_connect(platform, "south", gpio=True, lvds=False, gpio_attrs=dict(IO_TYPE="LVCMOS33", PULLMODE="UP", DRIVE="4"))

        usb3 = platform.request("usb3_plugin", "south")
        pic_io = platform.request("pic_io")

        def connect(output, input, invert=False):
            m.d.comb += output.o.eq(~input.i if invert else input.i)
            m.d.comb += output.oe.eq(1)
            m.d.comb += input.oe.eq(0)

        connect(usb3.jtag.tdi, pic_io.sdo)
        connect(usb3.jtag.tck, pic_io.sck)
        connect(usb3.jtag_enb, pic_io.ss)
        connect(usb3.init, pic_io.initn, invert=True)
        connect(pic_io.done, usb3.done, invert=True)
        connect(pic_io.sdi, usb3.jtag.tdo)
        connect(usb3.jtag.tms, pic_io.sn)
        connect(usb3.program, pic_io.pb22b, invert=True)

        return m


if __name__ == "__main__":
    cli(Top, runs_on=(BetaRFWPlatform,))
