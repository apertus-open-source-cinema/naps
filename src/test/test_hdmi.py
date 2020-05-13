from nmigen import *
from nmigen.back.pysim import Simulator
from nmigen.test.utils import FHDLTestCase
from tqdm import tqdm

from modules.hdmi import TimingGenerator, Hdmi
from util.bundle import Bundle
from util.nmigen import get_signals
from util.sim import sim


class TestHdmi(FHDLTestCase):
    def test_timing_generator(self):
        dut = TimingGenerator(640, 480, 60)

        def testbench():
            last_x = 0
            for i in range(800):
                yield
                this_x = (yield dut.x)
                assert this_x == last_x + 1, "x increment failed"
                last_x = this_x
            yield
            assert 1 == (yield dut.y), "y increment failed"

        sim(dut, testbench, filename="hdmi_timing_generator", traces=get_signals(dut))

    def test_until_encoder(self):
        class Pins(Bundle):
            data = Signal(3)
            clock = Signal()

        dut = Hdmi(640, 480, 60, Pins(), generate_clocks=False)

        simulator = Simulator(dut)
        simulator.add_clock(1 / 117.5e6, domain="pix")
        simulator.add_clock(1 / (117.5e6 * 5), domain="pix5x")
        filename = "hdmi"
        with simulator.write_vcd(".sim_{}.vcd".format(filename), ".sim_{}.gtkw".format(filename),
                                 traces=get_signals(dut)):
            deadline = 1 / 60 / 100
            with tqdm(total=deadline) as pbar:
                last_timestamp = 0
                while simulator._state.timestamp < deadline:
                    pbar.update(simulator._state.timestamp - last_timestamp)
                    last_timestamp = simulator._state.timestamp
                    simulator.step()


if __name__ == "__main__":
    TestHdmi().test_until_encoder()
