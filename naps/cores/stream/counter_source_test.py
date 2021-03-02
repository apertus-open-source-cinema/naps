import unittest

from . import CounterStreamSource
from naps import verify_stream_output_contract


class CounterStreamSourceTest(unittest.TestCase):
    def test_stream_contract(self):
        verify_stream_output_contract(CounterStreamSource(32))
