from amaranth import *
from naps import *
from naps.platform.prjsloth_platform import PrjSlothPlatform


class Top(Elaboratable):
    def __init__(self):
        self.width = 1280
        self.height = 720

    def elaborate(self, platform: PrjSlothPlatform):
        m = Module()


        # Control Pane
        i2c_pads = platform.request("i2c")
        m.submodules.i2c = BitbangI2c(i2c_pads)

        power_control = platform.request("power_ctl")
        for enable in power_control.layout:
            name = enable[0]
            signal = ControlSignal(name = name)
            setattr(self, name, signal)
            m.d.comb += power_control[name].o.eq(signal)
        # for entry in power_control:
        #     print(entry)


        return m


if __name__ == "__main__":
    cli(Top, runs_on=(PrjSlothPlatform,), possible_socs=(ZynqSocPlatform, ))
