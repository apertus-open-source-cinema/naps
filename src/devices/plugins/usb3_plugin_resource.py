# the usb3 plugin module plugin module resource
# (not the platform definition for building gateware for the fpga _on_ the plugin module itself)
# see: https://wiki.apertus.org/index.php/1x_USB_3.0_Plugin_Module

from nmigen.build import *

from devices import MicroR2Platform
from devices.plugins.plugin_connector import PluginDiffPair


def usb3_plugin_connect(platform, plugin_number):
    if isinstance(platform, MicroR2Platform):
        lowspeed_signals = [
            Subsignal(
                "jtag",
                Subsignal("tms", Pins("gpio0", dir="io", conn=("plugin", plugin_number)), Attrs(IOSTANDARD="LVCMOS25")),
                Subsignal("tck", Pins("gpio1", dir="io", conn=("plugin", plugin_number)), Attrs(IOSTANDARD="LVCMOS25")),
                Subsignal("tdi", Pins("gpio2", dir="io", conn=("plugin", plugin_number)), Attrs(IOSTANDARD="LVCMOS25")),
                Subsignal("tdo", Pins("gpio3", dir="io", conn=("plugin", plugin_number)), Attrs(IOSTANDARD="LVCMOS25")),
            ),
            Subsignal("jtag_enb", Pins("gpio4", dir="io", conn=("plugin", plugin_number)),
                      Attrs(IOSTANDARD="LVCMOS25")),
            Subsignal("program", PinsN("gpio5", dir="io", conn=("plugin", plugin_number)),
                      Attrs(IOSTANDARD="LVCMOS25")),
            Subsignal("init", PinsN("gpio6", dir="io", conn=("plugin", plugin_number)), Attrs(IOSTANDARD="LVCMOS25")),
            Subsignal("done", PinsN("gpio7", dir="io", conn=("plugin", plugin_number)), Attrs(IOSTANDARD="LVCMOS25")),
        ]
    else:
        lowspeed_signals = []

    platform.add_resources([
        Resource(
            "usb3_plugin", plugin_number,
            Subsignal(
                "lvds",
                Subsignal("valid", PluginDiffPair(platform, plugin_number, 0, dir='o', serdes=True), Attrs(IOSTANDARD="LVDS_25")),
                Subsignal("lane0", PluginDiffPair(platform, plugin_number, 1, dir='o', serdes=True), Attrs(IOSTANDARD="LVDS_25")),
                Subsignal("lane1", PluginDiffPair(platform, plugin_number, 2, dir='o', serdes=True), Attrs(IOSTANDARD="LVDS_25")),
                Subsignal("lane2", PluginDiffPair(platform, plugin_number, 3, dir='o', serdes=True), Attrs(IOSTANDARD="LVDS_25")),
                Subsignal("lane3", PluginDiffPair(platform, plugin_number, 4, dir='o', serdes=True), Attrs(IOSTANDARD="LVDS_25")),
                Subsignal("clk_word", PluginDiffPair(platform, plugin_number, 5, dir='o', serdes=True), Attrs(IOSTANDARD="LVDS_25")),
            ),
            *lowspeed_signals
        )
    ])
