from nmigen import *

__all__ = ["BlinkDebug"]


class BlinkDebug(Elaboratable):
    def __init__(self, led, divider=20, max_value=8):
        self.led = led
        self.max_value = max_value
        self.divider = divider

        self.value = Signal(range(max_value))

    def elaborate(self, platform):
        m = Module()

        div_counter = Signal(self.divider)
        m.d.sync += div_counter.eq(div_counter + 1)

        def next_div(m, next_state):
            with m.If(div_counter == 0):
                m.next = next_state

        with m.FSM():
            for i in range(self.max_value):
                with m.State("ON_{}".format(i)):
                    m.d.comb += self.led.eq(1)
                    next_div(m, "OFF_{}".format(i))

                with m.State("OFF_{}".format(i)):
                    m.d.comb += self.led.eq(0)
                    if i != self.max_value - 1:
                        with m.If(self.value > i):
                            next_div(m, "ON_{}".format(i + 1))
                        with m.Else():
                            next_div(m, "IDLE_0")
                    else:
                        next_div(m, "IDLE_0")

            idle_states = 4
            for i in range(idle_states):
                with m.State("IDLE_{}".format(i)):
                    m.d.comb += self.led.eq(0)
                    if i != idle_states - 1:
                        next_div(m, "IDLE_{}".format(i + 1))
                    else:
                        next_div(m, "ON_0")

        return m
