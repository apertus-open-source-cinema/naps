from nmigen import *
from nmigen.cli import main

from modules.managers.clock_manager import module_clockdomain


class Ws2812:
    """A driver for the popular digital ws2812 rgb leds
    (see https://www.seeedstudio.com/document/pdf/WS2812B%20Datasheet.pdf)

    It expects a 2Mhz clock to drive the leds with the correct speed
    """

    def __init__(self, out, led_number, channels_per_led=3, bits=8):
        self.out = out
        self.parallel_in = Array(Array(Signal(bits) for _ in range(channels_per_led)) for _ in range(led_number))

    def elaborate(self, platform):
        m = Module()
        sync = m.d.sync

        phy = m.submodules.ws2812__phy = Ws2812Phy(self.out)

        with m.FSM(reset="RESET"):
            with m.State("RESET"):
                sync += phy.pattern.eq(3)  # 3 is reset
                with m.If(phy.done):
                    m.next = "LED0_COLOR0_BIT0"

            for led_n, led in enumerate(self.parallel_in):
                next_led = led_n + 1 if led_n+1 < len(self.parallel_in) else 0
                for color_n, color in enumerate(led):
                    next_color = color_n+1 if color_n+1 < len(led) else 0
                    for bit in range(len(color)):
                        next_bit = bit+1 if bit+1 < len(color) else 0
                        with m.State("LED{}_COLOR{}_BIT{}".format(led_n, color_n, bit)):
                            sync += phy.pattern.eq(self.parallel_in[led_n][color_n][bit])

                            if led_n == len(self.parallel_in) - 1 \
                                    and color_n == len(led) - 1 \
                                    and bit == len(color) - 1:
                                with m.If(phy.done):
                                    m.next = "RESET"
                            else:
                                print("LED{}_COLOR{}_BIT{}".format(led_n, color_n, bit), "->", "LED{}_COLOR{}_BIT{}".format(next_led, next_color, next_bit))
                                with m.If(phy.done):
                                    m.next = "LED{}_COLOR{}_BIT{}".format(next_led, next_color, next_bit)
        return m


class Ws2812Phy:
    """Handling the low level timing for the ws2812 signal generation

    It expects a 2Mhz clock to drive the leds with the correct speed
    A 1 is encoded as 5 cycles HIGH and 18 cycles LOW, a 0 as 18 cycles HIGH and 5 cycles LOW.
    Reset is send when the output is more than 1000 cycles LOW.
    """

    def __init__(self, out, patterns=[(7, 18), (18, 7), (1023, 0)]):
        self.patterns = Array(Array(x for x in pattern) for pattern in patterns)

        self.pattern = Signal(max=len(patterns))
        self.out = out
        self.done = Signal()

    def elaborate(self, platform):
        m = Module()
        sync = m.d.sync

        buffered_pattern = Signal(len(self.pattern))

        # stupid hack to work around a nMigen Bug (see https://github.com/m-labs/nmigen/issues/51)
        dummy = Signal(max=len(self.patterns))
        m.d.comb += buffered_pattern.eq(dummy)

        max_pattern_length = max([sum(pattern) for pattern in self.patterns])
        counter = Signal(max=max_pattern_length)
        with m.If(counter == self.patterns[buffered_pattern][1]):
            sync += [
                counter.eq(0),
                self.done.eq(1),

                dummy.eq(self.pattern),
            ]
        with m.Else():
            sync += [
                counter.eq(counter+1),
                self.done.eq(0),
            ]

        with m.If(counter > self.patterns[buffered_pattern][0]):
            sync += self.out.eq(0)
        with m.Else():
            sync += self.out.eq(1)

        return m


if __name__ == "__main__":
    from nmigen.back import pysim
    out = Signal()
    ws2812 = Ws2812(out, led_number=1)
    main(ws2812)

    with pysim.Simulator(ws2812,
            vcd_file=open("ws2812.vcd", "w"),
            gtkw_file=open("ws2812.gtkw", "w"),
            traces=[out]) as sim:
        sim.add_clock(500e-9)
        def controller_proc():
            for led in ws2812.parallel_in:
                for color in led:
                    yield color.eq(4)

            for _ in range(65535):
                yield
                    
        sim.add_sync_process(controller_proc())
        sim.run_until(1000e-6, run_passive=False)
