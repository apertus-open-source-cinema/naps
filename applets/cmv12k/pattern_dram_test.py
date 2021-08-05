# set up and demonstrate capturing the test pattern of CMV12k into DRAM

# DEMO PROCEDURE:
# 1. build the fatbitstream with `python3 applets/cmv12k/pattern_dram_test.py -b`
# 2. copy the resulting build/pattern_dram_test_*/pattern_dram_test.zip file to the Beta
# 3. log into the Beta and get root access with e.g. `sudo su`
# 4. power up the sensor with `axiom_power_init.sh && axiom_power_on.sh`
# 5. load the fatbitstream with `./pattern_dram_test.zip --run`
# 6. run `design.capture_pattern()` function at the prompt
# 7. `exit()` and check pattern.bin

from nmigen import *
from naps import *

class Top(Elaboratable):
    def __init__(self):
        self.sensor_reset = ControlSignal()
        self.frame_req = PulseReg(1)

    def elaborate(self, platform: BetaPlatform):
        m = Module()

        m.submodules += self.frame_req

        platform.ps7.fck_domain(143e6, "axi_hp")

        sensor = platform.request("sensor")
        platform.ps7.fck_domain(250e6, "sensor_clk")
        m.d.comb += sensor.lvds_clk.eq(ClockSignal("sensor_clk"))
        m.d.comb += sensor.reset.eq(self.sensor_reset)

        m.d.comb += [
            sensor.frame_req.eq(self.frame_req.pulse),
            sensor.t_exp1.eq(0),
            sensor.t_exp2.eq(0),
        ]

        m.submodules.sensor_spi = Cmv12kSpi(platform.request("sensor_spi"))
        sensor_rx = Cmv12kRx(sensor)

        ip = Pipeline(m, prefix="input", start_domain="cmv12k")
        ip += sensor_rx

        ip += StreamGearbox(ip.output, 64)
        ip += BufferedAsyncStreamFIFO(ip.output, 2048, o_domain="axi_hp")
        ip += StreamBuffer(ip.output)
        ip += ImageStream2PacketizedStream(ip.output)
        ip += DramPacketRingbufferStreamWriter(ip.output, max_packet_size=0x200_0000, n_buffers=4)
        dram_writer = ip.last
        ip += DramPacketRingbufferCpuReader(dram_writer)

        return m

    @driver_method
    def train(self):
        self.input_cmv12k_rx.trainer.train(self.sensor_spi)

    @driver_method
    def configure(self):
        regs = {
            # internal exposure mode, default value
             70: 0,
             71: 1536,
             72: 0,

             80: 1, # one frame per request

             81: 1, # two side readout, 16 outputs per side

            # disable unused LVDS channels
             90: 0b0101010101010101,
             91: 0b0101010101010101,
             92: 0b0101010101010101,
             93: 0b0101010101010101,

            117: 1, # unity digital gain

            122: 3, # enable test pattern

            # 12 bit additional settings, 16 outputs per side, normal mode
             82: 1822,
             83: 5897,
             84: 257,
             85: 257,
             86: 257,
             87: 1910,
             88: 1910,
             98: 39433,
            107: (81 << 7) | 94, # 250MHz
            109: 14448,
            113: 542,
            114: 200,

            # ADC settings for 12 bit at 250MHz
            116: (3 << 8) | 167,
            100: 3,
        }

        for addr, value in regs.items():
            self.sensor_spi.write_reg(addr, value)

    @driver_method
    def capture_pattern(self):
        import time
        print("training link...")
        self.input_cmv12k_rx.configure_sensor_defaults(self.sensor_spi)
        self.input_cmv12k_rx.trainer.train(self.sensor_spi)

        print("capturing pattern...")
        self.sensor_spi.enable_test_pattern(True)
        self.frame_req = 1
        time.sleep(0.05)

        # make sure we transferred the full image
        txns = self.input_dram_packet_ringbuffer_stream_writer.writer.info_axi_data.successful_transactions_counter
        assert txns % (4096*3072*12/64) == 0, "pattern transfer FAILED!!!"

        print("downloading pattern...")
        # ../ puts the file outside the extracted zip
        self.input_dram_packet_ringbuffer_cpu_reader.read_packet_to_file("../pattern.bin")

if __name__ == "__main__":
    cli(Top, runs_on=(BetaPlatform, ), possible_socs=(ZynqSocPlatform, ))
