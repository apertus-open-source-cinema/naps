import inspect
from contextlib import contextmanager, AbstractContextManager
from datetime import datetime

from soc.zynq import ZynqSocPlatform
import argparse


class Cli(AbstractContextManager):
    def __init__(self, top_class):
        parser = argparse.ArgumentParser()
        parser.add_argument('-c', help='only check; dont build', action="store_true")
        parser.add_argument('-d', help='device', default='MicroR2')
        self.args = parser.parse_args()
        hardware_platform = getattr(__import__('devices'), "{}Platform".format(self.args.d))
        self.platform = ZynqSocPlatform(hardware_platform())
        self.top_class = top_class
        self.ran = False

    def __enter__(self):
        self.ran = True
        return self.platform

    def __exit__(self, exc_type, exc_value, traceback):
        name = inspect.stack()[1].filename.split("/")[-1].replace(".py", "") \
               + datetime.now().strftime("-%d-%b-%Y--%H-%M-%S")
        self.platform.build(self.top_class(), name=name, do_build=not self.args.c)

    def __del__(self):
        if not self.ran:
            self.__enter__()
            self.__exit__(None, None, None)


cli = Cli

