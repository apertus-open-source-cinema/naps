# the usb3 plugin module plugin module resource
# (not the platform definition for building gateware for the fpga _on_ the plugin module itself)
# see: https://wiki.apertus.org/index.php/1x_USB_3.0_Plugin_Module

from amaranth.build import *
from .plugin_connector import PluginDiffPair

__all__ = ["usb3_plugin_connect"]


def usb3_plugin_connect(platform, plugin_slot, resource_number=0, gpio=True, lvds=True, gpio_attrs=dict(IOSTANDARD="LVCMOS25")):
    if gpio:
        gpio_signals = [
            Subsignal(
                "jtag",
                Subsignal("tms", Pins("gpio0", dir="io", conn=("plugin", plugin_slot)), Attrs(**gpio_attrs)),
                Subsignal("tck", Pins("gpio1", dir="io", conn=("plugin", plugin_slot)), Attrs(**gpio_attrs)),
                Subsignal("tdi", Pins("gpio2", dir="io", conn=("plugin", plugin_slot)), Attrs(**gpio_attrs)),
                Subsignal("tdo", Pins("gpio3", dir="io", conn=("plugin", plugin_slot)), Attrs(**gpio_attrs)),
            ),
            Subsignal("jtag_enb", Pins("gpio4", dir="io", conn=("plugin", plugin_slot)), Attrs(**gpio_attrs)),
            Subsignal("program", PinsN("gpio5", dir="io", conn=("plugin", plugin_slot)), Attrs(**gpio_attrs)),
            Subsignal("init", PinsN("gpio6", dir="io", conn=("plugin", plugin_slot)), Attrs(**gpio_attrs)),
            Subsignal("done", PinsN("gpio7", dir="io", conn=("plugin", plugin_slot)), Attrs(**gpio_attrs)),
        ]
    else:
        gpio_signals = []

    if lvds:
        lvds_signals = [
            Subsignal(
                "lvds",
                Subsignal("valid", PluginDiffPair(platform, plugin_slot, 0, dir='o', serdes=True), Attrs(IOSTANDARD="LVDS_25")),
                Subsignal("lane0", PluginDiffPair(platform, plugin_slot, 1, dir='o', serdes=True), Attrs(IOSTANDARD="LVDS_25")),
                Subsignal("lane1", PluginDiffPair(platform, plugin_slot, 2, dir='o', serdes=True), Attrs(IOSTANDARD="LVDS_25")),
                Subsignal("lane2", PluginDiffPair(platform, plugin_slot, 3, dir='o', serdes=True), Attrs(IOSTANDARD="LVDS_25")),
                Subsignal("lane3", PluginDiffPair(platform, plugin_slot, 4, dir='o', serdes=True), Attrs(IOSTANDARD="LVDS_25")),
                Subsignal("clk_word", PluginDiffPair(platform, plugin_slot, 5, dir='o', serdes=True), Attrs(IOSTANDARD="LVDS_25")),
            ),
        ]
    else:
        lvds_signals = []

    platform.add_resources([
        Resource(
            "usb3_plugin", resource_number,
            *lvds_signals,
            *gpio_signals,
        )
    ])
