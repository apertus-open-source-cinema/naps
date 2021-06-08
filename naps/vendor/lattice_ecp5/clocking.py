from math import floor
from pprint import pprint
from nmigen import *
from naps import StatusSignal

__all__ = ["Pll"]


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
        if 400e6 > vco_freq:
            if exception:
                raise ValueError(f"{vco_freq} Hz is too small for the VCO frequency. Minimum 400 Mhz")
            return False
        if 800e6 < vco_freq:
            if exception:
                raise ValueError(f"{vco_freq} Hz is too big for the VCO frequency. Maximum 800 Mhz")
            return False
        return True

    def __init__(self, input_freq, vco_mul, vco_div, input_domain="sync", reset_less_input=False):
        Pll.is_valid_vco_conf(input_freq, vco_mul, vco_div, exception=True)
        self.vco_freq = input_freq * vco_mul / vco_div

        self.locked = StatusSignal()

        self.m = Module()

        clkop = Signal()

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
            "RST": Const(0) if reset_less_input else ResetSignal(input_domain),
            "CLKFB": clkop,
        }
        self.outputs = {
            "LOCK": self.locked,
            "CLKOP": clkop,
        }

    def output_domain(self, domain_name, divisor, phase=0.0):
        m = self.m

        freq = self.vco_freq / divisor

        ns_shift = 1 / freq * 1e6 * phase / 360.0
        phase_count = ns_shift * self.vco_freq
        cphase = floor(phase_count)
        fphase = floor((phase_count - cphase) * 8)

        cd = ClockDomain(domain_name)
        m.domains += cd
        self.clocks.append((cd.clk, self.vco_freq / divisor, domain_name))
        m.d.comb += ResetSignal(domain_name).eq(~self.locked)

        output_name = self.output_port_names.pop(0)
        self.outputs[output_name] = ClockSignal(domain_name)
        self.params[f"{output_name}_DIV"] = divisor
        self.params[f"{output_name}_ENABLE"] = "ENABLED"
        self.params[f"{output_name}_CPHASE"] = cphase
        self.params[f"{output_name}_FPHASE"] = fphase
        self.attributes[f"FREQUENCY_PIN_{output_name}"] = str(freq / 1e6)

    def elaborate(self, platform):
        m = self.m
        inst = m.submodules.inst = Instance(
            "EHXPLLL",
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
