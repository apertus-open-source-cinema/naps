import unittest
import random
from nmigen import *
from naps import SimPlatform
from naps.cores.hdmi.tx.tmds_encoder import TmdsEncoder
from naps.cores.hdmi.rx.tmds_decoder import TmdsDecoder


class TestTmds(unittest.TestCase):
    def test_roundtrip(self):
        # connect a tmds encoder to a tmds decoder and verify that we receive the characters we have sent.
        platform = SimPlatform()
        m = Module()

        data = Signal(8)
        control = Signal(2)
        data_enable = Signal(8)
        encoder = m.submodules.encoder = TmdsEncoder(data, control, data_enable)
        decoder = m.submodules.decoder = TmdsDecoder(encoder.out)

        random.seed(0)
        test_sequence = [10, *[random.randrange(0, 255 + 4) for _ in range(0, 1000)]]

        def writer():
            for x in test_sequence:
                if x < 256:
                    yield data.eq(x)
                    yield data_enable.eq(1)
                else:
                    yield data_enable.eq(0)
                    yield control.eq(x >> 8)
                yield
        platform.add_process(writer, "sync")

        def reader():
            active = False
            seq = [*test_sequence]
            while len(seq):
                x = seq[0]
                if active:
                    seq.pop(0)

                if active:
                    if x < 256:
                        self.assertEqual(x, (yield data))
                        self.assertEqual(1, (yield data_enable))
                    else:
                        self.assertEqual(0, (yield data_enable))
                        self.assertEqual(x >> 8, (yield control))
                elif (yield data) == x:
                    active = True
                    seq.pop(0)
                yield
        platform.add_process(reader, "sync")



        platform.add_sim_clock("sync", 100e6)
        platform.sim(m)
