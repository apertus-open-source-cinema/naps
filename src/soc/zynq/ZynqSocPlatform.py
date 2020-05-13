from typing import Callable

from nmigen import *
from nmigen_soc.memory import MemoryMap

from modules.xilinx.Ps7 import Ps7
from soc.SocPlatform import SocPlatform
from soc.zynq.program_bitstream_ssh import program_bitstream_ssh


class ZynqSocPlatform(SocPlatform):
    def __init__(self, platform):
        super().__init__(platform)
        self.ps7 = None
        self.init_script = ""
        platform.toolchain_program = lambda *args, **kwargs: program_bitstream_ssh(self, *args, **kwargs)

    def BusSlave(self, handle_read: Callable[[], None], handle_write, *, addr_window):
        raise NotImplementedError()

    def MemoryMap(self):
        return MemoryMap(addr_width=32, data_width=32, alignment=32)

    def get_ps7(self) -> Ps7:
        if self.ps7 is None:
            self.ps7 = Ps7(here_is_the_only_place_that_instanciates_ps7=True)
            self.inject_subfragment(self.ps7, "ps7")
        return self.ps7
