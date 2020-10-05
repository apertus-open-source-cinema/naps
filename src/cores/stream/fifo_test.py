import unittest

from nmigen.sim import Simulator
from nmigen import *
from cores.stream.fifo_out_of_tree_fix import AsyncFIFO

from cores.stream.fifo import AsyncStreamFifo
from cores.stream.sim_util import write_to_stream, read_from_stream
from util.stream import StreamEndpoint


class TestFifo(unittest.TestCase):
    def test_sim_async_fifo(self):
        m = Module()
        fifo = m.submodules.fifo = AsyncFIFO(width=32, depth=8, r_domain="sync", w_domain="sync")

        def testbench():
            for i in range(20):
                yield fifo.w_data.eq(i)
                yield fifo.w_en.eq(1)
                yield
            yield fifo.w_en.eq(0)
            yield
            yield
            yield
            yield

            assert (yield fifo.r_level) == 8

        simulator = Simulator(m)
        simulator.add_clock(1 / 100e6, domain="sync")
        simulator.add_sync_process(testbench, domain="sync")
        simulator.run()

    def test_sim_asnyc_stream_fifo(self):
        m = Module()
        input = StreamEndpoint(32, is_sink=False, has_last=False)
        fifo = m.submodules.fifo = AsyncStreamFifo(input, 1024, r_domain="sync", w_domain="sync", buffered=False)

        def testbench():
            for i in range(10):
                yield from write_to_stream(input, i)

            # async fifos need some time
            yield
            yield

            assert (yield fifo.r_level) == 10

            for i in range(10):
                assert (yield from read_from_stream(fifo.output)) == i

        simulator = Simulator(m)
        simulator.add_clock(1 / 100e6, domain="sync")
        simulator.add_sync_process(testbench, domain="sync")
        simulator.run()
