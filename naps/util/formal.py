import inspect
import subprocess
import textwrap
from pathlib import Path

from amaranth import Fragment, ValueCastable, Value, Module
from amaranth.lib import wiring
from amaranth._toolchain import require_tool
from amaranth.back import rtlil
from amaranth.lib.wiring import Component, In, Out
from sphinx.ext.viewcode import env_merge_info

from naps.util.amaranth_private import PortDirection
from shutil import rmtree

__all__ = ["FormalPlatform"]

class FormalPlatform:
    def __init__(self):
        self._ports = []

    def request_port(self, signature):
        self._ports.append(interface := wiring.Signature({ "port": signature }).create(path=[str(len(self._ports))]).port)
        return interface

    def _build_toplevel_component(self, m):
        frag = Fragment.get(m, self)
        frag.signature = wiring.Signature({
            f"i_am_very_public__port_{i}": Out(p.signature) for i, p in enumerate(self._ports)
        })
        for i, p in enumerate(self._ports):
            setattr(frag, f"i_am_very_public__port_{i}", p)

        return frag

    def run_formal(self, m: Module, mode="bmc", depth=1):
        assert mode in ["bmc", "cover"]

        target_dir, filename = self._get_artifacts_location()
        import sys
        print(target_dir, filename, file=sys.stderr)
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
            {rtlil.convert(self._build_toplevel_component(m), platform=self)}
        """)
        with subprocess.Popen([require_tool("sby"), "-f", "-d", filename], cwd=str(target_dir),
                              universal_newlines=True,
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE) as proc:
            stdout, stderr = proc.communicate(config)
            if proc.returncode != 0:
                assert False, "Formal verification failed:\n" + stdout + "\n\n" + f"vcd: {str(target_dir / filename)}/engine_0/trace.vcd"

    def _get_artifacts_location(self):
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

