import unittest

from . import CounterStreamSource
from ...stream.formal_util import stream_contract_test


class CounterStreamSourceTest(unittest.TestCase):
    @stream_contract_test
    def test_stream_contract(self, plat, m):
        m.submodules.counter_src = src = CounterStreamSource(32)
        return src.output
