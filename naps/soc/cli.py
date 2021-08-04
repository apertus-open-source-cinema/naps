import argparse
import inspect
import sys
from pathlib import Path
from shutil import rmtree
from textwrap import indent

from nmigen import Fragment
from nmigen.build.run import LocalBuildProducts, BuildPlan

__all__ = ["cli"]

from . import FatbitstreamContext
from .soc_platform import soc_platform_name
from ..util import timer


def fragment_repr(original: Fragment):
    attrs_str = "\n"
    for attr in ['ports', 'drivers', 'statements', 'attrs', 'generated', 'flatten']:
        attrs_str += f"{attr}={repr(getattr(original, attr))},\n"

    domains_str = "\n"
    for name, domain in original.domains.items():
        # TODO: this is not really sound because domains could be non local
        domains_str += f"{name}: {domain.name}\n"
    attrs_str += f"domains={{{indent(domains_str, '  ')}}},\n"

    children_str = "\n"
    for child, name in original.subfragments:
        children_str += f"[{name}, {fragment_repr(child)}]\n"
    attrs_str += f"children=[{indent(children_str, '  ')}],\n"

    return f"Fragment({indent(attrs_str, '  ')})"


def cli(top_class, runs_on, possible_socs=(None,)):
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--elaborate', help='Elaborates the experiment', action="store_true")
    parser.add_argument('-b', '--build', help='builds the gateware & assembles a fatbitstream; implies -e', action="store_true")
    parser.add_argument('--force_cache', help='forces caching of the gateware even if it changed', action="store_true")
    parser.add_argument('-p', '--program', help='programs the board; programs the last build if used without -b', action="store_true")
    parser.add_argument('-r', '--run', help='run the pydriver shell after programming', action="store_true")

    platform_choices = {plat.__name__.replace("Platform", ""): plat for plat in runs_on}
    default = list(platform_choices.keys())[0] if len(platform_choices) == 1 else None
    parser.add_argument('-d', '--device', help='specify the device to build for', choices=platform_choices.keys(), default=default, required=default is None)

    default = None
    if len(possible_socs) == 1:
        default = soc_platform_name(possible_socs[0])

    parser.add_argument('-s', '--soc', help='specifies the soc platform to build for', choices=list(map(soc_platform_name, possible_socs)), default=default, required=default is None)

    args = parser.parse_args()

    hardware_platform = platform_choices[args.device]
    if args.soc != 'None':
        for soc in possible_socs:
            if soc_platform_name(soc) == args.soc:
                soc_platform = soc
                break
        platform = soc_platform(hardware_platform())
    else:
        platform = hardware_platform()
    top_class = top_class

    caller_file = Path(inspect.stack()[1].filename)
    name = caller_file.stem
    build_dir = "build" / Path(f"{name}_{args.device}_{args.soc}")
    gateware_build_dir = build_dir / "gateware"
    cache_key_path = build_dir / "cache_key.txt"
    cache_key_old_path = build_dir / "cache_key_old.txt"
    fatbitstream_name = build_dir / f"{name}.zip"

    if not (args.program or args.build or args.elaborate or args.run):
        print("no action specified")
        parser.print_help(sys.stderr)
        exit(-1)

    if args.elaborate or args.build:
        timer.start_task("elaboration")
        if args.soc != 'None':
            elaborated = platform.prepare_soc(top_class())
        else:
            elaborated = Fragment.get(top_class(), platform)

    timer.end_task()

    if args.build:
        needs_rebuild = True
        elaborated_repr = fragment_repr(elaborated)
        if cache_key_path.exists():
            old_repr = cache_key_path.read_text()
            if args.force_cache:
                print("not rebuilding gateware because of --force_cache")
                needs_rebuild = False
            else:
                if old_repr == elaborated_repr:
                    print("gateware build is up to date")
                    needs_rebuild = False
                else:
                    print("gateware changed. rebuilding...")
        else:
            print("no previous build. rebuilding...")

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
            build_products = build_plan.execute_local(gateware_build_dir)

            # we write the pickle file in the end also as a marking that the build was successful
            if cache_key_path.exists():
                cache_key_old_path.write_text(old_repr)
            cache_key_path.write_text(elaborated_repr)
        else:
            build_products = LocalBuildProducts(gateware_build_dir)

        # we always rebuild the fatbitstream
        with open(fatbitstream_name, "wb") as f:
            fc = FatbitstreamContext.get(platform)
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
