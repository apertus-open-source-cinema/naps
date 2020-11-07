from cores.csr_bank import StatusSignal
from util.packedstruct import PackedStruct
from nmigen import *


class RingBufferAddressStorage(PackedStruct):
    def __init__(self, buffer_size, n, base_address=0x0f80_0000):
        super().__init__()
        self.buffer_size = buffer_size
        self.buffer_base_list = Array([base_address + buffer_size * i for i in range(n)])
        self.current_write_buffer = StatusSignal(range(n))

