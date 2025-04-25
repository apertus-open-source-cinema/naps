from amaranth import *
from amaranth.hdl import Cover, Assume, Assert

from .stream import Stream
from naps.util.formal import FormalPlatform, assert_formal

__all__ = ["verify_stream_output_contract", "LegalStreamSource"]

class StreamOutputCoverSpec(Elaboratable):
    """
    the valid signal MUST NOT depend on the ready signal.
    the other way round a dependency is okay.
    """
    def __init__(self, stream_output: Stream):
        self.stream_output = stream_output

    def elaborate(self, platform):
        m = Module()

        m.d.comb += Assume(~self.stream_output.ready)
        m.d.comb += Cover(self.stream_output.valid)

        return m


def verify_stream_output_contract_cover(module, stream_output, support_modules=()):
    spec = StreamOutputCoverSpec(stream_output)
    assert_formal(module, mode="cover", depth=10, submodules=[*support_modules, spec])


class StreamOutputAssertSpec(Elaboratable):
    """
    Assert that the payload signals of a stream do not change if valid is pulled high and the transaction wasnt accepted
    by the next node by pulling ready high.
    """
    def __init__(self, stream_output: Stream):
        self.stream_output = stream_output

    def elaborate(self, platform):
        m = Module()

        unfinished_transaction = Signal()
        with m.If(self.stream_output.ready & self.stream_output.valid):
            m.d.sync += unfinished_transaction.eq(0)
        with m.Elif(self.stream_output.valid):
            m.d.sync += unfinished_transaction.eq(1)
        m.d.comb += Assert(~unfinished_transaction | self.stream_output.valid)

        last_payload_signals = [Signal.like(s, name=f"{name}_last") for name, s in self.stream_output.payload_signals.items()]
        for l, s in zip(last_payload_signals, self.stream_output.payload_signals.values()):
            m.d.sync += l.eq(s)

        with m.If(unfinished_transaction):
            for l, s in zip(last_payload_signals, self.stream_output.payload_signals.values()):
                m.d.comb += Assert(l == s)

        return m


def verify_stream_output_contract_assert(module, stream_output, support_modules=()):
    spec = StreamOutputAssertSpec(stream_output)
    assert_formal(module, mode="bmc", depth=10, submodules=[*support_modules, spec])


class LegalStreamSource(Elaboratable):
    """A stream source that can be used to constrain stream input of cores"""
    def __init__(self, stream: Stream):
        self.output = stream

    def elaborate(self, platform):
        m = Module()

        unfinished_transaction = Signal()
        last_payload_signals = [Signal.like(s, name=f"{name}_last") for name, s in self.output.payload_signals.items()]
        with m.If(self.output.ready & self.output.valid):
            m.d.sync += unfinished_transaction.eq(0)
        with m.Elif(self.output.valid):
            m.d.sync += unfinished_transaction.eq(1)
            with m.If(~unfinished_transaction):
                for l, s in zip(last_payload_signals, self.output.payload_signals.values()):
                    m.d.sync += l.eq(s)

        with m.If(unfinished_transaction):
            m.d.comb += Assume(self.output.valid)
            for l, s in zip(last_payload_signals, self.output.payload_signals.values()):
                m.d.comb += Assume(l == s)

        return m


def verify_stream_output_contract(module, stream_output=None, support_modules=[]):
    if callable(module):
        module_generator = module
    else:
        def module_generator():
            output = stream_output
            if output is None:
                output = module.output
            return (module, output, support_modules)

    for text, check in [
        ("that valid does not depend on ready", verify_stream_output_contract_cover),
        ("hold unacknowledged transactions", verify_stream_output_contract_assert),
    ]:
        elab, stream_output, support_modules = module_generator()
        elab._MustUse__used = True
        print(f"testing {text}...")
        check(elab, stream_output, support_modules)
