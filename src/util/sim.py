from nmigen.back.pysim import Simulator


def wait_for(expr, timeout=100, must_clock=True):
    for i in range(timeout):
        if i > 0 or must_clock:
            yield
        if (yield expr):
            return
    raise TimeoutError("{} did not become '1' within {} cycles".format(expr, timeout))


def pulse(signal, length=1, after=0):
    yield signal.eq(1)
    for _ in range(length):
        yield
    yield signal.eq(0)
    for _ in range(after):
        yield


def do_nothing(length=10):
    for i in range(length):
        yield  # we expect that nothing happens here
