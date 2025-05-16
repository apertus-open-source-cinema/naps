import inspect
import subprocess
import textwrap
import unittest
from pathlib import Path

from amaranth import Fragment, ValueCastable, Value, Module
from amaranth.lib import wiring, stream
from amaranth._toolchain import require_tool
from amaranth.back import rtlil
from amaranth.lib.wiring import Component, In, Out, FlippedInterface
from sphinx.ext.viewcode import env_merge_info

from naps.util.amaranth_private import PortDirection
from shutil import rmtree

__all__ = ["FormalPlatform"]

class FormalPlatform:
    def __init__(self):
        self._ports = []

    def request_port(self, signature: wiring.Signature | wiring.PureInterface | wiring.FlippedInterface):
        if hasattr(signature, "signature"):
            signature = Out(signature.signature)
        self._ports.append(interface := wiring.Signature({ "port": signature }).create(path=[str(len(self._ports))]).port)
        return wiring.flipped(interface)

    def _build_toplevel_component(self, m):
        frag = Fragment.get(m, self)
        frag.signature = wiring.Signature({
            f"port_{i}": Out(p.signature) for i, p in enumerate(self._ports)
        })
        for i, p in enumerate(self._ports):
            setattr(frag, f"port_{i}", p)

        return frag

    def run_formal(self, testsuite: unittest.TestCase, m: Module, depth=10):
        target_dir, filename = self._get_artifacts_location()
        import sys
        print(target_dir, filename, file=sys.stderr)
        rtlil_src = rtlil.convert(self._build_toplevel_component(m), platform=self)
        has_covers = 'FLAVOR "cover"' in rtlil_src
        has_asserts = 'FLAVOR "assert"' in rtlil_src
        todo_modes = [mode for mode, check in (("bmc", has_asserts), ("cover", has_covers)) if check]
        assert len(todo_modes) > 0, "no covers or asserts found"

        subtest = None
        for mode in todo_modes:
            if len(todo_modes) > 1:
                subtest = testsuite.subTest().__enter__()
            config = textwrap.dedent(f"""
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
                {rtlil_src}
            """)
            with subprocess.Popen([require_tool("sby"), "-f", "-d", filename], cwd=str(target_dir),
                                  universal_newlines=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE) as proc:
                stdout, stderr = proc.communicate(config)
                if proc.returncode != 0:
                    testsuite.fail("Formal verification failed:\n" + stdout + "\n\n" + f"vcd: {str(target_dir / filename)}/engine_0/trace.vcd")

            if subtest: subtest.__exit__()

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

