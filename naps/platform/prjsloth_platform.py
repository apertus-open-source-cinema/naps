#!/usr/bin/env python3

from amaranth.build import Resource, Subsignal, Pins, DiffPairs, Attrs, PinsN
from amaranth_boards.zturn_lite_z010 import ZTurnLiteZ010Platform
from amaranth_boards.resources import SPIResource, I2CResource

__all__ = ["PrjSlothPlatform"]


class PrjSlothPlatform(ZTurnLiteZ010Platform):
    def __init__(self):
        super().__init__()
        self.add_resources([
            Resource("hmcad1511", 0,
                        Subsignal("d", DiffPairs("4 10 14 22 32 36 42 52", "6 12 16 24 34 38 44 54", dir='i', conn=("expansion", 0)), Attrs(IOSTANDARD="LVDS_25", DIFF_TERM="TRUE")),
                        Subsignal("lclk", DiffPairs("26", "28", dir='i', conn=("expansion", 0)), Attrs(IOSTANDARD="LVDS_25", DIFF_TERM="TRUE")),
                        Subsignal("fclk", DiffPairs("46", "48", dir='i', conn=("expansion", 0)), Attrs(IOSTANDARD="LVDS_25", DIFF_TERM="TRUE")),
                        Subsignal("clk", DiffPairs("56", "58", dir='o', conn=("expansion", 0)), Attrs(IOSTANDARD="LVDS_25", DIFF_TERM="TRUE")),
                        Subsignal("reset", PinsN("3", dir='o', conn=("expansion", 0)), Attrs(IOSTANDARD="LVCMOS25")),
                        Subsignal("power_down", Pins("9", dir='o', conn=("expansion", 0)), Attrs(IOSTANDARD="LVCMOS25")),
                     ),

            # hmcad
            SPIResource("hmcad1511_spi", 0,
                        cs_n="13", clk="5", copi="11", cipo="35",
                        attrs=Attrs(IOSTANDARD="LVCMOS25"),
                        conn=("expansion", 0)
            ),
            Resource("power_ctl", 0,
                     Subsignal("en_sensor_1v3", Pins("15", dir='o', conn=("expansion", 0)), Attrs(IOSTANDARD="LVCMOS25")),
                     Subsignal("en_sensor_1v5", Pins("21", dir='o', conn=("expansion", 0)), Attrs(IOSTANDARD="LVCMOS25")),
                     Subsignal("en_sensor_2v0", Pins("23", dir='o', conn=("expansion", 0)), Attrs(IOSTANDARD="LVCMOS25")),
                     Subsignal("en_sensor_3v3", Pins("25", dir='o', conn=("expansion", 0)), Attrs(IOSTANDARD="LVCMOS25")),
                     Subsignal("en_sensor_5v0", Pins("27", dir='o', conn=("expansion", 0)), Attrs(IOSTANDARD="LVCMOS25")),
                     Subsignal("en_sensor_hv", Pins("31", dir='o', conn=("expansion", 0)), Attrs(IOSTANDARD="LVCMOS25")),
                     Subsignal("en_adc_1v8", Pins("33", dir='o', conn=("expansion", 0)), Attrs(IOSTANDARD="LVCMOS25")),
                     ),
            # current sense (ina226)
            # sensor_3v3: 0x80
            # sensor_2v0: 0x82
            # sensor_1v5: 0x84
            # sensor_1v3: 0x86
            # sensor_5v0: 0x8A
            # sensor_-1v3: 0x88
        I2CResource(0,
            scl="88", sda="90",
                    attrs=Attrs(IOSTANDARD="LVCMOS33"),
                        conn=("expansion", 0)
        ),
            Resource("sensors_digital", 0,
                     # D6
                     Subsignal("px_clk_top", Pins("62", dir='o', conn=("expansion", 0)), Attrs(IOSTANDARD="LVCMOS33")),
                     # J5
                     Subsignal("px_clk_bot", Pins("100", dir='o', conn=("expansion", 0)), Attrs(IOSTANDARD="LVCMOS33")),
                     # C5
                     Subsignal("frame_rst", Pins("80", dir='o', conn=("expansion", 0)), Attrs(IOSTANDARD="LVCMOS33")),
                     # C3 C6 C17 J8 (J9 line_exp) J10 J11 J12 J15 J16 J17 J18 (J21 line_rst)
                     Subsignal("line", Pins("76 84 73 104 106 108 98 109 89 95 105 103 93", dir='o', conn=("expansion", 0)), Attrs(IOSTANDARD="LVCMOS33")),
                     # C13 C8 C4 D3 D4 J3 J14 J22
                     Subsignal("zero", Pins("75 86 78 74 64 110 85 87", dir='o', conn=("expansion", 0)), Attrs(IOSTANDARD="LVCMOS33")),
                     # C14
                     Subsignal("s_data", Pins("61", dir='o', conn=("expansion", 0)), Attrs(IOSTANDARD="LVCMOS33")),
                     # C15
                     Subsignal("s_clk", Pins("63", dir='o', conn=("expansion", 0)), Attrs(IOSTANDARD="LVCMOS33")),
                     # C16
                     Subsignal("s_cs", Pins("71", dir='o', conn=("expansion", 0)), Attrs(IOSTANDARD="LVCMOS33")),
                     )

        ])
