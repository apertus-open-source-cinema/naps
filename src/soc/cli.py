import inspect
from contextlib import contextmanager
from datetime import datetime

from soc.zynq import ZynqSocPlatform
import argparse


@contextmanager
def cli(top_class):
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', help='only check; dont build', action="store_true")
    parser.add_argument('-d', help='device', default='micro')
    args = parser.parse_args()

    from devices.micro_r2_platform import MicroR2Platform
    from devices.beta_platform import BetaPlatform
    from devices.zybo_platform import ZyboPlatform
    hardware_platform = {"micro": MicroR2Platform, "beta": BetaPlatform, "zybo": ZyboPlatform}[args.d]
    platform = ZynqSocPlatform(hardware_platform())
    try:
        yield platform
    finally:
        name = inspect.stack()[1].filename.split("/")[-1].replace(".py", "") \
               + datetime.now().strftime("-%d-%b-%Y--%H-%M-%S")
        platform.build(top_class(), name=name, do_build=not args.c)