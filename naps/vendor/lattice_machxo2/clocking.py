from pprint import pprint
from nmigen import *
from naps import StatusSignal

__all__ = ["Pll", "EClkSync", "ClkDiv", "Osc"]


class Pll(Elaboratable):
    vco_multipliers = list(range(2, 128))
    vco_dividers = list(range(1, 128))
    output_dividers = list(range(1, 128))

    @staticmethod
    def is_valid_vco_conf(input_freq, mul, div, exception=False):
        if not mul in Pll.vco_multipliers:
            if exception:
                raise ValueError
            return False
        if not div in Pll.vco_dividers:
            if exception:
                raise ValueError
            return False
        vco_freq = input_freq * mul / div
        if 200e6 > vco_freq:
            if exception:
                raise ValueError(vco_freq)
            return False
        if 800e6 < vco_freq:
            if exception:
                raise ValueError(vco_freq)
            return False
        return True

    def __init__(self, input_freq, vco_mul, vco_div, input_domain="sync"):
        Pll.is_valid_vco_conf(input_freq, vco_mul, vco_div, exception=True)
        self.vco_freq = input_freq * vco_mul / vco_div

        self.locked = StatusSignal()

        self.m = Module()

        clkop = Signal()
        clkfb = Signal()
        self.m.submodules.clkbufa = Instance(
            "CLKFBBUFA",
            i_A=clkop,
            o_Z=clkfb
        )

        self.output_port_names = ["CLKOS", "CLKOS2", "CLKOS3"]

        self.params = {
            "CLKI_DIV": vco_div,

            # we use OLKOP as our feedback path
            "CLKFB_DIV": vco_mul,
            "FEEDBK_PATH": "USERCLOCK",
            "CLKOP_DIV": 1,
            "CLKOP_ENABLE": "ENABLED",

            **{"{}_ENABLE".format(output): "DISABLED" for output in self.output_port_names}
        }
        self.attributes = {
            "FREQUENCY_PIN_CLKI": str(input_freq / 1e6),
            "FREQUENCY_PIN_CLKOP": str(self.vco_freq / 1e6),
        }

        self.clocks = []  # (signal, frequency, domain)

        self.clocks.append((clkop, self.vco_freq, None))
        self.inputs = {
            "CLKI": ClockSignal(input_domain),
            "RST": ResetSignal(input_domain),
            "CLKFB": clkfb,
        }
        self.outputs = {
            "LOCK": self.locked,
            "CLKOP": clkop,
        }

    def output_domain(self, domain_name, divisor):
        m = self.m

        cd = ClockDomain(domain_name)
        m.domains += cd
        self.clocks.append((cd.clk, self.vco_freq / divisor, domain_name))
        m.d.comb += ResetSignal(domain_name).eq(~self.locked)

        output_name = self.output_port_names.pop(0)
        self.outputs[output_name] = ClockSignal(domain_name)
        self.params["{}_DIV".format(output_name)] = divisor
        self.params["{}_ENABLE".format(output_name)] = "ENABLED"
        self.attributes["FREQUENCY_PIN_{}".format(output_name)] = str(self.vco_freq / divisor / 1e6)

    def elaborate(self, platform):
        m = self.m
        pprint({**{"p_{}".format(k): v for k, v in self.params.items()},
            **{"i_{}".format(k): v for k, v in self.inputs.items()},
            **{"o_{}".format(k): v for k, v in self.outputs.items()},})
        inst = m.submodules.inst = Instance(
            "EHXPLLJ",
            **{"p_{}".format(k): v for k, v in self.params.items()},
            **{"i_{}".format(k): v for k, v in self.inputs.items()},
            **{"o_{}".format(k): v for k, v in self.outputs.items()},
        )
        inst.attrs.update(self.attributes)

        for signal, frequency, domain in self.clocks:
            if hasattr(platform, "add_clock_constraint"):
                platform.add_clock_constraint(signal, frequency)
            elif domain is not None:
                platform.add_sim_clock(domain, frequency)

        return m


class EClkSync(Elaboratable):
    def __init__(self, input_domain, output_domain, input_frequency=None):
        self.input_frequency = input_frequency
        self.input_domain = input_domain
        self.output_domain = output_domain

    def elaborate(self, platform):
        m = Module()

        cd_output = ClockDomain(self.output_domain)
        m.domains += cd_output
        m.d.comb += ResetSignal(self.output_domain).eq(ResetSignal(self.input_domain))
        if self.input_frequency is not None:
            platform.add_clock_constraint(cd_output.clk, self.input_frequency)

        m.submodules.inst = Instance(
            "ECLKSYNCA",

            i_ECLKI=ClockSignal(self.input_domain),
            i_STOP=Const(0),
            o_ECLKO=ClockSignal(self.output_domain),
        )

        return m


class ClkDiv(Elaboratable):
    def __init__(self, input_domain, output_div_domain, div, bitslip=None, output_x1_domain=None, input_frequency=None):
        self.div = div
        self.output_div_domain = output_div_domain
        self.output_x1_domain = output_x1_domain
        self.input_frequency = input_frequency
        self.input_domain = input_domain
        self.bitslip = bitslip

    def elaborate(self, platform):
        m = Module()

        cd_div = ClockDomain(self.output_div_domain)
        m.domains += cd_div
        m.d.comb += ResetSignal(self.output_div_domain).eq(ResetSignal(self.input_domain))

        additional = {}
        if self.output_x1_domain is not None:
            cd_x1 = ClockDomain(self.output_x1_domain)
            m.domains = cd_x1
            m.d.comb += ResetSignal(self.output_x1_domain).eq(ResetSignal(self.input_domain))
            additional["o_CDIV1"] = ClockSignal(self.output_x1_domain)
            if self.input_frequency is not None:
                platform.add_clock_constraint(cd_x1.clk, self.input_frequency)
        if self.bitslip is not None:
            additional["i_ALIGNWD"] = self.bitslip

        if self.input_frequency is not None:
            platform.add_clock_constraint(cd_div.clk, self.input_frequency / self.div)

        m.submodules.inst = Instance(
            "CLKDIVC",
            p_DIV=str(float(self.div)),

            i_CLKI=ClockSignal(self.input_domain),
            o_CDIVX=ClockSignal(self.output_div_domain),
            **additional
        )

        return m


class Osc(Elaboratable):
    def __init__(self, output_domain="sync", freq=2.08e6):
        self.output_domain = output_domain
        self.freq = freq

    def elaborate(self, platform):
        m = Module()

        m.domains += ClockDomain(self.output_domain)
        inst = m.submodules.inst = Instance(
            "OSCH",

            o_OSC=ClockSignal(self.output_domain),
        )
        inst.attrs["NOM_FREQ"] = str(self.freq / 1e6)

        return m
