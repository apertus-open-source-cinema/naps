import json

from nmigen import *

from soc.memorymap import MemoryMap
from soc.peripherals.CsrBank import CsrBank
from soc.reg_types import ControlSignal, StatusSignal, _Csr, EventReg
from soc.tracing_elaborate import ElaboratableSames


def csr_hook(platform, fragment: Fragment, sames: ElaboratableSames):
    elaboratable = sames.get_elaboratable(fragment)
    if elaboratable:
        class_members = [(s, getattr(elaboratable, s)) for s in dir(elaboratable)]
        csr_signals = [(name, member) for name, member in class_members if isinstance(member, (_Csr))]
        if csr_signals:
            m = Module()

            csr_bank = CsrBank()
            m.submodules += csr_bank
            for name, signal in csr_signals:
                if isinstance(signal, ControlSignal):
                    csr_bank.reg(name, signal, writable=True, address=signal.address)
                elif isinstance(signal, StatusSignal):
                    csr_bank.reg(name, signal, writable=False, address=signal.address)
                elif isinstance(signal, EventReg):
                    raise NotImplementedError()

            fragment.memorymap = csr_bank.memorymap
            platform.to_inject_subfragments.append((m, "ignore"))

    for fragment, name in fragment.subfragments:
        csr_hook(platform, fragment, sames)


def address_assignment_hook(platform, top_fragment: Fragment, sames: ElaboratableSames):
    def inner(fragment):
        module = sames.get_module(fragment)
        elaboratable = sames.get_elaboratable(fragment)
        if hasattr(module, "bus_slave"):  # we have the fragment of a marker module for a bus slave
            bus_slave, memorymap = module.bus_slave
            fragment.memorymap = memorymap
            return

        # depth first recursion
        for sub_fragment, sub_name in fragment.subfragments:
            if sub_name != "ignore":
                inner(sub_fragment)

        # add everything to the own memorymap
        if not hasattr(fragment, "memorymap"):
            fragment.memorymap = MemoryMap()
        for sub_fragment, sub_name in fragment.subfragments:
            if sub_name != "ignore":
                assert hasattr(sub_fragment, "memorymap")
                fragment.memorymap.allocate_subrange(sub_fragment.memorymap, sub_name)
    inner(top_fragment)
    top_fragment.memorymap.top = True