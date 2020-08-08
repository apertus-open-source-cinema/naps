import inspect
import pickle
import re
from collections import OrderedDict
from datetime import datetime
from glob import glob
from hashlib import sha256
from json import dumps
from os import stat, path
import argparse

from nmigen.build.run import LocalBuildProducts

__all__ = ["cli"]


class Cli:
    def __init__(self, top_class, runs_on):
        parser = argparse.ArgumentParser()
        parser.add_argument('-e', '--elaborate', help='Elaborates the experiment', action="store_true")
        parser.add_argument('-b', '--build',
                            help='builds the experiment with the vendor tools if the elaboration result changed; implies -e',
                            action="store_true")
        parser.add_argument('-p', '--program', help='programs the board; programs the last build if used without -b',
                            action="store_true")
        runs_on_choices = [plat.__name__.replace("Platform", "") for plat in runs_on]
        parser.add_argument('-d', '--device', help='specify the device to build for', choices=runs_on_choices,
                            required=True)
        parser.add_argument('-s', '--soc', help='specifies the soc platform to build for')
        self.parser = parser
        self.args = parser.parse_args()

        hardware_platform = getattr(__import__('devices'), "{}Platform".format(self.args.device))
        if self.args.soc:
            soc_platform = getattr(__import__('soc.platforms').platforms, "{}SocPlatform".format(self.args.soc))
            self.platform = soc_platform(hardware_platform())
        else:
            self.platform = hardware_platform()
        self.top_class = top_class
        self.ran = False

    def __enter__(self):
        self.ran = True
        return self.platform

    def __exit__(self, exc_type, exc_value, traceback):
        name = "{file_basename}-{device}".format(
            file_basename=inspect.stack()[1].filename.split("/")[-1].replace(".py", ""),
            device=self.args.device
        )

        if self.args.elaborate or self.args.build:
            build_name = name + datetime.now().strftime("-%d-%b-%Y--%H-%M-%S")
            build_plan = self.platform.build(
                self.top_class(),
                name=build_name,
                do_build=False
            )

            do_build = True
            if self.args.build:
                # check if we need to rebuild
                build_plan_hash = hash_build_plan(build_plan.files)
                previous_build_name = get_previous_build_name(name)
                if previous_build_name:
                    previous_date = extract_date(previous_build_name)
                    old_build_plan_files = OrderedDict((replace_date(k, previous_date), open(in_build((replace_date(k, previous_date)))).read()) for k, v in build_plan.files.items())
                    old_build_plan_hash = hash_build_plan(old_build_plan_files)
                    if old_build_plan_hash == build_plan_hash:
                        do_build = False

            if do_build:
                build_plan.execute_local(in_build())
                with open(in_build('{}.extra_files.pickle'.format(build_name)), 'wb') as f:
                    pickle.dump(self.platform.extra_files, f)

        if self.args.program:
            build_files = glob(in_build('build_{}-*.sh'.format(name)))
            if not build_files:
                raise FileNotFoundError(
                    'no previous build exists for "{}". cant program it without building'.format(name)
                )
            sorted_build_files = sorted(build_files, key=lambda x: stat(x).st_mtime, reverse=True)
            build_name = sorted_build_files[0].replace('build/build_', '').replace('.sh', '')
            with open(in_build('{}.extra_files.pickle'.format(build_name)), 'rb') as f:
                self.platform.extra_files = pickle.load(f)
            self.platform.toolchain_program(LocalBuildProducts(in_build()), name=build_name)
        else:
            print("no action specified")
            self.parser.print_help()


cli = Cli


def in_build(subpath=''):
    return path.join('build', subpath)


def replace_date(name, replacement=""):
    return re.sub("-\\d{2}-\\w{3}-\\d{4}--\\d{2}-\\d{2}-\\d{2}", replacement, name)


def extract_date(name):
    return re.search("(-\\d{2}-\\w{3}-\\d{4}--\\d{2}-\\d{2}-\\d{2})", name).group(1)


def hash_build_plan(build_plan_files):
    striped_build_plan = OrderedDict((replace_date(k), replace_date(v)) for k, v in build_plan_files.items())
    json_repr = dumps(striped_build_plan)
    return sha256(json_repr.encode("utf-8")).hexdigest()


def get_previous_build_name(basename):
    build_files = glob(in_build('build_{}-*.sh'.format(basename)))
    if not build_files:
        return None
    sorted_build_files = sorted(build_files, key=lambda x: stat(x).st_mtime, reverse=True)
    return sorted_build_files[0].replace('build/build_', '').replace('.sh', '')
