from nmigen import *

from soc import MemoryMapFactory
from soc.peripherals.AutoCsrBank import AutoCsrBank
from soc.reg_types import ControlSignal, StatusSignal
from soc.elaboratable_sames import ElaboratableSames
from util.nmigen import get_signals


def auto_csr_hook(platform, fragment: Fragment, sames: ElaboratableSames):
    elaboratable = sames.get_elaboratable(fragment)
    if elaboratable:
        signals = get_signals(elaboratable)
        csr_signals = [s for s in signals if isinstance(s, (ControlSignal, StatusSignal))]
        if csr_signals:
            m = Module()
            csr_bank = m.submodules.csr_bank = AutoCsrBank()

            for signal in csr_signals:
                if isinstance(signal, ControlSignal):
                    m.d.comb += signal.eq(
                        csr_bank.reg(signal.name, width=len(signal), writable=True, reset=signal.reset))
                if isinstance(signal, StatusSignal):
                    m.d.comb += csr_bank.reg(signal.name, width=len(signal), writable=False).eq(signal)

            platform.to_inject_subfragments.append((m, None))

    for (fragment, name) in fragment.subfragments:
        auto_csr_hook(platform, fragment, sames)


def address_assignment_hook(platform, fragment: Fragment, sames: ElaboratableSames):
    # TODO: better memorymap organization; this is quite ad hoc, doesnt think about hierarchy, ...
    memorymap = MemoryMapFactory.MemoryMap()

    def inner(platform, fragment: Fragment, sames: ElaboratableSames):
        module = sames.get_module(fragment)
        if module:
            if hasattr(module, "bus_slave"):
                bus_slave, addr_map = module.bus_slave
                start, stop, ratio = memorymap.add_window(addr_map)
                bus_slave.address_range = range(start, stop)
        for (f, name) in fragment.subfragments:
            inner(platform, f, sames)
    inner(platform, fragment, sames)

    # TODO: generate useful files
    print(memorymap)
