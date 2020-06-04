from functools import reduce

from nmigen import *
from nmigen.hdl.ast import SignalSet

from soc.memorymap import MemoryMap
from soc.peripherals.csr_bank import CsrBank
from soc.reg_types import ControlSignal, StatusSignal, EventReg, _Csr
from soc.tracing_elaborate import ElaboratableSames


def csr_hook(platform, top_fragment: Fragment, sames: ElaboratableSames):
    already_done = []

    def inner(fragment):
        elaboratable = sames.get_elaboratable(fragment)
        if elaboratable:
            class_members = [(s, getattr(elaboratable, s)) for s in dir(elaboratable)]
            csr_signals = [(name, member) for name, member in class_members if isinstance(member, _Csr)]
            fragment_signals = reduce(lambda a, b: a | b, fragment.drivers.values(), SignalSet())
            csr_signals += [
                (signal.name, signal) for signal in fragment_signals
                if isinstance(signal, _Csr) and signal.name != "$signal" and any(signal is cmp_signal for name, cmp_signal in csr_signals)
            ]
            for signal in csr_signals:
                assert not any(signal is done for done in already_done), "attempting to add a csr to two modules"
                already_done.append(signal)
            if csr_signals:
                m = Module()

                csr_bank = CsrBank()
                m.submodules += csr_bank
                for name, signal in csr_signals:
                    if isinstance(signal, ControlSignal):
                        csr_bank.reg(name, signal, writable=True, address=signal.address)
                        signal._MustUse__used = True
                    elif isinstance(signal, StatusSignal):
                        csr_bank.reg(name, signal, writable=False, address=signal.address)
                        signal._MustUse__used = True
                    elif isinstance(signal, EventReg):
                        raise NotImplementedError()

                fragment.memorymap = csr_bank.memorymap
                platform.to_inject_subfragments.append((m, "ignore"))

        for subfragment, name in fragment.subfragments:
            inner(subfragment)
    inner(top_fragment)


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

    # prepare and finalize the memorymap
    top_memorymap: MemoryMap = top_fragment.memorymap
    top_memorymap.top = True

    assert hasattr(platform, "base_address")
    top_memorymap.place_at = platform.base_address

    print("memorymap:\n" + "\n".join(
        "    {}: {!r}".format(k, v) for k, v in top_memorymap.flat.items()))
    platform.memorymap = top_memorymap
