import unittest

from lib.bus.stream.counter_source import CounterStreamSource
from lib.bus.stream.formal_util import verify_stream_output_contract


class CounterStreamSourceTest(unittest.TestCase):
    def test_stream_contract(self):
        verify_stream_output_contract(CounterStreamSource(32))
