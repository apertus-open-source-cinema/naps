def gen_plugin_connector(*, lvds, gpio=None, i2c=None):
    con = {}
    for i, l in enumerate(lvds):
        p, n = l.split()
        con["lvds{}_p".format(i)] = "{}".format(p)
        con["lvds{}_n".format(i)] = "{}".format(n)

    if gpio is None:
        gpio = []
    for i, g in enumerate(gpio):
        con["gpio{}".format(i)] = "{}".format(g)

    if i2c:
        scl, sda = i2c

        con["i2c_scl"] = "{}".format(scl)
        con["i2c_sda"] = "{}".format(sda)

    return con