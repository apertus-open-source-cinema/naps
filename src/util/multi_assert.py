from varname import varname


def multi_assert(failure_desc, *args):
    for arg in args:
        assert arg, failure_desc.format(repr=str(arg))
