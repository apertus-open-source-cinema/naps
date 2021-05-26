# a decorator to mark methods in elaboratables that should end up in the pydriver
# all DriverMethod instances are collected and shipped with the pydriver

__all__ = ["driver_method", "driver_property", "driver_init", "DriverData"]


class DriverItem:
    pass


class DriverMethod(DriverItem):
    def __init__(self, function, is_property=False, is_init=False):
        self.is_property = is_property
        self.is_init = is_init
        self.function = function

    def __repr__(self):
        if self.is_property:
            return "driver_property"
        elif self.is_init:
            return "driver_init()"
        else:
            return "driver_method()"


def driver_method(function):
    return DriverMethod(function)


def driver_property(function):
    return DriverMethod(function, is_property=True)


def driver_init(function):
    return DriverMethod(function, is_init=True)


class DriverData(DriverItem):
    def __init__(self, data):
        self.data = data

    def __repr__(self):
        return "<DriverData>"
