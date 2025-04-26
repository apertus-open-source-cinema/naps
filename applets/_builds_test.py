# this is not actually an applet but a helper to run all the applets with the test runner.
# you can probably ignore this file, but it is very handy to catch major breakages.

import subprocess
from importlib import import_module
from pathlib import Path
import unittest
import amaranth

from naps.soc.platform import JTAGSocPlatform, ZynqSocPlatform


for path in Path(__file__).parent.glob("**/*.py"):
    if path.stem.startswith("_"):  # exclude ourselves
        continue
    name = str(path.relative_to(Path(__file__).parent)).removesuffix(".py").replace("/", ".")

    vars()[name] = type(name, (unittest.TestCase,), {})
    module = import_module(name)
    for target in module.Top.runs_on:
        device = target.__name__.replace("Platform", "")

        for soc in [None, JTAGSocPlatform, ZynqSocPlatform]:
            hardware_platform = target()

            if hasattr(module.Top, "soc_platform") and module.Top.soc_platform != soc:
                continue

            if soc is None:
                soc_name = "Plain"
                soc_platform = hardware_platform
            else:
                soc_name = soc.__name__.replace("SocPlatform", "")
                if not soc.can_wrap(hardware_platform):
                    continue
                soc_platform = soc(hardware_platform)
            
            build = hardware_platform.toolchain == "Trellis"
            if amaranth.__version__ == "0.5.4":
                build = False  # TODO: remove, once https://github.com/amaranth-lang/amaranth/commit/7664a00f4d3033e353b2f3a00802abb7403c0b68 is released
            def make_run(path, device, soc_name, build):
                def run(self):
                    command = ['python', str(path), '-e', '--no_cache', '-d', device, '-s', soc_name]
                    if build:
                        command.append("-b")
                    print("running '{}'".format(' '.join(command)))
                    process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
                    stdout, stderr = process.communicate()
                    if process.returncode != 0:
                        self.fail("\n" + stdout.decode())
                return run
            setattr(vars()[name], f"test_{'build' if build else 'elaborate'}_for_{device}_{soc_name}", make_run(path, device, soc_name, build))

