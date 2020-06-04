import inspect
from contextlib import contextmanager
from datetime import datetime

from devices.micro_r2_platform import MicroR2Platform
from soc.zynq import ZynqSocPlatform
import argparse


@contextmanager
def cli(top_class):
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', help='only check; dont build', action="store_true")
    args = parser.parse_args()

    platform = ZynqSocPlatform(MicroR2Platform())  # TODO: make this dynamically reconfigurable (via comandline switches)
    try:
        yield platform
    finally:
        name = inspect.stack()[1].filename.split("/")[-1].replace(".py", "") \
               + datetime.now().strftime("-%d-%b-%Y--%H-%M-%S")
        platform.build(top_class(), name=name, do_build=not args.c)