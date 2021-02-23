# the 1x hdmi plugin module
# see: https://wiki.apertus.org/index.php/Beta_HDMI_Plugin_Module

from nmigen.build import Resource, Subsignal, Pins, PinsN, Attrs
from .plugin_connector import PluginDiffPair

__all__ = ["hdmi_plugin_connect"]


def hdmi_plugin_connect(platform, plugin_number):
    if "plugin_{}:gpio0".format(plugin_number) in platform._conn_pins:
        lowspeed_signals = [
            # i2c to read edid data from the monitor
            Subsignal("sda", Pins("lvds5_n", dir='io', conn=("plugin", plugin_number)), Attrs(IOSTANDARD="LVCMOS25")),
            Subsignal("scl", Pins("lvds5_p", dir='io', conn=("plugin", plugin_number)), Attrs(IOSTANDARD="LVCMOS25")),

            # hdmi plugin-module specific signals
            Subsignal("output_enable", PinsN("gpio6", dir='o', conn=("plugin", plugin_number)), Attrs(IOSTANDARD="LVCMOS33")),
            Subsignal("equalizer", Pins("gpio1 gpio4", dir='o', conn=("plugin", plugin_number)), Attrs(IOSTANDARD="LVCMOS33")),
            Subsignal("dcc_enable", Pins("gpio5", dir='o', conn=("plugin", plugin_number)), Attrs(IOSTANDARD="LVCMOS33")),
            Subsignal("vcc_enable", Pins("gpio7", dir='o', conn=("plugin", plugin_number)), Attrs(IOSTANDARD="LVCMOS33")),
            Subsignal("ddet", Pins("gpio3", dir='o', conn=("plugin", plugin_number)), Attrs(IOSTANDARD="LVCMOS33")),
            Subsignal("ihp", Pins("gpio2", dir='i', conn=("plugin", plugin_number)), Attrs(IOSTANDARD="LVCMOS33")),
        ]
    else:
        lowspeed_signals = []

    platform.add_resources([
        Resource("hdmi", plugin_number,
             Subsignal("clock", PluginDiffPair(platform, plugin_number, pin=3, dir='o', serdes=True), Attrs(IOSTANDARD="LVDS_25")),
             Subsignal("b", PluginDiffPair(platform, plugin_number, pin=2, dir='o', serdes=True), Attrs(IOSTANDARD="LVDS_25")),
             Subsignal("g", PluginDiffPair(platform, plugin_number, pin=1, dir='o', serdes=True), Attrs(IOSTANDARD="LVDS_25")),
             Subsignal("r", PluginDiffPair(platform, plugin_number, pin=0, dir='o', serdes=True), Attrs(IOSTANDARD="LVDS_25")),
             *lowspeed_signals
        )
    ])
