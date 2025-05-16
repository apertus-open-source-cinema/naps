import unittest

from amaranth import Signal, Shape

from naps import out_of_band_signals, Packet, real_payload, substitute_payload


class PacketTestCase(unittest.TestCase):
    def rlist(self, s):
        return list(map(repr, s))

    def test_oob_signals_no_packet(self):
        a = Signal()
        expected = []
        self.assertListEqual(self.rlist(out_of_band_signals(a)), self.rlist(expected))

    def test_oob_signals_one_layer(self):
        a = Signal(Packet(1))
        expected = [a.last]
        self.assertListEqual(self.rlist(out_of_band_signals(a)), self.rlist(expected))

    def test_oob_signals_two_layers(self):
        a = Signal(Packet(Packet(1)))
        expected = [a.last, a.p.last]
        self.assertListEqual(self.rlist(out_of_band_signals(a)), self.rlist(expected))

    def test_real_payload_passthrough(self):
        s = Signal()
        self.assertIs(real_payload(s), s)

    def test_real_payload_one_layer(self):
        pkg = Signal(Packet(1))
        assert repr(real_payload(pkg)) == repr(pkg.p)

    def test_real_payload_two_layer(self):
        pkg = Signal(Packet(Packet(1)))
        assert repr(real_payload(pkg)) == repr(pkg.p.p)

    def test_substitute_payload_passthrough(self):
        shape = Shape(1)
        assert Shape.cast(substitute_payload(shape, 32)) == Shape.cast(32)

    def test_substitute_payload_one_layer(self):
        shape = Packet(1)
        assert substitute_payload(shape, 32) == Packet(32)

    def test_substitute_payload_two_layers(self):
        shape = Packet(Packet(1))
        assert substitute_payload(shape, 32) == Packet(Packet(32))
