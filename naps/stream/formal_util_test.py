import unittest

from nmigen import *

from naps.stream.formal_util import verify_stream_output_contract, LegalStreamSource
from naps import BasicStream


class BrokenStreamSource(Elaboratable):
    def __init__(self, mode):
        self.output = BasicStream(32)
        self.mode = mode

    def elaborate(self, platform):
        m = Module()

        if self.mode == "valid_is_ready":
            m.d.comb += self.output.valid.eq(self.output.ready)
        elif self.mode == "payload_unsteady":
            m.d.sync += self.output.payload.eq(self.output.payload + 1)
            m.d.comb += self.output.valid.eq(1)
        elif self.mode == "dont_wait_for_ready":
            m.d.sync += self.output.valid.eq(~self.output.valid)

        return m


class FormalUtilTestCase(unittest.TestCase):
    def test_catch_valid_depends_on_ready(self):
        with self.assertRaises(AssertionError):
            verify_stream_output_contract(BrokenStreamSource("valid_is_ready"))

    def test_catch_changing_payload(self):
        with self.assertRaises(AssertionError):
            verify_stream_output_contract(BrokenStreamSource("payload_unsteady"))

    def test_catch_dont_wait_for_ready(self):
        with self.assertRaises(AssertionError):
            verify_stream_output_contract(BrokenStreamSource("dont_wait_for_ready"))

    def test_legal_stream_source(self):
        verify_stream_output_contract(LegalStreamSource(BasicStream(32)))
