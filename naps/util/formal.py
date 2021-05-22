import inspect
import subprocess
import textwrap
from pathlib import Path

from nmigen import Fragment
from nmigen._toolchain import require_tool
from nmigen.back import rtlil
from shutil import rmtree

__all__ = ["assert_formal", "FormalPlatform"]


class FormalPlatform:
    pass


def assert_formal(spec, mode="bmc", depth=1):
    functions = []
    test_class = None
    caller_path = ""
    stack = inspect.stack()
    for frame in stack[1:]:
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

    if mode == "hybrid":
        # A mix of BMC and k-induction, as per personal communication with Claire Wolf.
        script = "setattr -unset init w:* a:nmigen.sample_reg %d"
        mode = "bmc"
    else:
        script = ""

    config = textwrap.dedent("""\
        [options]
        mode {mode}
        depth {depth}
        wait on
        [engines]
        smtbmc
        [script]
        read_ilang top.il
        prep
        {script}
        [file top.il]
        {rtlil}
    """).format(
        mode=mode,
        depth=depth,
        script=script,
        rtlil=rtlil.convert(Fragment.get(spec, platform=FormalPlatform))
    )
    with subprocess.Popen([require_tool("sby"), "-f", "-d", filename], cwd=str(target_dir),
                          universal_newlines=True,
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE) as proc:
        stdout, stderr = proc.communicate(config)
        if proc.returncode != 0:
            assert False, "Formal verification failed:\n" + stdout + "\n\n" + f"vcd: {str(target_dir / filename)}/engine_0/trace.vcd"
