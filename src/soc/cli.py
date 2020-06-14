import inspect
import pickle
import sys
from datetime import datetime
from glob import glob
from os import stat, path

from nmigen.build.run import LocalBuildProducts

from soc.zynq import ZynqSocPlatform
import argparse


def in_build(subpath):
    dirname = path.dirname(__file__)
    return path.join(dirname, '..', 'build', subpath)


class Cli:
    def __init__(self, top_class):
        parser = argparse.ArgumentParser()
        parser.add_argument('-e', help='elaborate', action="store_true")
        parser.add_argument('-b', help='build; implies -e', action="store_true")
        parser.add_argument('-p', help='program; programs the last build if used without -b', action="store_true")
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
        try:
            name = inspect.stack()[1].filename.split("/")[-1].replace(".py", "")
            if self.args.e or self.args.b:
                build_name = name + datetime.now().strftime("-%d-%b-%Y--%H-%M-%S")
                self.platform.build(
                    self.top_class(),
                    name=build_name,
                    do_build=self.args.b,
                    do_program=self.args.p
                )
                with open(in_build('{}.extra_files.pickle'.format(build_name)), 'wb') as f:
                    pickle.dump(self.platform.extra_files, f)
            elif self.args.p:
                # we program the last version
                build_files = glob(in_build('build_{}-*.sh'.format(name)))
                if not build_files:
                    raise FileNotFoundError(
                        'no previous build exists for "{}". cant programm it without building'.format(name))
                sorted_build_files = sorted(build_files, key=lambda x: stat(x).st_mtime, reverse=True)
                build_name = sorted_build_files[0].replace('build/build_', '').replace('.sh', '')
                with open(in_build('{}.extra_files.pickle'.format(build_name)), 'rb') as f:
                    self.platform.extra_files = pickle.load(f)
                self.platform.toolchain_program(LocalBuildProducts(in_build('')), name=build_name)
            else:
                print("nothing to do")
        except:
            print("\n\nAN EXCEPTION OCCURED:", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)

            exit(1)


cli = Cli
