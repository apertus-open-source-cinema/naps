from textwrap import dedent

from nmigen.build import *
from nmigen.vendor.lattice_machxo_2_3l import *

from naps import program_fatbitstream_ssh

__all__ = ["Usb3PluginPlatform"]

from naps.soc.fatbitstream import File


class Usb3PluginPlatform(LatticeMachXO2Platform):
    device = "LCMXO2-2000HC"
    package = "TG100"
    speed = "6"

    resources = [
        Resource("ft601", 0,
            Subsignal("reset", PinsN("4", dir="o"), Attrs(IO_TYPE="LVCMOS33")),

            Subsignal("data", Pins("75 74 70 69 68 67 66 65 64 61 60 59 58 57 54 53 83 84 85 86 87 88 96 97 98 99 7 8 21 24 20 25", dir="o"), Attrs(IO_TYPE="LVCMOS33")),
            Subsignal("be", Pins("19 18 17 16", dir="o"), Attrs(IO_TYPE="LVCMOS33")),
            Subsignal("oe", PinsN("9", dir="o"), Attrs(IO_TYPE="LVCMOS33")),

            Subsignal("read", PinsN("10", dir="o"), Attrs(IO_TYPE="LVCMOS33")),
            Subsignal("write", PinsN("12", dir="o"), Attrs(IO_TYPE="LVCMOS33")),
            Subsignal("siwu", PinsN("13", dir="o"), Attrs(IO_TYPE="LVCMOS33")),
            Subsignal("rxf", PinsN("14", dir="i"), Attrs(IO_TYPE="LVCMOS33")),
            Subsignal("txe", PinsN("15", dir="i"), Attrs(IO_TYPE="LVCMOS33")),

            Subsignal("gpio", Pins("2 1", dir="io"), Attrs(IO_TYPE="LVCMOS33")),
            Subsignal("wakeup", PinsN("3", dir="io"), Attrs(IO_TYPE="LVCMOS33")),

            Subsignal("clk", Pins("63", dir="i"), Attrs(IO_TYPE="LVCMOS33"), Clock(100e6)),
            Subsignal("clk1", Pins("62", dir="i"), Attrs(IO_TYPE="LVCMOS33"), Clock(100e6)),

            ),

        Resource("led", 0, Pins("71", dir="o"), Attrs(IO_TYPE="LVCMOS33")),

        Resource("plugin_stream_input", 0,
            # BEWARE: all of these inputs are inverted but cant be inverted here (they have to be inverted after the iserdes)
            Subsignal("valid", DiffPairs("45", "47", dir="i"), Attrs(IO_TYPE="LVDS25", DIFFRESISTOR="100")),  # lvds0
            Subsignal("lvds0", DiffPairs("42", "43", dir="i"), Attrs(IO_TYPE="LVDS25", DIFFRESISTOR="100")),  # lvds1
            Subsignal("lvds1", DiffPairs("40", "41", dir="i"), Attrs(IO_TYPE="LVDS25", DIFFRESISTOR="100")),  # lvds2
            Subsignal("lvds2", DiffPairs("36", "37", dir="i"), Attrs(IO_TYPE="LVDS25", DIFFRESISTOR="100")),  # lvds3 TODO: move to 37 / 38 in the next rev
            Subsignal("lvds3", DiffPairs("29", "30", dir="i"), Attrs(IO_TYPE="LVDS25", DIFFRESISTOR="100")),  # lvds4
            Subsignal("clk_word", DiffPairs("34", "35", dir="i"), Attrs(IO_TYPE="LVDS25", DIFFRESISTOR="100"), Clock(50e6)),  # lvds5
        )
    ]
    connectors = []

    def generate_openocd_conf(self):
        yield File("openocd_micro.cfg", dedent(r"""
            adapter driver sysfsgpio
    
            sysfsgpio_tms_num 898
            sysfsgpio_tck_num 899
            sysfsgpio_tdi_num 900
            sysfsgpio_tdo_num 901
            
            bindto 0.0.0.0
            transport select jtag
            jtag newtap dut tap -expected-id 0x012bb043 -irlen 8 -irmask 0xFF
            init
            scan_chain
        """))
        yield File("openoc_beta.cfg", dedent(r"""
            adapter driver rfdev_jtag
            rfdev_set_device /dev/rfjtag1 
    
            bindto 0.0.0.0
            transport select jtag
            jtag newtap dut tap -expected-id 0x012bb043 -irlen 8 -irmask 0xFF
            init
            scan_chain
        """))
        yield "[ $(cat /etc/hostname) == 'beta' ] && cp openocd_beta.cfg openocd.cfg || cp openocd_micro.cfg openocd.cfg"

    def program_fatbitstream(self, name, **kwargs):
        program_fatbitstream_ssh(name, **kwargs)
