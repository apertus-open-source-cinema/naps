"""Descriptions of useful Record layouts.
"""

i2c = [
    ("sda", 1),
    ("scl", 1)
]

plugin_module = [
    ("lvds", 6),
    ("gpio", 8),
    ("i2c", i2c),
]


def gen_plugin_connector(*, lvds, gpio, i2c):
    con = {}
    for i, l in enumerate(lvds):
        p, n = l.split()
        con["lvds{}_p".format(i)] = "{}".format(p)
        con["lvds{}_n".format(i)] = "{}".format(n)

    for i, g in enumerate(gpio):
        con["gpio{}".format(i)] = "{}".format(g)

    scl, sda = i2c

    con["i2c_scl"] = "{}".format(scl)
    con["i2c_sda"] = "{}".format(sda)

    return con
