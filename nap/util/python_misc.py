import re

__all__ = ["decimal_range", "camel_to_snake"]


def decimal_range(start, stop, step):
    next_decimal = start
    while next_decimal < stop:
        yield next_decimal
        next_decimal += step
    return


def camel_to_snake(name):
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
