from nmigen import *

from naps import StatusSignal, ControlSignal, driver_method


class DelayF(Elaboratable):
    def __init__(self, i):
        self.i = i

        self.move = ControlSignal()
        self.direction = ControlSignal()
        self.at_limit = StatusSignal()

        self.o = Signal()

    def elaborate(self, platform):
        m = Module()

        m.submodules.instance = Instance(
            "DELAYF",

            i_A=self.i,
            i_LOADN=Const(1),
            i_MOVE=self.move,
            i_DIRECTION=self.direction,

            o_Z=self.o,
            o_CFLAG=self.at_limit,
        )

        return m

    @driver_method
    def forward(self, count=1):
        self.direction = 1
        for i in range(count):
            self.do_move()

    @driver_method
    def backward(self, count=1):
        self.direction = 0
        for i in range(count):
            self.do_move()

    @driver_method
    def do_move(self):
        self.move = 1
        self.move = 0

    @driver_method
    def reset_delay(self):
        self.backward(128)

    @driver_method
    def set_delay(self, delay):
        self.reset_delay()
        self.forward(delay)


class IDDRX2F(Elaboratable):
    def __init__(self, pin, eclk_domain):
        self.pin = pin
        self.eclk_domain = eclk_domain

        self.output = Signal(4)

    def elaborate(self, platform):
        m = Module()

        m.submodules.instance = Instance(
            "IDDRX2F",

            i_D=self.pin,
            i_SCLK=ClockSignal(),
            i_RST=ResetSignal(),
            i_ECLK=ClockSignal(self.eclk_domain),
            # i_ALIGNWD=Const(0, 1),

            o_Q0=self.output[0],
            o_Q1=self.output[1],
            o_Q2=self.output[2],
            o_Q3=self.output[3],
        )

        return m


class IDDRX1F(Elaboratable):
    def __init__(self, pin):
        self.pin = pin

        self.output = Signal(2)

    def elaborate(self, platform):
        m = Module()

        m.submodules.instance = Instance(
            "IDDRX1F",

            i_D=self.pin,
            i_SCLK=ClockSignal(),
            i_RST=ResetSignal(),

            o_Q0=self.output[0],
            o_Q1=self.output[1],
        )

        return m
