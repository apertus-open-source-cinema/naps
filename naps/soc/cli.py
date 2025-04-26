import argparse
import datetime
import inspect
import sys
import os
import shlex
import hashlib
from pathlib import Path
from shutil import rmtree
from textwrap import indent
from datetime import timedelta

from amaranth import Fragment
from amaranth.vendor import LatticePlatform
from amaranth.build.run import LocalBuildProducts, BuildPlan

__all__ = ["cli"]

from . import FatbitstreamContext
from .soc_platform import SocPlatform, soc_platform_name
from .platform import JTAGSocPlatform, ZynqSocPlatform
from ..util import timer


def fragment_repr(original: Fragment):
    attrs_str = "\n"
    for attr in ['statements', 'attrs', 'generated']:
        attrs_str += f"{attr}={repr(getattr(original, attr))},\n"

    domains_str = "\n"
    for name, domain in original.domains.items():
        # TODO: this is not really sound because domains could be non local
        domains_str += f"{name}: {domain.name}\n"
    attrs_str += f"domains={{{indent(domains_str, '  ')}}},\n"

    children_str = "\n"
    for child, name, _src_loc in original.subfragments:
        children_str += f"[{name}, {fragment_repr(child)}]\n"
    attrs_str += f"children=[{indent(children_str, '  ')}],\n"

    return f"Fragment({indent(attrs_str, '  ')})"


def cli(top_class):
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--elaborate', help='Elaborates the experiment', action="store_true")
    parser.add_argument('-b', '--build', help='builds the gateware & assembles a fatbitstream; implies -e',
                        action="store_true")
    parser.add_argument('--force_cache', help='forces caching of the gateware even if it changed', action="store_true")
    parser.add_argument('--no_cache', help='forces caching of the gateware even if it changed', action="store_true")
    parser.add_argument('-p', '--program', help='programs the board; programs the last build if used without -b',
                        action="store_true")
    parser.add_argument('-r', '--run', help='run the pydriver shell after programming', action="store_true")
    parser.add_argument('-g', '--gc', help='oldest cached bitstream to keep', type=str, default="14d",
                        dest="gc_interval")

    platform_choices = {plat.__name__.replace("Platform", ""): plat for plat in top_class.runs_on}
    default = list(platform_choices.keys())[0] if len(platform_choices) == 1 else None
    parser.add_argument('-d', '--device', help='specify the device to build for', choices=platform_choices.keys(),
                        default=default, required=default is None)

    parser.add_argument('-s', '--soc', help='specifies the soc platform to build for')

    args = parser.parse_args()

    gc_age_string = args.gc_interval.strip()
    if gc_age_string[-1] == "d":
        gc_interval = timedelta(hours=int(gc_age_string[:-1]))
    elif gc_age_string[-1] == "m":
        gc_interval = timedelta(minutes=int(gc_age_string[:-1]))
    elif gc_age_string[-1] == "s":
        gc_interval = timedelta(seconds=int(gc_age_string[:-1]))
    elif gc_age_string[-1] == "w":
        gc_interval = timedelta(weeks=int(gc_age_string[:-1]))
    else:
        print(f"unable to parse gc interval {gc_age_string}")
    gc_cutoff = (datetime.datetime.now() - gc_interval).timestamp()

    if (build_dir := Path("build")).exists():
        for dir in build_dir.iterdir():
            gateware_dir = dir / "gateware"
            if gateware_dir.exists():
                cache_keys = sorted(
                    [
                        (cache_key, cache_key.stat().st_atime)
                        for e in gateware_dir.iterdir()
                        if e.is_dir() and (cache_key := (e / "cache_key.txt")).exists()
                    ],
                    key = lambda e: e[1],
                )
                for c in cache_keys[3:]:
                    if c[1] < gc_cutoff:
                        rmtree(c[0])

    hardware_platform = platform_choices[args.device]
    hardware_platform_args = {}
    platform = hardware_platform(**hardware_platform_args)

    if args.soc == "None" or args.soc == "Plain" or args.soc is None:
        pass
    else:
        socs = {"Zynq": ZynqSocPlatform, "JTAG": JTAGSocPlatform}
        if args.soc not in socs:
            print(f"{args.soc} is not a known SoC type")
            exit(-1)
        soc = socs[args.soc]
        if not soc.can_wrap(platform):
            print(f"{args.soc} cannot wrap platform {hardware_platform.__name__}")
            exit(-1)
        if hasattr(top_class, "soc_platform") and top_class.soc_platform != soc:
            print(f"applet needs {top_class.soc_platform.__name__}")
            exit(-1)
        platform = soc(platform)
    
    caller_file = Path(inspect.stack()[1].filename)
    name = caller_file.stem
    build_dir = "build" / Path(f"{name}_{args.device}_{args.soc}")
    fatbitstream_name = build_dir / f"{name}.zip"

    if not (args.program or args.build or args.elaborate or args.run):
        print("no action specified")
        parser.print_help(sys.stderr)
        exit(-1)

    if args.elaborate or args.build:
        timer.start_task("elaboration")
        if isinstance(platform, SocPlatform):
            elaborated = platform.prepare_soc(top_class())
        else:
            elaborated = Fragment.get(top_class(), platform)

    timer.end_task()

    if args.build:
        needs_rebuild = True
        elaborated_repr = fragment_repr(elaborated)

        cache_hash = hashlib.sha256(elaborated_repr.encode()).hexdigest()

        gateware_build_dir = build_dir / "gateware" / cache_hash
        cache_key_path = gateware_build_dir / "cache_key.txt"

        if cache_key_path.exists():
            old_repr = cache_key_path.read_text()
            if args.force_cache:
                print("not rebuilding gateware because of --force_cache")
                needs_rebuild = False
            else:
                if old_repr == elaborated_repr:
                    print("\n### skipping build - gateware build is up to date")
                    needs_rebuild = False
                else:
                    print("gateware changed. rebuilding...")
        else:
            print("no previous build. rebuilding...")

        if args.no_cache:
            needs_rebuild = True

        if needs_rebuild:
            if gateware_build_dir.exists():
                rmtree(gateware_build_dir)

            timer.start_task("platform.prepare (including rtlil generation & yosys verilog generation)")
            build_plan: BuildPlan = platform.build(
                elaborated,
                name=name,
                do_build=False,
            )

            # build the gateware
            timer.start_task("vendor toolchain build")
            
            if "NAPS_BUILD_DOCKER_IMAGE" in os.environ:
                docker_image = os.environ["NAPS_BUILD_DOCKER_IMAGE"]
                docker_args = shlex.split(os.environ["NAPS_BUILD_DOCKER_ARGS"])
                build_products = build_plan.execute_local_docker(
                    root=gateware_build_dir, image=docker_image, docker_args=docker_args
                )
            else:
                build_products = build_plan.execute_local(gateware_build_dir)                

            # we write the cache key file in the end also as a marking that the build was successful
            cache_key_path.write_text(elaborated_repr)
        else:
            build_products = LocalBuildProducts(gateware_build_dir)

        # we always rebuild the fatbitstream
        with open(fatbitstream_name, "wb") as f:
            fc = FatbitstreamContext.get(platform)
            if isinstance(platform, SocPlatform):
                fc.generate_fatbitstream(f, name, build_products)
        Path(fatbitstream_name).chmod(0o700)

    timer.end_task()

    if args.program or args.run:
        if not args.run:
            timer.start_task("program")
        else:
            print("\n### programming & running design")
        platform.program_fatbitstream(fatbitstream_name, run=args.run)

    timer.end_task()
