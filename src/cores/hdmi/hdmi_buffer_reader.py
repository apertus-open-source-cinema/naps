from nmigen import *


class HdmiBufferReader(Elaboratable):
    def __init__(self, ring_buffer, hdmi_plugin, modeline):
        self.modeline = modeline
        self.hdmi_plugin = hdmi_plugin
        self.ring_buffer = ring_buffer

    def elaborate(self, platform):
        m = Module()

        return m
