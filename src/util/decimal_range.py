def decimal_range(start, stop, step):
    next_decimal = start
    while next_decimal < stop:
        yield next_decimal
        next_decimal += step
    return