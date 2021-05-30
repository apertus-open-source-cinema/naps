import unittest

import pytest

from naps import SimPlatform, do_nothing
from naps.stream import BasicStream, verify_stream_output_contract, write_to_stream, read_from_stream
from . import UnbufferedAsyncStreamFIFO, BufferedAsyncStreamFIFO, UnbufferedSyncStreamFIFO, \
    BufferedSyncStreamFIFO


class TestFifo(unittest.TestCase):
    def check_fifo_basic(self, fifo_generator):
        input = BasicStream(32)
        fifo = fifo_generator(input, 1024)

        def testbench():
            for i in range(10):
                yield from write_to_stream(input, payload=i)

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
    def test_async_stream_fifo_output_properties(self):
        input = BasicStream(32)
        verify_stream_output_contract(UnbufferedAsyncStreamFIFO(input, 10, o_domain="sync", i_domain="sync"))

    def test_async_stream_fifo_buffered_output_properties(self):
        input = BasicStream(32)
        verify_stream_output_contract(BufferedAsyncStreamFIFO(input, 10, o_domain="sync", i_domain="sync"))

    @pytest.mark.skip("this can not be proven at the moment nmigen emits code that triggers a yosys assertion")
    def test_sync_stream_fifo_output_properties(self):
        input = BasicStream(32)
        verify_stream_output_contract(UnbufferedSyncStreamFIFO(input, 10))

    def test_sync_stream_fifo_buffered_output_properties(self):
        input = BasicStream(32)
        verify_stream_output_contract(BufferedSyncStreamFIFO(input, 10))
