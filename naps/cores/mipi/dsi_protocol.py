from contextlib import contextmanager

from nmigen import *

from naps import ImageStream, PacketizedStream, process_block, Process
from .py_dsi_generator import assemble, short_packet, ShortPacketDataType


class ImageStream2MipiDsiVideoBurstMode(Elaboratable):
    def __init__(self, input: ImageStream, num_lanes: int):
        self.input = input
        self.num_lanes = num_lanes

        self.output = PacketizedStream(num_lanes * 8)

    def elaborate(self, platform):
        m = Module()

        current_word = Signal(range(self.num_lanes))

        @process_block
        def outbox(data):
            try:
                stmt = m.Elif(timer >= cycles - 2)
                stmt.__enter__()
                yield None
            finally:
                stmt.__exit__(None, None, None)

        initial = Signal()
        with m.If(initial):
            with Process(m) as p:
                p += outbox(assemble(short_packet(ShortPacketDataType.V_SYNC_START)))
                p += outbox(assemble(short_packet(ShortPacketDataType.H_SYNC_START)))

        return m