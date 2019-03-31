from nmigen import *

from util.logger import log


class QuadratureDecoder:
    """Decodes quadrature coding produced by a rotary encoder.
    Counts the number of detents and outputs them parallel until it is reset.

    See https://en.wikipedia.org/wiki/Incremental_encoder#Quadrature_decoder for details.
    This implementation dies if there are errors in the quadrature input.
    """

    def __init__(self, quadrature):
        self.quadrature = quadrature
        assert self.quadrature.nbits == 2

        self.parallel = Signal((8, True), reset=0)

    def elaborate(self, platform):
        m = Module()

        last_quadrature = Signal(2)
        with m.If(self.quadrature != last_quadrature):
            m.d.sync += last_quadrature.eq(self.quadrature)
            for reverse in [False, True]:
                transitions = [("00", "01"), ("10", "11"), ("11", "01")]
                if reverse:
                    transitions = [[reversed(state) for state in transition] for transition in transitions]
                transitions = [[int("".join(state), base=2) for state in transition] for transition in transitions]

                for last, current in transitions:
                    with m.If((last_quadrature == last) & (self.quadrature == current)):
                        m.d.sync += self.parallel.eq(self.parallel + (0 if reverse else 1))
        return m
