from amaranth import *
from amaranth.hdl import Cover, Assume, Assert
from amaranth.lib import stream, wiring
from amaranth.lib.wiring import Component, In, Out

from .stream import Stream
from naps.util.formal import FormalPlatform

__all__ = ["verify_stream_output_contract", "LegalStreamSource", "StreamOutputAssertSpec"]

class StreamOutputCoverSpec(Component):
    """
    the valid signal MUST NOT depend on the ready signal.
    the other way round a dependency is okay.
    """
    def __init__(self, payload_shape):
        super().__init__(wiring.Signature({
            "input": In(stream.Signature(payload_shape))
        }))

    def elaborate(self, platform):
        m = Module()

        wiring.connect(m, wiring.flipped(self.input), wiring.flipped(platform.request_port(Out(stream.Signature(self.input.p.shape())))))

        m.d.comb += Assume(~self.input.ready)
        m.d.comb += Cover(self.input.valid)

        return m


def verify_stream_output_contract_cover(module, stream_output, support_modules=()):
    spec = StreamOutputCoverSpec(stream_output)
    assert_formal(module, mode="cover", depth=10, submodules=[*support_modules, spec])


class StreamOutputAssertSpec(Component):
    """
    Assert that the payload signals of a stream do not change if valid is pulled high and the transaction wasn't accepted
    by the next node by pulling ready high.
    """
    def __init__(self, payload_shape):
        super().__init__(wiring.Signature({
            "input": In(stream.Signature(payload_shape))
        }))

    def elaborate(self, platform):
        m = Module()

        wiring.connect(m, wiring.flipped(self.input), wiring.flipped(platform.request_port(Out(stream.Signature(self.input.p.shape())))))

        unfinished_transaction = Signal()
        with m.If(self.input.ready & self.input.valid):
            m.d.sync += unfinished_transaction.eq(0)
        with m.Elif(self.input.valid):
            m.d.sync += unfinished_transaction.eq(1)
        m.d.comb += Assert(~unfinished_transaction | self.input.valid)

        last_payload = Signal.like(self.input.p, name=f"payload_last")
        m.d.sync += last_payload.eq(self.input.p)

        with m.If(unfinished_transaction):
            m.d.comb += Assert(last_payload == self.input.p)

        return m


def verify_stream_output_contract_assert(module, stream_output, support_modules=()):
    spec = StreamOutputAssertSpec(stream_output)
    assert_formal(module, mode="bmc", depth=10, submodules=[*support_modules, spec])


class LegalStreamSource(Component):
    """A stream source that can be used to constrain stream input of cores"""
    def __init__(self, payload_shape):
        super().__init__(wiring.Signature({
            "output": Out(stream.Signature(payload_shape))
        }))

    def elaborate(self, platform):
        m = Module()

        wiring.connect(m, wiring.flipped(platform.request_port(In(stream.Signature(self.output.p.shape())))), wiring.flipped(self.output))

        unfinished_transaction = Signal()
        last_payload = Signal.like(self.output.p, name=f"payload_last")

        with m.If(self.output.ready & self.output.valid):
            m.d.sync += unfinished_transaction.eq(0)
        with m.Elif(self.output.valid):
            m.d.sync += unfinished_transaction.eq(1)
            with m.If(~unfinished_transaction):
                m.d.sync += last_payload.eq(self.output.p)

        with m.If(unfinished_transaction):
            m.d.comb += Assume(self.output.valid)
            m.d.comb += Assume(last_payload == self.output.p)

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
