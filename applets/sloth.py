from amaranth import *
from naps import *
from naps.platform.prjsloth_platform import PrjSlothPlatform
from naps.cores.hmcad1511.s7_phy import HMCAD1511Phy


class Top(Elaboratable):
    def elaborate(self, platform: PrjSlothPlatform):
        m = Module()

        platform.ps7.fck_domain(100e6, "sync")

        # Control Pane
        i2c_pads = platform.request("i2c")
        m.submodules.i2c = BitbangI2c(i2c_pads)

        power_control = platform.request("power_ctl")
        
        for name, *_ in power_control.layout:
            cs = ControlSignal(name=name)
            setattr(self, name, cs)
            m.d.comb += power_control[name].o.eq(cs)


        dr = DomainRenamer("frame_clk")
        p = Pipeline(m)
        p += HMCAD1511Phy()
        p += dr(StreamPacketizer(p.output))
        p += dr(DramPacketRingbufferStreamWriter(p.output, max_packet_size=0x1000000, n_buffers=2))
        p += dr(DramPacketRingbufferCpuReader(p.last))

        return m

    @driver_method
    def init(self):
        from time import sleep
        self.en_adc_1v8 = 1
        self.hmcad1511_phy.init()
        sleep(1)
        self.hmcad1511_phy.spi.set_test_pattern()

    @driver_method
    def set_16_bit(self):
        self.hmcad1511_phy.spi.write_word(0x53, 0b001)

    @driver_method
    def capture(self, path="capture.data"):
        from time import sleep
        self.stream_packetizer.length = 1024 * 1024
        self.stream_packetizer.start = 1
        sleep(1)
        self.dram_packet_ringbuffer_cpu_reader.read_packet_to_file(path)


class SlothTimingGenerator(Elaboratable):
    def __init__(self):
        pass

    def elaborate(self, platform):
        m = Module()

        sensor = platform.require("sensor_digital")


        # we take the rising edge on C5 as the frame counter reset.
        # A FHD frame has 1400 lines
        y = Signal(range(1400))

        # each line has 572 clock periods at 24Mhz
        x = Signal(range(572))

        # we also count the total pixelclk for the entire frame
        abs_position = Signal(range(1400 * 572))

        # J11 & J8 Hängen zusammen


        # frame signals:
        m.submodules.frame_rst = PulseGenerator(
            abs_position, sensor.abs_position, {0: 1, 1: 0}
        )
        m.submodules.frame_exp = PulseGenerator(
            abs_position, sensor.abs_position, 
            {24: 1, 42: 0, int(1/30 * 24e6): 1, int(1/30 * 24e6) + 18: 0},
            controlable=True
        )

        # line signals:
        m.submodules.frame_rst = PulseGenerator(
            abs_position, sensor.abs_position, {0: 1, 1: 0}
        )

        return m
    
class PulseGenerator(Elaboratable):
    def __init__(self, counter: Signal, pin: Signal, transition_points={}, controlable=False):
        self.pin = pin
        self.counter = counter
        assert transition_points % 2 == 0
        self.num_triggers = len(transition_points)
        for i, time, value in zip(range(self.num_triggers), transition_points.items()):
            setattr(self, f"trig_{i}_time", ControlSignal(16, reset=time) if controlable else time)
            setattr(self, f"trig_{i}_value", ControlSignal(1, reset=value) if controlable else value)

    def elaborate(self, platform):
        m = Module()

        for i in range(self.num_triggers):
            time = getattr(self, f"trig_{i}_time")
            value = getattr(self, f"trig_{i}_value")
            with m.If(self.counter >= time):
                m.d.comb += self.pin.eq(value)

        return m


if __name__ == "__main__":
    cli(Top, runs_on=(PrjSlothPlatform,), possible_socs=(ZynqSocPlatform, ))
