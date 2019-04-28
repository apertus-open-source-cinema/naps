from nmigen import *
from nmigen.cli import main


class SHREG(Elaboratable):
    """Shift register with clock (shift) enable and initial content
    """

    def __init__(self, initial_value=0, width=25):
        self.i = Signal()
        self.o = Signal()
        self.ce = Signal()

        self.buf = Signal(width, reset=initial_value)

    def elaborate(self, platform):
        m = Module()

        m.d.comb += self.o.eq(self.buf[-1])

        with m.If(self.ce):
            m.d.sync += self.buf.eq(Cat(self.i, self.buf[:-1]))

        return m


class nWs2812(Elaboratable):
    """Yet another driver for the popular digital ws2812b rgb leds
    (see https://www.seeedstudio.com/document/pdf/WS2812B%20Datasheet.pdf)

    It expects a 20Mhz clock to drive the leds with the correct speed
    """

    def __init__(self, leds=3, channels=3, bits=8):
        self.out = Signal()
        self.input = Signal(leds * channels * bits, reset=0xffffffffffffffffff)

    def elaborate(self, platform):
        m = Module()

        # pattern[i] = (high cycles, low cycles) for symbol i
        patterns = [(7, 18), (18, 7)]


        # number of cycles for reset
        reset_len = 1100
        
        def _pattern_len(p):
            return p[0] + p[1]


        def _gen_pattern(p):
            return int(("1" * p[0]) + ("0" * p[1]), 2)

        assert(_pattern_len(patterns[0]) == _pattern_len(patterns[1]))


        
        m.submodules.shreg_logical_low = shreg_logical_low = SHREG(
                initial_value=_gen_pattern(patterns[0]))

        m.submodules.shreg_logical_high = shreg_logical_high = SHREG(
                initial_value=_gen_pattern(patterns[1]))

        pattern_counter = Signal(max=_pattern_len(patterns[0]))
        input_pointer = Signal(max=len(self.input), reset=0)
        reset_counter = Signal(max=reset_len, reset=0)

        with m.FSM() as _: 
            with m.State("DATA"):
                m.d.comb += self.out.eq(
                        Mux(self.input.part(input_pointer, 1), shreg_logical_low.o, shreg_logical_high.o))

                m.d.comb += shreg_logical_low.ce.eq(1)
                m.d.comb += shreg_logical_high.ce.eq(1)

                m.d.comb += shreg_logical_low.i.eq(shreg_logical_low.o)
                m.d.comb += shreg_logical_high.i.eq(shreg_logical_high.o)

                with m.If(pattern_counter == _pattern_len(patterns[0]) - 1):
                    m.d.sync += pattern_counter.eq(0)
                    
                    with m.If(input_pointer == len(self.input) - 1):
                        m.next = "RESET"
                        m.d.sync += input_pointer.eq(0)
                    with m.Else():
                        m.next = "DATA"
                        m.d.sync += input_pointer.eq(input_pointer + 1)

                with m.Else():
                    m.d.sync += pattern_counter.eq(pattern_counter + 1)

            with m.State("RESET"):
                with m.If(reset_counter < reset_len):
                    m.d.sync += reset_counter.eq(reset_counter + 1)
                with m.Else():
                    m.next = "DATA"
                    m.d.sync += reset_counter.eq(0)
                    
    
        return m



if __name__ == "__main__":
    from nmigen.back import pysim
    ws2812 = nWs2812()

    with pysim.Simulator(ws2812,
            vcd_file=open("ws2812.vcd", "w"),
            gtkw_file=open("ws2812.gtkw", "w"),
            traces=[ws2812.out]) as sim:
        sim.add_clock(50e-9)
        def controller_proc():
            for _ in range(65535):
                yield
                    
        sim.add_sync_process(controller_proc())
        sim.run_until(1000e-6, run_passive=False)
