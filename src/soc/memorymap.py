from soc.reg_types import ControlSignal, StatusSignal


class MemoryMap:
    def __init__(self, address_range: range):
        self.address_range = address_range

    def allocate(self, name, writable):
        pass

    def allocate_for(self, signal):
        if isinstance(signal, ControlSignal):
            return self.allocate(signal.name, writable=True)
        elif isinstance(signal, StatusSignal):
            return self.allocate(signal.name, writable=False)

    def allocate_subrange(self, subrange: MemoryMap):
        pass
