from amaranth import *
from amaranth.lib.cdc import FFSynchronizer, PulseSynchronizer
from naps import driver_method, Rose, Fell
from naps.cores import StreamBuffer, ImageStream
from naps.soc import PERIPHERAL_DOMAIN
from .s7_phy import HostTrainer, Cmv12kPhy

__all__ = ["Cmv12kRx"]

class Cmv12kRx(Elaboratable):
    def __init__(self, sensor, num_lanes=32, bits=12, freq=250e6, mode="normal", domain="cmv12k"):
        """Sensor Configuration Options:
        num_lanes: Total number of sensor LVDS lanes to use.
            Valid values for the sensor are 64, 32, 16, 8, 4, 2, or 1.
            Notes: 64 lanes is not supported by the Beta hardware.
                   1 lane is not supported because one-sided readout is not supported.
                   Currently, only 32 lanes is supported, but others will be later.
        bits: Number of bits per pixel.
            Valid values for the sensor are 12, 10, or 8 bits.
            Notes: Currently, 10 and 8 bit modes are not supported, but will be later.
        freq: LVDS clock frequency to drive the sensor, in Hz.
            Valid values for the sensor are 100e6-600e6.
            Notes: Frequencies faster than 250e6 are liable to have timing problems.
                   Currently, only 250e6 is supported, but others might be later.
        mode: Sensor readout mode.
            Valid values for the sensor are "normal", "subsampling", "binning", and "onesided".
            Notes: Currently, only "normal" mode is supported. One-sided mode
                   will likely never be supported.
        """

        assert num_lanes in (64, 32, 16, 8, 4, 2, 1), "invalid number of lanes"
        assert bits in (12, 10, 8), "invalid bit depth"
        assert 100e6 < freq < 600e6, "invalid frequency"
        assert mode in ("normal", "subsampling", "binning", "onesided"), "invalid mode"

        assert num_lanes == 32, "unsupported number of lanes"
        assert bits == 12, "unsupported bit depth"
        assert freq == 250e6, "unsupported frequency"
        assert mode == "normal", "unsupported mode"

        self.num_lanes = num_lanes
        self.bits = bits
        self.freq = freq
        self.mode = mode
        self.domain = domain

        self.lvds_outclk = sensor.lvds_outclk.i
        # 32 lane mode uses every 2nd lane, 16 lane mode uses every 4th, etc...
        lane_nums = range(1, 65, 2**(7-num_lanes.bit_length()))
        self.lanes = Cat(getattr(sensor, f"lvds_{l}").i for l in lane_nums)
        self.lane_ctrl = sensor.lvds_ctrl.i

        self.output = ImageStream(num_lanes*bits)
        self.output_domain = domain

        self.trainer = HostTrainer(num_lanes, bits)
        self.phy = Cmv12kPhy(num_lanes, bits, freq, mode, domain=domain)

    def elaborate(self, platform):
        m = Module()

        # temp clock setup
        platform.ps7.fck_domain(200e6, self.domain+"_delay_ref")
        m.domains += ClockDomain(self.domain+"_ctrl")
        m.d.comb += ClockSignal(self.domain+"_ctrl").eq(ClockSignal(PERIPHERAL_DOMAIN))

        phy = m.submodules.phy = self.phy
        trainer = m.submodules.trainer = self.trainer
        m.submodules += FFSynchronizer(trainer.lane_pattern, phy.lane_pattern, o_domain=self.domain+"_hword")

        m.d.comb += [
            phy.outclk.eq(self.lvds_outclk),
            phy.lanes.eq(Cat(self.lanes, self.lane_ctrl)),

            phy.lane_delay_reset.eq(trainer.lane_delay_reset),
            phy.lane_delay_inc.eq(trainer.lane_delay_inc),
            phy.lane_bitslip.eq(trainer.lane_bitslip),
            phy.outclk_delay_reset.eq(trainer.outclk_delay_reset),
            phy.outclk_delay_inc.eq(trainer.outclk_delay_inc),
            phy.halfslip.eq(trainer.halfslip),

            trainer.lane_match.eq(phy.lane_match),
            trainer.lane_mismatch.eq(phy.lane_mismatch),
        ]

        # synchronize valid signal to output domain
        lanes_valid = Signal()
        valid_sync = m.submodules.valid_sync = PulseSynchronizer(self.domain+"_hword", self.output_domain)
        trained = Signal()
        m.submodules += FFSynchronizer(trainer.trained, trained, o_domain=self.domain+"_hword")
        m.d.comb += [
            valid_sync.i.eq(phy.output_valid & trained),
            lanes_valid.eq(valid_sync.o)
        ]

        # information about the "current" pixel
        data_lanes = Signal(len(self.lanes)*self.bits)
        pixel_valid = Signal()
        line_valid = Signal()
        frame_valid = Signal()

        # information about the next pixel, i.e. what we grab from the PHY
        next_data_lanes = Signal(len(self.lanes)*self.bits)
        next_pixel_valid = Signal()
        next_line_valid = Signal()
        next_frame_valid = Signal()

        # on the rising edge of the valid signal, grab the next pixel from the
        # PHY. this is a clock domain crossing, but since the source clock is in
        # phase with the output clock, we will be okay without synchronization.
        # note that the valid signal rises only once every `self.bits/2` clocks.
        with m.If(lanes_valid):
            m.d[self.output_domain] += [
                next_data_lanes.eq(Cat(*phy.output[:-1])),
                Cat(next_pixel_valid, next_line_valid, next_frame_valid).eq(phy.output[-1]),
                # move the next pixel to the current pixel
                data_lanes.eq(next_data_lanes),
                Cat(pixel_valid, line_valid, frame_valid).eq(Cat(next_pixel_valid, next_line_valid, next_frame_valid))
            ]

        # once we've got that, generate the output stream information
        output = ImageStream(len(self.lanes)*self.bits)
        m.d.comb += output.payload.eq(data_lanes)
        with m.If(Fell(m, lanes_valid, self.output_domain)):
            m.d.comb += [
                output.valid.eq(pixel_valid),
                # if the next pixel isn't a valid line or frame, this pixel is
                # the last one of the current line/frame
                output.line_last.eq(line_valid & ~next_line_valid),
                output.frame_last.eq(frame_valid & ~next_frame_valid),
            ]

        # we are naughty and do not respect the ready signal, so add a buffer
        # to handle that part of the contract for us
        buffer = m.submodules.buffer = DomainRenamer(self.output_domain)(StreamBuffer(output))
        m.d.comb += self.output.connect_upstream(buffer.output)

        return m

    @driver_method
    def configure_sensor_defaults(self, sensor_spi):
        """configure sensor readout modes and default settings"""
        sensor_spi.set_readout_configuration(self.num_lanes, self.bits, self.freq, self.mode)
        sensor_spi.enable_test_pattern(False)
        sensor_spi.set_number_frames(1)
        sensor_spi.set_exposure_value(1536)
