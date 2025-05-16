import unittest
from typing import Callable

from amaranth import *
from amaranth.hdl import Cover, Assume, Assert
from amaranth.lib import stream, wiring
from amaranth.lib.wiring import Component, In, Out

from naps.util.formal import FormalPlatform

__all__ = ["verify_stream_output_contract", "LegalStreamSource", "StreamOutputAssertSpec"]


class LegalStreamSource(Component):
    """A stream source that can be used to constrain stream input of cores"""
    def __init__(self, payload_shape):
        super().__init__(wiring.Signature({
            "output": Out(stream.Signature(payload_shape))
        }))

    def elaborate(self, platform):
        m = Module()

        wiring.connect(m, platform.request_port(wiring.flipped(self.output)), wiring.flipped(self.output))

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

        wiring.connect(m, input=wiring.flipped(self.input), port=platform.request_port(wiring.flipped(self.input)))

        m.d.comb += Assume(~self.input.ready)
        m.d.comb += Cover(self.input.valid)

        return m


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

        wiring.connect(m, wiring.flipped(self.input), platform.request_port(wiring.flipped(self.input)))

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

def stream_contract_test(func: Callable[[unittest.TestCase, FormalPlatform, Module], stream.Interface]):
    def inner(self: unittest.TestCase):
        verify_stream_output_contract(self, lambda plat, m: func(self, plat, m))
    return inner


def verify_stream_output_contract(testcase: unittest.TestCase, module_generator: Callable[[FormalPlatform, Module], stream.Interface]):
    for text, check in [
        ("valid_does_not_depend_on_ready", StreamOutputCoverSpec),
        ("hold_unacknowledged_transactions", StreamOutputAssertSpec),
    ]:
        with testcase.subTest(text):
            plat = FormalPlatform()
            m = Module()
            stream_output = module_generator(plat, m)
            m.submodules.spec = spec = check(stream_output.p.shape())
            wiring.connect(m, stream_output, spec.input)
            plat.run_formal(testcase, m)
