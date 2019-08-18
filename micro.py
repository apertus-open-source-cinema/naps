from nmigen.build import Resource, Subsignal, Pins, DiffPairs, Connector


def gen_plugin_connector(*, conn, lvds, gpio, i2c):
    a = {}

    conn_prefix = "{}_{}:".format(*conn)

    for i, l in enumerate(lvds):
        p, n = l.split()
        a["lvds{}_p".format(i)] = "{}{}".format(conn_prefix, p)
        a["lvds{}_n".format(i)] = "{}{}".format(conn_prefix, n)

    for i, g in enumerate(gpio):
        a["gpio{}".format(i)] = "{}{}".format(conn_prefix, g)

    scl, sda = i2c.split()

    a["i2c_scl"] = "{}{}".format(conn_prefix, scl)
    a["i2c_sda"] = "{}{}".format(conn_prefix, sda)

    return a


micro_r2 = [
            Resource("sensor", 0,
                Subsignal("shutter",  Pins("25", dir='o', conn=("extension", 0))),
                Subsignal("trigger",  Pins("27", dir='o', conn=("extension", 0))),
                Subsignal("reset",    Pins("31", dir='o', conn=("extension", 0))),
                Subsignal("clk",      Pins("33", dir='o', conn=("extension", 0))),
                Subsignal("lvds_clk", DiffPairs("52", dir='i', conn=("extension", 0))),
                Subsignal("lvds",     DiffPairs("41 45 55 65", "43 47 57 67", dir='i', conn=("extension", 0))),
            ),
            Resource("i2c", 0, 
                Subsignal("scl",  Pins("35", dir='io', conn=("extension", 0))),
                Subsignal("sda",  Pins("37", dir='io', conn=("extension", 0))),
            ),
            Connector("plugin_s", 0, 
                gen_plugin_connector(
                    lvds=["21 23", "3 5", "9 11", "13 15", "4 6", "10 12"], 
                    gpio=[71, 73, 63, 61, 64, 62, 75, 77],
                    i2c=[46, 48]),
                    conn=("extension", 0),
                ),

            Connector("plugin_n", 0, 
                gen_plugin_connector(
                    lvds=["14 16", "22 24", "26 28", "32 34", "36 38", "42 44"], 
                    gpio=[76, 78, 80, 84, 86, 88, 90, 74],
                    i2c=[52, 54]),
                    conn=("extension", 0),
                ),
            Connector("pmod_n", 0, "110 106 100 96 - - 108 104 98 94 - -", conn=("extension", 0),),
            Connector("pmod_s", 0, "97 95 89 85 - - 99 93 87 83 - -", conn=("extension", 0),),
            Connector("pmod_e", 0, "103 105 107 109 - -", conn=("extension", 0),),
            Resource("ws2812", Pins("56", dir='io', conn=("extension", 0)))
            Resource("encoder", 0,
                Subsignal("quadrature", Pins("58 68", dir='i', conn=("extension", 0))),
                Subsignal("push", Pins("66", dir='i', conn=("extension", 0))))
        ]
