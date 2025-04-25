import inspect
import subprocess
import textwrap
from typing import Iterable
from pathlib import Path

from amaranth import Fragment, ValueCastable, Value
from amaranth._toolchain import require_tool
from amaranth.back import rtlil
from shutil import rmtree

from naps.data_structure import Bundle

__all__ = ["assert_formal", "FormalPlatform"]


class FormalPlatform:
    pass

def get_artifacts_location():
    functions = []
    test_class = None
    caller_path = ""
    stack = inspect.stack()
    for frame in stack[2:]:
        if "unittest" in frame.filename:
            filename = "__".join(reversed(functions))
            if test_class:
                filename = f'{test_class}__{filename}'
            break
        functions.append(frame.function)
        try:
            test_class = frame.frame.f_locals['self'].__class__.__name__
        except:
            pass
        caller_path = frame.filename

    target_dir = Path(caller_path).parent / ".sim_results"
    target_dir.mkdir(exist_ok=True)
    if (target_dir / filename).exists():
        rmtree(target_dir / filename)
    return target_dir, filename

def assert_formal(spec, mode="bmc", depth=1, submodules=()):
    assert mode in ["bmc", "cover"]

    target_dir, filename = get_artifacts_location()
    import sys
    print(target_dir, filename, file=sys.stderr)
    spec._MustUse__used = True

    spec_module = spec.elaborate(FormalPlatform)
    for injected in submodules:
        spec_module.submodules += injected

    def flat_entry(entry):
        if isinstance(entry, Bundle):
            res = []
            for sig in entry.signals:
                if isinstance(sig, Bundle):
                    res += flat_entry(sig)
                else:
                    res.append(sig)
            return res
        elif isinstance(entry, ValueCastable):
            return [Value.cast(entry)]
        elif isinstance(entry, (list, tuple)):
            ports = []
            for e in entry:
                print(e, type(entry), file=sys.stderr)
                ports += flat_entry(e)
            return ports
        else:
            return []
    

    ports = flat_entry(list(spec.__dict__.values()))
    print(ports, file=sys.stderr)

    config = textwrap.dedent(f"""\
        [options]
        mode {mode}
        depth {depth}
        wait on
        [engines]
        smtbmc
        [script]
        read_rtlil top.il
        prep
        [file top.il]
        {rtlil.convert(spec_module, ports=ports)}
    """)
    with subprocess.Popen([require_tool("sby"), "-f", "-d", filename], cwd=str(target_dir),
                          universal_newlines=True,
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE) as proc:
        stdout, stderr = proc.communicate(config)
        if proc.returncode != 0:
            assert False, "Formal verification failed:\n" + stdout + "\n\n" + f"vcd: {str(target_dir / filename)}/engine_0/trace.vcd"
