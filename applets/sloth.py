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

        adc = m.submodules.adc = HMCAD1511Phy()

        # DramPacketRingbufferStreamWriter(adc.output, max_packet_size=0x800000, n_buffers=4)


        return m

if __name__ == "__main__":
    cli(Top, runs_on=(PrjSlothPlatform,), possible_socs=(ZynqSocPlatform, ))
