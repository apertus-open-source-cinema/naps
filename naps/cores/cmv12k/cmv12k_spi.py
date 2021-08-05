from nmigen import *
from naps import driver_method
from naps.cores.peripherals import BitbangSPI

__all__ = ["Cmv12kSpi"]

class Cmv12kSpi(Elaboratable):
    def __init__(self, sensor_spi):
        self.sensor_spi = sensor_spi

        # runtime variables
        self.spiobj = None
        self.num_lanes = None
        self.bits = None
        self.freq = None
        self.mode = None

    def elaborate(self, platform):
        m = Module()

        m.submodules.spi = BitbangSPI(self.sensor_spi)

        return m

    @driver_method
    def set_readout_configuration(self, num_lanes, bits, freq, mode):
        # see cmv12k_rx.py for definitions
        assert num_lanes == 32
        assert bits == 12
        assert freq == 250e6
        assert mode == "normal"
        self.num_lanes = num_lanes
        self.bits = bits
        self.freq = freq
        self.mode = mode

        regs = {
             81: 1, # two side readout, 16 outputs per side
            118: 0, # 12 bit readout

            # disable unused LVDS channels
             90: 0b0101010101010101,
             91: 0b0101010101010101,
             92: 0b0101010101010101,
             93: 0b0101010101010101,

            117: 1, # unity digital gain at 12 bits

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

            # fixed value registers
             99: 34956,
            102: 8302,
            108: 12381,
            110: 12368,
            112: 277,
            124: 15,
        }

        self.write_regs(regs.items())


    @driver_method
    def set_train_pattern(self, pattern):
        self.write_reg(89, pattern)

    @driver_method
    def enable_test_pattern(self, enabled):
        self.write_reg(122, 3 if enabled else 0)

    @driver_method
    def set_number_frames(self, number):
        """number of frames to be captured in internal exposure mode"""
        assert number > 0
        self.write_reg(80, number)

    @driver_method
    def set_exposure_value(self, value):
        """exposure value according to datasheet equation. if None, external exposure mode is enabled"""
        self.write_reg(70, 1 if value is None else 0) # external exposure mode
        if value is not None:
            self.write_regs([(71, value & 0xFFFF), (72, value >> 16)]) # 24 bits


    @driver_method
    def write_reg(self, reg, value):
        reg = int(reg) & 0x7F
        value = int(value) & 0xFFFF
        self.get_spi().xfer2([reg | 0x80, (value & 0xFF00) >> 8, value & 0xFF])

    @driver_method
    def write_regs(self, regs):
        xfer = []
        for reg, value in regs:
            reg = int(reg) & 0x7F
            value = int(value) & 0xFFFF
            xfer.extend((reg | 0x80, (value & 0xFF00) >> 8, value & 0xFF))

        self.get_spi().xfer2(xfer)

    @driver_method
    def read_reg(self, reg):
        reg = int(reg) & 0x7F
        response = self.get_spi().xfer2([reg, 0, 0])
        value = (response[1] << 8) | response[2]

        return value

    @driver_method
    def get_spi(self):
        spi = self.spiobj
        if spi is None:
            import spidev
            spi = spidev.SpiDev()
            spi.open(3, 0)
            self.spiobj = spi
        return spi
