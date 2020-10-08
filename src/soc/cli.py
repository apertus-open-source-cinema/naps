import inspect
import os
import pickle
from collections import OrderedDict
from datetime import datetime
from glob import glob
from hashlib import sha256
from json import dumps
from os import stat, path
import argparse
from os.path import exists, isdir
from warnings import warn

from nmigen.build.run import LocalBuildProducts

__all__ = ["cli"]


def hash_build_plan(build_plan_files):
    build_plan_files = {k: v.decode("utf-8") if isinstance(v, bytes) else v for k, v in build_plan_files.items()}
    json_repr = dumps(build_plan_files)
    return sha256(json_repr.encode("utf-8")).hexdigest()


def get_previous_build_dir(basename):
    build_files = glob("build/{}*".format(basename))
    build_files = [path for path in build_files if isdir(path)]
    if not build_files:
        return None
    sorted_build_files = sorted(build_files, key=lambda x: stat(x).st_mtime, reverse=True)
    return sorted_build_files[0].replace('build/build_', '').replace('.sh', '')


class Cli:
    def __init__(self, top_class, runs_on, possible_socs=(None,)):
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
        runs_on_choices = [plat.__name__.replace("SocPlatform", "") for plat in possible_socs if plat is not None]
        parser.add_argument('-s', '--soc', help='specifies the soc platform to build for', choices=runs_on_choices)
        self.parser = parser
        self.args = parser.parse_args()

        hardware_platform = getattr(__import__('devices'), "{}Platform".format(self.args.device))
        if self.args.soc:
            soc_platform = getattr(__import__('soc.platforms').platforms, "{}SocPlatform".format(self.args.soc))
            assert soc_platform in possible_socs
            self.platform = soc_platform(hardware_platform())
        else:
            assert None in possible_socs
            self.platform = hardware_platform()
        self.top_class = top_class
        self.ran = False

    def __enter__(self):
        self.ran = True
        return self.platform

    def __exit__(self, exc_type, exc_value, traceback):
        name = inspect.stack()[1].filename.split("/")[-1].replace(".py", "")
        dir_basename = "{}_{}_{}".format(name, self.args.device, self.args.soc)

        if self.args.elaborate or self.args.build:
            build_plan = self.platform.build(
                self.top_class(),
                name=name,
                do_build=False,
            )

            if self.args.build:
                needs_rebuild = True
                build_plan_hash = hash_build_plan(build_plan.files)
                previous_build_dir = get_previous_build_dir(dir_basename)
                if previous_build_dir:
                    try:
                        old_build_plan_files = OrderedDict(
                            (k, open(path.join(previous_build_dir, k)).read())
                            for k, v in build_plan.files.items()
                        )
                        old_build_plan_hash = hash_build_plan(old_build_plan_files)
                        if old_build_plan_hash == build_plan_hash and exists(
                                path.join(previous_build_dir, 'extra_files.pickle')):
                            needs_rebuild = False
                    except FileNotFoundError as e:
                        warn("something went wrong while determining if a rebuild is nescessary :(. "
                             "Rebuilding unconditionally ...\n" + str(e))

                if needs_rebuild:
                    build_subdir = dir_basename + datetime.now().strftime("__%d_%b_%Y__%H_%M_%S")
                    build_path = path.join("build", build_subdir)
                    build_plan.execute_local(build_path)
                    with open(path.join(build_path, 'extra_files.pickle'), 'wb') as f:
                        pickle.dump(self.platform.extra_files, f)

        if self.args.program:
            previous_build_dir = get_previous_build_dir(dir_basename)
            with open(path.join(previous_build_dir, 'extra_files.pickle'), 'rb') as f:
                self.platform.extra_files = pickle.load(f)
            cwd = os.getcwd()
            try:
                os.chdir(previous_build_dir)
                self.platform.toolchain_program(LocalBuildProducts(os.getcwd()), name=name)
            finally:
                os.chdir(cwd)

        if not (self.args.program or self.args.build or self.args.elaborate):
            print("no action specified")
            self.parser.print_help()


cli = Cli
