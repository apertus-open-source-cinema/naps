import unittest

import pytest
from amaranth.lib import wiring

from naps import SimPlatform, do_nothing, FormalPlatform
from naps.stream import write_to_stream, read_from_stream
from . import UnbufferedAsyncStreamFIFO, BufferedAsyncStreamFIFO, UnbufferedSyncStreamFIFO, \
    BufferedSyncStreamFIFO
from naps.stream.formal_util import StreamOutputCoverSpec, stream_contract_test


class TestFifo(unittest.TestCase):
    def check_fifo_basic(self, fifo_generator):
        fifo = fifo_generator(32, 1024)

        def testbench():
            for i in range(10):
                yield from write_to_stream(fifo.input, i)

            # async fifos need some time due to cdc
            yield from do_nothing()

            assert (yield fifo.r_level) == 10

            for i in range(10):
                assert (yield from read_from_stream(fifo.output)) == i, "read data doesnt match written data"

        platform = SimPlatform()
        platform.add_sim_clock("sync", 100e6)
        platform.sim(fifo, testbench)

    def test_sim_async_stream_fifo(self):
        fifo_gen = lambda input, depth: UnbufferedAsyncStreamFIFO(input, depth, o_domain="sync", i_domain="sync")
        self.check_fifo_basic(fifo_gen)

    def test_async_stream_fifo_buffered(self):
        fifo_gen = lambda input, depth: BufferedAsyncStreamFIFO(input, depth, o_domain="sync", i_domain="sync")
        self.check_fifo_basic(fifo_gen)

    def test_sync_stream_fifo(self):
        fifo_gen = lambda input, depth: UnbufferedSyncStreamFIFO(input, depth)
        self.check_fifo_basic(fifo_gen)

    def test_sync_stream_fifo_buffered(self):
        fifo_gen = lambda input, depth: BufferedSyncStreamFIFO(input, depth)
        self.check_fifo_basic(fifo_gen)

    @pytest.mark.skip("this can not be proven at the moment because a FFSyncronizer in the async FIFO is resetless")
    @stream_contract_test
    def test_async_stream_fifo_output_properties(self, plat, m):
        m.submodules.fifo = fifo = UnbufferedAsyncStreamFIFO(32, 10, o_domain="sync", i_domain="sync")
        wiring.connect(m, fifo.input, plat.request_port(fifo.input))
        return fifo.output

    @stream_contract_test
    def test_async_stream_fifo_buffered_output_properties(self, plat, m):
        m.submodules.fifo = fifo = BufferedAsyncStreamFIFO(32, 10, o_domain="sync", i_domain="sync")
        wiring.connect(m, fifo.input, plat.request_port(fifo.input))
        return fifo.output

    @stream_contract_test
    def test_sync_stream_fifo_output_properties(self, plat, m):
        m.submodules.fifo = fifo = UnbufferedSyncStreamFIFO(32, 10)
        wiring.connect(m, fifo.input, plat.request_port(fifo.input))
        return fifo.output

    @stream_contract_test
    def test_sync_stream_fifo_buffered_output_properties(self, plat, m):
        m.submodules.fifo = fifo = BufferedSyncStreamFIFO(32, 10)
        wiring.connect(m, fifo.input, plat.request_port(fifo.input))
        return fifo.output
