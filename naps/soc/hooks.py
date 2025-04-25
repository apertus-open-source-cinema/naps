from textwrap import indent

from amaranth import *
from amaranth.hdl._ast import Assign, Property, Switch, Print, Operator, Slice, Part, Concat, SwitchValue, ClockSignal, ResetSignal, Initial, ValueCastable
from amaranth.hdl._ir import RequirePosedge

from .csr_types import _Csr, ControlSignal, StatusSignal, EventReg
from .memorymap import MemoryMap
from .pydriver.driver_items import DriverItem, DriverData
from .tracing_elaborate import ElaboratableSames
from ..util.py_serialize import is_py_serializable


def csr_and_driver_item_hook(platform, top_fragment: Fragment, sames: ElaboratableSames):
    from naps.cores.peripherals.csr_bank import CsrBank
    already_done = []

    def inner(fragment):
        elaboratable = sames.get_elaboratable(fragment)
        if elaboratable:
            class_members = [(s, getattr(elaboratable, s)) for s in dir(elaboratable)]
            csr_signals = [(name, member) for name, member in class_members if isinstance(member, _Csr)]
            
            def get_statement_csrs(stmt):
                csrs = set()
                if stmt is None:
                    pass
                # statements
                elif isinstance(stmt, Assign):
                    csrs |= get_statement_csrs(stmt.lhs)
                    csrs |= get_statement_csrs(stmt.rhs)
                elif isinstance(stmt, Property):
                    csrs |= get_statement_csrs(stmt.message)
                    csrs |= get_statement_csrs(stmt.test)
                elif isinstance(stmt, Switch):
                    csrs |= get_statement_csrs(stmt.test)
                    for _patterns, statements, _src_loc  in stmt.cases:
                        for statement in statements:
                            csrs |= get_statement_csrs(statement)
                elif isinstance(stmt, Print):
                    for chunk in stmt.message._chunks:
                        if isinstance(chunk, tuple):
                            value, _format_spec = chunk
                            csrs |= get_statement_csrs(value)
                # Values
                elif isinstance(stmt, Operator):
                    for operand in stmt.operands:
                        csrs |= get_statement_csrs(operand)
                elif isinstance(stmt, Slice):
                    csrs |= get_statement_csrs(stmt.value)
                elif isinstance(stmt, Part):
                    csrs |= get_statement_csrs(stmt.value)
                    csrs |= get_statement_csrs(stmt.offset)
                elif isinstance(stmt, Concat):
                    for part in stmt.parts:
                        csrs |= get_statement_csrs(part)
                elif isinstance(stmt, SwitchValue):
                    csrs |= get_statement_csrs(stmt.test)
                    for pattern, value in stmt.cases:
                        csrs |= get_statement_csrs(value)
                elif isinstance(stmt, (ClockSignal, ResetSignal, Initial)):
                    pass
                elif isinstance(stmt, _Csr):
                    csrs.add(stmt)
                elif isinstance(stmt, (Signal, Const, ValueCastable)):
                    pass
                else:
                    raise AssertionError("unknown object {} of type {} in statement", stmt, type(stmt))
                return csrs

            fragment_signals = set()
            for _domain, statements in fragment.statements.items():
                for stmt in statements:
                    fragment_signals |= get_statement_csrs(stmt)

            csr_signals += [
                (signal.name, signal) for signal in fragment_signals
                if isinstance(signal, _Csr)
                   and signal.name != "$signal"
                   and not any(signal is cmp_signal for name, cmp_signal in csr_signals)
            ]

            new_csr_signals = [(name, signal) for name, signal in csr_signals if not any(signal is done for done in already_done)]
            old_csr_signals = [(name, signal) for name, signal in csr_signals if any(signal is done for done in already_done)]
            for name, signal in new_csr_signals:
                already_done.append(signal)

            mmap = fragment.memorymap = MemoryMap()

            if new_csr_signals:
                m = Module()
                csr_bank = m.submodules.csr_bank = CsrBank()
                for name, signal in new_csr_signals:
                    if isinstance(signal, (ControlSignal, StatusSignal, EventReg)):
                        csr_bank.reg(name, signal)
                        signal._MustUse__used = True

                mmap.allocate_subrange(csr_bank.memorymap, name=None)  # name=None means that the Memorymap will be inlined
                platform.to_inject_subfragments.append((m, "ignore"))

            for name, signal in old_csr_signals:
                mmap.add_alias(name, signal)

            driver_items = [
                (name, getattr(elaboratable, name))
                for name in dir(elaboratable)
                if isinstance(getattr(elaboratable, name), DriverItem)
            ]
            driver_items += [
                (name, DriverData(getattr(elaboratable, name)))
                for name in dir(elaboratable)
                if is_py_serializable(getattr(elaboratable, name)) and not name.startswith("_")
            ]
            for name, driver_item in driver_items:
                fragment.memorymap.add_driver_item(name, driver_item)

        for subfragment, name, _src_loc in fragment.subfragments:
            if isinstance(subfragment, RequirePosedge):
                continue
            inner(subfragment)
    inner(top_fragment)


def address_assignment_hook(platform, top_fragment: Fragment, sames: ElaboratableSames):
    def inner(fragment):
        module = sames.get_module(fragment)
        if hasattr(module, "peripheral"):  # we have the fragment of a marker module for a peripheral
            fragment.memorymap = module.peripheral.memorymap
            return

        # depth first recursion is important so that all the subfragments have a fully populated memorymap later on
        for sub_fragment, sub_name, _src_loc in fragment.subfragments:
            if isinstance(sub_fragment, RequirePosedge) or sub_name == "ignore":
                continue
            inner(sub_fragment)

        # add everything to the own memorymap
        if not hasattr(fragment, "memorymap"):
            fragment.memorymap = MemoryMap()
        for sub_fragment, sub_name, _src_loc in fragment.subfragments:
            if isinstance(sub_fragment, RequirePosedge) or sub_name == "ignore":
                continue
            assert hasattr(sub_fragment, "memorymap")  # this holds because we did depth first recursion
            fragment.memorymap.allocate_subrange(sub_fragment.memorymap, sub_name)
    inner(top_fragment)

    # prepare and finalize the memorymap
    top_memorymap: MemoryMap = top_fragment.memorymap
    top_memorymap.is_top = True

    assert platform.base_address is not None
    top_memorymap.place_at = platform.base_address

    print("memorymap:\n" + "\n".join(
        "    {}: {!r}".format(".".join(k), v) for k, v in top_memorymap.flattened.items()))

    def print_reg_stats(memorymap: MemoryMap, name="top", indent_size=0):
        def get_child_bits(memorymap: MemoryMap):
            bits = 0
            for row in memorymap.direct_children:
                if isinstance(row.obj, (ControlSignal, StatusSignal, EventReg)):
                    bits += row.address.bit_len
            for row in memorymap.subranges:
                bits += get_child_bits(row.obj)
            return bits
        print(indent(f"{name}: {get_child_bits(memorymap)}", " " * (indent_size * 4)))
        for row in memorymap.subranges:
            print_reg_stats(row.obj, row.name, indent_size + 1)

    print("\n\nregister bit stats:")
    print_reg_stats(top_memorymap)

    platform.memorymap = top_memorymap


def peripherals_collect_hook(platform, top_fragment: Fragment, sames: ElaboratableSames):
    platform.peripherals = []

    def collect_peripherals(platform, fragment: Fragment, sames):
        module = sames.get_module(fragment)
        if module:
            if hasattr(module, "peripheral"):
                platform.peripherals.append(module.peripheral)
        for f, name, _src_loc in fragment.subfragments:
            if isinstance(f, RequirePosedge):
                continue
            collect_peripherals(platform, f, sames)

    collect_peripherals(platform, top_fragment, sames)

    ranges = [(peripheral.range(), peripheral) for peripheral in platform.peripherals
              if not peripheral.memorymap.is_empty and not peripheral.memorymap.was_inlined]

    def range_overlapping(x, y):
        if x.start == x.stop or y.start == y.stop:
            return False
        return ((x.start < y.stop and x.stop > y.start) or
                (x.stop > y.start and y.stop > x.start))

    for a, peripheral_a in ranges:
        for b, peripheral_b in ranges:
            if a is not b and range_overlapping(a, b):
                raise AssertionError("{!r} overlaps with {!r}".format(peripheral_a, peripheral_b))
