"""Descriptions of useful Record layouts.
"""

i2c = [
    ("sda", 1),
    ("scl", 1)
]

ar0330 = [
    ("shutter", 1),
    ("trigger", 1),
    ("clk", 1),
    ("reset", 1),
    ("lvds", 4),
    ("lvds_clk", 1),
]

plugin_module = [
    ("lvds", 6),
    ("gpio", 8),
    ("i2c", i2c),
]

encoder = [
    ("push", 1),
    ("quadrature", 2)
]
