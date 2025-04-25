# this is a somewhat unholy utility to be able to import private amaranth stuff without warning:
# the one stop shop for unstable amaranth internals

def __getattr__(name):
    import warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", "name `.*` is a private implementation detail and should not be imported")
        import amaranth.hdl.xfrm as xfrm
        import amaranth.hdl.ast as ast
        for option in [xfrm, ast]:
            if hasattr(option, name):
                return getattr(option, name)
        raise AttributeError()
