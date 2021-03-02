from nmigen import *
from nmigen import Elaboratable, Module, ClockSignal, ResetSignal, Cat
from naps import ControlSignal, StatusSignal, is_signal_inverted
from ..instance_helper import InstanceHelper

__all__ = ["OSerdes10", "IDelayCtrl", "IDelay", "DDRDeserializer", "DDRSerializer"]


_OSerdes = InstanceHelper("+/xilinx/cells_xtra.v", "OSERDESE2")
_ISerdes = InstanceHelper("+/xilinx/cells_xtra.v", "ISERDESE2")
_IDelay = InstanceHelper("+/xilinx/cells_xtra.v", "IDELAYE2")
_IDelayCtrl = InstanceHelper("+/xilinx/cells_xtra.v", "IDELAYCTRL")


class OSerdes10(Elaboratable):
    def __init__(self, input: Signal, pad: Signal, domain: str, domain_5x: str):
        self.pad = pad
        self.input = input

        self.domain = domain
        self.domain_5x = domain_5x

    def elaborate(self, platform):
        m = Module()

        self.invert = ControlSignal(reset=is_signal_inverted(platform, self.pad))

        data = Signal.like(self.input)
        m.d[self.domain] += data.eq(self.input ^ Repl(self.invert, len(self.input)))

        ce = Signal()
        m.d.comb += ce.eq(~ResetSignal(self.domain))

        shift = Signal(2)

        m.submodules += Instance("OSERDESE2",
                                 p_DATA_WIDTH=10, p_TRISTATE_WIDTH=1,
                                 p_DATA_RATE_OQ="DDR", p_DATA_RATE_TQ="SDR",
                                 p_SERDES_MODE="MASTER",

                                 o_OQ=self.pad,
                                 i_OCE=ce,
                                 i_TCE=0,
                                 i_RST=ResetSignal(self.domain),
                                 i_CLK=ClockSignal(self.domain_5x), i_CLKDIV=ClockSignal(self.domain),
                                 i_D1=data[0], i_D2=data[1],
                                 i_D3=data[2], i_D4=data[3],
                                 i_D5=data[4], i_D6=data[5],
                                 i_D7=data[6], i_D8=data[7],

                                 i_SHIFTIN1=shift[0], i_SHIFTIN2=shift[1],
                                 )

        m.submodules += Instance("OSERDESE2",
                                 p_DATA_WIDTH=10, p_TRISTATE_WIDTH=1,
                                 p_DATA_RATE_OQ="DDR", p_DATA_RATE_TQ="SDR",
                                 p_SERDES_MODE="SLAVE",

                                 i_OCE=ce,
                                 i_TCE=0,
                                 i_RST=ResetSignal(self.domain),
                                 i_CLK=ClockSignal(self.domain_5x), i_CLKDIV=ClockSignal(self.domain),
                                 i_D1=0, i_D2=0,
                                 i_D3=data[8], i_D4=data[9],
                                 i_D5=0, i_D6=0,
                                 i_D7=0, i_D8=0,

                                 i_SHIFTIN1=0, i_SHIFTIN2=0,
                                 o_SHIFTOUT1=shift[0], o_SHIFTOUT2=shift[1]
                                 )

        return m


class IDelayCtrl(Elaboratable):
    def __init__(self, refclk_domain):
        self.refclk_domain = refclk_domain
        self.ready = StatusSignal()

    def elaborate(self, platform):
        m = Module()

        idelay_ctl = m.submodules.idelay_ctl = _IDelayCtrl()
        m.d.comb += self.ready.eq(idelay_ctl.rdy)
        m.d.comb += idelay_ctl.refclk.eq(ClockSignal(self.refclk_domain))
        m.d.comb += idelay_ctl.rst.eq(ResetSignal(self.refclk_domain))

        return m


class IDelay(Elaboratable):
    def __init__(self, pin):
        self.pin = pin

        self.delay = ControlSignal(5)
        self.load = ControlSignal()

        self.output = Signal()

    def elaborate(self, platform):
        m = Module()

        idelay = m.submodules.idelay = _IDelay(
            delay_src="iDataIn",
            signal_pattern="data",
            cinvctrl_sel=False,
            high_performance_mode=True,
            refclk_frequency=200.0,
            pipe_sel=False,
            idelay_type="var_load",
            idelay_value=0
        )
        m.d.comb += idelay.c.eq(ClockSignal())  # this is really the clock to which the control inputs are syncronous!
        m.d.comb += idelay.ld.eq(self.load)
        m.d.comb += idelay.ldpipeen.eq(0)
        m.d.comb += idelay.ce.eq(0)
        m.d.comb += idelay.inc.eq(0)
        m.d.comb += idelay.cntvalue.in_.eq(self.delay)
        m.d.comb += idelay.idatain.eq(self.pin)
        m.d.comb += self.output.eq(idelay.data.out)

        return m


class DDRSerializer(Elaboratable):
    def __init__(self, value, pad, ddr_domain, bit_width=8, msb_first=False):
        self.msb_first = msb_first
        self.bit_width = bit_width
        self.ddr_domain = ddr_domain
        self.value = value
        self.pad = pad

    def elaborate(self, platform):
        m = Module()

        self.invert = ControlSignal(reset=is_signal_inverted(platform, self.pad))

        oserdes = m.submodules.oserdes = _OSerdes(
            data_width=self.bit_width,
            tristate_width=1,
            data_rate_oq="ddr",
            serdes_mode="master",
            data_rate_tq="buf"
        )
        m.d.comb += oserdes.oce.eq(1)
        m.d.comb += oserdes.clk.eq(ClockSignal(self.ddr_domain))
        m.d.comb += oserdes.clkdiv.eq(ClockSignal())
        m.d.comb += oserdes.rst.eq(ResetSignal())
        m.d.comb += Cat(oserdes.d[i] for i in (range(1, 9) if self.msb_first else reversed(range(1, 9)))).eq(self.value ^ self.invert)
        m.d.comb += self.pad.eq(oserdes.oq)

        return m


class DDRDeserializer(Elaboratable):
    def __init__(self, pad, ddr_domain, bit_width=8, msb_first=False):
        self.msb_first = msb_first
        self.bit_width = bit_width
        self.ddr_domain = ddr_domain
        self.pad = pad

        self.bitslip = Signal()
        self.output = Signal(bit_width)

    def elaborate(self, platform):
        m = Module()

        iserdes = m.submodules.iserdes = _ISerdes(
            data_width=self.bit_width,
            data_rate="ddr",
            serdes_mode="master",
            interface_type="networking",
            num_ce=1,
            iobDelay="ifd",
        )
        m.d.comb += iserdes.ddly.eq(self.pad)
        m.d.comb += iserdes.ce[1].eq(1)
        m.d.comb += iserdes.clk.eq(ClockSignal(self.ddr_domain))
        m.d.comb += iserdes.clkb.eq(~ClockSignal(self.ddr_domain))
        m.d.comb += iserdes.rst.eq(ResetSignal())
        m.d.comb += iserdes.clkdiv.eq(ClockSignal())
        m.d.comb += self.output.eq(Cat(iserdes.q[i] for i in (range(1, 9) if self.msb_first else reversed(list(range(1, 9))))))
        m.d.comb += iserdes.bitslip.eq(self.bitslip)

        return m
