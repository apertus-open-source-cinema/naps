from nmigen import *
from naps import driver_method
from naps.cores.peripherals import BitbangSPI

__all__ = ["Cmv12kSpi"]

class Cmv12kSpi(Elaboratable):
    def __init__(self, sensor_spi):
        self.sensor_spi = sensor_spi

    def elaborate(self, platform):
        m = Module()

        m.submodules.spi = BitbangSPI(self.sensor_spi)

        return m

    @driver_method
    def set_train_pattern(self, pattern):
        self.write_reg(89, pattern)

    @driver_method
    def set_bit_mode(self, mode):
        assert mode == 12
        self.write_reg(118, 0) # for 12 bits

    @driver_method
    def write_reg(self, reg, value):
        import spidev
        spi = spidev.SpiDev()
        spi.open(3, 0)

        reg = int(reg) & 0x7F
        value = int(value) & 0xFFFF
        spi.xfer2([reg | 0x80, (value & 0xFF00) >> 8, value & 0xFF])

        spi.close()

    @driver_method
    def read_reg(self, reg):
        import spidev
        spi = spidev.SpiDev()
        spi.open(3, 0)

        reg = int(reg) & 0x7F
        response = spi.xfer2([reg, 0, 0])
        value = (response[1] << 8) | response[2]

        spi.close()
        return value
