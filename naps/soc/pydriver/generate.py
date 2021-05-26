import re
from inspect import getsource
from pathlib import Path
from textwrap import indent, dedent

from nmigen import Signal
from nmigen.build import Platform

from .driver_items import DriverMethod, DriverData
from ..fatbitstream import FatbitstreamContext
from ..memorymap import MemoryMap
from ..tracing_elaborate import ElaboratableSames
from ...util.py_serialize import py_serialize


def gen_hardware_proxy_python_code(mmap: MemoryMap, name="design", superclass="", top=True) -> str:
    name = name.lower()
    class_name = ("_" if not top else "") + name.capitalize()
    to_return = "class {}({}):\n".format(class_name, superclass)
    for row in mmap.direct_children:
        address = mmap.own_offset.translate(row.address)
        to_return += indent(
            f"{row.name} = {'Value' if isinstance(row.obj, Signal) else 'Blob'}(0x{address.address:02x}, {address.bit_offset}, {address.bit_len})\n",
            "    "
        )
    init_function_seen = False
    for name, item in mmap.driver_items.items():
        if isinstance(item, DriverMethod):
            print(item.function)
            function_body = dedent(getsource(item.function))
            function_body_without_decorator = re.sub("^@.*$", "", function_body, flags=re.MULTILINE).strip()
            function_string = ("@property\n" if item.is_property else "") + function_body_without_decorator
            to_return += indent("\n" + function_string + "\n", "    ")
            if item.is_init:
                assert not init_function_seen, "only one function can be driver_init()"
                init_function_seen = True
                to_return += indent("\n" + f"init_function = {item.function.__name__}" + "\n\n", "    ")

        elif isinstance(item, DriverData):
            to_return += indent(f"\n{name} = {py_serialize(item.data)}\n", "    ")
        else:
            raise TypeError("Unknown driver item type")

    for row in mmap.subranges:
        to_return += indent(gen_hardware_proxy_python_code(row.obj, row.name, superclass=superclass, top=False), "    ")
    return to_return


def generate_pydriver(top_memorymap, memory_accessor):
    pycode = "# pydriver hardware access file"
    pycode += "\n\n## HARDWARE PROXY STATIC: ###\n"
    pycode += (Path(__file__).parent / "hardware_proxy.py").read_text()
    pycode += "\n\n## HARDWARE PROXY DYNAMIC: ###\n"
    pycode += gen_hardware_proxy_python_code(top_memorymap, superclass="HardwareProxy")
    pycode += "\n\n## MEMORY ACCESSOR: ###\n"
    pycode += memory_accessor
    pycode += "\n\n## INTERACTIVE SHELL: ###\n"
    pycode += (Path(__file__).parent / "interactive.py").read_text()
    return pycode


def pydriver_hook(platform: Platform, top_fragment, sames: ElaboratableSames):
    if hasattr(platform, "pydriver_memory_accessor"):
        memorymap = top_fragment.memorymap
        pydriver = generate_pydriver(memorymap, platform.pydriver_memory_accessor)
        fc = FatbitstreamContext.get(platform)
        fc.self_extracting_blobs["pydriver.py"] = pydriver
