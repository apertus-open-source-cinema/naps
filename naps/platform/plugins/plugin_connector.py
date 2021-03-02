# a helper to generate the plugin connector *on the camera side*
from nmigen.build import Connector, DiffPairs
from naps.util.sim import SimPlatform

__all__ = ["add_plugin_connector", "PluginDiffPair", "is_resource_pin_inverted", "is_connector_pin_inverted", "is_signal_inverted"]


def add_plugin_connector(platform, number, conn=None, lvds=None, gpio=None, i2c=None):
    if not hasattr(platform, "inverts"):
        platform.inverts = {}

    mapping = {}

    if lvds is None:
        lvds = []
    for i, l in enumerate(lvds):
        splited = l.split()
        if len(splited) == 3:
            p, n = splited[0], splited[2]
            invert = True
        elif len(splited) == 2:
            p, n = splited
            invert = False
        else:
            raise ValueError()

        platform.inverts["plugin_{}:lvds{}_p".format(number, i)] = invert
        mapping["lvds{}_p".format(i)] = "{}".format(p)
        mapping["lvds{}_n".format(i)] = "{}".format(n)

    if gpio is None:
        gpio = []
    for i, g in enumerate(gpio):
        mapping["gpio{}".format(i)] = "{}".format(g)

    if i2c is not None:
        scl, sda = i2c

        mapping["i2c_scl"] = "{}".format(scl)
        mapping["i2c_sda"] = "{}".format(sda)

    platform.add_connectors([
        Connector(
            "plugin", number,
            mapping,
            conn=conn,
        ),
    ])


# the serdes parameter makes that we do not invert the pin here but defer it
def _is_pin_inverted(platform, plugin_number, pin, serdes):
    if not hasattr(platform, "inverts"):
        return False

    inverts_intex = "plugin_{}:lvds{}_p".format(plugin_number, pin)
    invert = platform.inverts[inverts_intex]
    if serdes:
        return False
    else:
        del platform.inverts[inverts_intex]
        return invert


def PluginDiffPair(platform, plugin_number, pin, dir, serdes=False):
    return DiffPairs(
        p="lvds{}_p".format(pin),
        n="lvds{}_n".format(pin),
        dir=dir,
        conn=("plugin", plugin_number),
        invert=_is_pin_inverted(platform, plugin_number, pin, serdes)
    )


def is_connector_pin_inverted(platform, connector_pin):
    if not hasattr(platform, "inverts"):
        return False

    if connector_pin in platform.inverts:
        invert = platform.inverts[connector_pin]
        return invert
    else:
        return False


def is_resource_pin_inverted(platform, resource, path):
    def subsignal_by_path(subsignal, path):
        for s in subsignal.ios:
            if s.name == path[0]:
                if len(path) > 1:
                    return subsignal_by_path(s, path[1:])
                else:
                    return s
        raise KeyError()
    subsignal = subsignal_by_path(platform.resources[resource], path)
    assert len(subsignal.ios) == 1
    assert len(subsignal.ios[0].p.names) == 1
    return is_connector_pin_inverted(platform, subsignal.ios[0].p.names[0])


def is_signal_inverted(platform, signal):
    if isinstance(platform, SimPlatform):
        return False

    for res_name, res in platform._requested.items():
        def recurse_fields(x, path):
            if hasattr(x, "fields"):
                for pin, field in x.fields.items():
                    if field is signal:
                        return is_resource_pin_inverted(platform, res_name, [*path, pin])
                    result = recurse_fields(field, path=[*path, pin])
                    if result is not None:
                        return result
            return None
        result = recurse_fields(res, path=[])
        if result is not None:
            break
    if result is not None:
        return result
    raise KeyError("signal {} was not found in platform. could not determine if it should be inverted".format(signal))
