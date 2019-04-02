from nmigen import *
from nmigen.cli import main
from modules.ps7 import layouts
import pandas as pd
from os import path

from util.nmigen_util import get_signals


class Ps7:
    """Wraps the processing system of the Xilinx Zynq.
    """

    def __init__(self):
        self.axi_gp_master = [Record(layouts.axi_gp_master, name="MAXIGP{}".format(i)) for i in range(2)]
        self.axi_gp_slave = [Record(layouts.axi_gp_slave, name="SAXIGP{}".format(i)) for i in range(2)]
        self.axi_hp_slave = [Record(layouts.axi_hp_slave, name="SAXIHP{}".format(i)) for i in range(4)]
        self.axi_acp_slave = [Record(layouts.axi_acp_slave, name="SAXIACP") for i in range(1)]

    def elaborate(self, platform):
        m = Module()

        filename = path.join(path.dirname(__file__), "ps7_signals.csv")
        ps7_signals = pd.read_csv(filename, skip_blank_lines=True, comment='#')

        named_ports = {
            "{}_{}".format(row["direction"], row["name"]): self.find_signal(row["name"], row["width"])
            for _, row in ps7_signals.iterrows()
        }
        m.submodules.ps7 = Instance("ps7", **named_ports)

        return m

    def find_signal(self, name, width):
        """Looks for a similar named signal

        :param name: the name to look for
        :return: the closest match, if any acceptable thing was found
        """

        signals = get_signals(self)

        def prepossess_string(s):
            return s.replace("_", "").upper()

        to_consider = [signal for signal in signals if prepossess_string(signal.name) == prepossess_string(name)]

        if len(to_consider) == 1:
            result = to_consider[0]
            assert len(result) == width
        else:
            assert "AXI" not in name  # ensure all axi signals are mapped sucessfully
            result = Signal(width, name=name)

        return result


if __name__ == "__main__":
    m = Ps7()
    main(m, ports=get_signals(m))
