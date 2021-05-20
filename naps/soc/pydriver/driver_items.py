# a decorator to mark methods in elaboratables that should end up in the pydriver
# all DriverMethod instances are collected and shipped with the pydriver

__all__ = ["driver_method", "driver_property", "DriverData"]


class DriverItem:
    pass


class DriverMethod(DriverItem):
    def __init__(self, function, is_property):
        self.is_property = is_property
        self.function = function

    def __repr__(self):
        if self.is_property:
            return "driver_property"
        else:
            return "driver_method()"


def driver_method(function):
    return DriverMethod(function, is_property=False)


def driver_property(function):
    return DriverMethod(function, is_property=True)


class DriverData(DriverItem):
    def __init__(self, data):
        self.data = data

    def __repr__(self):
        return "<DriverData>"
