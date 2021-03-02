import os

from nmigen.build.run import BuildProducts

__all__ = ["program_fatbitstream_local"]


def program_fatbitstream_local(platform, build_products: BuildProducts, name, **kwargs):
    fatbitstream_name = "{}.fatbitstream.sh".format(name)
    with build_products.extract(fatbitstream_name) as fatbitstream_file:
        os.system("bash {}".format(fatbitstream_file))
